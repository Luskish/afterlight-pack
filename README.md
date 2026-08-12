# AFTERLIGHT

AFTERLIGHT is a story-driven kitchen-sink modpack for Minecraft 1.21.1 on NeoForge 21.1.248.

You are not discovering technology. You are remembering it.

## Play

- Download the current Prism, CurseForge, or Modrinth-compatible release from [rl-labs.org/afterlight](https://rl-labs.org/afterlight/).
- Prism is recommended. Its instance checks the stable Packwiz channel before each launch and applies accepted pack updates automatically.
- CurseForge imports are complete snapshots. Import each new release as a replacement profile, verify it reaches the title screen, then remove the old profile.
- Player instructions and recovery steps are in `docs/INSTALL.md`.

## Signal Reliquary

Release `1.0.0-rc.1` integrates the AFTERLIGHT Signal companion:

- A physical ECHO device with a custom Signal Reliquary interface.
- A custom recovered-terminal and blackbox-cathedral presentation.
- A guided route across the complete Story quest line.
- An in-book recovery protocol plus the permission-zero `echo recover` command.
- The Gate of Return, guaranteed outbound travel, safe return routing, and the custom Far Relay dimension.
- A postgame Far Relay arrival quest and rewards.

## Repository

- `pack.toml` and `index.toml`: Packwiz manifest and immutable file index.
- `mods/`: one metadata descriptor per mod, with no mod JARs stored in Git.
- `config/`, `defaultconfigs/`, and `kubejs/`: shipped pack configuration and integration layer.
- `config/ftbquests/`: the quest book source.
- `server/`: Docker Compose operations, backups, updates, rollback, and scheduled maintenance.
- `docs/SERVER.md`: VPS setup, backup, deployment, rollback, restore, and maintenance procedures.
- `tools/`: deterministic builders, validators, release tooling, and test harnesses.
- `docs/`: design, release, installation, and server operations records.

## Development

Every Packwiz shell starts with:

```bash
source tools/versions.env
export PATH="$PATH_EXTRA:$PATH"
```

Primary gates:

```bash
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
```

Release procedures are documented in `docs/RELEASING.md`. Project guardrails are in `AGENTS.md`.
