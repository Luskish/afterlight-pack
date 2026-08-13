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
sudo install -d -o root -g "$AFTERLIGHT_GROUP" -m 0750 /run/afterlight /var/lib/afterlight/quest-update-quarantine
sudo install -o root -g "$AFTERLIGHT_GROUP" -m 0660 /dev/null /run/afterlight/maintenance.lock
sudo install -d -o "$AFTERLIGHT_USER" -g "$AFTERLIGHT_GROUP" -m 0700 /var/lib/afterlight/quest-update-snapshots
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
sudo server/afterlight-quest-safe-update.sh EXPECTED_40_CHARACTER_SHA /var/lib/afterlight/accepted/EXPECTED_40_CHARACTER_SHA/gauntlet-receipt.json RECEIPT_SHA256 --confirm
server/afterlight-server.sh rollback /srv/afterlight/backups/afterlight-20260809-120000.tar.zst --confirm
```

`update` is only for revisions that do not change the quest corpus. It creates and verifies an on-demand backup before recreating Minecraft at the new exact repository revision. A failed health check leaves both services stopped and prints the exact rollback command. Rollback performs a preflight check for `world/level.dat` and the recorded revision before stopping, renames the current data tree to a timestamped rescue sibling, starts the restored world from the archive's immutable Packwiz revision, and never deletes the selected archive or either world tree.

Every revision that changes FTB Quests data must use `afterlight-quest-safe-update.sh` through `sudo`, because the transaction owns a host firewall rule and durable transaction authority. The command accepts only the exact clean commit bound by an immutable gauntlet receipt and its independently captured digest. Install the complete accepted gauntlet directory, including `public/`, outside Git, then pass the receipt path and separately captured digest explicitly. Published `dev` and `main` CI, the annotated release tag, the GitHub release inventory, `pack.toml` and `index.toml` bytes, release artifacts, the server mod inventory, the installed quest corpus, and the FTB Quests load record are all revalidated.

The transaction publishes and parent-fsyncs `/var/lib/afterlight/quest-update-quarantine/state` before its first protected mutation. It then proves zero players twice, installs one uniquely commented `DOCKER-USER` rule for new TCP `25565` connections, flushes and stops the world, and creates a mode `0700` snapshot. That snapshot is sensitive root-only recovery data. It contains a complete world backup, player data, canonical progress hashes with pseudonymized path identifiers, and an authenticated inventory. It must never enter Git, CI artifacts, public release evidence, logs, or chat. The candidate starts and stops once behind the gate for progress and release checks, then starts a second time before the exact owned rule is removed and the authority is terminalized.

Any candidate failure keeps the gate closed while the transaction restores the prior full data tree and exact prior Packwiz revision from one descriptor-bound authenticated archive. The restored release must start, stop, match the original canonical snapshot, and start again before the rule is removed. A rollback failure updates the already durable authority to quarantine, then independently and resumably disables and stops each container. Ordinary mutations and scheduled maintenance take the same no-follow lock and reject every pending or quarantined authority. Retention policy: retain a failed transaction snapshot until reviewed recovery succeeds and a separate reviewed cleanup approves deletion. Retain successful snapshots for seven days, then delete them only with a dedicated root maintenance action while the shared lock is held.

## Daily Warned Restart

The supplied systemd timer starts warnings every day at 4:45 AM Eastern and begins the restart around 5:00 AM Eastern. Players receive warnings at 15 minutes, 5 minutes, 1 minute, and immediately before shutdown. The restart proceeds even when players are online after the full warning sequence.

Before shutdown, the service requires working RCON, the same healthy container throughout the countdown, and a new verified backup. Any warning, identity, health, or backup failure leaves the server running. Missed timer events do not catch up after host boot.

The unit files target the dedicated VPS layout with the repository at `/opt/afterlight` and the operator account named `afterlight`:

```bash
sudo install -m 0644 server/systemd/afterlight-maintenance.service /etc/systemd/system/
sudo install -m 0644 server/systemd/afterlight-maintenance.timer /etc/systemd/system/
sudo install -m 0755 server/afterlight-safety.py /opt/afterlight/server/
sudo install -m 0755 server/afterlight-ingress-boot-gate.sh /opt/afterlight/server/
sudo install -m 0755 server/afterlight-quarantine-gate.sh /opt/afterlight/server/
sudo install -m 0755 server/afterlight-quarantine-recover.sh /opt/afterlight/server/
sudo install -m 0644 server/systemd/afterlight-ingress-boot-gate.service /etc/systemd/system/
sudo install -m 0644 server/systemd/afterlight-quarantine-gate.service /etc/systemd/system/
sudo install -d -o root -g afterlight -m 0750 /run/afterlight /var/lib/afterlight/quest-update-quarantine
sudo install -o root -g afterlight -m 0660 /dev/null /run/afterlight/maintenance.lock
sudo install -d -o afterlight -g afterlight -m 0700 /var/lib/afterlight/quest-update-snapshots
sudo systemd-analyze verify /etc/systemd/system/afterlight-maintenance.service /etc/systemd/system/afterlight-maintenance.timer /etc/systemd/system/afterlight-ingress-boot-gate.service /etc/systemd/system/afterlight-quarantine-gate.service
systemd-analyze calendar '*-*-* 04:45:00 America/New_York'
sudo systemctl daemon-reload
sudo systemctl enable afterlight-ingress-boot-gate.service
sudo systemctl enable afterlight-quarantine-gate.service
sudo systemctl enable --now afterlight-maintenance.timer
systemctl list-timers afterlight-maintenance.timer
```

The root-owned transaction directory is mode `0750` and its authority is mode `0640`, both grouped to the dedicated `afterlight` account. The pre-Docker unit reconstructs a discoverable pending gate before Docker can restart containers. The post-Docker unit then reconciles each container independently. The root-owned shared lock is mode `0660` in a canonical root-owned mode `0750` runtime directory. All mutating operators open that inode without following links and verify its owner, group, mode, link count, and identity before locking.

Inspect the most recent check with `journalctl -u afterlight-maintenance.service -n 100 --no-pager`.

## Durable Quarantine Recovery

Never remove or edit transaction authority merely to make an update command run. The reviewed recovery helper validates the canonical authority and snapshot paths, opens the archive and receipt without following links, authenticates and extracts the same pinned archive descriptor, checks the complete inventory, restores the exact prior revision behind the exact owned firewall gate, repeats progress and live-release verification, and only then terminalizes authority:

```bash
sudo /opt/afterlight/server/afterlight-quarantine-recover.sh --confirm
```

Keep the rejected data rescue and authenticated snapshot until a later reviewed cleanup. Do not print whitelist contents, player identities, UUIDs, document identifiers, or raw progress during recovery.

Pregen remains deferred. Chunky is installed, but no deliberate pregen command or world-border change has run.

See `docs/SERVER.md` for firewall setup, recovery details, and troubleshooting.
