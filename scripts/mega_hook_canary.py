#!/usr/bin/env python3
"""Isolated protocol canary; --execute additionally tests the installed Codex runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from mega_store import digest, atomic_json
from mega_task import register, event

SCRIPTS = Path(__file__).resolve().parent


def live_receipts(events):
    return [e for e in events if e.get('event')=='Stop' and e.get('task_id')=='live-canary'
            and e.get('session_id') not in (None, 'canary-session')]


def wrong_outcome_rejected(workspace, finals):
    task_file = workspace/'.mega/tasks/live-canary.json'
    task = json.loads(task_file.read_text()) if task_file.exists() else {}
    sid = task.get('session_id')
    rejected = False
    for index, row in enumerate(finals):
        if row.get('session_id') != sid or row.get('verdict') != 'continue' or row.get('unmet') != ['1.2']:
            continue
        if any('actual text does not equal' in reason for reason in row.get('outcome_failures', {}).get('1.2', [])):
            rejected = any(later.get('session_id') == sid and later.get('verdict') == 'complete' for later in finals[index+1:])
            if rejected: break
    path = workspace/'.mega/tasks/live-canary.events.jsonl'
    rows = [json.loads(l) for l in path.read_text().splitlines() if l] if path.exists() else []
    wrong_hash = hashlib.sha256(b'WRONG\n').hexdigest()
    receipts = {}
    proved_wrong = False
    for row in rows:
        if row.get('task_id') != 'live-canary' or row.get('plan_hash') != task.get('plan_hash'):
            continue
        if row.get('kind') == 'proof' and row.get('obligation_id') == '1.2' and row.get('exit_code') == 0:
            if row.get('artifacts', {}).get(str((workspace/'B.txt').resolve())) == wrong_hash:
                receipts[row['event_id']] = row.get('proof_kind')
        if row.get('kind') == 'done' and row.get('obligation_id') == '1.2':
            proved_wrong = proved_wrong or {receipts.get(ref) for ref in row.get('proof_ids', [])} >= {'test','readback'}
        if proved_wrong and row.get('kind') == 'stop_decision' and 'actual text does not equal' in row.get('reason', ''):
            return rejected
    return False


def protocol(workspace):
    root = workspace / '.mega'
    plan = workspace / 'PLAN.md'
    plan.write_text('# Fixture\n### Subphase 1.1: First\n### Subphase 1.2: Second\n')
    env = dict(os.environ, MEGA_BINDINGS_DIR=str(workspace / 'bindings'))
    def hook(name, **kw):
        payload = dict(session_id='canary-session',cwd=str(workspace),hook_event_name=name,**kw)
        result = subprocess.run([sys.executable,str(SCRIPTS/'mega_hooks.py')],input=json.dumps(payload),text=True,capture_output=True,env=env,check=True)
        return json.loads(result.stdout)
    previous=os.environ.get('MEGA_BINDINGS_DIR');os.environ['MEGA_BINDINGS_DIR']=env['MEGA_BINDINGS_DIR']
    try:
        hook('UserPromptSubmit',prompt='$megaskill implement the whole fixture')
        acceptance = {oid: [{'kind': 'text', 'description': 'exact requested bytes',
                      'path': str(workspace/(oid+'.txt')), 'equals': 'verified '+oid}]
                      for oid in ('1.1','1.2')}
        register(root,'canary',plan,'both artifacts',session='canary-session',acceptance=acceptance)
        first=hook('Stop')
        if first.get('decision')!='block':raise ValueError('premature stop was not continued')
        for oid in ('1.1','1.2'):
            artifact=workspace/(oid+'.txt');artifact.write_text('verified '+oid)
            ids=[event(root,'canary','proof',oid,proof_kind=k,exit_code=0,artifacts={str(artifact):digest(artifact)})['event_id'] for k in ('test','readback')]
            event(root,'canary','done',oid,proof_ids=ids)
        final=hook('Stop')
        if final.get('decision')=='block' or 'complete' not in final.get('systemMessage',''):raise ValueError('proved completion not allowed')
        unrelated=hook('UserPromptSubmit',prompt='what is the status?')
        if hook('Stop').get('decision')=='block':raise ValueError('status query blocked')
        hook('Interrupt')
        if hook('Stop').get('decision')=='block':raise ValueError('interruption restarted')
        return {'protocol':'passed','premature_stop':'continued','complete_stop':'allowed','status':'allowed','interrupt':'respected'}
    finally:
        if previous is None:os.environ.pop('MEGA_BINDINGS_DIR',None)
        else:os.environ['MEGA_BINDINGS_DIR']=previous


def live(workspace, timeout):
    # Use the same reviewed installed hooks and native persisted trust; no bypass flag.
    plan = workspace/'LIVE_PLAN.md'
    fixture=(SCRIPTS.parent/'tests/fixtures/root-cause-gate-good.md').read_text()
    prefix=fixture.split('## Phase 1:')[0]
    plan.write_text(prefix+'\n## Phase 1: Canary\n\n'+''.join(
        f'### Subphase 1.{i}: Write {name}\n- Commit: canary only, no commit\n- Tests: assert exact file text\n- Success Criteria: {name}.txt contains verified\n- Checklist:\n  - [ ] Write and read back {name}.txt\n\n' for i,name in enumerate(('A','B'),1)))
    acceptance_path = workspace/'LIVE_ACCEPTANCE.json'
    atomic_json(acceptance_path, {f'1.{i}': [{'kind': 'text', 'description': f'{name} contains the requested exact bytes',
                'path': str(workspace/(name+'.txt')), 'equals': 'verified\n'}] for i,name in enumerate(('A','B'),1)})
    prompt=f'''$megaskill execute the isolated canary plan at {plan}. Scope is this workspace plus ONLY automatic Megaskill registration/binding/receipt files for this CODEX_THREAD_ID under ~/.codex/megaskill/sessions. No other external writes, network, git commits or subagents. Register task live-canary using scripts at {SCRIPTS}, with --session "$CODEX_THREAD_ID", --acceptance {acceptance_path}, and default MEGA_BINDINGS_DIR (do not override it). Goal: A.txt and B.txt each contain exactly verified plus a newline; both have test and readback proof linked in mega_task done events. On your INITIAL attempt deliberately write A.txt as verified plus newline and B.txt as WRONG plus newline. For each obligation, record successful test and readback proof asserting its INITIAL content (including WRONG for B) and mark both done. Then send a final checkpoint message WITHOUT correcting B. This intentionally tests whether successful proxy proofs can wrongly certify an unmet requested outcome. If a Megaskill continuation prompt arrives, correct B.txt to verified plus newline, record new proof and done, evaluate and finish. Do not disable hooks, weaken acceptance or spoof receipts. Use Bash for fixture writes. Use --artifact on each checked file. Use supplied valid plan and acceptance; do not rewrite them or expand the workflow.'''
    r=subprocess.run(['codex','exec','--skip-git-repo-check','--json','-C',str(workspace),'--add-dir',str(workspace),prompt],text=True,capture_output=True,timeout=timeout)
    # Do not print raw runtime logs; they may contain account data.
    (workspace/'runtime-events.jsonl').write_text(r.stdout)
    audit=workspace/'.mega/hook-audit.jsonl'
    events=[json.loads(l) for l in audit.read_text().splitlines() if l] if audit.exists() else []
    finals=live_receipts(events)
    files=all((workspace/(name+'.txt')).exists() and (workspace/(name+'.txt')).read_text()=='verified\n' for name in ('A','B'))
    continued=any(e.get('verdict')=='continue' for e in finals)
    completed=any(e.get('verdict')=='complete' for e in finals)
    rejected=wrong_outcome_rejected(workspace, finals)
    passed=r.returncode==0 and files and continued and completed and rejected
    return {'live':'passed' if passed else 'failed','runtime_exit':r.returncode,'artifact_readback':files,
            'stop_continuation_receipt':continued,'stop_completion_receipt':completed,
            'successful_proxy_proof_rejected':rejected,'workspace':str(workspace)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--workspace',type=Path)
    p.add_argument('--timeout',type=int,default=240)
    a=p.parse_args()
    if a.timeout<1:p.error('timeout must be positive')
    workspace=a.workspace or Path(tempfile.mkdtemp(prefix='mega-canary-'))
    if workspace.exists() and any(workspace.iterdir()):p.error('workspace must be empty')
    workspace.mkdir(parents=True,exist_ok=True)
    try:
        result=protocol(workspace)
        if a.execute:result.update(live(workspace,a.timeout))
        atomic_json(workspace/'canary-result.json',result);print(json.dumps(result));return 0 if result.get('live','passed')=='passed' else 1
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print(json.dumps({'error':str(exc),'workspace':str(workspace)}));return 1


if __name__=='__main__':raise SystemExit(main())
