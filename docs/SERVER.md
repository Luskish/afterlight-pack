# AFTERLIGHT Friend Server Operations

This is the supported operating procedure for the private AFTERLIGHT server. The target is Ubuntu 24.04 LTS or another current x86-64 Linux host with Docker Engine, Docker Compose v2, Git, OpenSSL, working SSH access, at least 16 GiB RAM, 4 CPU threads, and 30 GiB free storage.

## VPS Checklist

1. Provision the host and confirm SSH access before changing any firewall rule.
2. Install Docker Engine, Docker Compose v2, Git, and OpenSSL.
3. Clone `https://github.com/Luskish/afterlight-pack.git` as one normal operator account, switch to `main`, and run all commands from the repository root.
4. Create the exact data, backup, and secret paths shown below, then create the mode `0600` RCON secret.
5. Run `server/afterlight-server.sh doctor`, then `server/afterlight-server.sh start`. Do not use Compose directly for lifecycle operations.
6. Allow TCP `25565` in UFW and the provider firewall or router. Allow UDP `24454` only if the group decides to use Simple Voice Chat. Never expose TCP `25575`.
7. Add every friend to the Minecraft whitelist before sharing the address.
8. Run `status`, create one verified `backup`, and save the printed rollback command before opening the server.

## Initial Setup

The supported model is one normal dedicated operator account with access to Docker. Clone or update the repository as that operator, switch to the stable `main` branch, and run from the repository root:

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

The first three values in `server/.env` must remain exact absolute host paths matching `^/([A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$`. Dollar signs, quotes, backslashes, whitespace, and comments are rejected so the operator and Docker Compose read identical literal paths. The operator command parses the file as data. It does not execute it.

The three optional memory values use positive whole gigabytes. `AFTERLIGHT_INIT_MEMORY` must not exceed `AFTERLIGHT_MAX_MEMORY`, and `AFTERLIGHT_MEMORY_LIMIT` must leave at least 2 GiB above the maximum Java heap for native JVM memory. The portable defaults are `4G`, `10G`, and `13G`. A dedicated host with about 24 GiB usable RAM can use `6G`, `14G`, and `17G` while retaining operating-system and backup headroom.

## Performance Guardrails

The Minecraft service sets `mem_swappiness: 1`, the lowest value production Docker Compose reliably carries into the container. Runtime verification must show both Docker HostConfig and the cgroup at `1`. Do not change this value to `0` until the production Compose implementation preserves numeric zero instead of inheriting the host default. Keep the container memory limit at least 2 GiB above the maximum Java heap. Do not replace the Java 21 G1 defaults, change ServerCore gameplay settings, disable synchronous chunk writes, or reduce view and simulation distance without a Spark profile showing a sustained bottleneck.

Install `sysstat` for low-overhead host history. The production VPS collects every five minutes and retains 28 days. Confirm package-specific scheduling and retention after installation, then use these live samples when diagnosing performance:

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

Use Spark for Minecraft tick, entity, heap, and garbage-collection evidence. Capture profiles during normal multiplayer activity rather than tuning from an idle server. Keep Chunky pregeneration deferred until the current world and pack release are accepted for longer-term play.

## Firewall

Confirm the currently working SSH port before changing UFW. Set `SSH_PORT` to that existing port, then allow SSH before enabling the default deny policy:

```bash
SSH_PORT=22
sudo ufw allow "$SSH_PORT/tcp"
sudo ufw allow 25565/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
sudo ufw status verbose
```

The group uses Discord, so UDP `24454` is optional. Only if Simple Voice Chat will be used, add this rule and the matching provider firewall or router forwarding rule:

```bash
sudo ufw allow 24454/udp
```

Forward TCP `25565` through the provider firewall or router. RCON `25575` must never be forwarded. Populate the Minecraft whitelist before the address is shared. The lifecycle wrapper does not expose a generic console command; for the one-time whitelist administration, use the internal RCON client and do not publish its port:

```bash
docker compose --project-name afterlight --env-file server/.env -f server/docker-compose.yml exec minecraft rcon-cli whitelist add FRIEND_NAME
docker compose --project-name afterlight --env-file server/.env -f server/docker-compose.yml exec minecraft rcon-cli whitelist list
```

This direct Compose call is limited to Minecraft administration. Continue using `server/afterlight-server.sh` for start, stop, status, backup, update, and rollback.

## Routine Commands

Check host paths, permissions, the secret, Compose rendering, and ports:

```bash
server/afterlight-server.sh doctor
```

Start, inspect, or stop both services:

```bash
server/afterlight-server.sh start
server/afterlight-server.sh status
server/afterlight-server.sh stop
```

The supported operator command resolves the repository's exact `HEAD`, starts
Minecraft from that immutable Packwiz revision, and records it in
`DATA_DIR/.afterlight-pack-sha`. Run server operations from the stable `main`
checkout. Do not start the Compose file directly for a supported deployment.
`start` accepts a new world or an existing world already marked with the same
revision. If the checkout changed, use `update` so a verified backup exists
before Minecraft loads the new pack. An existing unmarked world must be moved
through a separately planned migration or restored from a verified backup.

Create and verify an on-demand archive before maintenance:

```bash
server/afterlight-server.sh backup
```

Backups also run every 6 hours and are retained for 14 days. Archives live outside the Minecraft data directory at the configured `BACKUP_DIR`. A usable archive must contain a nonempty `world/level.dat` plus the exact `.afterlight-pack-sha` marker.

## Daily Warned Restart

For the dedicated VPS layout, keep the repository at `/opt/afterlight` and run the stack as the `afterlight` account. Install the supplied systemd units instead of a blind cron restart:

```bash
sudo install -m 0644 server/systemd/afterlight-maintenance.service /etc/systemd/system/
sudo install -m 0644 server/systemd/afterlight-maintenance.timer /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/afterlight-maintenance.service /etc/systemd/system/afterlight-maintenance.timer
sudo systemctl daemon-reload
sudo systemctl enable --now afterlight-maintenance.timer
systemctl list-timers afterlight-maintenance.timer
```

The timer starts a warning sequence every day at 4:45 AM Eastern and begins the restart around 5:00 AM Eastern. It announces the restart at 15 minutes, 5 minutes, 1 minute, and immediately before shutdown. The restart proceeds even when players are online after the complete warning sequence.

- Minecraft is running and healthy.
- RCON accepts every player warning and returns a parseable player count.
- A new verified backup succeeds.
- The exact same container remains healthy throughout the countdown and after backup.

An RCON failure, unparseable player count, changed container, failed backup, or failed health check stops the maintenance attempt without stopping a running server. Missed runs do not catch up after a host reboot because the JVM already restarted with the host. A successful attempt uses the lifecycle wrapper for backup, stop, start, and final status. Review the parsed Eastern schedule, timer state, and logs with:

```bash
systemd-analyze calendar '*-*-* 04:45:00 America/New_York'
systemctl status afterlight-maintenance.timer --no-pager
journalctl -u afterlight-maintenance.service -n 100 --no-pager
```

The default direct invocation, `server/afterlight-maintenance.sh idle`, retains the previous 20-hour and zero-player safety gates for an operator-requested idle restart. Production systemd invokes only `scheduled` mode.

Pregen remains deferred. Chunky is installed, but no deliberate pregen command or world-border change has run.

## Update

The update command creates a verified backup, resolves the new repository `HEAD`, stops both services, force-recreates only Minecraft from that immutable Packwiz revision, waits up to 10 minutes for health, records the new revision marker, then starts the backup service:

```bash
server/afterlight-server.sh update
```

If health fails, both services remain stopped and the command prints the exact rollback command for the backup it selected.

## Rollback

Run rollback only with the archive path printed by `backup` or `update`:

```bash
server/afterlight-server.sh rollback /srv/afterlight/backups/afterlight-20260809-120000.tar.zst --confirm
```

Rollback accepts only a regular, non-symlinked archive beneath `BACKUP_DIR`. Before stopping either service, it performs a preflight extraction and requires a nonempty `world/level.dat`, a valid `.afterlight-pack-sha`, and no symlinks. It then renames the current data directory to a UTC timestamped rescue sibling, promotes the staged tree, restarts Minecraft from the archive's immutable Packwiz revision, starts backups, and waits for health. It preserves the archive, rescue tree, and restored tree if any later step fails. A failed start receives a compensating stop so neither service is intentionally left running.

## Troubleshooting

1. Run `server/afterlight-server.sh doctor` and correct every reported dependency, path, permission, secret, Compose, or port error.
2. Run `server/afterlight-server.sh status` to inspect Compose state and Minecraft health.
3. Keep both services stopped after a failed update until the printed rollback command succeeds or the cause is understood.
4. Never replace the RCON secret with a symlink. It must be one nonempty line in a mode `0600` regular file.
5. Never expose TCP `25575` through Docker, UFW, a provider firewall, or a router.
