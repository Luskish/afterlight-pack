from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"
LEDGER = ROOT / "docs" / "PROJECT_MEMORY.md"
SKILL = ROOT / ".agents" / "skills" / "afterlight-project-memory" / "SKILL.md"
EXPECTED_FIELDS = (
    "Date",
    "Category",
    "Status",
    "Subsystem",
    "Summary",
    "Evidence",
    "Files or Commit",
    "Impact",
    "Follow-up",
)
ALLOWED_CATEGORIES = {
    "issue",
    "vulnerability",
    "addition",
    "failure",
    "success",
    "decision",
}
ALLOWED_STATUSES = {
    "open",
    "investigating",
    "resolved",
    "verified",
    "accepted",
    "superseded",
}


def split_event_blocks(ledger: str) -> dict[str, str]:
    event_blocks: dict[str, str] = {}
    blocks = re.split(r"(?m)^### (MEM-\d{4}-\d{2}-\d{2}-\d{3})\n", ledger)
    for index in range(1, len(blocks), 2):
        event_id = blocks[index]
        body = blocks[index + 1]
        if event_id in event_blocks:
            raise AssertionError(f"duplicate memory event ID: {event_id}")
        event_blocks[event_id] = body
    return event_blocks


def parse_events(ledger: str) -> dict[str, dict[str, str]]:
    events: dict[str, dict[str, str]] = {}
    for event_id, body in split_event_blocks(ledger).items():
        fields = re.findall(r"(?m)^- \*\*([^*]+):\*\* (.*)$", body)
        events[event_id] = dict(fields)
        if len(fields) != len(events[event_id]):
            raise AssertionError(f"duplicate field in memory event: {event_id}")
    return events


class ProjectMemoryContractTests(unittest.TestCase):
    def test_guardrails_require_memory_skill_before_and_after_tasks(self) -> None:
        agents = AGENTS.read_text(encoding="utf-8")

        self.assertIn("afterlight-project-memory", agents)
        self.assertRegex(agents, r"(?i)before (?:starting )?(?:any|every) task")
        self.assertRegex(agents, r"(?i)(?:after|before completing) (?:any|every) task")
        self.assertIn("docs/PROJECT_MEMORY.md", agents)

    def test_ledger_defines_complete_event_schema(self) -> None:
        ledger = LEDGER.read_text(encoding="utf-8")

        for field in EXPECTED_FIELDS:
            with self.subTest(field=field):
                self.assertRegex(ledger, rf"(?m)^- \*\*{re.escape(field)}:\*\*")

        for category in ALLOWED_CATEGORIES:
            with self.subTest(category=category):
                self.assertRegex(ledger, rf"(?i)\b{category}\b")

    def test_every_event_has_exact_schema_and_allowed_values(self) -> None:
        ledger = LEDGER.read_text(encoding="utf-8")
        events = parse_events(ledger)

        self.assertTrue(events)
        for event_id, event in events.items():
            with self.subTest(event_id=event_id):
                body = split_event_blocks(ledger)[event_id]
                nonempty_lines = [line for line in body.splitlines() if line.strip()]
                self.assertEqual(len(nonempty_lines), len(EXPECTED_FIELDS))
                for line in nonempty_lines:
                    self.assertRegex(line, r"^- \*\*[^*]+:\*\* \S.*$")
                self.assertEqual(tuple(event), EXPECTED_FIELDS)
                self.assertRegex(event["Date"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertEqual(event["Date"], event_id[4:14])
                self.assertIn(event["Category"], ALLOWED_CATEGORIES)
                self.assertIn(event["Status"], ALLOWED_STATUSES)
                for field, value in event.items():
                    self.assertTrue(value.strip(), f"{event_id} has empty {field}")

    def test_event_bodies_reject_identity_secrets_and_raw_progress(self) -> None:
        ledger = LEDGER.read_text(encoding="utf-8")
        event_blocks = split_event_blocks(ledger)
        sensitive_patterns = {
            "UUID": r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
            "IPv4 address": r"(?<![\d.])(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?![\d.])",
            "credential": r"(?i)\b(?:gh[pousr]_[A-Za-z0-9]{20,}|bearer\s+[A-Za-z0-9._~-]{16,})\b",
            "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            "identity field": r"(?i)\b(?:player(?:[ _-]?name)?|username|uuid|ip(?:[ _-]?address)?)\s*[:=]\s*\S+",
            "raw progress": r"(?i)\b(?:task_progress|claimed_rewards|completion_count|player_data)\s*[:=]\s*[^,.;]+",
        }
        for event_id, body in event_blocks.items():
            for label, pattern in sensitive_patterns.items():
                with self.subTest(event_id=event_id, sensitive=label):
                    self.assertNotRegex(body, pattern)

    def test_skill_requires_search_update_and_verification(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")

        self.assertRegex(skill, r"(?i)search.*docs/PROJECT_MEMORY\.md")
        self.assertRegex(skill, r"(?i)append|update")
        self.assertRegex(skill, r"(?i)same-session evidence")
        self.assertRegex(skill, r"(?i)issue.*vulnerability.*addition.*failure.*success.*decision")
        self.assertIn("Co-Authored-By", skill)

        openai_yaml = (SKILL.parent / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("$afterlight-project-memory", openai_yaml)

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
