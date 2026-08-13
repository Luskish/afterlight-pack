# AFTERLIGHT Friend Server

This directory contains the private-friend Docker Compose stack and its operator command. The stack runs Minecraft plus continuous backups. RCON stays inside the Compose network.

## Host Setup

The supported model is one normal dedicated operator account with access to Docker. Run these commands as that operator from the repository root on the Linux host:

```bash
cp server/.env.example server/.env
AFTERLIGHT_USER=$(id -un)
AFTERLIGHT_GROUP=$(id -gn)
sudo install -d -o "$AFTERLIGHT_USER" -g "$AFTERLIGHT_GROUP" -m 0750 /srv/afterlight/data /srv/afterlight/backups
sudo install -d -o "$AFTERLIGHT_USER" -g "$AFTERLIGHT_GROUP" -m 0700 /etc/afterlight/secrets
umask 077
openssl rand -base64 36 > /etc/afterlight/secrets/rcon_password
chmod 0600 /etc/afterlight/secrets/rcon_password
server/afterlight-server.sh doctor
server/afterlight-server.sh start
```

Each path value in `server/.env` must match `^/([A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$`. Dollar signs, quotes, backslashes, whitespace, and comments are rejected so the operator and Docker Compose read identical literal paths. Memory values use positive whole gigabytes. Initial memory cannot exceed the maximum heap, and the container limit must leave at least 2 GiB above that heap.

The Minecraft service sets `mem_swappiness: 1`, the lowest value production Docker Compose reliably enforces. Numeric zero currently inherits the host default instead. Install `sysstat` on the host and use `sar -u 1 5` for a live CPU sample. Use Spark during real multiplayer activity before changing heap, garbage collection, view distance, simulation distance, or ServerCore gameplay settings.

Populate the Minecraft whitelist before sharing the server address. RCON `25575` must never be forwarded.

The operator command pins each start to the repository's immutable Packwiz revision and records it as `DATA_DIR/.afterlight-pack-sha`. `start` refuses an existing world from another or unknown revision, so use `update` after changing the checkout. Backups are accepted only when they contain that marker plus a nonempty `world/level.dat`.

## Operations

```bash
server/afterlight-server.sh doctor
server/afterlight-server.sh start
server/afterlight-server.sh stop
server/afterlight-server.sh status
server/afterlight-server.sh backup
server/afterlight-server.sh update
sudo server/afterlight-quest-safe-update.sh EXPECTED_40_CHARACTER_SHA --confirm
server/afterlight-server.sh rollback /srv/afterlight/backups/afterlight-20260809-120000.tar.zst --confirm
```

`update` is only for revisions that do not change the quest corpus. It creates and verifies an on-demand backup before recreating Minecraft at the new exact repository revision. A failed health check leaves both services stopped and prints the exact rollback command. Rollback performs a preflight check for `world/level.dat` and the recorded revision before stopping, renames the current data tree to a timestamped rescue sibling, starts the restored world from the archive's immutable Packwiz revision, and never deletes the selected archive or either world tree.

Every revision that changes FTB Quests data must use `afterlight-quest-safe-update.sh` through `sudo`, because the transaction owns a host firewall rule and the root-only quarantine marker. The command requires the exact 40-character repository `HEAD`, takes the maintenance lock, proves zero players twice, installs one uniquely commented `DOCKER-USER` rule for new TCP `25565` connections, flushes and stops the world, and creates a mode `0700` snapshot. The snapshot contains privacy-safe canonical FTB Quests and FTB Teams hashes plus a direct post-stop full backup with SHA-256 and extraction proof. The candidate starts and stops once behind the gate for canonical progress and whitelist checks, then starts a second time before the owned rule is removed. RCON remains internal to Compose throughout.

Any candidate failure keeps the gate closed while the transaction restores the prior full data tree and exact prior Packwiz revision. The restored release must start, stop, match the original canonical snapshot, and start again before the rule is removed. A rollback failure sets both containers to restart policy `no`, stops and verifies them, preserves the exact firewall rule, and writes `/var/lib/afterlight/quest-update-quarantine/state` with mode `0600`. Ordinary `update` and all scheduled maintenance reject that marker.

## Daily Warned Restart

The supplied systemd timer starts warnings every day at 4:45 AM Eastern and begins the restart around 5:00 AM Eastern. Players receive warnings at 15 minutes, 5 minutes, 1 minute, and immediately before shutdown. The restart proceeds even when players are online after the full warning sequence.

Before shutdown, the service requires working RCON, the same healthy container throughout the countdown, and a new verified backup. Any warning, identity, health, or backup failure leaves the server running. Missed timer events do not catch up after host boot.

The unit files target the dedicated VPS layout with the repository at `/opt/afterlight` and the operator account named `afterlight`:

```bash
sudo install -m 0644 server/systemd/afterlight-maintenance.service /etc/systemd/system/
sudo install -m 0644 server/systemd/afterlight-maintenance.timer /etc/systemd/system/
sudo install -m 0755 server/afterlight-quarantine-gate.sh /opt/afterlight/server/
sudo install -m 0644 server/systemd/afterlight-quarantine-gate.service /etc/systemd/system/
sudo install -d -o root -g root -m 0711 /var/lib/afterlight/quest-update-quarantine
sudo install -d -o afterlight -g afterlight -m 0700 /var/lib/afterlight/quest-update-snapshots
sudo systemd-analyze verify /etc/systemd/system/afterlight-maintenance.service /etc/systemd/system/afterlight-maintenance.timer /etc/systemd/system/afterlight-quarantine-gate.service
systemd-analyze calendar '*-*-* 04:45:00 America/New_York'
sudo systemctl daemon-reload
sudo systemctl enable afterlight-quarantine-gate.service
sudo systemctl enable --now afterlight-maintenance.timer
systemctl list-timers afterlight-maintenance.timer
```

Mode `0711` on the root-owned quarantine directory lets the unprivileged maintenance account test the exact marker path without listing or reading the mode `0600` marker.

Inspect the most recent check with `journalctl -u afterlight-maintenance.service -n 100 --no-pager`.

## Durable Quarantine Recovery

Never remove the quarantine marker merely to make an update command run. Keep the maintenance timer disabled and preserve the external gate until the prior release has completed the same stop, compare, and second-start proof:

```bash
set -euo pipefail
sudo systemctl disable --now afterlight-maintenance.timer
MARKER=/var/lib/afterlight/quest-update-quarantine/state
test "$(stat -c '%a' "$MARKER")" = 600
EXPECTED_SHA=$(sed -n 's/^expected_sha=//p' "$MARKER")
COMMENT=$(sed -n 's/^comment=//p' "$MARKER")
[[ "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]]
[[ "$COMMENT" =~ ^afterlight-quest-update-${EXPECTED_SHA}-[0-9]+$ ]]
SNAPSHOT_DIR=$(sed -n 's/^snapshot_dir=//p' "$MARKER")
test -d "$SNAPSHOT_DIR/progress"
cd "$SNAPSHOT_DIR"
sha256sum -c full-backup.sha256
STAGING=/srv/afterlight/.quest-quarantine-restore-$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 0700 "$STAGING"
tar --extract --zstd --file full-backup.tar.zst --directory "$STAGING" --no-same-owner --no-same-permissions
/opt/afterlight/server/afterlight-progress-guard.py compare --world "$STAGING/world" --snapshot "$SNAPSHOT_DIR/progress"
WHITELIST_SHA=$(sha256sum "$STAGING/whitelist.json" | awk '{print $1}')
USERCACHE_SHA=$(sha256sum "$STAGING/usercache.json" | awk '{print $1}')
PRIOR_SHA=$(cat "$STAGING/.afterlight-pack-sha")
test "${#PRIOR_SHA}" = 40
git -C /opt/afterlight cat-file -e "$PRIOR_SHA^{commit}"
git -C /opt/afterlight checkout --detach "$PRIOR_SHA"
/opt/afterlight/server/afterlight-server.sh stop
mv /srv/afterlight/data "/srv/afterlight/data.quarantined-$EXPECTED_SHA"
mv "$STAGING" /srv/afterlight/data
/opt/afterlight/server/afterlight-server.sh start
/opt/afterlight/server/afterlight-server.sh stop
/opt/afterlight/server/afterlight-progress-guard.py compare --world /srv/afterlight/data/world --snapshot "$SNAPSHOT_DIR/progress"
test "$(sha256sum /srv/afterlight/data/whitelist.json | awk '{print $1}')" = "$WHITELIST_SHA"
test "$(sha256sum /srv/afterlight/data/usercache.json | awk '{print $1}')" = "$USERCACHE_SHA"
/opt/afterlight/server/afterlight-server.sh start
/opt/afterlight/server/afterlight-server.sh status
test "$(sha256sum /srv/afterlight/data/whitelist.json | awk '{print $1}')" = "$WHITELIST_SHA"
test "$(sha256sum /srv/afterlight/data/usercache.json | awk '{print $1}')" = "$USERCACHE_SHA"
RULE=(-p tcp --dport 25565 -m conntrack --ctstate NEW -m comment --comment "$COMMENT" -j REJECT)
sudo iptables -w -C DOCKER-USER "${RULE[@]}"
sudo iptables -w -D DOCKER-USER "${RULE[@]}"
if sudo iptables -w -C DOCKER-USER "${RULE[@]}"; then exit 1; fi
sudo rm -- "$MARKER"
sudo docker update --restart=unless-stopped afterlight-minecraft-1 afterlight-backup-1
sudo systemctl reset-failed afterlight-quarantine-gate.service
sudo systemctl enable --now afterlight-maintenance.timer
```

Use only the snapshot directory recorded in the validated marker. Keep the rejected data rescue and authenticated snapshot until a later reviewed cleanup. Do not print whitelist contents, player identities, UUIDs, or raw progress during recovery.

Pregen remains deferred. Chunky is installed, but no deliberate pregen command or world-border change has run.

See `docs/SERVER.md` for firewall setup, recovery details, and troubleshooting.
