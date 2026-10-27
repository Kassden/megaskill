#!/usr/bin/env python3
"""Completion retries with user-clearable pauses; never a tool permission gate."""
import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import sys

from mega_store import append_jsonl, atomic_json, binding_root, digest, locked, read_json, safe_id
from mega_outcomes import handler_revision, receipt_path
from mega_completion import evaluate


def state_for(payload):
    return binding_root() / (safe_id(payload.get('session_id', '')) + '.json')


def command_intent(prompt):
    """Recognize direct scheduling commands, never arbitrary mentions of review."""
    prompt = re.sub(r'^<hook_prompt\b[^>]*>(.*?)</hook_prompt>$', r'\1', prompt, flags=re.S).strip()
    if prompt.startswith('Megaskill continuation:'):
        return 'continuation'
    text = re.sub(r'```.*?```|(?m:^\s*>.*$)', '', prompt, flags=re.S)
    text = re.sub(r'"[^"\n]*"|(?<!\w)\'[^\'\n]*\'(?!\w)', '', text).strip().lower()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    text = re.sub(r'^(?:\$megaskill\s+|use megaskill\s+)', '', lines[0])
    lead = r'^(?:(?:please|ok|okay|yes|now|can you|could you)\s*[, :]*\s*)*'
    # Direct limits pause automatic completion only; they never deny editing tools.
    direct_limit = r'(?:do not|don.t|never)\s+(?:execute|implement|edit|fix|repair|continue)\b'
    review_request = r'(?:(?:continue|resume)\s+(?:the\s+)?)?(?:review(?:ing)?|audit(?:ing)?|inspect(?:ing)?)\b'
    for line in lines:
        if re.search(lead + r'(?:stop|cancel|pause)\b', line):
            return 'pause'
        if re.search(lead + direct_limit, line):
            return 'review'
        if re.search(lead + review_request, line) and re.search(r'\bonly\b|\bafter approval\b', line):
            return 'review'
        direct_request = re.search(lead + r'(?:continue|execute|resume|implement|review|audit|inspect)\b', line)
        if direct_request and re.search(r'(?:;|,\s*(?:but|and)?|\bbut)\s*(?:please\s+)?' + direct_limit, line):
            return 'review'
    mixed_execution = (re.search(lead + r'(?:check|review|audit|inspect)\b', text)
                       and re.search(r'\b(?:and|then)\s+(?:fix|repair|update|implement|execute)\b', text))
    if mixed_execution:
        return 'execute'
    if re.search(lead + r'(?:(?:continue|resume)\s+(?:the\s+)?)?(?:review(?:ing)?|audit(?:ing)?|inspect(?:ing)?)\b', text):
        return 'review'
    if re.search(lead + r'(?:stop|cancel|pause)\b', text):
        return 'pause'
    if re.search(lead + r'(?:continue|execute|resume|implement|go ahead|keep goin(?:g)?|solve it|finish it|unlock|remove\s+(?:(?:the|these|this|all)\s+)?restrictions?)\b', text):
        return 'execute'
    if re.search(lead + r'(?:what|why|how|show|tell|can you (?:check|tell)|write (?:a |the )?plan)\b', text):
        return 'checkpoint'
    return None


def user_control(payload, state, path):
    """Megaskill scheduling state is revocable by the user's next direct command."""
    action = command_intent(payload.get('prompt', ''))
    if action in (None, 'continuation') or state.get('is_child'):
        return {}
    saved = state.get('completion_control')
    control = dict(saved) if isinstance(saved, dict) else {}
    native_permission = payload.get('permission_mode', control.get('native_permission'))
    if action == 'execute':
        for key in ('authority', 'authority_conflict', 'conflict_notified', 'fingerprint',
                    'stop_verified_revision', 'error_count'):
            state.pop(key, None)
        state.update(mode='execute', status_turn=False, paused=False, stall_count=0)
        control = dict(paused=False, checkpoint=False, origin_turn_id=payload.get('turn_id'),
                       unchanged_attempts=0, reason='explicit-user-resume', native_permission=native_permission)
    else:
        control.update(paused=action in ('pause', 'review'), checkpoint=action == 'checkpoint',
                       origin_turn_id=payload.get('turn_id'), reason='user-' + action)
    state['completion_control'] = control
    atomic_json(path, state)
    if action != 'execute':
        return {}
    task_id, root = state.get('task_id'), state.get('root')
    if task_id and root:
        from mega_task import task_path
        task_file = task_path(Path(root), task_id)
        with locked(task_file.with_suffix('.lock')):
            task = read_json(task_file)
            if isinstance(task, dict):
                # Resume changes intent/lifecycle only, never plan hashes, proof or acceptance.
                task.update(mode='execute', status='active', lifecycle_reason='explicit user resume')
                atomic_json(task_file, task)
    return {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext':
            "Megaskill resume: the user explicitly requested execution. Megaskill's own earlier review/status "
            "scheduling hints and pauses are cleared for this session. Continue the current authorized goal; "
            "old Megaskill packets and binding flags are not permission boundaries. Other controlling "
            "instructions and native permissions still apply."}}


def completion_stop(payload, state, path):
    saved = state.get('completion_control')
    control = dict(saved) if isinstance(saved, dict) else {}
    native_permission = payload.get('permission_mode', control.get('native_permission'))
    if (state.get('is_child') or state.get('mode') != 'execute' or state.get('paused')
            or state.get('status_turn') or control.get('paused') or control.get('checkpoint')
            or native_permission not in (None, 'default', 'acceptEdits', 'dontAsk', 'bypassPermissions')
            or not state.get('task_id')):
        return {}
    root = Path(state['root']); task_id = state['task_id']
    result = evaluate(root, task_id, require_outcomes=True)
    from mega_agents import open_agents, list_agents
    children = [child for child in open_agents(root, task_id)
                if child.get('parent_session_id') == state['session_id']]
    if children and result['verdict'] != 'paused':
        result = dict(verdict='continue', reason='collect results and close owned agents: ' +
                      ', '.join(c['agent_id'] for c in children), unmet=['child-cleanup'])
    if result['verdict'] in ('complete', 'blocked', 'paused'):
        return {}
    events_path = root / 'tasks' / (task_id + '.events.jsonl')
    records = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()] if events_path.exists() else []
    def current_proof(row):
        artifacts = row.get('artifacts')
        try:
            return isinstance(artifacts, dict) and bool(artifacts) and all(
                isinstance(p, str) and Path(p).is_absolute() and Path(p).is_file() and digest(p) == expected
                for p, expected in artifacts.items())
        except (OSError, ValueError, TypeError):
            return False
    verified = {json.dumps({k: row.get(k) for k in ('plan_hash','obligation_id','proof_kind','artifacts')}, sort_keys=True)
                       for row in records if isinstance(row, dict) and row.get('kind') == 'proof'
                       and row.get('task_id') == task_id and row.get('plan_hash') == result.get('plan_hash')
                       and type(row.get('exit_code')) is int and row['exit_code'] == 0 and current_proof(row)}
    seen = control.get('seen_proofs', [])
    seen = set(seen) if isinstance(seen, list) and all(isinstance(v, str) for v in seen) else set()
    closed = {row['agent_id'] for row in list_agents(root, task_id, state['session_id']) if row['status'] == 'closed'}
    seen_closed = control.get('seen_closed', [])
    seen_closed = set(seen_closed) if isinstance(seen_closed, list) and all(isinstance(v, str) for v in seen_closed) else set()
    best_unmet = control.get('best_unmet_count')
    current_unmet = len(result.get('unmet', []))
    improved = type(best_unmet) is int and current_unmet < best_unmet
    progress = bool(verified - seen or closed - seen_closed or improved)
    previous = control.get('unchanged_attempts', 0)
    previous = previous if type(previous) is int and previous >= 0 else 0
    attempts = 1 if progress or previous == 0 else previous + 1
    control.update(seen_proofs=sorted(seen | verified), seen_closed=sorted(seen_closed | closed),
                   best_unmet_count=min(best_unmet, current_unmet) if type(best_unmet) is int else current_unmet,
                   unchanged_attempts=attempts)
    state['completion_control'] = control
    atomic_json(path, state)
    append_jsonl(root / 'hook-audit.jsonl', dict(event='Stop', session_id=state['session_id'],
        task_id=task_id, verdict=result['verdict'], reason=result['reason'], attempts=attempts))
    if attempts > 3:
        return {'systemMessage': 'Megaskill task remains unfinished after unchanged retries and a diagnosis request. '
                'Automatic retries are paused; an explicit continue or execute restarts them. No edit restriction was imposed.'}
    reason = ('Megaskill continuation: ' + result['reason'] + '. Original goal: ' + state['goal'] +
              '. Continue authorized work and verify actual outcomes. This retry grants no new permission.')
    if attempts == 3:
        reason += (' Repeated attempts show no new verified progress. Perform root-cause diagnosis, '
                   'inspect the controlling instructions and obtain independent review when useful; '
                   'change the approach instead of repeating the same failed attempt.')
    return {'decision':'block', 'reason':reason}


def handle(payload):
    """Record observations; task metadata never becomes an instruction."""
    native_sid = safe_id(payload.get('session_id', ''))
    state = read_json(state_for(payload), {})
    state = state if isinstance(state, dict) else {}
    sid = native_sid
    name = payload.get('hook_event_name')
    if name not in ('SubagentStart', 'SubagentStop'):
        routes = state.get('child_turns', {})
        child_id = payload.get('agent_id') or (routes.get(payload.get('turn_id')) if isinstance(routes, dict) else None)
        if child_id:
            child = read_json(binding_root() / (safe_id(child_id) + '.json'), {})
            if (isinstance(child, dict) and child.get('parent_session_id') == native_sid
                    and child.get('task_id') == state.get('task_id') and child.get('root') == state.get('root')):
                sid, state = child_id, child
    append_jsonl(receipt_path(sid), dict(
        event=name, session_id=sid, native_session_id=native_sid,
        turn_id=payload.get('turn_id'), agent_id=payload.get('agent_id'),
        timestamp=datetime.now(timezone.utc).isoformat(),
        handler_revision=handler_revision(), task_id=state.get('task_id'),
        policy='completion-retry-with-user-unlock'))
    active_payload = dict(payload, session_id=sid)
    active_path = binding_root() / (sid + '.json')
    if state and name == 'UserPromptSubmit':
        return user_control(active_payload, state, active_path)
    if state and name == 'Interrupt' and not state.get('is_child'):
        state['completion_control'] = dict(paused=True, reason='user-interruption')
        atomic_json(active_path, state)
        return {}
    if state and name == 'Stop':
        return completion_stop(active_payload, state, active_path)
    task_id = state.get('task_id')
    root = Path(state['root']) if isinstance(state.get('root'), str) else None
    if task_id and root and name in ('SubagentStart', 'SubagentStop', 'PostToolUse'):
        from mega_agents import observe
        observe(dict(payload, session_id=state.get('parent_session_id', native_sid)), root, task_id)
    if task_id and name == 'SubagentStart' and payload.get('agent_id'):
        child_id = safe_id(payload['agent_id'])
        # Identity metadata only; no inferred authority or role ceiling.
        child = {k: state[k] for k in ('root', 'task_id', 'goal', 'mode') if k in state}
        child.update(session_id=child_id, parent_session_id=native_sid, is_child=True)
        atomic_json(binding_root() / (child_id + '.json'), child)
        if payload.get('turn_id'):
            state.setdefault('child_turns', {})[safe_id(payload['turn_id'])] = child_id
            atomic_json(state_for(payload), state)
    # Tool calls are never denied by this adapter.
    return {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event')
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError('hook input must be an object')
        if args.event:
            payload['hook_event_name'] = args.event
        with locked(state_for(payload).with_suffix('.lock')):
            output = handle(payload)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        # Optional observation must not turn corrupt/stale data into a work lock.
        print('Megaskill observation unavailable: ' + str(exc), file=sys.stderr)
        output = {}
    print(json.dumps(output))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
