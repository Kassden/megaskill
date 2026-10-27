import base64
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mega_hooks_install.py"
spec = importlib.util.spec_from_file_location("mega_hooks_install", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class HooksInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "hooks.json"

    def run_cli(self, *args, target=None):
        return subprocess.run([sys.executable, str(SCRIPT), "--target",
                               str(target or self.target), *args],
                              text=True, capture_output=True, cwd=self.root)

    def config(self):
        return json.loads(self.target.read_bytes())

    def write_json(self, data):
        self.target.write_text(json.dumps(data, indent=2) + "\n")

    def test_help_and_missing_default_dry_run(self):
        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        for option in ("--apply", "--uninstall", "--target", "--status", "--dry-run"):
            self.assertIn(option, help_result.stdout)
        self.assertIn("/hooks", help_result.stdout)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["changed_events"], list(installer.EVENTS))
        self.assertFalse(self.target.exists())
        self.assertFalse(installer.manifest_path(self.target).exists())

    def test_default_target_and_status_do_not_write(self):
        with patch.dict(os.environ, {"HOME": str(self.root)}):
            result = subprocess.run([sys.executable, str(SCRIPT), "--status"],
                                    text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["target"], str(self.root / ".codex" / "hooks.json"))
        self.assertFalse(report["installed"])
        self.assertEqual(report["trusted"], "unknown")
        self.assertEqual(report["definitions"], installer.definitions())
        self.assertIn("/hooks", report["trust_review"])
        self.assertFalse((self.root / ".codex").exists())

    def test_definitions_protocol(self):
        definitions = installer.definitions()
        self.assertEqual(len(definitions), 10)
        for event, group in definitions.items():
            hook = group["hooks"][0]
            self.assertEqual(hook["type"], "command")
            self.assertFalse(hook["async"])
            self.assertEqual(hook["statusMessage"], f"Megaskill {event}")
            self.assertEqual(hook["timeout"], 3 if event == "Interrupt" else 5)
            self.assertEqual(shlex.split(hook["command"]),
                             [sys.executable, str(SCRIPT.with_name("mega_hooks.py")),
                              "--event", event])
            if event in {"SessionStart", "UserPromptSubmit", "SubagentStart"}:
                self.assertEqual(hook["additionalContextLimit"], 1500)
            else:
                self.assertNotIn("additionalContextLimit", hook)

    def test_shell_sensitive_interpreter_and_handler_paths(self):
        hostile = self.root / "space ' quote $(touch INJECTED); &" / "installer.py"
        with patch.object(installer, "__file__", str(hostile)), \
                patch.object(installer.sys, "executable", "/bin/python ' $(touch INJECTED)"):
            command = installer.definitions()["Stop"]["hooks"][0]["command"]
        self.assertEqual(shlex.split(command),
                         ["/bin/python ' $(touch INJECTED)",
                          str(hostile.resolve().with_name("mega_hooks.py")), "--event", "Stop"])
        result = subprocess.run(["/bin/sh", "-c", "set -- " + command + '; printf "%s\\n" "$@"'],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(), shlex.split(command))
        self.assertFalse((self.root / "INJECTED").exists())

    def test_install_twice_status_uninstall_missing_config(self):
        first = self.run_cli("--apply")
        self.assertEqual(first.returncode, 0, first.stderr)
        config_raw = self.target.read_bytes()
        sidecar = installer.manifest_path(self.target)
        manifest_raw = sidecar.read_bytes()
        self.assertIsNone(json.loads(manifest_raw)["original"])
        second = self.run_cli("--apply")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["changed_events"], [])
        self.assertEqual(self.target.read_bytes(), config_raw)
        self.assertEqual(sidecar.read_bytes(), manifest_raw)
        status = json.loads(self.run_cli("--status").stdout)
        self.assertTrue(status["installed"])
        self.assertEqual(status["trusted"], "unknown")
        self.assertEqual(status["definitions"], installer.definitions())
        preview = self.run_cli("--uninstall")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(self.target.read_bytes(), config_raw)
        removed = self.run_cli("--uninstall", "--apply")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertFalse(self.target.exists())
        self.assertEqual(json.loads(sidecar.read_bytes())["entries"], {})
        again = self.run_cli("--uninstall", "--apply")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertFalse(self.target.exists())

    def test_preserves_original_json_and_sibling_toml_bytes(self):
        original = b'{ "description": "original", "hooks": {"Stop": []}, "other": 9 }\n'
        self.target.write_bytes(original)
        sibling = self.root / "config.toml"
        sibling.write_bytes(b'# Preserve trust and features\n[features]\nhooks = false\n')
        sibling_raw = sibling.read_bytes()
        self.assertEqual(self.run_cli("--apply").returncode, 0)
        manifest = json.loads(installer.manifest_path(self.target).read_bytes())
        self.assertEqual(base64.b64decode(manifest["original"]), original)
        self.assertEqual(self.run_cli("--uninstall", "--apply").returncode, 0)
        self.assertEqual(self.target.read_bytes(), original)
        self.assertEqual(sibling.read_bytes(), sibling_raw)

    def test_uninstall_preserves_later_changes_and_other_handlers(self):
        unrelated = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo original"}]}
        self.write_json({"hooks": {"Stop": [unrelated]}, "custom": {"before": 1}})
        installer.inspect(self.target, apply=True)
        current = self.config()
        current["hooks"]["Stop"][0]["hooks"][0]["command"] = "echo later"
        later = {"hooks": [{"type": "command", "command": "echo new"}]}
        current["hooks"]["Stop"].append(later)
        current["hooks"]["NewEvent"] = [later]
        current["custom"]["after"] = 2
        self.write_json(current)
        installer.inspect(self.target, uninstall=True, apply=True)
        actual = self.config()
        self.assertEqual(actual["hooks"]["Stop"], [current["hooks"]["Stop"][0], later])
        self.assertEqual(actual["hooks"]["NewEvent"], [later])
        self.assertEqual(actual["custom"], {"before": 1, "after": 2})

    def test_modified_owned_definition_is_retained(self):
        installer.inspect(self.target, apply=True)
        current = self.config()
        current["hooks"]["Stop"][0]["hooks"][0]["timeout"] = 77
        self.write_json(current)
        result = self.run_cli("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Owned Stop changed", result.stderr)
        report = installer.inspect(self.target, uninstall=True, apply=True)
        self.assertEqual(report["preserved_modified_events"], ["Stop"])
        self.assertEqual(self.config(), {"hooks": {"Stop": current["hooks"]["Stop"]}})
        self.assertEqual(set(json.loads(installer.manifest_path(self.target).read_bytes())["entries"]), {"Stop"})
        self.assertFalse(installer.inspect(self.target, status=True)["installed"])

    def test_modified_matcher_or_extra_handler_kept_as_whole_group(self):
        installer.inspect(self.target, apply=True)
        current = self.config()
        current["hooks"]["Stop"][0]["matcher"] = "custom"
        current["hooks"]["SessionStart"][0]["hooks"].append({"command": "extra", "type": "command"})
        self.write_json(current)
        report = installer.inspect(self.target, uninstall=True, apply=True)
        self.assertEqual(set(report["preserved_modified_events"]), {"Stop", "SessionStart"})
        self.assertEqual(self.config()["hooks"],
                         {event: current["hooks"][event] for event in ("Stop", "SessionStart")})

    def test_preexisting_exact_definition_not_owned(self):
        group = installer.definitions()["Stop"]
        self.write_json({"hooks": {"Stop": [group]}})
        original = self.target.read_bytes()
        installer.inspect(self.target, apply=True)
        manifest = json.loads(installer.manifest_path(self.target).read_bytes())
        self.assertNotIn("Stop", manifest["entries"])
        installer.inspect(self.target, uninstall=True, apply=True)
        self.assertEqual(self.target.read_bytes(), original)

    def test_uninstall_without_manifest_does_not_claim_definitions(self):
        self.write_json({"hooks": {"Stop": [installer.definitions()["Stop"]]}})
        before = self.target.read_bytes()
        installer.inspect(self.target, uninstall=True, apply=True)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(installer.manifest_path(self.target).exists())

    def test_conflicting_status_message_rejected_before_write(self):
        self.write_json({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other",
                         "statusMessage": "Megaskill Stop"}]}]}})
        before = self.target.read_bytes()
        result = self.run_cli("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(installer.manifest_path(self.target).exists())

    def test_malformed_configs_rejected_without_mutation(self):
        for raw in (b'{broken', b'', b'[]', b'{"hooks":null}', b'{"hooks":{"Stop":{}}}',
                    b'{"hooks":{"Stop":[{}]}}', b'{"hooks":{"Stop":[{"hooks":[null]}]}}',
                    b'{"hooks":{},"hooks":{}}', b'{"other":NaN}'):
            with self.subTest(raw=raw):
                self.target.write_bytes(raw)
                result = self.run_cli("--apply")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.target.read_bytes(), raw)
                self.assertFalse(installer.manifest_path(self.target).exists())

    def test_toml_preserves_comments_tables_and_later_changes(self):
        target = self.root / "config.toml"
        original = b'# user config\nmodel = "test"\n[features]\nhooks = false\n\n[[hooks.Stop]]\nmatcher = "Bash"\n[[hooks.Stop.hooks]]\ntype = "command"\ncommand = "echo original"\n'
        target.write_bytes(original)
        installer.inspect(target, apply=True)
        installed = target.read_bytes()
        self.assertTrue(installed.startswith(original))
        self.assertTrue(installer.inspect(target, status=True)["installed"])
        installer.inspect(target, apply=True)
        self.assertEqual(target.read_bytes(), installed)
        later = b'\n# Added later\n[another]\nvalue = 12\n'
        target.write_bytes(installed + later)
        installer.inspect(target, uninstall=True, apply=True)
        self.assertEqual(target.read_bytes(), original + later)

    def test_toml_missing_and_original_restored_exactly(self):
        target = self.root / "config.toml"
        installer.inspect(target, apply=True)
        installer.inspect(target, uninstall=True, apply=True)
        self.assertFalse(target.exists())
        original = b'# no final newline\nmodel="test"'
        target.write_bytes(original)
        installer.inspect(target, apply=True)
        installer.inspect(target, uninstall=True, apply=True)
        self.assertEqual(target.read_bytes(), original)

    def test_modified_toml_owned_block_preserved(self):
        target = self.root / "config.toml"
        installer.inspect(target, apply=True)
        raw = target.read_text()
        stop = installer.toml_block("Stop", installer.definitions()["Stop"])
        modified = stop.replace("timeout = 5", "timeout = 99")
        target.write_text(raw.replace(stop, modified))
        report = installer.inspect(target, uninstall=True, apply=True)
        self.assertEqual(report["preserved_modified_events"], ["Stop"])
        self.assertEqual(target.read_text(), modified)

    def test_malformed_or_inline_toml_does_not_write(self):
        target = self.root / "config.toml"
        for raw in (b'[broken', b'hooks = {Stop = []}\n'):
            with self.subTest(raw=raw):
                target.write_bytes(raw)
                result = self.run_cli("--apply", target=target)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(target.read_bytes(), raw)
                self.assertFalse(installer.manifest_path(target).exists())

    def test_corrupt_manifest_refused(self):
        installer.inspect(self.target, apply=True)
        before = self.target.read_bytes()
        sidecar = installer.manifest_path(self.target)
        data = json.loads(sidecar.read_bytes())
        data["original_sha256"] = "bad"
        sidecar.write_text(json.dumps(data))
        result = self.run_cli("--uninstall", "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_bytes(), before)

    def test_malformed_ownership_records_fail_cleanly(self):
        installer.inspect(self.target, apply=True)
        before = self.target.read_bytes()
        sidecar = installer.manifest_path(self.target)
        original = sidecar.read_bytes()
        for field, value in (("entries", {"Stop": {"group": {"hooks": [None]}}}),
                             ("original", []), ("owner", "someone-else"),
                             ("target", str(self.root / "elsewhere.json"))):
            with self.subTest(field=field):
                data = json.loads(original)
                data[field] = value
                sidecar.write_text(json.dumps(data))
                result = self.run_cli("--uninstall", "--apply")
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(self.target.read_bytes(), before)

    def test_rollback_when_config_replace_fails(self):
        self.write_json({"keep": 1})
        before = self.target.read_bytes()
        real_write = installer.atomic_write
        def failing_write(path, raw):
            if path == self.target:
                raise OSError("injected write failure")
            real_write(path, raw)
        with patch.object(installer, "atomic_write", side_effect=failing_write):
            with self.assertRaisesRegex(OSError, "injected"):
                installer.inspect(self.target, apply=True)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(installer.manifest_path(self.target).exists())

    def test_rollback_uninstall_restores_manifest(self):
        installer.inspect(self.target, apply=True)
        before = self.target.read_bytes()
        sidecar = installer.manifest_path(self.target)
        manifest_before = sidecar.read_bytes()
        real_replace = installer.replace_if_unchanged
        def failing_replace(path, previous, after):
            if path == self.target:
                raise OSError("cannot remove config")
            real_replace(path, previous, after)
        with patch.object(installer, "replace_if_unchanged", side_effect=failing_replace):
            with self.assertRaises(OSError):
                installer.inspect(self.target, uninstall=True, apply=True)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(sidecar.read_bytes(), manifest_before)

    def test_rollback_failure_after_config_replace(self):
        self.write_json({"keep": 1})
        before = self.target.read_bytes()
        real_write = installer.atomic_write
        failed = False
        def fail_after_write(path, raw):
            nonlocal failed
            real_write(path, raw)
            if path == self.target and not failed:
                failed = True
                raise OSError("injected after replacement")
        with patch.object(installer, "atomic_write", side_effect=fail_after_write):
            with self.assertRaisesRegex(OSError, "after replacement"):
                installer.inspect(self.target, apply=True)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(installer.manifest_path(self.target).exists())

    def test_external_deletion_does_not_recreate_config_on_uninstall(self):
        self.write_json({"keep": 1})
        installer.inspect(self.target, apply=True)
        self.target.unlink()
        installer.inspect(self.target, uninstall=True, apply=True)
        self.assertFalse(self.target.exists())

    def test_removing_a_modified_entry_then_reinstalling(self):
        installer.inspect(self.target, apply=True)
        config = self.config()
        config["hooks"]["Stop"][0]["hooks"][0]["timeout"] = 10
        self.write_json(config)
        installer.inspect(self.target, uninstall=True, apply=True)
        config = self.config()
        config["hooks"].pop("Stop")
        config["new_setting"] = "retained"
        self.write_json(config)
        installer.inspect(self.target, uninstall=True, apply=True)
        installer.inspect(self.target, apply=True)
        self.assertTrue(installer.inspect(self.target, status=True)["installed"])
        installer.inspect(self.target, uninstall=True, apply=True)
        self.assertEqual(self.config()["new_setting"], "retained")

    def test_reinstall_preserves_new_empty_hook_containers(self):
        installer.inspect(self.target, apply=True)
        installer.inspect(self.target, uninstall=True, apply=True)
        self.write_json({"hooks": {"Stop": []}})
        before = self.config()
        installer.inspect(self.target, apply=True)
        installer.inspect(self.target, uninstall=True, apply=True)
        self.assertEqual(self.config(), before)

    def test_empty_original_hooks_container_preserved(self):
        self.write_json({"hooks": {}})
        original = self.target.read_bytes()
        installer.inspect(self.target, apply=True)
        installer.inspect(self.target, uninstall=True, apply=True)
        self.assertEqual(self.target.read_bytes(), original)

    def test_concurrent_change_not_overwritten_and_manifest_rolled_back(self):
        self.write_json({"before": 1})
        real_write = installer.atomic_write
        def concurrent_write(path, raw):
            real_write(path, raw)
            if path == installer.manifest_path(self.target):
                self.write_json({"external": 2})
        with patch.object(installer, "atomic_write", side_effect=concurrent_write):
            with self.assertRaisesRegex(ValueError, "Concurrent change"):
                installer.inspect(self.target, apply=True)
        self.assertEqual(self.config(), {"external": 2})
        self.assertFalse(installer.manifest_path(self.target).exists())

    def test_failed_backup_write_leaves_config_intact(self):
        self.write_json({"before": 1})
        before = self.target.read_bytes()
        with patch.object(installer, "atomic_write", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                installer.inspect(self.target, apply=True)
        self.assertEqual(self.target.read_bytes(), before)

    def test_cli_conflicting_modes_rejected(self):
        for flags in (("--apply", "--dry-run"), ("--apply", "--status"),
                      ("--status", "--uninstall"), ("--unknown",)):
            with self.subTest(flags=flags):
                result = self.run_cli(*flags)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.target.exists())

    def test_permissions_retained_and_symlink_refused(self):
        self.write_json({"keep": 1})
        self.target.chmod(0o640)
        installer.inspect(self.target, apply=True)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o640)
        installer.inspect(self.target, uninstall=True, apply=True)
        link = self.root / "linked.json"
        link.symlink_to(self.target)
        result = self.run_cli("--apply", target=link)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)


if __name__ == "__main__":
    unittest.main()
