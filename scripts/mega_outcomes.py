"""Pinned, side-effect-free outcome assertions and per-session hook diagnostics."""
from datetime import datetime, timezone
from collections import deque
import hashlib
import json
from pathlib import Path
from mega_store import binding_root, digest, read_json, safe_id


def validate_acceptance(policy, ids):
    if not isinstance(policy, dict) or set(policy) != set(ids):
        raise ValueError('acceptance must cover every exact obligation ID')
    for checks in policy.values():
        if not isinstance(checks, list) or not checks:
            raise ValueError('each obligation requires nonempty outcome assertions')
        for check in checks:
            if not isinstance(check, dict) or check.get('kind') not in ('text', 'json', 'review'):
                raise ValueError('unknown outcome assertion kind')
            if not isinstance(check.get('description'), str) or not check['description'].strip():
                raise ValueError('outcome assertion requires the requested criterion')
            paths = [check.get('path')] + check.get('inputs', []) if isinstance(check.get('inputs', []), list) else []
            if not paths or any(not isinstance(p, str) or not Path(p).is_absolute() for p in paths):
                raise ValueError('outcome and input paths must be absolute')
            if check['kind'] in ('json', 'review') and not check.get('inputs'):
                raise ValueError('report assertions require their source inputs')
            if check['kind'] == 'text' and not isinstance(check.get('equals'), str):
                raise ValueError('text outcome requires exact expected text')
            if check['kind'] == 'json':
                pointer = check.get('pointer')
                if not isinstance(pointer, list) or not pointer or any(not isinstance(k, str) for k in pointer) or 'equals' not in check:
                    raise ValueError('JSON outcome requires a nonempty key path and expected value')
    return policy


def outcome_errors(task, oid, evidence):
    policy = task.get('acceptance')
    if not policy:
        return ['pin requested outcome assertions with mega_task acceptance before certification']
    validate_acceptance(policy, [o['id'] for o in task['obligations']])
    covered = {str(Path(p).resolve()) for receipt in evidence for p in receipt.get('artifacts', {})}
    errors = []
    for check in policy[oid]:
        label = check['description']
        try:
            paths = [check['path']] + check.get('inputs', [])
            if any(str(Path(p).resolve()) not in covered for p in paths):
                raise ValueError('proof must cover the outcome and all source inputs')
            path = Path(check['path'])
            if path.stat().st_size > 2_000_000:
                raise ValueError('outcome report exceeds 2 MB')
            if check['kind'] == 'text':
                if path.read_text() != check['equals']:
                    raise ValueError('actual text does not equal requested output')
                continue
            report = read_json(path)
            if check['kind'] == 'json':
                value = report
                for key in check['pointer']:
                    value = value[key]
                if type(value) is not type(check['equals']) or value != check['equals']:
                    raise ValueError(f'actual value {value!r} != required {check["equals"]!r}')
            else:
                reviewer = report.get('reviewer_session_id')
                executors = set(task.get('executor_sessions', [])) | {task.get('session_id')}
                from mega_agents import _read
                executors.update(a['agent_id'] for a in _read(Path(task['root']))['agents']
                                 if a.get('task_id') == task['task_id'] and
                                 (a.get('role') in ('executor', 'tester') or a.get('edit_set')))
                if report.get('verdict') != 'pass' or not isinstance(reviewer, str) or not reviewer.strip() or reviewer in executors:
                    raise ValueError('requires a passing review from someone other than the executor')
                if not isinstance(report.get('rationale'), str) or not report['rationale'].strip():
                    raise ValueError('review requires substantive rationale')
            snapshots = report.get('inputs', {})
            if not isinstance(snapshots, dict): raise ValueError('report input snapshots must be an object')
            snapshots = {str(Path(p).resolve()): h for p,h in snapshots.items() if isinstance(p,str) and Path(p).is_absolute()}
            if any(snapshots.get(str(Path(p).resolve())) != digest(p) for p in check.get('inputs', [])):
                raise ValueError('report/review does not describe current source inputs')
        except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
            errors.append(label + ': ' + str(exc))
    return errors


def handler_revision():
    names = ('mega_hooks.py', 'mega_outcomes.py', 'mega_completion.py', 'mega_task.py',
             'mega_store.py', 'mega_agents.py', 'mega_decision.py', 'mega_plan_check.py')
    snapshot = [(name, digest(Path(__file__).with_name(name))) for name in names]
    return hashlib.sha256(json.dumps(snapshot).encode()).hexdigest()


def receipt_path(session):
    return binding_root() / 'receipts' / (safe_id(session) + '.jsonl')


def runtime_status(session, max_age=900, task_id=None, root=None):
    """Missing invocation is unknown enforcement, never an empty successful audit."""
    path = receipt_path(session)
    binding = read_json(binding_root()/(safe_id(session)+'.json'), {})
    bound = isinstance(binding, dict) and binding.get('session_id') == session and bool(binding.get('task_id'))
    task_id = task_id or (binding.get('task_id') if bound else None)
    bound = bound and binding.get('task_id') == task_id
    if root is not None:
        bound = bound and Path(binding.get('root', '')).resolve() == Path(root).resolve()
    rows = []
    if path.exists():
        try:
            with path.open() as stream:
                rows = [json.loads(line) for line in deque(stream, maxlen=500) if line.strip()]
        except (OSError, ValueError):
            return {'verified': False, 'reason': 'malformed runtime receipts', 'session_id': session}
    now = datetime.now(timezone.utc)
    revision = handler_revision()
    valid = []
    for row in rows:
        try:
            age = (now - datetime.fromisoformat(row['timestamp'])).total_seconds()
            if row.get('session_id') == session and row.get('handler_revision') == revision and 0 <= age <= max_age:
                valid.append(row)
        except (TypeError, KeyError, ValueError):
            pass
    events = sorted({r.get('event') for r in valid if isinstance(r.get('event'), str)})
    scoped_events = {r.get('event') for r in valid if r.get('task_id') == task_id}
    invoked = bound and 'UserPromptSubmit' in events and any(e in scoped_events for e in ('PreToolUse', 'PostToolUse'))
    stop_observed = bound and 'Stop' in scoped_events
    verified = invoked and stop_observed
    return {'verified': verified, 'session_id': session, 'events': events,
            'task_id': task_id, 'binding_matches': bool(bound),
            'prompt_and_tools_observed': bool(invoked), 'stop_observed': bool(stop_observed),
            'reason': 'current prompt, tool and Stop handlers observed in this session' if verified else
            'current prompt/tool hook invocation is unverified; inspect native /hooks and host support before claiming enforcement',
            'receipt_file': str(path), 'handler_revision': revision}
