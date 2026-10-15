#!/usr/bin/env python3
"""Synchronous Codex lifecycle adapter. All completion checks use task contracts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from mega_store import atomic_json, append_jsonl, binding_root, locked, read_json, safe_id
from mega_task import task_path, event
from mega_completion import evaluate
from mega_outcomes import handler_revision, receipt_path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent


def context(name, text):
    return {'hookSpecificOutput': {'hookEventName': name, 'additionalContext': text}}


def state_for(payload):
    sid = safe_id(payload.get('session_id', ''))
    return binding_root() / (sid + '.json')


def valid_binding(state, sid):
    return (isinstance(state, dict) and bool(state)
            and isinstance(state.get('root'), str) and Path(state['root']).is_absolute()
            and state.get('mode') in ('execute','plan','review','monitor')
            and state.get('session_id') == sid
            and isinstance(state.get('goal'), str) and bool(state['goal'])
            and all(type(state[k]) is bool for k in ('pending','paused','status_turn','is_child') if k in state))


def activation(prompt):
    # Quoted references, instruction bundles and skill payloads do not activate a task.
    if prompt.lstrip().startswith(('<skill>', '<environment_context>')):
        return None
    prompt = re.sub(r'(["\']).*?\1', '', prompt)
    if not re.search(r'(?i)(?:\$megaskill\b|\buse megaskill\b)', prompt):
        return None
    if re.search(r'(?i)\b(?:do not|don.t|never)\s+(?:execute|implement)\b|\bonly\s+(?:write|review|plan)\b', prompt):
        return 'plan'
    if re.search(r'(?i)\b(review|audit|write (?:a |the )?plan|proposal)\b', prompt) and not re.search(r'(?i)\b(?:then|and)\s+(?:execute|implement|fix)\b', prompt):
        return 'plan'
    if re.search(r'(?i)\b(implement|execute|repair|finish|build|fix|ship|do not stop)\b', prompt):
        return 'execute'
    if re.search(r'(?i)\b(plan|proposal|review|audit)\b', prompt):
        return 'plan'
    return None


def handle(payload):
    name = payload.get('hook_event_name')
    path = state_for(payload)
    sid = payload['session_id']
    state = read_json(path, {})
    # Record invocation before every early return, including absent bindings and status/pause turns.
    append_jsonl(receipt_path(sid), {'event': name, 'session_id': sid,
                 'turn_id': payload.get('turn_id'), 'timestamp': datetime.now(timezone.utc).isoformat(),
                 'handler_revision': handler_revision(), 'task_id': state.get('task_id') if isinstance(state, dict) else None})
    if path.exists() and not valid_binding(state, sid):
        raise ValueError('invalid persisted session binding')
    if name == 'UserPromptSubmit':
        prompt = payload.get('prompt', '')
        prompt = re.sub(r'^<hook_prompt\b[^>]*>(.*?)</hook_prompt>$', r'\1', prompt, flags=re.S)
        if prompt.startswith('Megaskill continuation:'):
            state['status_turn'] = False
        else:
            plain = prompt.strip().lower()
            read_only = bool(re.search(r'\b(?:review(?:ing)?|audit(?:ing)?|inspect(?:ing)?|report|diagnos\w*)\b.*\bonly\b|\b(?:do not|don.t|never)\s+(?:execute|implement|fix|repair|make changes|edit)\b', plain))
            mode = activation(prompt)
            replacement = bool(re.search(r'(?i)\b(new task|replace (?:this|the) task|start over)\b', prompt))
            if read_only and state:
                state['status_turn'] = True
            elif mode and state.get('task_id') and not replacement and evaluate(Path(state['root']), state['task_id'], require_outcomes=True)['verdict'] != 'complete':
                # Follow-ups steer the existing goal; reviews can end without replacing it.
                state.update(status_turn=(mode == 'plan'), paused=False)
                if mode == 'execute':
                    contract_path = task_path(Path(state['root']), state['task_id'])
                    contract = read_json(contract_path)
                    if contract:
                        contract['status'] = 'active'
                        if contract['mode'] != 'execute':
                            contract['mode'] = 'execute'; contract['execution_authority'] = prompt
                            state['mode'] = 'execute'
                        atomic_json(contract_path, contract)
            elif mode:
                # An explicit new invocation may replace a completed contract, never silently satisfy it.
                state.update(root=str(Path(payload.get('cwd', '.')).resolve() / '.mega'),
                             goal=prompt[:3000], mode=mode, pending=True, task_id=None,
                             session_id=sid, status_turn=False, stall_count=0)
            elif state:
                plain = prompt.strip().lower()
                execution_followup = bool(re.search(r'^(continue|resume|finish|go ahead|keep goin(?:g)?|solve it)\b|^can you\b.*\b(fix|repair|finish|implement|continue)\b|\bcontinue until\b', plain))
                execution_followup = execution_followup and not re.search(r'\b(do not|don.t|never)\s+(execute|implement|fix|repair|continue)\b', plain)
                if re.fullmatch(r'(?:please\s+)?(?:stop|cancel|pause)(?:\s+(?:(?:this|the|current)\s+)*(?:task|work|working on this))?(?:\s+(?:now|please))?[.!]?', plain):
                    state['paused'] = True
                    if state.get('task_id'):
                        contract_path = task_path(Path(state['root']), state['task_id'])
                        contract = read_json(contract_path)
                        if contract:
                            contract['status'] = 'cancelled' if 'cancel' in plain else 'paused'
                            contract['lifecycle_reason'] = prompt
                            atomic_json(contract_path, contract)
                elif execution_followup or plain in ('$megaskill', 'megaskill'):
                    state['paused'] = False; state['status_turn'] = False
                    if state.get('task_id'):
                        contract_path = task_path(Path(state['root']), state['task_id'])
                        contract = read_json(contract_path)
                        if contract:
                            contract['status'] = 'active'; atomic_json(contract_path, contract)
                else:
                    # A question can finish as a status turn while the task remains bound.
                    state['status_turn'] = bool(re.search(r'^(what|why|how|is|are|can you (?:tell|check)|do we|show|review)\b', plain))
            # Rejection revokes old acceptance, but never authorizes implementation in a review-only turn.
            if state.get('task_id') and re.search(r'\b(not done|not finished|not acceptable|does not meet|you dropped|still unfinished|complete slop|botched template)\b', plain):
                task = read_json(task_path(Path(state['root']), state['task_id']))
                if task and task.get('status') == 'active' and task.get('mode') == 'execute':
                    for obligation in task['obligations']:
                        event(Path(state['root']), state['task_id'], 'reopen', obligation['id'], reason='User rejected outcome: ' + prompt[:1000])
                    state['status_turn'] = read_only
        if state:
            atomic_json(path, state)
            return context(name, packet(state, sid))
        return {}
    if not state:
        return {}
    root = Path(state['root'])
    task_id = state.get('task_id')
    if name == 'Interrupt':
        state['paused'] = True; atomic_json(path, state)
        if task_id:
            contract_path = task_path(root, task_id)
            with locked(contract_path.with_suffix('.lock')):
                contract = read_json(contract_path)
                if contract:
                    contract['status'] = 'paused'; contract['lifecycle_reason'] = 'user interruption'
                    atomic_json(contract_path, contract)
        append_jsonl(root / 'hook-audit.jsonl', {'event': name, 'session_id': sid, 'task_id': task_id})
        return {'systemMessage': 'Megaskill interruption recorded; no automatic restart.'}
    if name == 'SessionStart':
        return context(name, packet(state, sid))
    if name in ('PostCompact', 'PreCompact'):
        return {'systemMessage': packet(state, sid)}
    if name == 'SubagentStart':
        if task_id:
            from mega_agents import observe
            parent = state.get('parent_session_id', sid)
            observe(dict(payload, session_id=parent), root, task_id)
            child_id = safe_id(payload['agent_id'])
            child_path = binding_root() / (child_id + '.json')
            if child_path != path:
                with locked(child_path.with_suffix('.lock')):
                    atomic_json(child_path, dict(state, session_id=child_id,
                                parent_session_id=parent, is_child=True, pending=False,
                                status_turn=False, stall_count=0))
        return context(name, 'Use only the assigned scope. Return concrete evidence. Do not spawn children. The parent must integrate the result and call close_agent; completion is not closure.')
    if name == 'SubagentStop':
        if task_id:
            from mega_agents import observe
            observe(dict(payload, session_id=state.get('parent_session_id', sid)), root, task_id)
        # A child's final is not whole-plan acceptance. Parent performs integration/cleanup.
        return {}
    if name == 'PreToolUse':
        tool = payload.get('tool_name', '')
        tool = tool.rsplit('__', 1)[-1].rsplit('.', 1)[-1]
        if tool == 'Agent' or tool.endswith('spawn_agent'):
            if state.get('is_child'):
                return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'deny',
                                              'permissionDecisionReason': 'Assigned children cannot recursively delegate; return work to the parent orchestrator.'}}
            actor = payload.get('agent_id')
            # Some child-tool paths carry the child's session ID; others carry agent_id.
            # Only deny when ownership is known, never infer it from another session's ID.
            if task_id:
                from mega_agents import open_agents
                children = open_agents(root, task_id)
                if any(c.get('agent_id') in (sid, actor) for c in children):
                    return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'deny',
                                                  'permissionDecisionReason': 'Nested delegation is disabled for this assigned child; return work to its owning orchestrator.'}}
        if state.get('pending') and state.get('mode') == 'execute' and (tool == 'Agent' or tool.endswith('spawn_agent')):
            return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'deny',
                                          'permissionDecisionReason': 'Register the Megaskill task before spawning children so ownership and cleanup can be tracked.'}}
        if task_id and (tool == 'Agent' or tool.endswith('spawn_agent')):
            from mega_agents import check_spawn
            check = check_spawn(root, task_id, sid)
            if not check.get('allowed'):
                return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'deny',
                                              'permissionDecisionReason': check['reason']}}
        if task_id and tool in ('apply_patch', 'Write', 'Edit'):
            task = read_json(task_path(root, task_id))
            from mega_plan_check import validate
            raw = payload.get('tool_input', {})
            patch_text = raw.get('command', raw.get('input', '')) if isinstance(raw, dict) else str(raw)
            paths = re.findall(r'^\*\*\* (?:Add|Update|Delete) File: (.+)$', patch_text, re.M)
            if task and paths and all((Path(payload.get('cwd','.')) / p).resolve() == Path(task['plan']).resolve() for p in paths):
                return {}
            errors = validate(Path(task['plan']).read_text()) if task else ['missing task']
            if errors:
                return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'deny',
                                              'permissionDecisionReason': 'Repair canonical plan prerequisites: ' + '; '.join(errors[:3])}}
        if task_id and tool in ('Bash', 'exec_command'):
            raw = payload.get('tool_input', {})
            command = raw.get('command', raw.get('cmd', '')) if isinstance(raw, dict) else ''
            if re.search(r'\b(?:git\s+push|deploy|systemctl\s+(?:restart|stop)|rm\s+-rf)\b', command):
                from mega_decision import read_records, replay, ACCEPTED
                records, errors = read_records(root/'decisions.jsonl')
                decisions, replay_errors = replay(records)
                contract = read_json(task_path(root, task_id))
                accepted = any(d.get('task_id') == task_id and d.get('plan_sha256') == contract['plan_hash'] and d.get('status') in ACCEPTED for d in decisions.values())
                if errors or replay_errors or not accepted:
                    return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'deny',
                                                  'permissionDecisionReason': 'Record and challenge a current task-scoped material decision before this consequential operation. Existing user approval is still required where applicable.'}}
        if state.get('pending') and state.get('mode') == 'execute':
            if tool in ('apply_patch', 'Write', 'Edit'):
                raw = payload.get('tool_input', {})
                patch = raw.get('command', raw.get('input', '')) if isinstance(raw, dict) else str(raw)
                files = re.findall(r'^\*\*\* (?:Add|Update|Delete) File: (.+)$', patch, re.M)
                if files and all(Path(f).suffix == '.md' and 'plan' in Path(f).name.lower() for f in files):
                    return {}
                return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'deny',
                                              'permissionDecisionReason': 'Register and validate the Megaskill task before implementation edits. Canonical PLAN Markdown and read-only inspection remain allowed.'}}
        return {}
    if name == 'PostToolUse':
        if task_id:
            from mega_agents import observe
            observe(dict(payload, session_id=state.get('parent_session_id', sid)), root, task_id)
        return {}
    if name != 'Stop':
        return {}
    first_current_stop = state.get('stop_verified_revision') != handler_revision()
    state['stop_verified_revision'] = handler_revision()
    atomic_json(path, state)
    if state.get('paused') or state.get('status_turn') or state.get('mode') != 'execute':
        append_jsonl(root / 'hook-audit.jsonl', {'event': name, 'session_id': sid, 'task_id': task_id,
                     'verdict': 'bypassed', 'reason': 'paused' if state.get('paused') else 'status_or_nonexecute'})
        return {}
    if state.get('pending') or not task_id:
        result = {'verdict': 'invalid', 'reason': 'register the goal and canonical plan before execution', 'unmet': ['registration']}
    else:
        result = evaluate(root, task_id, require_outcomes=True)
        if result['verdict'] == 'complete' and first_current_stop:
            result = {'verdict': 'continue', 'reason': 'native Stop invocation is now observed; rerun the strict manual final gate with --task before finishing', 'unmet': ['runtime-stop-readback']}
        from mega_agents import open_agents
        children = open_agents(root, task_id)
        if children:
            ids = [c.get('agent_id', c.get('id')) for c in children]
            result = {'verdict': 'continue', 'reason': 'collect remaining child results, then call native close_agent for these owned IDs and record the receipts: ' + ', '.join(ids), 'unmet': ['child-cleanup']}
    append_jsonl(root / 'hook-audit.jsonl', {'event': name, 'session_id': sid,
                 'task_id': task_id, 'verdict': result['verdict'], 'reason': result['reason'],
                 'outcome_failures': result.get('outcome_failures', {}), 'unmet': result['unmet']})
    if task_id:
        event(root, task_id, 'stop_decision', verdict=result['verdict'], reason=result['reason'], unmet=result['unmet'])
    if result['verdict'] in ('complete', 'blocked', 'paused'):
        return {'systemMessage': 'Megaskill completion gate: ' + result['verdict'] + '. ' + result['reason']}
    # Audit events and failed/repeated attempts do not count as progress.
    events_path = root / 'tasks' / ((task_id or 'unregistered') + '.events.jsonl')
    records = [json.loads(line) for line in events_path.read_text().splitlines() if line] if events_path.exists() else []
    # Deduplicate semantic evidence: fresh UUIDs for the same proof are not progress.
    verified = sorted({json.dumps({k: e.get(k) for k in ('obligation_id','proof_kind','artifacts','kind')}, sort_keys=True)
                       for e in records if e.get('kind') in ('proof', 'done', 'unblocked') and e.get('exit_code', 0) == 0})
    fingerprint = hashlib.sha256(json.dumps([result, verified], sort_keys=True).encode()).hexdigest()
    state['stall_count'] = state.get('stall_count', 0) + 1 if state.get('fingerprint') == fingerprint else 1
    state['fingerprint'] = fingerprint
    atomic_json(path, state)
    if state['stall_count'] > 3:
        failure = 'Megaskill enforcement failed after three unchanged continuation attempts. Unfinished: ' + ', '.join(result['unmet']) + '. ' + result['reason']
        append_jsonl(root / 'hook-audit.jsonl', {'event': 'enforcement_failed', 'session_id': sid, 'reason': failure})
        return {'continue': False, 'stopReason': failure, 'systemMessage': failure}
    return {'decision': 'block', 'reason': 'Megaskill continuation: ' + result['reason'] + '. '
            + packet(state, sid) + ' Preserve the original scope and user authority; do not ask the user to perform executable engineering work.'}


def packet(state, sid):
    cmd = f'{sys.executable} {SCRIPT_DIR / "mega_task.py"} --root {state["root"]}'
    turn_note = 'This turn is review/status-only; do not implement. Original obligations remain open. ' if state.get('status_turn') else ''
    if state.get('pending'):
        return f'Megaskill {state["mode"]} task pending. Goal: {state["goal"]}. Write/validate the canonical plan, then register: {cmd} register --id TASK_ID --plan PLAN.md --goal "requested outcome" --mode {state["mode"]} --session {sid} --acceptance ACCEPTANCE.json. Pin actual text/JSON/review outcome assertions for every obligation, not file-existence proxies. If registered, repair binding with {cmd} bind --id TASK_ID --session {sid}. Binding directory: {binding_root()}; do not override it. Registration precedes implementation. Link current test/readback proof and explicit done events.'
    return f'{turn_note}Megaskill goal: {state["goal"]}. Task {state.get("task_id")}; mode {state["mode"]}. Use {cmd} show/evaluate --id {state.get("task_id")}. Missing acceptance: use acceptance --file ACCEPTANCE.json --authority USER_AUTHORITY --reason REASON, then refresh proof. Pin actual requested outcomes; qualitative work needs an independent review, not presence/keyword checks. Use runtime --id {state.get("task_id")} --session {sid} before claiming hook coverage. Prove each obligation with prove --kind test/readback --artifact PATH -- COMMAND, then done --proof EVENT_ID. Make delegated engineering decisions and record them with mega_decision.py. Close owned agents after collecting results, including previous owners of this same task. A release blocker only blocks its affected obligations.'


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--event')
    a = p.parse_args()
    payload = {}
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict): raise ValueError('hook input must be object')
        if a.event: payload['hook_event_name'] = a.event
        path = state_for(payload)
        with locked(path.with_suffix('.lock')):
            output = handle(payload)
        print(json.dumps(output, sort_keys=True)); return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        message = 'Megaskill hook error: ' + str(exc)
        try:
            state = read_json(state_for(payload), {})
            if not valid_binding(state, payload.get('session_id')):
                raise ValueError('invalid persisted session binding')
            if payload.get('hook_event_name') == 'Stop' and state.get('mode') == 'execute' and not state.get('paused'):
                state['error_count'] = state.get('error_count', 0) + 1
                atomic_json(state_for(payload), state)
                if state['error_count'] <= 3:
                    print(json.dumps({'decision': 'block', 'reason': 'Megaskill continuation: repair evaluator error before handoff. ' + message})); return 0
                print(json.dumps({'continue': False, 'stopReason': message, 'systemMessage': 'Megaskill enforcement failed; task remains unfinished. ' + message})); return 0
        except (ValueError, KeyError, TypeError, OSError):
            if isinstance(locals().get('payload'), dict) and payload.get('hook_event_name') == 'Stop':
                print(json.dumps({'continue': False, 'stopReason': message,
                                  'systemMessage': 'Megaskill enforcement failed: unreadable session binding; task completion is unverified. ' + message})); return 0
        print(json.dumps({'systemMessage': message})); return 0


if __name__ == '__main__': raise SystemExit(main())
