import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mega_completion import evaluate
from mega_hooks import handle
from mega_outcomes import validate_acceptance, runtime_status, receipt_path
from mega_task import register, event
from mega_store import atomic_json, digest, read_json


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name); self.root = self.cwd/'.mega'
        env = patch.dict(os.environ, MEGA_BINDINGS_DIR=str(self.cwd/'bindings'))
        env.start(); self.addCleanup(env.stop)
        self.plan = self.cwd/'PLAN.md'; self.plan.write_text('### Subphase 1.1: Requested outcome\n')
        self.source = self.cwd/'source.txt'; self.source.write_text('real source')
        self.report = self.cwd/'report.json'

    def policy(self, kind='json'):
        check = dict(kind=kind, description='requested outcome, not its proxy', path=str(self.report), inputs=[str(self.source)])
        if kind == 'json': check.update(pointer=['unrouted'], equals=0)
        return {'1.1':[check]}

    def task(self, policy=None):
        register(self.root, 't', self.plan, 'finish until X', session='parent', acceptance=policy)

    def report_value(self, **changes):
        row = dict(unrouted=0, inputs={str(self.source):digest(self.source)})
        row.update(changes); atomic_json(self.report, row)

    def proof(self, paths=None):
        artifacts = {str(p):digest(p) for p in (paths or [self.source,self.report])}
        refs = [event(self.root,'t','proof','1.1',proof_kind=k,exit_code=0,artifacts=artifacts)['event_id'] for k in ('test','readback')]
        event(self.root,'t','done','1.1',proof_ids=refs)

    def hook(self, name, **fields):
        return handle(dict(session_id='parent',hook_event_name=name,cwd=str(self.cwd),**fields))

    def test_pcb_proxy_proofs_cannot_certify_723_unrouted(self):
        self.task(self.policy()); self.report_value(unrouted=723); self.proof()
        result = evaluate(self.root,'t',require_outcomes=True)
        self.assertEqual(result['verdict'],'continue')
        self.assertIn('723',str(result['outcome_failures']))
        self.assertEqual(self.hook('Stop')['decision'],'block')
        self.report_value(); self.proof()
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'complete')

    def test_website_rejected_or_self_review_cannot_certify_quality(self):
        self.task(self.policy('review'))
        for reviewer,verdict in [('other','reject'),('parent','pass'),('', 'pass')]:
            self.report_value(reviewer_session_id=reviewer,verdict=verdict,rationale='reviewed screenshots over time')
            self.proof(); self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'continue')
        self.report_value(reviewer_session_id='independent-verifier',verdict='pass',rationale='Compared timed screenshots and buyer messaging against requested criteria')
        self.proof(); self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'complete')

    def test_missing_policy_is_not_certified_by_public_boundaries(self):
        self.task(); self.report_value(); self.proof()
        self.assertEqual(evaluate(self.root,'t')['assurance'],'artifact-only')
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'continue')
        self.assertEqual(self.hook('Stop')['decision'],'block')
        cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/mega_task.py'),'--root',str(self.root),'evaluate','--id','t']
        self.assertEqual(subprocess.run(cmd,capture_output=True,text=True).returncode,1)

    def test_stale_or_uncovered_inputs_and_report_cannot_pass(self):
        self.task(self.policy()); self.report_value(); self.proof([self.report])
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'continue')
        self.proof(); self.source.write_text('changed'); self.proof()
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'continue')
        self.report_value(); self.proof()
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'complete')

    def test_boolean_zero_and_malformed_outcomes_rejected(self):
        self.task(self.policy()); self.report_value(unrouted=False); self.proof()
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'continue')
        for bad in ({}, {'1.1':[]}, {'1.1':[{'kind':'shell'}]}, {'1.1':[dict(self.policy()['1.1'][0],inputs='source')]}):
            with self.assertRaises(ValueError): validate_acceptance(bad,['1.1'])

    def test_explicit_resume_clears_completion_pause_without_edit_permissions(self):
        self.task(self.policy())
        for prompt in ('keep going man','keep goin','continue','execute','solve it then'):
            self.hook('Interrupt'); self.hook('UserPromptSubmit',prompt=prompt)
            state=read_json(self.cwd/'bindings/parent.json')
            self.assertFalse(state['completion_control']['paused'])
            self.assertFalse(state['status_turn'])
            self.assertEqual(read_json(self.root/'tasks/t.json')['status'],'active')

    def test_explicit_outcomes_can_pass_without_automatic_hooks(self):
        self.task(self.policy()); self.report_value(); self.proof()
        script=Path(__file__).resolve().parents[1]/'scripts/mega_state.py'
        cmd=[sys.executable,str(script),'final-gate','--plan',str(self.plan),
             '--task','t','--root',str(self.root),'--verdict','done']
        result=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        result=subprocess.run(cmd+['--require-native-runtime'],capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('hook invocation is unverified',result.stdout)

    def test_hook_messages_do_not_silently_rewrite_acceptance(self):
        self.task(self.policy()); self.report_value(); self.proof()
        self.hook('UserPromptSubmit',prompt='what is the status?')
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'complete')
        self.hook('UserPromptSubmit',prompt='You dropped before it was done; not acceptable')
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'complete')
        event(self.root,'t','reopen','1.1',reason='Explicit reviewer rejection')
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'continue')

    def test_missing_receipts_not_success_and_early_returns_are_audited(self):
        self.assertFalse(runtime_status('parent')['verified']); self.task(self.policy())
        self.hook('UserPromptSubmit',prompt='what is the status?'); self.hook('PreToolUse',tool_name='exec_command',tool_input={'cmd':'pwd'})
        self.assertFalse(runtime_status('parent')['verified']); self.assertEqual(self.hook('Stop'),{})
        self.assertTrue(runtime_status('parent')['verified'])
        rows=[json.loads(l) for l in receipt_path('parent').read_text().splitlines()]
        self.assertTrue(all(row['policy']=='completion-retry-with-user-unlock' for row in rows))
        for row in rows: row['handler_revision']='old'
        receipt_path('parent').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        self.assertFalse(runtime_status('parent')['verified'])

    def test_wrapped_continuation_preserves_review_scope_and_goal(self):
        self.task(self.policy()); self.hook('UserPromptSubmit',prompt='what is the status?')
        self.hook('UserPromptSubmit',prompt='<hook_prompt hook_run_id="x">Megaskill continuation: execute obligation 1.1</hook_prompt>')
        self.assertFalse(read_json(self.cwd/'bindings/parent.json')['status_turn'])
        self.assertEqual(read_json(self.cwd/'bindings/parent.json')['task_id'], 't')

    def test_custom_hook_does_not_add_a_shell_permission_system(self):
        self.task(self.policy())
        result=self.hook('PreToolUse',tool_name='functions.exec_command',tool_input={'cmd':'git push origin branch'})
        self.assertEqual(result,{})

    def test_new_task_cannot_silently_replace_unfinished_whole_goal(self):
        self.task(self.policy())
        with self.assertRaisesRegex(ValueError, 'unfinished original goal'):
            register(self.root,'slice',self.plan,'only the homepage',session='parent',acceptance=self.policy())
        self.assertFalse((self.root/'tasks/slice.json').exists())
        register(self.root,'slice',self.plan,'only the homepage',session='parent',acceptance=self.policy(),replace_authority='User explicitly replaced the entire website task with homepage only')
        self.assertEqual(read_json(self.cwd/'bindings/parent.json')['replaced_goal'],'finish until X')

    def test_mixed_question_and_execution_is_not_status_only(self):
        self.task(self.policy()); self.report_value(unrouted=723); self.proof()
        self.hook('UserPromptSubmit',prompt='Can you check the output and fix it, continue until it matches exactly?')
        self.assertFalse(read_json(self.cwd/'bindings/parent.json')['status_turn'])
        self.assertEqual(self.hook('Stop')['decision'],'block')

    def test_rebound_executor_cannot_self_review(self):
        from mega_task import bind
        self.task(self.policy('review')); bind(self.root,'t','new-executor')
        self.report_value(reviewer_session_id='new-executor',verdict='pass',rationale='I inspected my own work')
        self.proof(); self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'continue')

    def test_symlink_path_aliases_match_proof_and_report_inputs(self):
        alias = self.cwd/'alias'; alias.symlink_to(self.cwd, target_is_directory=True)
        policy=self.policy(); policy['1.1'][0]['path']=str(alias/self.report.name)
        policy['1.1'][0]['inputs']=[str(alias/self.source.name)]
        self.task(policy); self.report_value(); self.proof()
        self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'complete')

    def test_runtime_receipts_cannot_certify_another_bound_goal(self):
        self.task(self.policy()); self.hook('UserPromptSubmit',prompt='what is the status?')
        self.hook('PreToolUse',tool_name='exec_command',tool_input={'cmd':'pwd'}); self.hook('Stop')
        self.assertTrue(runtime_status('parent',task_id='t',root=self.root)['verified'])
        self.assertFalse(runtime_status('parent',task_id='different',root=self.root)['verified'])
        self.assertFalse(runtime_status('parent',task_id='t',root=self.cwd/'other')['verified'])

    def test_explicit_read_only_and_rejection_do_not_authorize_execution(self):
        self.task(self.policy())
        for prompt in ('Please review the current changes only. Do not execute or fix anything.',
                       'Review only: this is not acceptable; report defects, do not fix.',
                       'Continue reviewing only; do not implement or fix anything.'):
            response=self.hook('UserPromptSubmit',prompt=prompt)
            self.assertFalse(read_json(self.cwd/'bindings/parent.json')['status_turn'])
            self.assertEqual(response,{})
            self.assertEqual(self.hook('Stop'),{})

    def test_binding_changes_current_owner_and_keeps_executor_history(self):
        from mega_task import bind
        self.task(self.policy()); bind(self.root,'t','new-owner')
        task=read_json(self.root/'tasks/t.json')
        self.assertEqual(task['session_id'],'new-owner')
        self.assertEqual(set(task['executor_sessions']),{'parent','new-owner'})

    def test_executor_child_cannot_self_review_even_after_closure(self):
        from mega_agents import assign, close
        self.task(self.policy('review'))
        assign(self.root,'t','parent','child','executor','produce output',[str(self.source)],'check output')
        self.hook('SubagentStart',agent_id='child')
        self.report_value(reviewer_session_id='child',verdict='pass',rationale='I reviewed my own output')
        self.proof(); self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'continue')
        close(self.root,'t','parent','child',{'tool':'close_agent','arguments':{'target':'child'},'result':{'previous_status':{'completed':'fixture only'}}})
        self.proof(); self.assertEqual(evaluate(self.root,'t',require_outcomes=True)['verdict'],'continue')


if __name__ == '__main__': unittest.main()
