import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/mega_hook_canary.py'


class CanaryTests(unittest.TestCase):
    def test_protocol_replay_cannot_substitute_for_live_receipts(self):
        sys.path.insert(0,str(SCRIPT.parent))
        from mega_hook_canary import live_receipts
        fake=[dict(event='Stop',task_id='canary',session_id='canary-session',verdict=v) for v in ('continue','complete')]
        self.assertEqual(live_receipts(fake),[])
        real=[dict(event='Stop',task_id='live-canary',session_id='actual-runtime',verdict=v) for v in ('continue','complete')]
        self.assertEqual(live_receipts(fake+real),real)

    def test_repeatable_protocol_and_artifact_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            results=[]
            for name in ('first','second'):
                workspace=Path(tmp)/name
                r=subprocess.run([sys.executable,str(SCRIPT),'--workspace',str(workspace)],capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                results.append(json.loads(r.stdout))
                self.assertEqual((workspace/'1.2.txt').read_text(),'verified 1.2')
            self.assertEqual(results[0],results[1])

    def test_refuses_nonempty_workspace_and_bad_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'user-data').write_text('keep')
            r=subprocess.run([sys.executable,str(SCRIPT),'--workspace',tmp],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertEqual((p/'user-data').read_text(),'keep')
            r=subprocess.run([sys.executable,str(SCRIPT),'--timeout','0'],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
