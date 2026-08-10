# AFTERLIGHT Friend Server

This directory contains the private-friend Docker Compose stack and its operator command. The stack runs Minecraft plus continuous backups. RCON stays inside the Compose network.

## Host Setup

Run these commands from the repository root on the Linux host:

```bash
cp server/.env.example server/.env
sudo install -d -m 0750 /srv/afterlight/data /srv/afterlight/backups
sudo install -d -m 0700 /etc/afterlight/secrets
openssl rand -base64 36 | sudo tee /etc/afterlight/secrets/rcon_password >/dev/null
sudo chmod 0600 /etc/afterlight/secrets/rcon_password
server/afterlight-server.sh doctor
server/afterlight-server.sh start
```

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
