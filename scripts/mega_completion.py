"""Task-scoped completion evaluator used by CLI and lifecycle hooks."""
import json
from pathlib import Path
from mega_store import digest, read_json, safe_id


MODES = {'execute', 'plan', 'review', 'monitor'}
STATUSES = {'active', 'paused', 'cancelled'}
PROOF_KINDS = {'test', 'readback'}
BLOCKER_CLASSES = {'credentials', 'approval', 'external_outage', 'platform', 'product_decision'}


def nonempty_text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_contract(task, root, task_id):
    """Validate persisted contracts and new registrations with the same rules."""
    if not isinstance(task, dict) or type(task.get('schema_version')) is not int or task['schema_version'] != 1:
        raise ValueError('missing or unsupported task contract')
    if task.get('task_id') != task_id or not nonempty_text(task.get('root')) or not Path(task['root']).is_absolute() or Path(task['root']).resolve() != Path(root).resolve():
        raise ValueError('task/workspace identity mismatch')
    if not isinstance(task.get('mode'), str) or task['mode'] not in MODES or not isinstance(task.get('status'), str) or task['status'] not in STATUSES:
        raise ValueError('unknown task mode or lifecycle status')
    if not nonempty_text(task.get('goal')) or not nonempty_text(task.get('plan')) or not Path(task['plan']).is_absolute():
        raise ValueError('task requires a goal and absolute plan path')
    plan_hash = task.get('plan_hash')
    if not isinstance(plan_hash, str) or len(plan_hash) != 64 or any(c not in '0123456789abcdef' for c in plan_hash):
        raise ValueError('invalid plan hash')
    obligations = task.get('obligations')
    if not isinstance(obligations, list) or not obligations:
        raise ValueError('task has no acceptance obligations')
    graph = {}
    for obligation in obligations:
        if not isinstance(obligation, dict) or not nonempty_text(obligation.get('id')):
            raise ValueError('invalid obligation identity')
        oid = obligation['id']
        if oid in graph:
            raise ValueError('duplicate obligations')
        kinds, deps = obligation.get('proof_kinds'), obligation.get('depends_on', [])
        if not isinstance(kinds, list) or not kinds or any(not isinstance(k, str) or k not in PROOF_KINDS for k in kinds) or len(kinds) != len(set(kinds)):
            raise ValueError('nonempty known unique proof policy required')
        if not isinstance(deps, list) or any(not nonempty_text(d) for d in deps) or len(deps) != len(set(deps)):
            raise ValueError('invalid dependency references')
        graph[oid] = deps
    visited = set()
    def visit(node, stack):
        if node in stack or node not in graph:
            raise ValueError('unknown or cyclic dependency')
        if node in visited:
            return
        for dep in graph[node]:
            visit(dep, stack | {node})
        visited.add(node)
    for node in graph:
        visit(node, set())
    if 'acceptance' in task:
        from mega_outcomes import validate_acceptance
        validate_acceptance(task['acceptance'], graph)
    return task


def load_contract(root, task_id, executable=False, check_plan=True):
    task = validate_contract(read_json(Path(root) / 'tasks' / (safe_id(task_id) + '.json')), root, task_id)
    if executable and (task['mode'] != 'execute' or task['status'] != 'active'):
        raise ValueError('proof/outcome requires an active execute-mode task')
    if check_plan and (not Path(task['plan']).is_file() or digest(task['plan']) != task['plan_hash']):
        raise ValueError('plan revision changed; explicitly reconcile the contract')
    return task


def validate_blocker(fields):
    """External intervention is explicit; executable setup alone cannot stop work."""
    if not isinstance(fields.get('blocker_class'), str) or fields['blocker_class'] not in BLOCKER_CLASSES or fields.get('needs_external') is not True:
        raise ValueError('blocker requires an allowed external class and needs_external=true')
    if any(not nonempty_text(fields.get(k)) for k in ('reason', 'evidence', 'resolution')):
        raise ValueError('blocker requires reason, evidence and external resolution')
    attempts = fields.get('attempted_alternatives')
    if not isinstance(attempts, list) or not attempts or any(not nonempty_text(a) for a in attempts):
        raise ValueError('blocker requires attempted alternatives')
    # Recognize obvious setup resolutions, not arbitrary words embedded in evidence.
    import re
    resolution = fields['resolution'].lower().strip()
    resolution = re.sub(r'^(?:please\s+|kindly\s+|you\s+(?:can|should|must)\s+|(?:the\s+)?agent\s+(?:can|should|must)\s+)+', '', resolution)
    words = resolution.split()
    if words[:1] == ['run']:
        words = words[1:]
    setup = words[:1] in (['install'], ['configure'], ['setup']) or words[:2] == ['set', 'up']
    setup = setup or words[:2] in (['pip', 'install'], ['pip3', 'install'], ['npm', 'install'], ['brew', 'install'], ['apt', 'install'])
    setup = setup or words[:3] in (['python', '-m', 'pip'], ['python3', '-m', 'pip'])
    if setup:
        raise ValueError('install/setup is executable work, not an external resolution')


def evaluate(root, task_id, require_outcomes=False):
    root = Path(root).resolve()
    safe_id(task_id)
    try:
        task = load_contract(root, task_id, check_plan=False)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return {'verdict': 'invalid', 'reason': str(exc), 'unmet': []}
    if task['status'] in ('paused', 'cancelled'):
        return {'verdict': 'paused', 'reason': task.get('lifecycle_reason', task['status']), 'unmet': []}
    try:
        if not Path(task['plan']).is_file() or digest(task['plan']) != task['plan_hash']:
            raise ValueError('plan revision changed; explicitly reconcile the contract')
    except (ValueError, OSError) as exc:
        return {'verdict': 'invalid', 'reason': str(exc), 'unmet': []}
    if task['mode'] != 'execute':
        return {'verdict': 'invalid', 'reason': 'execution completion requires execute mode', 'unmet': []}
    obligations = task['obligations']
    ids = [o['id'] for o in obligations]
    events = []
    path = root / 'tasks' / (task_id + '.events.jsonl')
    if path.exists():
        try:
            events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        except (ValueError, TypeError):
            return {'verdict': 'invalid', 'reason': 'malformed task event ledger', 'unmet': ids}
    if any(not isinstance(e, dict) for e in events):
        return {'verdict': 'invalid', 'reason': 'event must be an object', 'unmet': ids}
    seen = set()
    for e in events:
        eid = e.get('event_id')
        if not nonempty_text(eid) or eid in seen:
            return {'verdict': 'invalid', 'reason': 'missing or duplicate event ID', 'unmet': ids}
        seen.add(eid)
    scoped = [e for e in events if e.get('task_id') == task_id and e.get('plan_hash') == task['plan_hash']]
    unmet, blockers, executable = [], [], []
    outcome_failures = {}
    complete = set()
    for obligation in obligations:
        oid = obligation['id']
        relevant = [e for e in scoped if e.get('obligation_id') == oid]
        boundary = max((i for i, e in enumerate(relevant) if e.get('kind') in ('reopen', 'failed', 'edit') or
                        (e.get('kind') == 'proof' and (type(e.get('exit_code')) is not int or e['exit_code'] != 0))), default=-1)
        done_index = max((i for i, e in enumerate(relevant) if e.get('kind') == 'done'), default=-1)
        latest = relevant[done_index] if done_index >= 0 else {}
        refs = latest.get('proof_ids', [])
        receipts = {e['event_id']: e for i, e in enumerate(relevant) if boundary < i < done_index and e.get('kind') == 'proof'}
        valid = done_index > boundary and isinstance(refs, list) and bool(refs)
        valid = valid and all(isinstance(eid, str) and eid in receipts for eid in refs) and len(refs) == len(set(refs))
        evidence = [receipts[eid] for eid in refs] if valid else []
        valid = valid and all(p.get('proof_kind') in obligation['proof_kinds'] for p in evidence)
        for proof in evidence:
            hashes = proof.get('artifacts', {})
            try:
                fresh = isinstance(hashes, dict) and bool(hashes) and all(isinstance(p, str) and Path(p).is_absolute() and Path(p).is_file() and digest(p) == h for p, h in hashes.items())
            except OSError:
                fresh = False
            valid = valid and fresh
        valid = valid and all(any(p.get('proof_kind') == kind for p in evidence) for kind in obligation['proof_kinds'])
        if require_outcomes or task.get('acceptance'):
            from mega_outcomes import outcome_errors
            failures = outcome_errors(task, oid, evidence)
            if failures:
                valid = False
                outcome_failures[oid] = failures
        if valid:
            complete.add(oid)
        else:
            unmet.append(oid)
    for obligation in obligations:
        oid = obligation['id']
        if oid in complete:
            continue
        relevant = [e for e in scoped if e.get('obligation_id') == oid and e.get('kind') in ('blocked', 'unblocked')]
        latest = relevant[-1] if relevant else {}
        try:
            validate_blocker(latest)
            blocked = latest.get('kind') == 'blocked'
        except (ValueError, TypeError):
            blocked = False
        if blocked:
            blockers.append(oid)
        elif all(dep in complete for dep in obligation.get('depends_on', [])):
            executable.append(oid)
    if not unmet:
        verdict, reason = 'complete', 'all acceptance obligations have current successful proof'
    elif executable:
        verdict, reason = 'continue', 'execute obligation ' + executable[0]
    elif blockers:
        verdict, reason = 'blocked', 'remaining obligations are externally blocked or depend on blocked work'
    else:
        verdict, reason = 'invalid', 'unmet dependencies without an executable obligation or active blocker'
    if outcome_failures and executable:
        reason += '; ' + outcome_failures.get(executable[0], ['refresh current proof'])[0]
    return {'verdict': verdict, 'reason': reason, 'unmet': unmet, 'executable': executable,
            'outcome_failures': outcome_failures,
            'assurance': 'outcome-checked' if task.get('acceptance') else 'artifact-only',
            'blocked': blockers, 'task_id': task_id, 'plan_hash': task['plan_hash']}
