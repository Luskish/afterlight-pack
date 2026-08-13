from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"
LEDGER = ROOT / "docs" / "PROJECT_MEMORY.md"
SKILL = ROOT / ".agents" / "skills" / "afterlight-project-memory" / "SKILL.md"


class ProjectMemoryContractTests(unittest.TestCase):
    def test_guardrails_require_memory_skill_before_and_after_tasks(self) -> None:
        agents = AGENTS.read_text(encoding="utf-8")

        self.assertIn("afterlight-project-memory", agents)
        self.assertRegex(agents, r"(?i)before (?:starting )?(?:any|every) task")
        self.assertRegex(agents, r"(?i)(?:after|before completing) (?:any|every) task")
        self.assertIn("docs/PROJECT_MEMORY.md", agents)

    def test_ledger_defines_complete_event_schema(self) -> None:
        ledger = LEDGER.read_text(encoding="utf-8")

        for field in (
            "Date",
            "Category",
            "Status",
            "Subsystem",
            "Summary",
            "Evidence",
            "Files or Commit",
            "Impact",
            "Follow-up",
        ):
            with self.subTest(field=field):
                self.assertRegex(ledger, rf"(?m)^- \*\*{re.escape(field)}:\*\*")

        for category in (
            "issue",
            "vulnerability",
            "addition",
            "failure",
            "success",
            "decision",
        ):
            with self.subTest(category=category):
                self.assertRegex(ledger, rf"(?i)\b{category}\b")

    def test_skill_requires_search_update_and_verification(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")

        self.assertRegex(skill, r"(?i)search.*docs/PROJECT_MEMORY\.md")
        self.assertRegex(skill, r"(?i)append|update")
        self.assertRegex(skill, r"(?i)same-session evidence")
        self.assertRegex(skill, r"(?i)issue.*vulnerability.*addition.*failure.*success.*decision")
        self.assertIn("Co-Authored-By", skill)

    def test_memory_files_forbid_sensitive_live_data(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in (AGENTS, LEDGER, SKILL)
        )

        for phrase in (
            "secrets",
            "player names",
            "UUIDs",
            "raw live progress",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

    def test_memory_files_do_not_contain_em_dash(self) -> None:
        for path in (AGENTS, LEDGER, SKILL):
            with self.subTest(path=path):
                self.assertNotIn("\N{EM DASH}", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
