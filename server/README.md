# AFTERLIGHT Friend Server

The supported production model is a root-only host control plane plus one explicit unprivileged data identity inside the Minecraft and backup containers. Every host mutation, scheduled restart, transaction, recovery, and retention action runs as root and shares one authenticated no-follow lock. The `afterlight` account owns only `/srv/afterlight/data` and `/srv/afterlight/backups`. It does not run host commands and does not need Docker access.

Production scripts must run from `/opt/afterlight/server`. The canonical paths are fixed:

```text
/opt/afterlight/server/.env
/run/afterlight
/var/lib/afterlight/quest-update-quarantine
/var/lib/afterlight/quest-update-snapshots
/srv/afterlight/data
/srv/afterlight/backups
/etc/afterlight/secrets
```

## Host Setup

From the repository installed at `/opt/afterlight`:

```bash
sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin afterlight 2>/dev/null || true
AFTERLIGHT_DATA_UID=$(id -u afterlight)
AFTERLIGHT_DATA_GID=$(id -g afterlight)
sudo install -d -o root -g root -m 0755 /srv/afterlight
sudo install -d -o "$AFTERLIGHT_DATA_UID" -g "$AFTERLIGHT_DATA_GID" -m 0750 /srv/afterlight/data /srv/afterlight/backups
sudo install -d -o root -g root -m 0700 /etc/afterlight/secrets /var/lib/afterlight/quest-update-quarantine /var/lib/afterlight/quest-update-snapshots /var/lib/afterlight/accepted
sudo cp server/.env.example server/.env
sudo sed -i "s/^AFTERLIGHT_DATA_UID=.*/AFTERLIGHT_DATA_UID=$AFTERLIGHT_DATA_UID/" server/.env
sudo sed -i "s/^AFTERLIGHT_DATA_GID=.*/AFTERLIGHT_DATA_GID=$AFTERLIGHT_DATA_GID/" server/.env
sudo chown root:root server/.env
sudo chmod 0600 server/.env
RCON_SECRET=$(mktemp)
umask 077
openssl rand -base64 36 > "$RCON_SECRET"
sudo install -o root -g root -m 0600 "$RCON_SECRET" /etc/afterlight/secrets/rcon_password
rm -f "$RCON_SECRET"
```

Each path in `server/.env` must remain the exact canonical value shown above and must match `^/([A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$`. Dollar signs, quotes, backslashes, whitespace, and comments are rejected. `AFTERLIGHT_DATA_UID` and `AFTERLIGHT_DATA_GID` must each appear exactly once and must equal the owner and group of both data directories.

Install the root-owned units and helpers:

```bash
sudo install -m 0644 server/afterlight-safety-contract.sh /opt/afterlight/server/
sudo install -m 0755 server/afterlight-safety.py server/afterlight-progress-guard.py server/afterlight-server.sh server/afterlight-maintenance.sh server/afterlight-quest-safe-update.sh server/afterlight-ingress-boot-gate.sh server/afterlight-quarantine-gate.sh server/afterlight-quarantine-recover.sh server/afterlight-snapshot-retention.sh /opt/afterlight/server/
sudo install -m 0644 server/systemd/*.service server/systemd/*.timer /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/afterlight-ingress-boot-gate.service /etc/systemd/system/afterlight-quarantine-gate.service /etc/systemd/system/afterlight-maintenance.service /etc/systemd/system/afterlight-maintenance.timer /etc/systemd/system/afterlight-snapshot-retention.service /etc/systemd/system/afterlight-snapshot-retention.timer
sudo systemctl daemon-reload
sudo systemctl enable --now afterlight-ingress-boot-gate.service
sudo systemctl enable afterlight-quarantine-gate.service
sudo systemctl enable --now afterlight-maintenance.timer afterlight-snapshot-retention.timer
```

`afterlight-ingress-boot-gate.service` is the only unit that manages `/run/afterlight`. It creates that directory as root mode `0700`. The first control action creates `maintenance.lock` as root mode `0600`. No setup command should replace or chmod an existing lock inode.

## Network Contract

Compose publishes Minecraft TCP `25565` and voice UDP `24454` on `0.0.0.0` only. Give players the server's IPv4 address or a DNS A record. Do not advertise an IPv6 address or AAAA-only name. RCON TCP `25575` is never published.

Allow the existing SSH port before enabling a default-deny firewall:

```bash
SSH_PORT=22
sudo ufw allow "$SSH_PORT/tcp"
sudo ufw allow 25565/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
sudo ufw status verbose
```

UDP `24454` is optional because the group uses Discord. Populate the whitelist before sharing the IPv4 server address.

## Operations

All supported host operations use the root control plane:

```bash
sudo /opt/afterlight/server/afterlight-server.sh doctor
sudo /opt/afterlight/server/afterlight-server.sh start
sudo /opt/afterlight/server/afterlight-server.sh status
sudo /opt/afterlight/server/afterlight-server.sh backup
sudo /opt/afterlight/server/afterlight-server.sh stop
sudo /opt/afterlight/server/afterlight-server.sh update
sudo /opt/afterlight/server/afterlight-server.sh rollback /srv/afterlight/backups/afterlight-20260809-120000.tar.zst --confirm
```

The operator pins each start to the exact repository commit and writes `/srv/afterlight/data/.afterlight-pack-sha` as the data UID/GID with mode `0600`. Ordinary `update` is only for revisions that do not change the quest corpus. A usable backup must contain this marker and a nonempty `world/level.dat`.

The daily timer warns at 4:45 AM Eastern and restarts around 5:00 AM after 15-minute, 5-minute, 1-minute, and final warnings. It proceeds with players online only after a new verified backup. The backup image demotes its process to the owner of `/backups`. Its healthcheck uses the same demotion before proving readable server data, writable backup storage, and a successful `mc-monitor` connection to Minecraft.

## Quest-Safe Deployment

Quest changes require a clean checkout at the exact accepted SHA and the complete root-controlled gauntlet directory:

```bash
sudo /opt/afterlight/server/afterlight-quest-safe-update.sh EXPECTED_40_CHARACTER_SHA /var/lib/afterlight/accepted/EXPECTED_40_CHARACTER_SHA/gauntlet-receipt.json RECEIPT_SHA256 --confirm
```

The receipt verifier reads the accepted Packwiz URL from the exact checkout's `tools/release-policy.env`. It revalidates the annotated tag, published release, exact `dev` and `main` CI runs, five release assets, Pages `pack.toml` and `index.toml`, installed server jar names, hashes and sizes, positive FTB Quests counts, and candidate-bound log evidence.

The transaction parent-fsyncs durable authority before its first protected mutation. It then closes new IPv4 game ingress, proves zero players, flushes and stops both services, creates a root mode `0700` snapshot, authenticates the full backup through one descriptor, and tests the candidate behind the gate. Every mutating server script authenticates the same inherited lock descriptor. Caller-controlled environment text cannot bypass the lock.

Successful snapshots receive a root mode `0600` retention marker. `afterlight-snapshot-retention.timer` runs the dedicated root helper weekly. The helper holds the shared lock and removes only successful snapshots older than seven days. Failed or incomplete snapshots are never selected.

## Durable Quarantine Recovery

The quarantine directory and every snapshot contain sensitive root-only recovery data. Keep them mode `0700`, root-owned, and unavailable to players or the runtime account.

Never edit authority, delete a staging or rescue directory, or run inline archive commands. Use only:

```bash
sudo /opt/afterlight/server/afterlight-quarantine-recover.sh --confirm
```

When an authenticated snapshot exists, recovery resumes any partial staging or rescue rename, restores the exact prior tree, checks progress, starts and stops the prior release for candidate-bound verification, then reopens service. Repeating the helper after a crash is safe.

When authority was created but no snapshot exists, recovery first proves that the original data root, release marker, ownership, modes, device, inode, link count, and bytes are unchanged. It restores the prior checkout, terminalizes authority, and intentionally leaves Minecraft stopped. Then run the normal root `start` command. If original identity changed or protected mutation began, the no-snapshot path fails closed.

Keep rejected rescue data and incomplete snapshots until a separate review decides their disposition. Do not print player identities, UUIDs, whitelist contents, document identifiers, or raw progress.

Pregen remains deferred. Chunky is installed, but no deliberate pregeneration or world-border change has run.
