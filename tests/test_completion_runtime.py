import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mega_task import register, event
from mega_completion import evaluate
from mega_store import digest, atomic_json, read_json, append_jsonl
from mega_plan_check import validate


class CompletionRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name); self.root = self.cwd / '.mega'
        self.plan = self.cwd / 'PLAN.md'
        self.plan.write_text('# Plan\n### Subphase 1.1: First\n### Subphase 1.10: Second\n')
        self.artifact = self.cwd / 'artifact.txt'; self.artifact.write_text('expected')
        register(self.root, 'one', self.plan, 'both artifacts')

    def prove(self, oid):
        proofs = [event(self.root, 'one', 'proof', oid, proof_kind=k, exit_code=0,
                        artifacts={str(self.artifact): digest(self.artifact)})['event_id'] for k in ('test','readback')]
        event(self.root, 'one', 'done', oid, proof_ids=proofs)
        return proofs

    def blocker(self, **changes):
        fields = dict(blocker_class='credentials', needs_external=True,
                      reason='vendor login denied', evidence='vendor returned 401',
                      resolution='supply authorized vendor credentials',
                      attempted_alternatives=['retried existing credentials; 401', 'checked local cache; unavailable'])
        fields.update(changes)
        return fields

    def cli(self, *args):
        script = Path(__file__).resolve().parents[1] / 'scripts/mega_task.py'
        return subprocess.run([sys.executable, '-B', str(script), '--root', str(self.root), *args],
                              cwd=self.cwd, capture_output=True, text=True)

    def rewrite_contract(self, **changes):
        path = self.root / 'tasks/one.json'
        task = read_json(path); task.update(changes); atomic_json(path, task)
        return task

    def test_exact_id_and_independent_work(self):
        self.prove('1.10')
        self.assertEqual(evaluate(self.root, 'one')['unmet'], ['1.1'])
        event(self.root, 'one', 'blocked', '1.1', **self.blocker())
        self.assertEqual(evaluate(self.root, 'one')['verdict'], 'blocked')

    def test_stale_artifact_and_later_failure(self):
        self.prove('1.1'); self.prove('1.10')
        self.assertEqual(evaluate(self.root,'one')['verdict'], 'complete')
        event(self.root,'one','failed','1.1')
        self.assertEqual(evaluate(self.root,'one')['unmet'], ['1.1'])
        self.prove('1.1'); self.artifact.write_text('changed')
        self.assertEqual(evaluate(self.root,'one')['verdict'], 'continue')

    def test_self_declared_done_and_partial_blocker(self):
        event(self.root,'one','done','1.1',proof_ids=[])
        event(self.root,'one','blocked','1.1',**self.blocker())
        self.assertEqual(evaluate(self.root,'one')['executable'], ['1.10'])
        event(self.root,'one','unblocked','1.1')
        self.assertEqual(evaluate(self.root,'one')['executable'], ['1.1','1.10'])

    def test_revision_requires_reconciliation(self):
        self.prove('1.1'); self.plan.write_text(self.plan.read_text()+'changed\n')
        self.assertEqual(evaluate(self.root,'one')['verdict'], 'invalid')

    def test_cross_task_proof_not_counted(self):
        register(self.root,'other',self.plan,'other goal')
        event(self.root,'other','done','1.1',proof_ids=[])
        self.assertEqual(evaluate(self.root,'one')['unmet'], ['1.1','1.10'])

    def test_empty_plan_and_invalid_id_rejected(self):
        self.plan.write_text('# Empty')
        with self.assertRaises(ValueError): register(self.root,'empty',self.plan,'empty')
        with self.assertRaises(ValueError): evaluate(self.root,'../escape')

    def test_cli_run_records_failed_command(self):
        script=Path(__file__).resolve().parents[1]/'scripts/mega_task.py'
        r=subprocess.run([sys.executable,str(script),'--root',str(self.root),'prove','--id','one',
                          '--obligation','1.1','--kind','test','--artifact',str(self.artifact),'--',sys.executable,'-c','raise SystemExit(3)'],capture_output=True,text=True)
        self.assertEqual(r.returncode,1,r.stderr)
        self.assertEqual(json.loads(r.stdout)['exit_code'],3)

    def test_cycles_not_mislabeled_blocked(self):
        from mega_store import atomic_json, read_json
        path=self.root/'tasks/one.json'; c=read_json(path)
        c['obligations'][0]['depends_on']=['1.10'];c['obligations'][1]['depends_on']=['1.1'];atomic_json(path,c)
        self.assertEqual(evaluate(self.root,'one')['verdict'],'invalid')

    def test_cli_authority_validated_before_command_side_effect(self):
        original = read_json(self.root / 'tasks/one.json')
        sentinel = self.cwd / 'SENTINEL'
        cases = [dict(mode=mode) for mode in ('plan', 'review', 'monitor')]
        cases += [dict(status=s) for s in ('paused', 'cancelled', 'invented')]
        cases += [dict(task_id='wrong'), dict(schema_version=True), dict(mode='invented'),
                  dict(root=str(self.cwd)), dict(obligations=[dict(id='1.1', proof_kinds=[], depends_on=[])])]
        for changes in cases:
            with self.subTest(changes=changes):
                atomic_json(self.root / 'tasks/one.json', dict(original, **changes))
                r = self.cli('prove', '--id', 'one', '--obligation', '1.1', '--kind', 'test',
                             '--artifact', str(self.artifact), '--', sys.executable, '-c',
                             'from pathlib import Path; Path("SENTINEL").touch()')
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertFalse(sentinel.exists())
        atomic_json(self.root / 'tasks/one.json', original)
        for task_id, oid in [('missing', '1.1'), ('one', '1'), ('one', '1.100')]:
            r = self.cli('prove', '--id', task_id, '--obligation', oid, '--kind', 'test',
                         '--artifact', str(self.artifact), '--', sys.executable, '-c',
                         'from pathlib import Path; Path("SENTINEL").touch()')
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertFalse(sentinel.exists())
        self.plan.write_text(self.plan.read_text() + '\nchanged')
        r = self.cli('prove', '--id', 'one', '--obligation', '1.1', '--kind', 'test',
                     '--artifact', str(self.artifact), '--', sys.executable, '-c',
                     'from pathlib import Path; Path("SENTINEL").touch()')
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertFalse(sentinel.exists())
        self.assertFalse((self.root / 'tasks/one.events.jsonl').exists())

    def test_cli_proof_success_and_completion_control(self):
        for oid in ('1.1', '1.10'):
            refs = []
            for kind in ('test', 'readback'):
                r = self.cli('prove', '--id', 'one', '--obligation', oid, '--kind', kind,
                             '--artifact', str(self.artifact), '--', sys.executable, '-c',
                             'from pathlib import Path; assert Path("artifact.txt").read_text() == "expected"')
                self.assertEqual(r.returncode, 0, r.stderr)
                refs.append(json.loads(r.stdout)['event_id'])
            r = self.cli('done', '--id', 'one', '--obligation', oid, '--proof', refs[0], '--proof', refs[1])
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(evaluate(self.root, 'one')['verdict'], 'complete')

    def test_contract_schema_rejected_at_registration_and_evaluation(self):
        original = read_json(self.root / 'tasks/one.json')
        invalid_policies = [[], ['unknown'], ['test', 'test'], 'test', [None]]
        for kinds in invalid_policies:
            with self.subTest(kinds=kinds):
                obligations = [dict(id='1.1', proof_kinds=kinds, depends_on=[])]
                with self.assertRaises(ValueError):
                    register(self.root, 'bad', self.plan, 'goal', obligations=obligations)
                self.assertFalse((self.root / 'tasks/bad.json').exists())
                self.rewrite_contract(obligations=obligations)
                self.assertEqual(evaluate(self.root, 'one')['verdict'], 'invalid')
        changes = [dict(schema_version='1'), dict(schema_version=True), dict(status='invented'),
                   dict(mode='invented'), dict(goal=''), dict(obligations={}), dict(plan_hash=''),
                   dict(obligations=[dict(id='1.1', proof_kinds=['test'], depends_on=['missing'])])]
        for change in changes:
            atomic_json(self.root / 'tasks/one.json', dict(original, **change))
            self.assertEqual(evaluate(self.root, 'one')['verdict'], 'invalid')
        for mode in ('invented', ''):
            with self.assertRaises(ValueError): register(self.root, 'bad', self.plan, 'goal', mode=mode)
        with self.assertRaises(ValueError): register(self.root, 'bad', self.plan, '')

    def test_nonexecute_api_cannot_certify_execution(self):
        for mode in ('plan', 'review', 'monitor'):
            self.rewrite_contract(mode=mode)
            with self.assertRaises(ValueError): event(self.root, 'one', 'proof', '1.1', proof_kind='test')
            with self.assertRaises(ValueError): event(self.root, 'one', 'done', '1.1', proof_ids=[])
            self.assertEqual(evaluate(self.root, 'one')['verdict'], 'invalid')

    def test_failed_proof_invalidates_done_and_old_proof_replay(self):
        old = self.prove('1.1'); self.prove('1.10')
        r = self.cli('prove', '--id', 'one', '--obligation', '1.1', '--kind', 'test',
                     '--artifact', str(self.artifact), '--', sys.executable, '-c', 'raise SystemExit(5)')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(evaluate(self.root, 'one')['unmet'], ['1.1'])
        event(self.root, 'one', 'done', '1.1', proof_ids=old)
        self.assertEqual(evaluate(self.root, 'one')['unmet'], ['1.1'])
        self.prove('1.1')
        self.assertEqual(evaluate(self.root, 'one')['verdict'], 'complete')

    def test_reopen_edit_failed_require_proofs_after_boundary(self):
        self.prove('1.10')
        for kind in ('reopen', 'edit', 'failed'):
            with self.subTest(kind=kind):
                old = self.prove('1.1')
                event(self.root, 'one', kind, '1.1')
                event(self.root, 'one', 'done', '1.1', proof_ids=old)
                self.assertEqual(evaluate(self.root, 'one')['unmet'], ['1.1'])
                fresh = event(self.root, 'one', 'proof', '1.1', proof_kind='test', exit_code=0,
                              artifacts={str(self.artifact): digest(self.artifact)})['event_id']
                event(self.root, 'one', 'done', '1.1', proof_ids=[fresh, old[1]])
                self.assertEqual(evaluate(self.root, 'one')['unmet'], ['1.1'])
                self.prove('1.1')
                self.assertEqual(evaluate(self.root, 'one')['verdict'], 'complete')

    def test_every_proof_reference_must_be_exact_prior_scoped_receipt(self):
        own = self.prove('1.1'); other_oid = self.prove('1.10')
        register(self.root, 'other', self.plan, 'other goal')
        other_task = event(self.root, 'other', 'proof', '1.1', proof_kind='test', exit_code=0,
                           artifacts={str(self.artifact): digest(self.artifact)})['event_id']
        for refs in (own + ['nonexistent'], own + [other_task], own + [other_oid[0]],
                     own + [own[0]], 'not-a-list', [None], [[]]):
            with self.subTest(refs=refs):
                event(self.root, 'one', 'done', '1.1', proof_ids=refs)
                self.assertEqual(evaluate(self.root, 'one')['unmet'], ['1.1'])
        future = 'evt-future'
        event(self.root, 'one', 'done', '1.1', proof_ids=[future, own[1]])
        append_jsonl(self.root / 'tasks/one.events.jsonl', dict(event_id=future, task_id='one',
                     plan_hash=digest(self.plan), obligation_id='1.1', kind='proof', proof_kind='test',
                     exit_code=0, artifacts={str(self.artifact): digest(self.artifact)}))
        self.assertEqual(evaluate(self.root, 'one')['unmet'], ['1.1'])
        self.prove('1.1')
        self.assertEqual(evaluate(self.root, 'one')['verdict'], 'complete')

    def test_blocker_fields_required_before_record_and_during_evaluation(self):
        ledger = self.root / 'tasks/one.events.jsonl'
        invalid = [dict(blocker_class=None), dict(blocker_class='setup'), dict(needs_external='true'),
                   dict(needs_external=1), dict(needs_external=False), dict(attempted_alternatives=[]),
                   dict(attempted_alternatives='retried'), dict(attempted_alternatives=['']),
                   dict(evidence=True), dict(resolution=''), dict(reason='')]
        for changes in invalid:
            with self.subTest(changes=changes):
                fields = self.blocker(**changes)
                with self.assertRaises(ValueError): event(self.root, 'one', 'blocked', '1.1', **fields)
                before = ledger.read_text() if ledger.exists() else ''
                # Persisted legacy or forged rows must never certify an external stop.
                append_jsonl(ledger, dict(fields, event_id='evt-' + str(len(before)), task_id='one',
                             plan_hash=digest(self.plan), obligation_id='1.1', kind='blocked'))
                self.assertEqual(evaluate(self.root, 'one')['executable'], ['1.1', '1.10'])

    def test_setup_only_claims_rejected_but_external_setup_failure_allowed(self):
        for resolution in ('run pip install pytest', 'install pytest', 'set up Playwright', 'npm install', 'configure tooling'):
            with self.assertRaises(ValueError):
                event(self.root, 'one', 'blocked', '1.1', **self.blocker(
                    reason='tool not installed', evidence='pytest not installed; no installation attempted', resolution=resolution))
        for cls in ('credentials', 'approval', 'external_outage', 'platform', 'product_decision'):
            event(self.root, 'one', 'blocked', '1.1', **self.blocker(blocker_class=cls,
                  reason='setup cannot proceed', evidence='installation attempted; vendor access denied',
                  resolution='restore authorized access to installation service'))
            self.assertEqual(evaluate(self.root, 'one')['verdict'], 'continue')
            self.assertEqual(evaluate(self.root, 'one')['blocked'], ['1.1'])
        self.prove('1.10')
        self.assertEqual(evaluate(self.root, 'one')['verdict'], 'blocked')
        event(self.root, 'one', 'unblocked', '1.1')
        self.assertEqual(evaluate(self.root, 'one')['verdict'], 'continue')

    def test_cli_block_requires_class_and_attempt_and_records_external_semantics(self):
        args = ['block', '--id', 'one', '--obligation', '1.1', '--reason', 'vendor outage',
                '--evidence', 'vendor returned 503', '--resolution', 'vendor restores service']
        self.assertEqual(self.cli(*args).returncode, 2)
        self.assertEqual(self.cli(*args, '--blocker-class', 'external_outage').returncode, 2)
        r = self.cli(*args, '--blocker-class', 'external_outage', '--attempted', 'retry returned 503')
        self.assertEqual(r.returncode, 0, r.stderr)
        row = json.loads(r.stdout)
        self.assertIs(row['needs_external'], True)
        self.assertEqual(row['attempted_alternatives'], ['retry returned 503'])
        self.assertEqual(evaluate(self.root, 'one')['executable'], ['1.10'])

    def test_cli_registration_validates_plan_before_writing(self):
        r = self.cli('register', '--id', 'bad', '--plan', str(self.plan), '--goal', 'goal')
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn('invalid plan', r.stderr)
        self.assertFalse((self.root / 'tasks/bad.json').exists())
        fixture = Path(__file__).parent / 'fixtures/root-cause-gate-good.md'
        self.assertEqual(validate(fixture.read_text()), [])
        r = self.cli('register', '--id', 'valid', '--plan', str(fixture), '--goal', 'goal')
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn('--acceptance', r.stderr)
        import re
        acceptance = self.cwd/'acceptance.json'
        atomic_json(acceptance, {oid:[dict(kind='text', description='exact fixture bytes',
                    path=str(self.artifact), equals='expected')]
                    for oid in re.findall(r'^###\s+Subphase\s+(\d+(?:\.\d+)+):', fixture.read_text(), re.M)})
        r = self.cli('register', '--id', 'valid', '--plan', str(fixture), '--goal', 'goal', '--acceptance', str(acceptance))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(read_json(self.root / 'tasks/valid.json')['schema_version'], 1)
        policies = self.cwd / 'policies.json'
        for value in (None, {}, [], [dict(id='1.1', proof_kinds=[], depends_on=[])]):
            atomic_json(policies, value)
            r = self.cli('register', '--id', 'bad-schema', '--plan', str(fixture), '--goal', 'goal',
                         '--obligations', str(policies))
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertFalse((self.root / 'tasks/bad-schema.json').exists())
        with self.assertRaises(ValueError):
            register(self.root, 'callback', self.plan, 'goal', plan_validator=validate)
        self.assertFalse((self.root / 'tasks/callback.json').exists())

    def test_stop_decision_audit_does_not_grant_execution_or_require_fresh_plan(self):
        for mode, status in [('execute', 'paused'), ('review', 'active'), ('plan', 'cancelled')]:
            self.rewrite_contract(mode=mode, status=status)
            self.plan.write_text(self.plan.read_text() + '\nrevision')
            row = event(self.root, 'one', 'stop_decision', verdict='paused', reason='diagnostic', unmet=[])
            self.assertEqual(row['obligation_id'], '')
            self.assertIn('unmet', evaluate(self.root, 'one'))
            if status in ('paused', 'cancelled'):
                self.assertEqual(evaluate(self.root, 'one')['verdict'], 'paused')
            with self.assertRaises(ValueError): event(self.root, 'one', 'done', '1.1', proof_ids=[])
        with self.assertRaises(ValueError): event(self.root, 'one', 'arbitrary_audit')
