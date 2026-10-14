import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from mega_hooks import handle
from mega_task import register, event
from mega_store import digest, read_json


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.cwd=Path(self.tmp.name);self.root=self.cwd/'.mega';self.bind=self.cwd/'bindings'
        self.env=patch.dict(os.environ,MEGA_BINDINGS_DIR=str(self.bind));self.env.start();self.addCleanup(self.env.stop)
        self.plan=self.cwd/'PLAN.md';self.plan.write_text('### Subphase 1.1: Work\n')
        self.file=self.cwd/'out.txt';self.file.write_text('ok')
    def call(self,name,**args):
        return handle(dict(session_id='session-a',hook_event_name=name,cwd=str(self.cwd),**args))
    def activate(self):
        self.call('UserPromptSubmit',prompt='$megaskill implement the whole plan')
        register(self.root,'test',self.plan,'complete the whole goal',session='session-a')
    def test_incomplete_stop_continues_and_proved_stop_allows(self):
        self.activate();self.assertEqual(self.call('Stop')['decision'],'block')
        ids=[event(self.root,'test','proof','1.1',proof_kind=k,exit_code=0,artifacts={str(self.file):digest(self.file)})['event_id'] for k in ('test','readback')]
        event(self.root,'test','done','1.1',proof_ids=ids)
        self.assertNotIn('decision',self.call('Stop'))
    def test_unregistered_execution_and_plan_only(self):
        self.call('UserPromptSubmit',prompt='$megaskill implement it')
        self.assertEqual(self.call('Stop')['decision'],'block')
        self.call('UserPromptSubmit',prompt='$megaskill write a plan')
        self.assertEqual(self.call('Stop'),{})
    def test_interrupt_and_status_do_not_restart(self):
        self.activate();self.call('Interrupt');self.assertEqual(self.call('Stop'),{})
        self.call('UserPromptSubmit',prompt='resume');self.assertEqual(self.call('Stop')['decision'],'block')
        self.call('UserPromptSubmit',prompt='what is the status?');self.assertEqual(self.call('Stop'),{})
        self.assertEqual(read_json(self.bind/'session-a.json')['task_id'],'test')
    def test_loop_bounded_across_turns(self):
        self.activate()
        for i in range(3):self.assertEqual(self.call('Stop',turn_id=str(i))['decision'],'block')
        self.assertFalse(self.call('Stop',turn_id='4')['continue'])
    def test_internal_continuation_preserves_contract(self):
        self.activate();self.call('UserPromptSubmit',prompt='Megaskill continuation: execute obligation 1.1')
        self.assertEqual(read_json(self.bind/'session-a.json')['task_id'],'test')
    def test_no_false_activation_quoted_skill_or_unknown_session(self):
        self.assertEqual(self.call('Stop'),{})
        self.assertEqual(self.call('UserPromptSubmit',prompt='What does $megaskill do?'),{})
    def test_cwd_change_restore(self):
        self.activate();r=handle(dict(session_id='session-a',hook_event_name='SessionStart',cwd='/another'))
        self.assertIn(str(self.root),r['hookSpecificOutput']['additionalContext'])
    def test_pending_plan_patch_allowed_implementation_denied(self):
        self.call('UserPromptSubmit',prompt='$megaskill fix it')
        good=self.call('PreToolUse',tool_name='apply_patch',tool_input={'command':'*** Add File: PLAN.md\n+plan'})
        bad=self.call('PreToolUse',tool_name='apply_patch',tool_input={'command':'*** Add File: app.py\n+code'})
        self.assertEqual(good,{})
        self.assertEqual(bad['hookSpecificOutput']['permissionDecision'],'deny')

    def test_followup_keeps_original_task_and_review_mode(self):
        self.activate(); self.call('UserPromptSubmit',prompt='$megaskill finish the current task')
        self.assertEqual(read_json(self.bind/'session-a.json')['task_id'],'test')
        self.call('UserPromptSubmit',prompt='$megaskill review the plan to fix deployment')
        state=read_json(self.bind/'session-a.json')
        self.assertEqual(state['task_id'],'test');self.assertEqual(state['mode'],'execute')

    def test_polite_cancel_and_negated_execute(self):
        self.activate();self.call('UserPromptSubmit',prompt='Please cancel this task.')
        self.assertEqual(self.call('Stop'),{})
        self.call('UserPromptSubmit',prompt='$megaskill do not execute; only write a plan')
        state=read_json(self.bind/'session-a.json')
        self.assertEqual(state['mode'],'execute')
        self.assertTrue(state['status_turn'])

    def test_repeated_same_proof_does_not_reset_stall_count(self):
        self.activate()
        for i in range(4):
            event(self.root,'test','proof','1.1',proof_kind='test',exit_code=0,artifacts={str(self.file):digest(self.file)})
            out=self.call('Stop',turn_id=str(i))
        self.assertFalse(out['continue'])

    def test_corrupt_binding_reports_enforcement_failure(self):
        import subprocess
        self.activate();(self.bind/'session-a.json').write_text('{broken')
        r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/mega_hooks.py')],input=json.dumps(dict(session_id='session-a',hook_event_name='Stop',cwd=str(self.cwd))),capture_output=True,text=True)
        self.assertFalse(json.loads(r.stdout)['continue'])

    def test_explicit_execute_can_authorize_previously_planning_task(self):
        register(self.root,'test',self.plan,'plan first',mode='plan',session='session-a')
        self.call('UserPromptSubmit',prompt='$megaskill execute the plan now')
        self.assertEqual(read_json(self.bind/'session-a.json')['mode'],'execute')
        self.assertEqual(read_json(self.root/'tasks/test.json')['mode'],'execute')
        self.assertEqual(self.call('Stop')['decision'],'block')

    def test_empty_or_wrong_shape_binding_fails_explicitly(self):
        import subprocess
        self.activate()
        for value in (None, [], {}):
            (self.bind/'session-a.json').write_text(json.dumps(value))
            r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/mega_hooks.py')],input=json.dumps(dict(session_id='session-a',hook_event_name='Stop',cwd=str(self.cwd))),capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertFalse(json.loads(r.stdout)['continue'])

    def test_missing_binding_mode_fails_explicitly(self):
        import subprocess
        self.activate();p=self.bind/'session-a.json';state=read_json(p);del state['mode'];p.write_text(json.dumps(state))
        r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/mega_hooks.py')],input=json.dumps(dict(session_id='session-a',hook_event_name='Stop',cwd=str(self.cwd))),capture_output=True,text=True)
        self.assertFalse(json.loads(r.stdout)['continue'])

    def test_interrupt_revokes_task_command_authority(self):
        from mega_completion import load_contract
        self.activate(); self.call('Interrupt')
        with self.assertRaises(ValueError): load_contract(self.root,'test',executable=True)

    def test_child_binding_blocks_recursive_spawn(self):
        self.activate()
        self.call('SubagentStart',agent_id='child-a',agent_type='executor')
        out=handle(dict(session_id='child-a',hook_event_name='PreToolUse',tool_name='spawn_agent',cwd=str(self.cwd)))
        self.assertEqual(out['hookSpecificOutput']['permissionDecision'],'deny')
        self.assertEqual(read_json(self.bind/'child-a.json')['parent_session_id'],'session-a')
