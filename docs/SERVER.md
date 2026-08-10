# AFTERLIGHT Friend Server Operations

This is the supported operating procedure for the private AFTERLIGHT server. The target is Ubuntu 24.04 LTS or another current x86-64 Linux host with Docker Engine, Docker Compose v2, at least 16 GiB RAM, 4 CPU threads, and 30 GiB free storage.

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

The three values in `server/.env` must remain exact absolute host paths matching `^/([A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$`. Dollar signs, quotes, backslashes, whitespace, and comments are rejected so the operator and Docker Compose read identical literal paths. The operator command parses the file as data. It does not execute it.

## Firewall

Confirm the currently working SSH port before changing UFW. Set `SSH_PORT` to that existing port, then allow SSH before enabling the default deny policy:

```bash
SSH_PORT=22
sudo ufw allow "$SSH_PORT/tcp"
sudo ufw allow 25565/tcp
sudo ufw allow 24454/udp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
sudo ufw status verbose
```

Forward TCP `25565` and UDP `24454` from the router or provider firewall when needed. RCON `25575` must never be forwarded. Populate the Minecraft whitelist before the address is shared.

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

Create and verify an on-demand archive before maintenance:

```bash
server/afterlight-server.sh backup
```

Backups also run every 6 hours and are retained for 14 days. Archives live outside the Minecraft data directory at the configured `BACKUP_DIR`.

## Update

The update command creates a verified backup, stops both services, force-recreates only Minecraft so Packwiz synchronizes stable `main`, waits up to 10 minutes for health, then starts the backup service:

```bash
server/afterlight-server.sh update
```

If health fails, both services remain stopped and the command prints the exact rollback command for the backup it selected.

## Rollback

Run rollback only with the archive path printed by `backup` or `update`:

```bash
server/afterlight-server.sh rollback /srv/afterlight/backups/afterlight-20260809-120000.tar.zst --confirm
```

Rollback accepts only a regular, non-symlinked archive beneath `BACKUP_DIR`. It stops both services, renames the current data directory to a UTC timestamped rescue sibling, creates a fresh data directory, restores the selected zstd tar archive without archive owner or permission restoration, starts both services, and waits for health. It preserves the archive, rescue tree, and restored tree if any later step fails.

## Troubleshooting

1. Run `server/afterlight-server.sh doctor` and correct every reported dependency, path, permission, secret, Compose, or port error.
2. Run `server/afterlight-server.sh status` to inspect Compose state and Minecraft health.
3. Keep both services stopped after a failed update until the printed rollback command succeeds or the cause is understood.
4. Never replace the RCON secret with a symlink. It must be one nonempty line in a mode `0600` regular file.
5. Never expose TCP `25575` through Docker, UFW, a provider firewall, or a router.
