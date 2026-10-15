#!/usr/bin/env python3
"""Register scoped tasks and record verified acceptance outcomes."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4
from mega_store import atomic_json, append_jsonl, binding_root, digest, locked, read_json, safe_id
from mega_completion import evaluate, load_contract, validate_contract, validate_blocker, BLOCKER_CLASSES


def task_path(root, task_id):
    return Path(root) / 'tasks' / (safe_id(task_id) + '.json')


def register(root, task_id, plan, goal, mode='execute', session=None, obligations=None, plan_validator=None, acceptance=None, replace_authority=None):
    """API fixtures may omit plan_validator; the public CLI always supplies it."""
    root, plan = Path(root).resolve(), Path(plan).resolve()
    if not plan.is_file():
        raise ValueError('plan does not exist')
    if plan_validator is not None:
        errors = plan_validator(plan.read_text())
        if errors:
            raise ValueError('invalid plan: ' + '; '.join(errors))
    if obligations is None:
        ids = re.findall(r'^###\s+Subphase\s+(\d+(?:\.\d+)+):', plan.read_text(), re.M)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError('plan requires nonempty unique subphase IDs')
        obligations = [{'id': oid, 'proof_kinds': ['test', 'readback'], 'depends_on': []} for oid in ids]
    path = task_path(root, task_id)
    contract = {'schema_version': 1, 'task_id': safe_id(task_id), 'root': str(root),
                'plan': str(plan), 'plan_hash': digest(plan), 'goal': goal, 'mode': mode,
                'status': 'active', 'obligations': obligations, 'session_id': session}
    if acceptance is not None:
        contract['acceptance'] = acceptance
    validate_contract(contract, root, task_id)
    if session:
        check_binding_replacement(root, task_id, session, replace_authority)
    with locked(path.with_suffix('.lock')):
        if path.exists():
            raise ValueError('task already exists; reconcile explicitly')
        atomic_json(path, contract)
    if session:
        bind(root, task_id, session, replace_authority)
    return contract


def check_binding_replacement(root, task_id, session, authority=None):
    previous = read_json(binding_root() / (safe_id(session) + '.json'), {})
    if not isinstance(previous, dict): raise ValueError('invalid previous session binding')
    old_id = previous.get('task_id')
    if old_id and (old_id != task_id or previous.get('root') != str(Path(root).resolve())):
        result = evaluate(Path(previous['root']), old_id, require_outcomes=True)
        if result['verdict'] != 'complete' and not (isinstance(authority, str) and authority.strip()):
            raise ValueError('cannot replace unfinished original goal; provide explicit --replace-authority from the user')
    return previous


def bind(root, task_id, session, replace_authority=None):
    task = load_contract(root, task_id)
    path = binding_root() / (safe_id(session) + '.json')
    with locked(path.with_suffix('.lock')):
        previous = check_binding_replacement(root, task_id, session, replace_authority)
        contract_path = task_path(root, task_id)
        with locked(contract_path.with_suffix('.lock')):
            task = load_contract(root, task_id)
            task['executor_sessions'] = sorted(set(task.get('executor_sessions', [])) | {session})
            task['session_id'] = session
            atomic_json(contract_path, task)
        atomic_json(path, {'root': str(Path(root).resolve()), 'task_id': task_id,
                          'session_id': session, 'goal': task['goal'], 'mode': task['mode'],
                          'status_turn': False, 'pending': False, 'stall_count': 0,
                          'replaced_goal': previous.get('goal') if replace_authority else None,
                          'replacement_authority': replace_authority})


def event(root, task_id, kind, oid='', **fields):
    if kind == 'stop_decision':
        # Audit records must survive invalid/paused contracts without granting execution.
        task = read_json(task_path(root, task_id))
        if not isinstance(task, dict) or task.get('task_id') != task_id:
            raise ValueError('task missing or identity mismatch')
        if oid or fields.get('verdict') not in {'complete', 'blocked', 'paused', 'continue', 'invalid'}:
            raise ValueError('invalid stop decision audit')
        if not isinstance(fields.get('reason'), str) or not isinstance(fields.get('unmet'), list) or any(not isinstance(v, str) for v in fields['unmet']):
            raise ValueError('stop decision requires reason and unmet IDs')
        record = dict(fields, event_id='evt-' + uuid4().hex, task_id=task_id,
                      plan_hash=task.get('plan_hash'), obligation_id='', kind=kind)
        append_jsonl(Path(root) / 'tasks' / (task_id + '.events.jsonl'), record)
        return record
    task = load_contract(root, task_id, executable=True)
    if kind not in {'proof', 'done', 'reopen', 'failed', 'edit', 'blocked', 'unblocked'}:
        raise ValueError('unknown outcome event kind')
    if not oid:
        raise ValueError('outcome requires an exact obligation ID')
    if oid and oid not in {o['id'] for o in task['obligations']}:
        raise ValueError('unknown exact obligation ID')
    if kind == 'proof' and fields.get('proof_kind') not in next(o['proof_kinds'] for o in task['obligations'] if o['id'] == oid):
        raise ValueError('proof kind is outside obligation policy')
    if kind == 'blocked':
        validate_blocker(fields)
    record = dict(fields, event_id='evt-' + uuid4().hex, task_id=task_id,
                  plan_hash=task['plan_hash'], obligation_id=oid, kind=kind)
    append_jsonl(Path(root) / 'tasks' / (task_id + '.events.jsonl'), record)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.cwd() / '.mega')
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('register'); r.add_argument('--id', required=True); r.add_argument('--plan', required=True)
    r.add_argument('--goal', required=True); r.add_argument('--session'); r.add_argument('--mode', choices=['execute', 'plan', 'review', 'monitor'], default='execute')
    r.add_argument('--obligations', help='JSON file containing explicit proof policies/dependencies')
    r.add_argument('--acceptance', type=Path, help='JSON mapping each obligation to pinned outcome assertions; required for execution')
    r.add_argument('--replace-authority', help='explicit user authority to replace an unfinished bound goal')
    ac = sub.add_parser('acceptance'); ac.add_argument('--id', required=True)
    ac.add_argument('--file', type=Path, required=True); ac.add_argument('--authority', required=True); ac.add_argument('--reason', required=True)
    rt = sub.add_parser('runtime'); rt.add_argument('--id', required=True); rt.add_argument('--session')
    for name in ('show', 'evaluate', 'bind', 'pause', 'cancel', 'resume', 'reconcile'):
        c = sub.add_parser(name); c.add_argument('--id', required=True)
        if name == 'bind':
            c.add_argument('--session', required=True)
            c.add_argument('--replace-authority')
        if name in ('pause', 'cancel', 'resume', 'reconcile'): c.add_argument('--reason', required=True)
        if name == 'reconcile': c.add_argument('--authority', required=True, help='user authority for changed acceptance')
    proof = sub.add_parser('prove'); proof.add_argument('--id', required=True); proof.add_argument('--obligation', required=True)
    proof.add_argument('--kind', choices=['test', 'readback'], required=True); proof.add_argument('--artifact', action='append', required=True)
    proof.add_argument('command', nargs=argparse.REMAINDER)
    done = sub.add_parser('done'); done.add_argument('--id', required=True); done.add_argument('--obligation', required=True)
    done.add_argument('--proof', action='append', required=True)
    for name in ('reopen', 'block', 'unblock'):
        c = sub.add_parser(name); c.add_argument('--id', required=True); c.add_argument('--obligation', required=True); c.add_argument('--reason', required=True)
        if name == 'block':
            c.add_argument('--evidence', required=True); c.add_argument('--resolution', required=True)
            c.add_argument('--blocker-class', choices=sorted(BLOCKER_CLASSES), required=True)
            c.add_argument('--attempted', action='append', required=True, help='attempted alternative and observed result')
    a = p.parse_args(); root = a.root.resolve()
    try:
        if a.cmd == 'register':
            from mega_plan_check import validate
            obligations = read_json(Path(a.obligations)) if a.obligations else None
            if a.obligations and not isinstance(obligations, list):
                raise ValueError('explicit obligations must be a nonempty list')
            if a.mode == 'execute' and not a.acceptance:
                # Validate the plan first, retaining useful prerequisite diagnostics.
                errors = validate(Path(a.plan).read_text())
                if errors: raise ValueError('invalid plan: ' + '; '.join(errors))
                raise ValueError('execute registration requires --acceptance FILE with actual outcome assertions')
            if a.acceptance and not isinstance(read_json(a.acceptance), dict):
                raise ValueError('acceptance file must contain an outcome assertion object')
            out = register(root, a.id, a.plan, a.goal, a.mode, a.session, obligations, plan_validator=validate,
                           acceptance=read_json(a.acceptance) if a.acceptance else None, replace_authority=a.replace_authority)
        elif a.cmd == 'runtime':
            from mega_outcomes import runtime_status
            task = load_contract(root, a.id, check_plan=False)
            out = runtime_status(a.session or task.get('session_id') or '', task_id=a.id, root=root)
            print(json.dumps(out)); return 0 if out['verified'] else 1
        elif a.cmd == 'acceptance':
            from mega_outcomes import validate_acceptance
            if not a.authority.strip() or not a.reason.strip(): raise ValueError('acceptance revision requires authority and reason')
            path = task_path(root, a.id)
            with locked(path.with_suffix('.lock')):
                task = load_contract(root, a.id, executable=True)
                task['acceptance'] = validate_acceptance(read_json(a.file), [o['id'] for o in task['obligations']])
                task['acceptance_authority'] = a.authority; task['acceptance_reason'] = a.reason
                # Invalidate before changing policy; a crash cannot carry old completion forward.
                for obligation in task['obligations']:
                    event(root, a.id, 'edit', obligation['id'], reason='outcome acceptance revision: ' + a.reason)
                atomic_json(path, task)
            out = {'acceptance_updated': a.id, 'requires_fresh_proof': True}
        elif a.cmd == 'bind':
            bind(root, a.id, a.session, a.replace_authority); out = {'bound': a.session}
        elif a.cmd == 'evaluate':
            out = evaluate(root, a.id, require_outcomes=True); print(json.dumps(out)); return 0 if out['verdict'] in ('complete', 'blocked', 'paused') else 1
        elif a.cmd == 'show': out = read_json(task_path(root, a.id))
        elif a.cmd in ('pause', 'cancel', 'resume', 'reconcile'):
            path = task_path(root, a.id)
            with locked(path.with_suffix('.lock')):
                out = read_json(path)
                if not out: raise ValueError('task missing')
                if a.cmd == 'reconcile':
                    # No implicit proof carry-forward across changed plans.
                    ids = re.findall(r'^###\s+Subphase\s+(\d+(?:\.\d+)+):', Path(out['plan']).read_text(), re.M)
                    if not ids or len(ids) != len(set(ids)): raise ValueError('invalid revised plan')
                    out['plan_hash'] = digest(out['plan']); out['authority'] = a.authority
                    out['obligations'] = [{'id': oid, 'proof_kinds': ['test', 'readback'], 'depends_on': []} for oid in ids]
                    if 'acceptance' in out and set(out['acceptance']) != set(ids):
                        del out['acceptance']
                else: out['status'] = {'pause':'paused', 'cancel':'cancelled', 'resume':'active'}[a.cmd]
                out['lifecycle_reason'] = a.reason; atomic_json(path, out)
        elif a.cmd == 'prove':
            task = load_contract(root, a.id, executable=True)
            obligation = next((o for o in task['obligations'] if o['id'] == a.obligation), None)
            if obligation is None: raise ValueError('unknown exact obligation ID')
            if a.kind not in obligation['proof_kinds']: raise ValueError('proof kind is outside obligation policy')
            cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
            if not cmd: raise ValueError('proof requires a verification command after --')
            paths = [Path(raw).resolve() for raw in a.artifact]
            if not all(path.is_file() for path in paths): raise ValueError('proof artifact missing')
            before = {str(path): digest(path) for path in paths}
            result = subprocess.run(cmd, capture_output=True, text=True)
            after = {str(path): digest(path) for path in paths if path.is_file()}
            code = result.returncode if before == after else 1
            out = event(root, a.id, 'proof', a.obligation, proof_kind=a.kind, exit_code=code,
                        command=cmd, artifacts=after, output_hash=__import__('hashlib').sha256((result.stdout+result.stderr).encode()).hexdigest())
            print(json.dumps(out)); return 0 if code == 0 else 1
        elif a.cmd == 'done': out = event(root, a.id, 'done', a.obligation, proof_ids=a.proof)
        else:
            out = event(root, a.id, {'block':'blocked','unblock':'unblocked','reopen':'reopen'}[a.cmd], a.obligation,
                        reason=a.reason, evidence=getattr(a, 'evidence', None), resolution=getattr(a, 'resolution', None),
                        blocker_class=getattr(a, 'blocker_class', None), attempted_alternatives=getattr(a, 'attempted', None),
                        needs_external=a.cmd == 'block')
        print(json.dumps(out)); return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
