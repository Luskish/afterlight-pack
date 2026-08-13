# AFTERLIGHT Project Memory

This committed ledger is the canonical cross-agent memory for AFTERLIGHT. Search it before work and update it before completion. External memory indexes can assist recall but do not override this file.

## Event Schema

Every event uses the following fields. Update the original event when its status changes.

- **Date:** `YYYY-MM-DD`
- **Category:** `issue`, `vulnerability`, `addition`, `failure`, `success`, or `decision`
- **Status:** `open`, `investigating`, `resolved`, `verified`, `accepted`, or `superseded`
- **Subsystem:** Searchable project area, mod, quest, release stage, or infrastructure component
- **Summary:** One concise statement of what happened
- **Evidence:** Same-session command, failure marker, test result, artifact digest, or production check
- **Files or Commit:** Repository paths and fixing or deciding commit when available
- **Impact:** Player, operator, security, compatibility, or maintenance consequence
- **Follow-up:** Next action, residual risk, or `None`

## Privacy Rules

- Never record secrets, player names, UUIDs, raw live progress, access tokens, private keys, IP addresses, or production backup contents.
- Keep evidence minimal and reproducible. Do not paste complete logs or private artifacts.
- A success requires same-session evidence. A prior agent's claim is context, not proof.

## Events

### MEM-2026-08-13-001

- **Date:** 2026-08-13
- **Category:** decision
- **Status:** accepted
- **Subsystem:** Cross-agent continuity
- **Summary:** The committed project ledger is canonical because the available external memory index had no prior AFTERLIGHT observations and exposed no write operation.
- **Evidence:** External memory search returned no matching observations; repository guardrails and contract tests define the fallback.
- **Files or Commit:** `AGENTS.md`, `.agents/skills/afterlight-project-memory/SKILL.md`, `tools/tests/test_project_memory.py`
- **Impact:** Codex and Claude share durable history through Git even when session memory is absent.
- **Follow-up:** Search both stores before work and keep this ledger current.

### MEM-2026-08-13-002

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** Signal companion networking
- **Summary:** ECHO Pin and Claim actions disconnected clients because the server attempted to encode an invalid custom payload.
- **Evidence:** Client disconnect reports named `minecraft:custom_payload`; the Signal 0.2.1 focused tests and server boot passed after the payload fix.
- **Files or Commit:** `30a5416` and the Signal companion source under `mods-src/`
- **Impact:** Players can use Archive, Pin, and Claim without losing the connection.
- **Follow-up:** Treat every custom payload path as client/server compatibility code and retain focused packet tests.

### MEM-2026-08-13-003

- **Date:** 2026-08-13
- **Category:** issue
- **Status:** resolved
- **Subsystem:** FTB Quests, Slow Fire
- **Summary:** The Coke Oven quest could not progress because it required a held item even though completion is represented by a formed multiblock.
- **Evidence:** The task now tracks the verified Immersive Engineering multiblock formation advancement and the quest and server gates passed.
- **Files or Commit:** `5a41531`
- **Impact:** Normal Coke Oven construction completes Slow Fire without admin intervention.
- **Follow-up:** Prefer exact installed advancements for formed multiblocks when no inventory item can prove completion.

### MEM-2026-08-13-004

- **Date:** 2026-08-13
- **Category:** addition
- **Status:** verified
- **Subsystem:** FTB Quests, Steel Yourself
- **Summary:** Steel Yourself accepts any steel ingot represented by the common `c:ingots/steel` tag through FTB Filter System.
- **Evidence:** Focused quest tests passed, `VERIFY: ALL GREEN` passed, and `SERVER BOOT: OK` passed with FTB Filter System 21.1.4 on both sides.
- **Files or Commit:** `7fcbc3a`
- **Impact:** Cross-mod steel production no longer blocks story progression.
- **Follow-up:** Audit other item tasks, but generalize only commodities with equivalent semantics and verified runtime tags.

### MEM-2026-08-13-005

- **Date:** 2026-08-13
- **Category:** issue
- **Status:** resolved
- **Subsystem:** CurseForge client installation
- **Summary:** A friend received a JavaFML provider mismatch after installing a SmartBrainLib artifact from the wrong loader line despite selecting a NeoForge-labeled file.
- **Evidence:** The exact pack-managed dependency worked in a clean Prism install; replacing the manual CurseForge artifact with the release-managed file restored compatibility.
- **Files or Commit:** Packwiz SmartBrainLib metadata and launcher archives
- **Impact:** Manual mod replacement can silently create loader-line mismatches and prevent startup.
- **Follow-up:** Distribute immutable launcher archives and tell players not to mix manually downloaded dependencies into managed instances.

### MEM-2026-08-13-006

- **Date:** 2026-08-13
- **Category:** vulnerability
- **Status:** resolved
- **Subsystem:** Public release artifacts
- **Summary:** An earlier CI artifact path could expose a jar-bearing CurseForge export without the final release inventory and archive classification gates.
- **Evidence:** The jar-bearing artifact was deleted, CI now publishes metadata-safe output, and the release pipeline enforces a five-file flat inventory with archive inspection.
- **Files or Commit:** `98f62b9`, `AGENTS.md`, release artifact tests
- **Impact:** Public delivery no longer depends on an unclassified intermediate archive.
- **Follow-up:** Reject extra files, links, unsafe paths, secrets, and checksum drift on every immutable release.

### MEM-2026-08-13-007

- **Date:** 2026-08-13
- **Category:** decision
- **Status:** accepted
- **Subsystem:** Story cohesion and live progress
- **Summary:** The main story remains the required spine while eight optional field manuals teach linked mods from zero without becoming dependencies.
- **Evidence:** The approved design freezes existing identities, defines a complete compatibility fixture, and requires canonical pre-deploy and post-deploy progress comparison.
- **Files or Commit:** `76389da`, `docs/superpowers/specs/2026-08-13-afterlight-story-cohesion-design.md`
- **Impact:** Story guidance can improve without invalidating completed, active, claimed, or pinned player state.
- **Follow-up:** Fail the build or deployment on any undeclared quest corpus or live progress mutation.

### MEM-2026-08-13-008

- **Date:** 2026-08-13
- **Category:** success
- **Status:** verified
- **Subsystem:** Release verification discipline
- **Summary:** AFTERLIGHT requires static pack validation, a fresh Java 21 dedicated-server boot, exact-SHA CI, immutable artifact inspection, and zero-player guarded deployment before production claims.
- **Evidence:** `./tools/verify-pack.sh` requires `VERIFY: ALL GREEN`; `BOOT_TIMEOUT=600 ./tools/server-test.sh` requires `SERVER BOOT: OK`; release and deployment tests encode the remaining gates.
- **Files or Commit:** `AGENTS.md`, `tools/verify-pack.sh`, `tools/server-test.sh`, release scripts and tests
- **Impact:** Client/server parity and deployment safety are executable contracts instead of agent assumptions.
- **Follow-up:** Re-run every applicable gate in the same session as each release.

### MEM-2026-08-13-009

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** Local skill validation
- **Summary:** The system skill validator could not start under the default Python because PyYAML was not installed.
- **Evidence:** The first run failed with `ModuleNotFoundError: No module named 'yaml'`; a disposable virtual environment with PyYAML then printed `Skill is valid!`.
- **Files or Commit:** `.agents/skills/afterlight-project-memory/SKILL.md`
- **Impact:** Project skill validation remains reproducible without changing the repository or system Python.
- **Follow-up:** Use `/tmp/afterlight-skill-validator/bin/python` for subsequent local skill validation in this session.
