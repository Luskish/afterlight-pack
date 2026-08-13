from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
TEMP_ROOT = Path(tempfile.gettempdir()).resolve()
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


class ManualAcquisitionRcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hygiene = importlib.import_module("rc_hygiene")
        cls.builder = importlib.import_module("afterlight_quests.builder")
        cls.acquisition = importlib.import_module("afterlight_quests.acquisition")
        cls.manifest = cls.acquisition.load_manifest(
            ROOT / cls.acquisition.FIXTURE_RELATIVE
        )
        cls.nonce = "task8-rc-shared-nonce"
        specification = importlib.util.spec_from_file_location(
            "afterlight_task8_rereview_build_quests",
            TOOLS / "build-quests.py",
        )
        assert specification is not None
        assert specification.loader is not None
        cls.build_script = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.build_script)

    def test_manual_acquisition_tests_use_platform_temp_root(self) -> None:
        forbidden_root = "/private" "/tmp"
        for relative in (
            "tools/tests/test_manual_acquisition.py",
            "tools/tests/test_manual_acquisition_rc.py",
        ):
            with self.subTest(relative=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn(forbidden_root, source)

    def canonical_sources(self) -> dict[str, bytes]:
        return {
            "kubejs/server_scripts/afterlight/generated_quest_item_audit.js": (
                self.builder._render_quest_item_audit(
                    ROOT / "config" / "ftbquests" / "quests"
                ).encode("utf-8")
            ),
            "kubejs/server_scripts/afterlight/generated_manual_acquisition_audit.js": (
                self.acquisition.render_manual_acquisition_audit(
                    self.manifest
                ).encode("utf-8")
            ),
        }

    def make_install(self, base: Path) -> tuple[Path, dict[str, bytes]]:
        install = base / "install"
        sources = self.canonical_sources()
        for relative, payload in sources.items():
            target = install / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        return install, sources

    def make_generated_pack(self, base: Path) -> Path:
        root = base / "pack"
        for relative in ("config", "global_packs", "kubejs", "mods"):
            shutil.copytree(ROOT / relative, root / relative)
        shutil.copytree(
            ROOT / "tools" / "fixtures",
            root / "tools" / "fixtures",
        )
        (root / "server-test" / "mods").mkdir(parents=True)
        self.build_script._build_quests(root)
        return root

    def test_seal_digest_is_stable_after_deterministic_quest_generation(self) -> None:
        before_inventory = self.hygiene._seal_code_inventory(ROOT, "repository")
        before_digest = self.hygiene._seal_code_corpus_digest(before_inventory)

        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temporary:
            generated_root = self.make_generated_pack(Path(temporary))
            generated_inventory = self.hygiene._seal_code_inventory(
                generated_root,
                "generated repository",
            )
            generated_digest = self.hygiene._seal_code_corpus_digest(
                generated_inventory
            )
            self.assertEqual(
                before_inventory[
                    "kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
                ],
                generated_inventory[
                    "kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
                ],
            )
            self.assertEqual(generated_digest, before_digest)
            self.assertEqual(
                generated_digest,
                self.hygiene.EXPECTED_SEAL_CODE_CORPUS_SHA256,
            )

    def test_seal_digest_normalization_still_rejects_generated_data_tamper(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temporary:
            base = Path(temporary)
            generated_root = self.make_generated_pack(base)
            install = base / "install"
            shutil.copytree(generated_root / "kubejs", install / "kubejs")
            generated_digest = self.hygiene._seal_code_corpus_digest(
                self.hygiene._seal_code_inventory(
                    generated_root,
                    "generated repository",
                )
            )
            self.assertEqual(
                generated_digest,
                self.hygiene.EXPECTED_SEAL_CODE_CORPUS_SHA256,
            )
            self.assertEqual(
                self.hygiene._verify_seal_code_corpus(generated_root, install),
                self.hygiene.EXPECTED_SEAL_CODE_CORPUS_SHA256,
            )
            relative = Path(
                "kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
            )
            for corpus_root in (generated_root, install):
                audit = corpus_root / relative
                source = audit.read_bytes()
                changed = source.replace(
                    b'"ae2:blank_pattern",',
                    b'"ae2:wrong_pattern",',
                    1,
                )
                self.assertNotEqual(changed, source)
                audit.write_bytes(changed)
            with self.assertRaisesRegex(
                self.hygiene.VerificationError,
                "not canonical",
            ):
                self.hygiene._verify_seal_code_corpus(generated_root, install)

    def test_dual_renderer_uses_one_nonce_and_writes_canonical_provenance(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temporary:
            install, sources = self.make_install(Path(temporary))
            result = self.hygiene.render_installed_quest_audits(
                ROOT,
                install,
                self.nonce,
            )
            verified = self.hygiene.verify_installed_quest_audits(
                ROOT,
                install,
                self.nonce,
            )
            self.assertEqual(result, verified)
            for relative, source in sources.items():
                rendered = (install / relative).read_bytes()
                self.assertEqual(rendered, source.replace(
                    b"__AFTERLIGHT_BOOT_NONCE__",
                    self.nonce.encode("ascii"),
                    1,
                ))
                self.assertEqual(rendered.count(self.nonce.encode("ascii")), 1)

            provenance_path = (
                install / "afterlight-runtime-audit-provenance.json"
            )
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            self.assertEqual(provenance["schema_version"], 1)
            self.assertEqual(provenance["nonce"], self.nonce)
            self.assertEqual(
                [entry["path"] for entry in provenance["audits"]],
                sorted(sources),
            )
            self.assertEqual(
                stat.S_IMODE(provenance_path.stat().st_mode),
                0o600,
            )
            self.assertEqual(
                provenance_path.read_bytes(),
                (
                    json.dumps(provenance, indent=2, sort_keys=True)
                    + "\n"
                ).encode("utf-8"),
            )
            gate = self.hygiene.render_installed_gate_audit(ROOT, self.nonce)
            self.assertIn(self.nonce.encode("ascii"), gate)

    def test_cli_exposes_exact_dual_audit_commands(self) -> None:
        parser = self.hygiene.build_parser()
        install_path = str(TEMP_ROOT / "install")
        for command in (
            "render-installed-quest-audits",
            "verify-quest-audits",
        ):
            parsed = parser.parse_args(
                [command, "--install", install_path, "--nonce", self.nonce]
            )
            self.assertEqual(parsed.command, command)

    def test_preflight_failure_rolls_back_without_rendering_first_audit(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temporary:
            install, sources = self.make_install(Path(temporary))
            acquisition_path = install / (
                "kubejs/server_scripts/afterlight/"
                "generated_manual_acquisition_audit.js"
            )
            acquisition_path.write_bytes(b"stale source\n")
            with self.assertRaisesRegex(
                self.hygiene.VerificationError,
                "pre-render source",
            ):
                self.hygiene.render_installed_quest_audits(
                    ROOT,
                    install,
                    self.nonce,
                )
            item_relative = (
                "kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
            )
            self.assertEqual(
                (install / item_relative).read_bytes(),
                sources[item_relative],
            )

    def test_second_write_failure_restores_first_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temporary:
            install, sources = self.make_install(Path(temporary))
            original_write = self.hygiene._atomic_runtime_write
            call_count = 0

            def fail_second(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise self.hygiene.VerificationError("injected write failure")
                return original_write(*args, **kwargs)

            with mock.patch.object(
                self.hygiene,
                "_atomic_runtime_write",
                side_effect=fail_second,
            ), self.assertRaisesRegex(
                self.hygiene.VerificationError,
                "injected write failure",
            ):
                self.hygiene.render_installed_quest_audits(
                    ROOT,
                    install,
                    self.nonce,
                )
            for relative, source in sources.items():
                self.assertEqual((install / relative).read_bytes(), source)

    def test_symlink_and_post_render_tamper_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temporary:
            base = Path(temporary)
            install, _ = self.make_install(base)
            acquisition_path = install / (
                "kubejs/server_scripts/afterlight/"
                "generated_manual_acquisition_audit.js"
            )
            target = base / "outside.js"
            target.write_bytes(acquisition_path.read_bytes())
            acquisition_path.unlink()
            acquisition_path.symlink_to(target)
            with self.assertRaisesRegex(
                self.hygiene.VerificationError,
                "symlink",
            ):
                self.hygiene.render_installed_quest_audits(
                    ROOT,
                    install,
                    self.nonce,
                )

        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temporary:
            install, _ = self.make_install(Path(temporary))
            self.hygiene.render_installed_quest_audits(
                ROOT,
                install,
                self.nonce,
            )
            item_path = install / (
                "kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
            )
            item_path.write_bytes(item_path.read_bytes() + b"// tamper\n")
            with self.assertRaisesRegex(
                self.hygiene.VerificationError,
                "post-render",
            ):
                self.hygiene.verify_installed_quest_audits(
                    ROOT,
                    install,
                    self.nonce,
                )


if __name__ == "__main__":
    unittest.main()
