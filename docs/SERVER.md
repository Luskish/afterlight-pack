# AFTERLIGHT Friend Server Operations

The production server uses NeoForge 1.21.1, Java 21, Docker Compose v2, and a root-only host control plane. `server/README.md` is the exact installation and recovery runbook. This document summarizes routine VPS operation without introducing alternate commands or ownership.

## Production Identity

- Repository: `/opt/afterlight`
- Host control identity: `root:root`
- Container data identity: the numeric `AFTERLIGHT_DATA_UID` and `AFTERLIGHT_DATA_GID` recorded once in `/opt/afterlight/server/.env`
- Data: `/srv/afterlight/data`, owned by the container data identity, mode `0750`
- Backups: `/srv/afterlight/backups`, owned by the container data identity, mode `0750`
- Secrets: `/etc/afterlight/secrets`, owned by root, mode `0700`
- Transaction authority: `/var/lib/afterlight/quest-update-quarantine`, owned by root, mode `0700`
- Transaction snapshots: `/var/lib/afterlight/quest-update-snapshots`, owned by root, mode `0700`
- Shared runtime: `/run/afterlight`, created only by the root ingress unit, mode `0700`

The `afterlight` account is an unprivileged file owner for the two container bind mounts. It does not run server scripts and does not need membership in the Docker group. Every host command below uses `sudo`.

The first three values in `server/.env` are fixed canonical paths and must match `^/([A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$`. Dollar signs, quotes, backslashes, whitespace, and comments are rejected. The UID and GID must each occur exactly once. Follow the complete setup commands in `server/README.md` rather than creating an alternate layout.

## Firewall and Address

Compose binds TCP `25565` and UDP `24454` only to `0.0.0.0`. Friends must use the VPS IPv4 address or a DNS A record. Do not advertise an IPv6 address for this deployment. RCON `25575` must never be forwarded.

Confirm the real SSH port before changing UFW, then allow SSH first:

```bash
SSH_PORT=22
sudo ufw allow "$SSH_PORT/tcp"
sudo ufw allow 25565/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
sudo ufw status verbose
```

The group uses Discord, so UDP `24454` is optional. Add `sudo ufw allow 24454/udp` only if Simple Voice Chat is intentionally enabled. Populate the Minecraft whitelist before sharing the IPv4 address.

For one-time whitelist administration, use the internal RCON client without publishing its port:

```bash
sudo docker compose --project-name afterlight --env-file /opt/afterlight/server/.env -f /opt/afterlight/server/docker-compose.yml exec minecraft rcon-cli whitelist add FRIEND_NAME
sudo docker compose --project-name afterlight --env-file /opt/afterlight/server/.env -f /opt/afterlight/server/docker-compose.yml exec minecraft rcon-cli whitelist list
```

## Routine Commands

```bash
sudo /opt/afterlight/server/afterlight-server.sh doctor
sudo /opt/afterlight/server/afterlight-server.sh start
sudo /opt/afterlight/server/afterlight-server.sh status
sudo /opt/afterlight/server/afterlight-server.sh backup
sudo /opt/afterlight/server/afterlight-server.sh stop
```

The root operator resolves the exact clean repository commit, starts its immutable Packwiz URL, and records that commit in `/srv/afterlight/data/.afterlight-pack-sha`. The marker is owned by the container data identity and mode `0600`. `start` accepts a new world or an existing world already marked with the same revision.

Backups run every six hours and are retained for 14 days. An on-demand backup is accepted only when it creates a new recoverable archive containing a nonempty `world/level.dat` and the exact revision marker.

## Updates

Use ordinary update only when the quest corpus does not change:

```bash
sudo /opt/afterlight/server/afterlight-server.sh update
```

It creates a verified backup before recreating Minecraft. A failure leaves both services stopped and prints the exact rollback command.

Use rollback only with a path printed by backup or update:

```bash
sudo /opt/afterlight/server/afterlight-server.sh rollback /srv/afterlight/backups/afterlight-20260809-120000.tar.zst --confirm
```

Rollback performs a preflight that requires a nonempty `world/level.dat` before stopping either service. It preserves the selected archive, rescue tree, and restored tree if a later step fails.

Quest changes require the accepted gauntlet receipt and the dedicated transaction:

```bash
sudo /opt/afterlight/server/afterlight-quest-safe-update.sh EXPECTED_40_CHARACTER_SHA /var/lib/afterlight/accepted/EXPECTED_40_CHARACTER_SHA/gauntlet-receipt.json RECEIPT_SHA256 --confirm
```

The transaction requires a clean exact checkout and authentic release-policy URL, closes new IPv4 game ingress, proves zero players, takes an authenticated complete snapshot, checks every installed server jar hash and size, requires positive quest counts with no FTB Quests error, and binds log evidence to the candidate container start.

## Recovery and Retention

Pending or quarantined authority blocks every mutation and scheduled restart. Never delete or edit authority and never improvise archive commands. Run:

```bash
sudo /opt/afterlight/server/afterlight-quarantine-recover.sh --confirm
```

Snapshot recovery resumes partial staging and rescue states and is idempotent. A no-snapshot recovery is allowed only while durable authority proves the original data and release marker are byte-for-byte and identity-for-identity unchanged. That path restores the prior checkout and leaves the server stopped. Start it afterward with the normal root command.

The weekly `afterlight-snapshot-retention.timer` invokes the dedicated root retention helper while holding the same authenticated lock. It removes only successful transaction snapshots older than seven days. Failed and incomplete snapshots remain for review.

## Daily Restart

`afterlight-maintenance.timer` begins warnings at 4:45 AM Eastern and restarts around 5:00 AM. Players receive 15-minute, 5-minute, 1-minute, and final warnings. The restart proceeds with players online only after a new verified backup and repeated proof that the same Minecraft container remains healthy.

Inspect scheduling and logs:

```bash
systemd-analyze calendar '*-*-* 04:45:00 America/New_York'
systemctl list-timers afterlight-maintenance.timer afterlight-snapshot-retention.timer --no-pager
journalctl -u afterlight-maintenance.service -n 100 --no-pager
journalctl -u afterlight-snapshot-retention.service -n 100 --no-pager
```

## Performance Guardrails

The Minecraft service uses `mem_swappiness: 1`, a 10 GiB default Java heap, and a 13 GiB container limit. Keep at least 2 GiB above the heap for native memory. Do not change garbage collection, view distance, simulation distance, synchronous chunk writes, or ServerCore gameplay settings without Spark evidence from real multiplayer load.

Install `sysstat` and inspect the host before tuning:

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends sysstat
sudo systemctl enable --now sysstat
sar -u 1 5
sar -r 1 5
sar -q 1 5
sar -d 1 5
sar -n DEV 1 5
```

Pregen remains deferred. Chunky is installed, but no deliberate pregeneration or world-border change has run.
