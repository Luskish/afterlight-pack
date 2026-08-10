# AFTERLIGHT Daily Restart Design

Date: 2026-08-10

Status: approved in conversation, pending written-spec review

## Context

The current systemd timer checks every two hours and restarts only when the Minecraft container has been healthy for at least 20 hours and RCON reports zero players. Shane wants one predictable restart every day even when players are online.

The intended restart time is 5:00 AM in `America/New_York`. The operation must warn connected players, create a verified backup, and fail without stopping the server if any safety-critical step fails.

Chunky is installed, but no deliberate world pregen has been run. Pregen remains deferred until the release candidate has completed real gameplay and bug validation.

## Goals

- Restart the dedicated server once daily at approximately 5:00 AM Eastern.
- Warn players at 15 minutes, 5 minutes, 1 minute, and immediately before shutdown.
- Restart even when players remain online after the warning sequence.
- Create and verify a fresh backup before stopping Minecraft.
- Preserve the existing operation lock, container identity checks, health checks, lifecycle wrapper, and fail-closed behavior.
- Follow Eastern daylight-saving transitions automatically.

## Non-Goals

- Running or scheduling Chunky pregen.
- Changing the world border, seed, generation settings, or existing chunks.
- Changing JVM memory, garbage collector settings, mod configuration, quests, recipes, or pack content.
- Restarting more than once daily unless an operator explicitly invokes a lifecycle command.

## Selected Approach

Extend `server/afterlight-maintenance.sh` with an explicit scheduled mode and point the existing systemd service at that mode. The default idle-safe mode remains available for direct operator use, but the production timer no longer invokes it automatically.

The timer starts the service at 4:45 AM Eastern. The service runs the complete 15-minute warning sequence, then begins the verified backup and restart at approximately 5:00 AM. If the service starts late, it still gives the full warning period instead of shortening player notice.

The timer uses an IANA timezone expression so daylight-saving changes do not require edits:

```ini
OnCalendar=*-*-* 04:45:00 America/New_York
Persistent=false
AccuracySec=1s
```

`Persistent=false` is deliberate. A host boot already restarts the JVM, so a missed 4:45 AM event must not cause a second immediate restart after boot. Ubuntu 20.04 systemd supports IANA timezone calendar expressions, and deployment validation will run `systemd-analyze calendar` on the target VPS.

## Scheduled Restart Flow

1. Acquire the existing nonblocking maintenance lock. If another maintenance operation owns it, skip without disturbing the server.
2. Resolve the Minecraft container. If Minecraft is intentionally stopped, skip successfully.
3. Require `running|healthy`, then capture the exact container ID and `StartedAt` value.
4. Broadcast a 15-minute warning through internal RCON.
5. Wait 10 minutes, revalidate the same container and health, then broadcast the 5-minute warning.
6. Wait 4 minutes, revalidate again, then broadcast the 1-minute warning.
7. Wait 1 minute, revalidate again, then broadcast the immediate restart warning.
8. Run `server/afterlight-server.sh backup` and require the returned path to be a new regular recoverable archive.
9. Revalidate the exact container ID, start time, and health after backup.
10. Stop and start through the lifecycle wrapper, wait for healthy status, and log the verified backup path.

The player count is informational in scheduled mode. Online players do not cancel the restart after the warning sequence.

## Failure Behavior

- Warning delivery failure aborts the operation before shutdown so players are never removed without notice by this automation.
- A missing container, changed container ID, changed start time, or unhealthy container aborts the remaining sequence.
- Backup failure aborts before shutdown and leaves the running server untouched.
- A manual restart during the countdown changes container identity, causing the scheduled operation to exit without a second restart.
- A concurrent maintenance run fails the nonblocking lock and exits without waiting or restarting.
- The systemd service retains `TimeoutStartSec=infinity` so systemd cannot terminate the 15-minute sequence between backup and restart.

## Player Messages

Messages use the server RCON `say` command and identify the daily AFTERLIGHT restart clearly:

- `AFTERLIGHT restarts daily at 5:00 AM Eastern. Restart in 15 minutes.`
- `AFTERLIGHT restart in 5 minutes. Please reach a safe stopping point.`
- `AFTERLIGHT restart in 1 minute. Please disconnect safely.`
- `AFTERLIGHT is restarting now. A verified world backup is being created.`

## Alternatives Considered

### Restart Every 24 Hours From Container Start

Rejected because the wall-clock time drifts after manual restarts, updates, and host reboots. Players would not have one memorable maintenance time.

### Restart Every 12 Hours

Rejected because it creates unnecessary interruptions for a private friend server and provides little practical benefit over one predictable daily JVM reset.

### Keep Idle-Only Restarts

Rejected because an active friend group can prevent maintenance indefinitely, which is the behavior Shane asked to change.

## Verification

Automated tests will prove:

- The timer targets 4:45 AM `America/New_York`, has no random delay, and does not catch up missed runs.
- Scheduled mode restarts with zero or nonzero online players.
- Warning order and wait durations are exact.
- Every warning failure, health failure, identity change, and backup failure aborts before stop.
- The verified backup occurs after the countdown and before stop.
- The existing idle-safe mode keeps its current behavior when invoked directly.
- Shell syntax, executable mode, systemd hardening, and documentation remain valid.

Repository verification requires the complete Python suite, `./tools/verify-pack.sh`, a fresh `BOOT_TIMEOUT=600 ./tools/server-test.sh`, ShellCheck, clean Git state, and green `pack-ci` on `dev` before promotion.

VPS verification requires `systemd-analyze verify`, `systemd-analyze calendar`, an enabled and active timer with the correct next Eastern trigger, an unchanged healthy Minecraft container after installation, and journal evidence from a safe direct validation path. The first production scheduled restart will provide the final real-time countdown and restart evidence.

## World Pregen Decision

No Chunky command will be run as part of this change. The current world remains limited to chunks generated naturally by startup and player exploration. Pregen will receive its own radius, dimension, storage, backup, and performance design only after the group confirms the release candidate has no world-generation blockers.

## References

- Ubuntu 20.04 `systemd.time`: https://manpages.ubuntu.com/manpages/focal/man7/systemd.time.7.html
- Ubuntu 20.04 `systemd.timer`: https://manpages.ubuntu.com/manpages/focal/man5/systemd.timer.5.html
