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

Each path value in `server/.env` must match `^/([A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$`. Dollar signs, quotes, backslashes, whitespace, and comments are rejected so the operator and Docker Compose read identical literal paths.

Populate the Minecraft whitelist before sharing the server address. RCON `25575` must never be forwarded.

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

`update` creates and verifies an on-demand backup before recreating Minecraft. A failed health check leaves both services stopped and prints the exact rollback command. Rollback renames the current data tree to a timestamped rescue sibling and never deletes the selected archive or either world tree.

See `docs/SERVER.md` for firewall setup, recovery details, and troubleshooting.
