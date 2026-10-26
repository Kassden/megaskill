#!/usr/bin/env python3
"""Disposable completion-loop regression: explicit resume and no edit locks."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from mega_store import atomic_json, digest, read_json
from mega_task import register, event
from mega_completion import evaluate

SCRIPTS = Path(__file__).resolve().parent


def protocol(workspace):
    root = workspace / '.mega'
    plan = workspace / 'PLAN.md'
    plan.write_text('### Subphase 1.1: First\n### Subphase 1.2: Second\n')
    env = dict(os.environ, MEGA_BINDINGS_DIR=str(workspace / 'bindings'))
    previous = os.environ.get('MEGA_BINDINGS_DIR')
    os.environ['MEGA_BINDINGS_DIR'] = env['MEGA_BINDINGS_DIR']
    try:
        acceptance = {oid: [{'kind':'text', 'description':'exact outcome',
                        'path':str(workspace / (oid + '.txt')), 'equals':'verified ' + oid}]
                      for oid in ('1.1', '1.2')}
        register(root, 'canary', plan, 'both actual outputs', session='canary-session', acceptance=acceptance)
        binding_path = workspace / 'bindings/canary-session.json'
        binding = read_json(binding_path)
        binding.update(status_turn=True, authority={'effective_mode':'review'},
                       authority_conflict={'reason':'historical review lock'})
        atomic_json(binding_path, binding)
        for name in ('UserPromptSubmit', 'SessionStart', 'PostCompact', 'PreToolUse', 'Stop'):
            payload = dict(session_id='canary-session', hook_event_name=name,
                           prompt='The quoted failure says review-only.',
                           tool_name='Bash', tool_input={'command':'python3 update_workbook.py'})
            result = subprocess.run([sys.executable, str(SCRIPTS / 'mega_hooks.py')],
                input=json.dumps(payload), capture_output=True, text=True, env=env, check=True)
            if json.loads(result.stdout) != {}:
                raise ValueError('observer injected instructions or a blocking decision')
        if evaluate(root, 'canary', require_outcomes=True)['verdict'] != 'continue':
            raise ValueError('observation falsely completed an unfinished task')
        def hook(name, **fields):
            payload=dict(session_id='canary-session',hook_event_name=name,**fields)
            result=subprocess.run([sys.executable,str(SCRIPTS/'mega_hooks.py')],input=json.dumps(payload),
                                  capture_output=True,text=True,env=env,check=True)
            return json.loads(result.stdout)
        resumed=hook('UserPromptSubmit',prompt='continue',turn_id='real-resume',permission_mode='default')
        if 'earlier review/status' not in resumed.get('hookSpecificOutput',{}).get('additionalContext',''):
            raise ValueError('explicit continue did not clear the stale Megaskill review lock')
        hook('UserPromptSubmit',prompt='Megaskill continuation: execute obligation 1.1',turn_id='synthetic')
        if hook('Stop').get('decision') != 'block':
            raise ValueError('authorized incomplete work did not continue')
        hook('UserPromptSubmit',prompt='review only; do not implement',turn_id='review')
        if hook('Stop') != {}:
            raise ValueError('review checkpoint was forced into implementation')
        hook('UserPromptSubmit',prompt='execute',turn_id='execute')
        if hook('Stop').get('decision') != 'block':
            raise ValueError('execute did not restart the completion loop')
        for oid in ('1.1', '1.2'):
            artifact = workspace / (oid + '.txt')
            artifact.write_text('verified ' + oid)
            refs = [event(root, 'canary', 'proof', oid, proof_kind=kind, exit_code=0,
                          artifacts={str(artifact):digest(artifact)})['event_id']
                    for kind in ('test', 'readback')]
            event(root, 'canary', 'done', oid, proof_ids=refs)
        if evaluate(root, 'canary', require_outcomes=True)['verdict'] != 'complete':
            raise ValueError('explicit outcome verification failed')
        if hook('Stop') != {}:
            raise ValueError('completed outcomes did not end the loop')
        return {'protocol':'passed', 'tool_denials':False, 'review_only_injections':False,
                'explicit_resume_unlock':True, 'completion_retries':True, 'explicit_outcomes':'verified'}
    finally:
        if previous is None:
            os.environ.pop('MEGA_BINDINGS_DIR', None)
        else:
            os.environ['MEGA_BINDINGS_DIR'] = previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--timeout', type=int, default=240)
    parser.add_argument('--execute', action='store_true', help='retired native automation entrypoint; rejected')
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error('timeout must be positive')
    if args.execute:
        parser.error('native runtime automation is separate; this isolated canary never installs or enables hooks')
    workspace = args.workspace or Path(tempfile.mkdtemp(prefix='mega-observer-'))
    if workspace.exists() and any(workspace.iterdir()):
        parser.error('workspace must be empty')
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        result = protocol(workspace)
        atomic_json(workspace / 'canary-result.json', result)
        print(json.dumps(result)); return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({'error':str(exc), 'workspace':str(workspace)})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
