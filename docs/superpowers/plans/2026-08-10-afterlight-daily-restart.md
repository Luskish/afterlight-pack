# AFTERLIGHT Daily Restart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the production idle-only timer with one predictable daily restart around 5:00 AM Eastern, including player warnings, a verified backup, and fail-closed safety checks.

**Architecture:** Extend the existing maintenance script with an explicit `scheduled` mode while preserving its default idle-safe mode. Start the scheduled service at 4:45 AM `America/New_York`, issue a complete 15-minute countdown, verify a fresh backup, and restart through the existing lifecycle wrapper even when players remain online.

**Tech Stack:** Bash, Python `unittest`, Docker Compose, internal RCON, systemd 245 on Ubuntu 20.04, GitHub Actions.

## Global Constraints

- Minecraft remains `1.21.1`, NeoForge remains `21.1.248`, and Java remains `21`.
- The restart target is approximately 5:00 AM `America/New_York` every day.
- Warnings occur at 15 minutes, 5 minutes, 1 minute, and immediately before restart.
- Online players do not cancel scheduled mode after warnings complete.
- No successful verified backup means no automated shutdown.
- Existing lock, container identity, start-time, health, and lifecycle-wrapper gates remain mandatory.
- `Persistent=false` prevents a missed timer from causing a redundant restart after host boot.
- No Chunky command, world pregen, world-border change, seed change, or worldgen change is in scope.
- No em dashes are permitted in source, tests, documentation, commit messages, or agent responses.
- No Packwiz command may run after the final local evidence commit.

---

## File Structure

- `server/afterlight-maintenance.sh`: Owns idle and scheduled maintenance control flow, RCON warnings, countdown waits, fail-closed validation, backup, and lifecycle restart.
- `tools/tests/test_server_maintenance.py`: Provides deterministic fake Docker, RCON, sleep, and lifecycle processes for both maintenance modes.
- `server/systemd/afterlight-maintenance.service`: Invokes scheduled mode under the existing hardened service sandbox.
- `server/systemd/afterlight-maintenance.timer`: Starts the 15-minute countdown at 4:45 AM Eastern each day.
- `docs/SERVER.md`: Supplies the complete operator-facing schedule, warning, backup, failure, and inspection behavior.
- `server/README.md`: Supplies the short host setup and maintenance summary.
- `docs/HANDOFF.md`: Records the selected production behavior and explicit pregen deferral for future agents.

### Task 1: Scheduled Restart Mode

**Files:**
- Modify: `tools/tests/test_server_maintenance.py`
- Modify: `server/afterlight-maintenance.sh`

**Interfaces:**
- Consumes: `server/afterlight-server.sh backup|stop|start|status`, Docker Compose service `minecraft`, `docker exec CONTAINER rcon-cli`, and `/run/afterlight/maintenance.lock`.
- Produces: `server/afterlight-maintenance.sh` with CLI `afterlight-maintenance.sh [idle|scheduled]`, where omitted mode is `idle`.
- Produces: scheduled warnings through `rcon-cli say MESSAGE` and delays of exactly `600`, `240`, and `60` seconds.

- [ ] **Step 1: Extend the fake-process harness**

Change `_run` so tests can invoke either mode:

```python
def _run(self, mode: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [str(MAINTENANCE)]
    if mode is not None:
        command.append(mode)
    return subprocess.run(
        command,
        cwd=ROOT,
        env=self.environment,
        text=True,
        capture_output=True,
        check=False,
    )
```

Add `FAKE_EVENT_LOG` to the test environment. Make the fake operator append `operator:backup`, `operator:stop`, `operator:start`, and `operator:status`. Make fake Docker distinguish `rcon-cli list` from `rcon-cli say`, append each warning as `rcon-say:MESSAGE`, and support `FAKE_RCON_SAY_FAIL_AT` as a one-based warning index. Add a fake `sleep` command that appends `sleep:SECONDS` without waiting.

- [ ] **Step 2: Write scheduled-mode regression tests**

Add these exact tests:

```python
def test_scheduled_mode_restarts_with_online_players_after_full_warning_sequence(self) -> None:
    self.environment["FAKE_RCON_OUTPUT"] = (
        "There are 2 of a max of 12 players online: FriendOne, FriendTwo"
    )
    result = self._run("scheduled")
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(
        self._operator_calls(), ["backup", "stop", "start", "status"]
    )
    self.assertIn("Scheduled restart: OK", result.stdout)

def test_scheduled_mode_orders_warnings_waits_backup_and_restart(self) -> None:
    result = self._run("scheduled")
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(
        self._events(),
        [
            "rcon-say:AFTERLIGHT restarts daily at 5:00 AM Eastern. Restart in 15 minutes.",
            "sleep:600",
            "rcon-say:AFTERLIGHT restart in 5 minutes. Please reach a safe stopping point.",
            "sleep:240",
            "rcon-say:AFTERLIGHT restart in 1 minute. Please disconnect safely.",
            "sleep:60",
            "rcon-say:AFTERLIGHT is restarting now. A verified world backup is being created.",
            "operator:backup",
            "operator:stop",
            "operator:start",
            "operator:status",
        ],
    )
```

Also add tests proving:

- each `FAKE_RCON_SAY_FAIL_AT` value from 1 through 4 exits nonzero before backup or stop;
- container ID drift, `StartedAt` drift, or health drift during any countdown revalidation exits before backup;
- backup failure exits before stop;
- an intentionally stopped server skips successfully;
- unknown modes and extra arguments fail before Docker is called;
- omitted mode and explicit `idle` both preserve all current idle-safe behavior.

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```bash
python3 -m unittest tools.tests.test_server_maintenance.ServerMaintenanceTests -v
```

Expected: the new scheduled tests fail because the script rejects the argument or does not produce the warning sequence.

- [ ] **Step 4: Implement explicit modes and shared validation**

Add a strict mode parser inside `main` after helper functions are defined:

```bash
main() {
  local mode=${1:-idle}
  if [[ "$#" -gt 1 ]]; then
    fail "Usage: server/afterlight-maintenance.sh [idle|scheduled]"
    return 1
  fi
  case "$mode" in
    idle) run_idle_maintenance ;;
    scheduled) run_scheduled_maintenance ;;
    *)
      fail "Usage: server/afterlight-maintenance.sh [idle|scheduled]"
      return 1
      ;;
  esac
}
```

Extract one shared identity and health validator:

```bash
validate_same_healthy_container() {
  local expected_container_id=$1
  local expected_started_at=$2
  local current_container_id
  local current_started_at
  local health

  current_container_id=$(compose ps -q minecraft) || return 1
  if [[ "$current_container_id" != "$expected_container_id" ]]; then
    fail "Minecraft container changed during maintenance"
    return 1
  fi
  current_started_at=$(docker inspect --format '{{.State.StartedAt}}' "$expected_container_id") || return 1
  if [[ "$current_started_at" != "$expected_started_at" ]]; then
    fail "Minecraft container start time changed during maintenance"
    return 1
  fi
  health=$(container_health "$expected_container_id") || return 1
  if [[ "$health" != "running|healthy" ]]; then
    fail "Minecraft became unhealthy during maintenance: $health"
    return 1
  fi
}
```

Add strict warning delivery:

```bash
announce_restart() {
  local container_id=$1
  local message=$2
  docker exec "$container_id" rcon-cli say "$message" </dev/null >/dev/null 2>&1 || {
    fail "RCON restart warning failed"
    return 1
  }
}
```

Scheduled mode must query and parse the current player count once, log `Scheduled restart: N players online`, and continue regardless of whether `N` is zero. It must issue each approved message, call `sleep 600`, `sleep 240`, and `sleep 60`, validate the same container after every wait, announce the immediate restart, run the existing verified backup command, validate once more, then call `stop`, `start`, and `status`. A player-count query failure remains fail-closed because warning delivery and the verified backup also depend on working RCON. Player count must never become a cancellation gate in scheduled mode.

Idle mode must keep the 20-hour minimum, both player-count checks, and all current failure messages.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```bash
python3 -m unittest tools.tests.test_server_maintenance.ServerMaintenanceTests -v
bash -n server/afterlight-maintenance.sh
```

Expected: every maintenance test passes and Bash syntax is valid.

- [ ] **Step 6: Run the full offline Python suite**

Run:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
```

Expected: all tests pass with only the repository's expected offline skips.

- [ ] **Step 7: Commit Task 1**

```bash
git add server/afterlight-maintenance.sh tools/tests/test_server_maintenance.py
git commit -m "feat(server): add warned scheduled restarts" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

### Task 2: Daily Eastern Timer and Operator Documentation

**Files:**
- Modify: `tools/tests/test_server_maintenance.py`
- Modify: `server/systemd/afterlight-maintenance.service`
- Modify: `server/systemd/afterlight-maintenance.timer`
- Modify: `docs/SERVER.md`
- Modify: `server/README.md`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Consumes: Task 1 CLI `server/afterlight-maintenance.sh scheduled`.
- Produces: systemd timer trigger `*-*-* 04:45:00 America/New_York` with `Persistent=false` and `AccuracySec=1s`.
- Produces: operator documentation that states countdown begins at 4:45 AM and restart begins around 5:00 AM Eastern.

- [ ] **Step 1: Replace the old systemd and documentation assertions**

Rename the systemd test to `test_systemd_timer_runs_warned_restart_daily_at_five_eastern`. Assert the service contains:

```python
for expected in (
    "Description=AFTERLIGHT daily warned server restart",
    "ExecStart=/opt/afterlight/server/afterlight-maintenance.sh scheduled",
    "TimeoutStartSec=infinity",
    "ConditionFileIsExecutable=/opt/afterlight/server/afterlight-maintenance.sh",
):
    self.assertIn(expected, service)
```

Assert the timer contains:

```python
for expected in (
    "OnCalendar=*-*-* 04:45:00 America/New_York",
    "Persistent=false",
    "AccuracySec=1s",
):
    self.assertIn(expected, timer)
self.assertNotIn("RandomizedDelaySec", timer)
self.assertNotIn("01,03,05,07,09,11,13,15,17,19,21,23", timer)
```

Assert combined documentation includes `5:00 AM Eastern`, `15 minutes`, `even when players are online`, `verified backup`, and `Pregen remains deferred`.

- [ ] **Step 2: Run the focused systemd test and verify RED**

Run:

```bash
python3 -m unittest \
  tools.tests.test_server_maintenance.ServerMaintenanceTests.test_systemd_timer_runs_warned_restart_daily_at_five_eastern \
  -v
```

Expected: FAIL because the old units still define two-hour idle checks.

- [ ] **Step 3: Update the hardened service and timer**

Set the service identity and command to:

```ini
[Unit]
Description=AFTERLIGHT daily warned server restart

[Service]
ExecStart=/opt/afterlight/server/afterlight-maintenance.sh scheduled
TimeoutStartSec=infinity
```

Keep every existing user, group, runtime directory, path restriction, privilege restriction, and filesystem hardening directive. Remove the unused `AFTERLIGHT_MIN_UPTIME_SECONDS` environment assignment from the production service.

Set the timer to:

```ini
[Unit]
Description=Warn at 4:45 AM and restart AFTERLIGHT around 5:00 AM Eastern

[Timer]
OnCalendar=*-*-* 04:45:00 America/New_York
Persistent=false
AccuracySec=1s
Unit=afterlight-maintenance.service

[Install]
WantedBy=timers.target
```

- [ ] **Step 4: Update all operator documentation**

Replace the idle-only sections in `docs/SERVER.md` and `server/README.md` with:

- countdown starts daily at 4:45 AM Eastern;
- approved warning times and exact restart target;
- restart proceeds even with online players;
- backup, container identity, and health failures abort before shutdown;
- missed runs do not catch up after host boot;
- commands for `systemd-analyze verify`, `systemd-analyze calendar '*-*-* 04:45:00 America/New_York'`, `systemctl list-timers`, and `journalctl`.

Add a concise Current RC2 Handoff bullet to `docs/HANDOFF.md` recording the selected daily restart behavior and that no deliberate Chunky pregen has run.

- [ ] **Step 5: Run focused tests and static checks**

Run:

```bash
python3 -m unittest tools.tests.test_server_maintenance.ServerMaintenanceTests -v
bash -n server/afterlight-maintenance.sh
git diff --check
if git diff --unified=0 -- \
  server/afterlight-maintenance.sh \
  tools/tests/test_server_maintenance.py \
  server/systemd/afterlight-maintenance.service \
  server/systemd/afterlight-maintenance.timer \
  docs/SERVER.md server/README.md docs/HANDOFF.md |
  sed -n '/^+/p' |
  LC_ALL=C grep $'\u2014'; then
  exit 1
fi
```

Expected: all maintenance tests and static checks pass.

- [ ] **Step 6: Commit Task 2**

```bash
git add \
  tools/tests/test_server_maintenance.py \
  server/systemd/afterlight-maintenance.service \
  server/systemd/afterlight-maintenance.timer \
  docs/SERVER.md server/README.md docs/HANDOFF.md
git commit -m "feat(server): schedule daily warned restarts" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

### Task 3: Verification, Promotion, and VPS Rollout

**Files:**
- Modify: `docs/HANDOFF.md` only if verification evidence needs correction before the final evidence commit.
- Deploy: `/opt/afterlight`, `/etc/systemd/system/afterlight-maintenance.service`, `/etc/systemd/system/afterlight-maintenance.timer` on the VPS.

**Interfaces:**
- Consumes: Task 2 tested script and units.
- Produces: green `dev` and `main`, a healthy VPS on exact `main`, and an enabled daily Eastern timer.

- [ ] **Step 1: Run the complete local non-Packwiz suite**

Run:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py'
shellcheck -x \
  server/afterlight-maintenance.sh \
  server/afterlight-server.sh \
  tools/*.sh
git diff --check
```

Expected: all tests pass, ShellCheck reports no finding, and the diff check is clean.

- [ ] **Step 2: Run the required Packwiz and server gates**

Run exactly once before the final evidence commit:

```bash
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
```

Expected: `VERIFY: ALL GREEN` and `SERVER BOOT: OK`.

Do not run Packwiz or `./tools/verify-pack.sh` again after the next commit.

- [ ] **Step 3: Record final local evidence and commit**

If the handoff evidence needs an exact test count or clarification, update only `docs/HANDOFF.md`. Then run:

```bash
git diff --check
git add docs/HANDOFF.md
git commit -m "docs(server): record scheduled restart verification" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
```

If `docs/HANDOFF.md` already contains exact correct evidence and has no diff, skip this commit. Require a clean worktree either way.

- [ ] **Step 4: Push `dev` and require exact-SHA CI**

```bash
git push origin dev
DEV_SHA=$(git rev-parse HEAD)
gh run list --workflow pack-ci --branch dev --limit 10
gh run watch RUN_ID --exit-status
gh run view RUN_ID --json headSha,conclusion,url
```

Select the run whose `headSha` equals `$DEV_SHA`. Expected: `conclusion` is `success`.

- [ ] **Step 5: Merge to `main` and require exact-SHA CI**

```bash
git switch main
git pull --ff-only origin main
git merge --no-ff dev \
  -m "merge: schedule daily warned restarts" \
  -m "Co-Authored-By: Codex <noreply@openai.com>"
git push origin main
MAIN_SHA=$(git rev-parse HEAD)
gh run list --workflow pack-ci --branch main --limit 10
gh run watch RUN_ID --exit-status
gh run view RUN_ID --json headSha,conclusion,url
```

Select the run whose `headSha` equals `$MAIN_SHA`. Expected: `conclusion` is `success`.

- [ ] **Step 6: Restore temporary, least-duration VPS access**

Generate a new one-use Ed25519 key outside the repository, have Shane add only its public key to root's `authorized_keys`, and verify batch SSH. Never store the private key or VPS address in Git.

- [ ] **Step 7: Update the VPS transactionally**

On the VPS:

```bash
sudo systemctl stop afterlight-maintenance.timer
sudo -u afterlight git -C /opt/afterlight fetch origin main
sudo -u afterlight git -C /opt/afterlight switch main
sudo -u afterlight git -C /opt/afterlight merge --ff-only origin/main
cd /opt/afterlight
sudo -u afterlight server/afterlight-server.sh update
install -m 0644 server/systemd/afterlight-maintenance.service /etc/systemd/system/
install -m 0644 server/systemd/afterlight-maintenance.timer /etc/systemd/system/
systemd-analyze verify \
  /etc/systemd/system/afterlight-maintenance.service \
  /etc/systemd/system/afterlight-maintenance.timer
systemd-analyze calendar '*-*-* 04:45:00 America/New_York'
systemctl daemon-reload
systemctl enable --now afterlight-maintenance.timer
```

The update wrapper must print a verified backup path and return the server to healthy state before the new timer is enabled.

- [ ] **Step 8: Run the live VPS gauntlet**

Verify:

```bash
sudo -u afterlight git -C /opt/afterlight status --short
sudo -u afterlight git -C /opt/afterlight rev-parse HEAD
cat /srv/afterlight/data/.afterlight-pack-sha
cd /opt/afterlight
sudo -u afterlight server/afterlight-server.sh status
systemctl is-enabled afterlight-maintenance.timer
systemctl is-active afterlight-maintenance.timer
systemctl list-timers afterlight-maintenance.timer --no-pager
systemctl cat afterlight-maintenance.service afterlight-maintenance.timer
journalctl -u afterlight-maintenance.service -n 50 --no-pager
```

Require the repository SHA and deployed marker to equal exact green `main`, a clean checkout, `running|healthy`, an enabled active timer, and the next trigger corresponding to 4:45 AM Eastern. Do not manually start the scheduled service merely to test it because that would initiate the real 15-minute forced restart.

- [ ] **Step 9: Remove temporary access and finalize**

Remove only the exact temporary public-key material from remote `authorized_keys`, prove a new connection with that key is denied, delete the local temporary key, and verify local `main` remains clean at `origin/main`.

Final handoff must state:

- countdown starts daily at 4:45 AM Eastern;
- restart begins around 5:00 AM even with players online;
- warning or backup failure prevents shutdown;
- automatic backups still run every 6 hours;
- no deliberate world pregen has run;
- Chunky remains installed but unused until gameplay validation is complete.
