---
name: afterlight-project-memory
description: Maintain and query AFTERLIGHT's durable cross-agent project memory. Use before and after every repository task, incident investigation, bug fix, feature addition, release, deployment, design decision, or handoff. Records verified issues, vulnerabilities, additions, failures, successes, and decisions without secrets or live player data.
---

# AFTERLIGHT Project Memory

Use `docs/PROJECT_MEMORY.md` as the canonical history shared by Codex, Claude, and other agents. External memory tools can improve recall, but they never replace the committed ledger.

## Before Work

1. Read `AGENTS.md`.
2. Search `docs/PROJECT_MEMORY.md` using the subsystem, symptom, file, mod, quest ID, command, or release term involved.
3. Search any available external memory index with the same terms.
4. Reuse prior evidence and decisions only after confirming they still apply to the current commit and environment.

Example:

```bash
rg -ni "signal|packet|quest|steel|release" docs/PROJECT_MEMORY.md
```

## During Work

Capture candidate events as they occur. The six required operational categories are issue, vulnerability, addition, failure, success, and decision. Do not call an event successful until same-session evidence proves it.

Use these status values consistently:

- `open`: known and unresolved
- `investigating`: root cause not yet proven
- `resolved`: root cause fixed with focused evidence
- `verified`: full required gates passed
- `accepted`: deliberate decision or documented residual risk
- `superseded`: replaced by a newer event, linked in Follow-up

## After Work

Before reporting completion:

1. Append a new event or update the matching existing event.
2. Include date, category, status, subsystem, summary, evidence, files or commit, impact, and follow-up.
3. Put commands and exact pass or failure markers in Evidence.
4. Link the fixing commit when available.
5. Keep the summary searchable and concise.
6. Run the project-memory contract test and the required task-specific verification.

```bash
python3 -m unittest tools.tests.test_project_memory -v
```

## Privacy and Integrity

- Never record secrets, player names, UUIDs, raw live progress, access tokens, private keys, IP addresses, or production backup contents.
- Do not paste large logs. Record the minimal diagnostic line, command, artifact hash, or test marker needed for recall.
- Do not rewrite history to hide a failure. Update its status and add the resolution evidence.
- Do not infer success from a prior session. Re-run the required check.
- Do not commit live snapshots or temporary evidence directories.

## Commit Rule

Memory commits follow the repository attribution rule and include `Co-Authored-By: Codex <noreply@openai.com>` when Codex authored them.
