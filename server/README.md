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
server/afterlight-server.sh rollback /srv/afterlight/backups/afterlight-20260809-120000.tar.zst --confirm
```

`update` creates and verifies an on-demand backup before recreating Minecraft at the new exact repository revision. A failed health check leaves both services stopped and prints the exact rollback command. Rollback performs a preflight check for `world/level.dat` and the recorded revision before stopping, renames the current data tree to a timestamped rescue sibling, starts the restored world from the archive's immutable Packwiz revision, and never deletes the selected archive or either world tree.

## Daily Warned Restart

The supplied systemd timer starts warnings every day at 4:45 AM Eastern and begins the restart around 5:00 AM Eastern. Players receive warnings at 15 minutes, 5 minutes, 1 minute, and immediately before shutdown. The restart proceeds even when players are online after the full warning sequence.

Before shutdown, the service requires working RCON, the same healthy container throughout the countdown, and a new verified backup. Any warning, identity, health, or backup failure leaves the server running. Missed timer events do not catch up after host boot.

The unit files target the dedicated VPS layout with the repository at `/opt/afterlight` and the operator account named `afterlight`:

```bash
sudo install -m 0644 server/systemd/afterlight-maintenance.service /etc/systemd/system/
sudo install -m 0644 server/systemd/afterlight-maintenance.timer /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/afterlight-maintenance.service /etc/systemd/system/afterlight-maintenance.timer
systemd-analyze calendar '*-*-* 04:45:00 America/New_York'
sudo systemctl daemon-reload
sudo systemctl enable --now afterlight-maintenance.timer
systemctl list-timers afterlight-maintenance.timer
```

Inspect the most recent check with `journalctl -u afterlight-maintenance.service -n 100 --no-pager`.

Pregen remains deferred. Chunky is installed, but no deliberate pregen command or world-border change has run.

See `docs/SERVER.md` for firewall setup, recovery details, and troubleshooting.
