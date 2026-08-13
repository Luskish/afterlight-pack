# AFTERLIGHT Handoff Guide

This is the current recovery record for Codex, Claude, or another capable agent. Last updated 2026-08-12 by Codex while preparing `1.0.0-rc.1`.

## Hard rules the prompts assume (also in AGENTS.md)

- Public release policy approved on 2026-08-11 requires exactly `AFTERLIGHT-prism-instance.zip`, `AFTERLIGHT-curseforge.zip`, `AFTERLIGHT.mrpack`, `SHA256SUMS`, and `release-metadata.json`.
- Read the repository `AGENTS.md` before acting.
- Never use em dashes in replies, docs, quest text, comments, or commits.
- Check and invoke every applicable project skill before work.
- Use `dev` for active release work and `main` for the stable Packwiz channel.
- Never force-push `dev` or `main`.
- Never commit JARs, credentials, tokens, or private release receipts.
- Every Packwiz shell starts with `source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"`.
- Every mod, config, or script change requires `./tools/verify-pack.sh` and `BOOT_TIMEOUT=600 ./tools/server-test.sh` before merge.
- Do not update the VPS until the accepted release is published, no players are online, and a verified backup exists.
- Pregen remains deferred.

## Current Release Candidate

- Pack worktree: `/private/tmp/afterlight-echo-signal-reliquary-20260811`.
- Working branch: `codex/echo-signal-reliquary`.
- Target version: `1.0.0-rc.1`.
- Minecraft: `1.21.1`.
- NeoForge: `21.1.248`.
- Java: `21`.
- Integration commit: `66eac04ecaa2160a392b57da1fcc1b311f15a9a6`.
- Remote `dev` duplicate design lineage was reconciled without changing pack bytes in merge commit `5bba025182ebba312c29b998c6a50ccd897bdee1`.
- The integrated preflight passed 522 authenticated tests and printed `SERVER BOOT: OK` before the version-only RC1 preparation.
- Accepted RC1 commit: `fc3bb555f240e7d8a51d30570404413305bf5b9f`.
- Immutable RC1 tag: `v1.0.0-rc.1`.
- Exact accepted `dev` CI succeeded: `https://github.com/Luskish/afterlight-pack/actions/runs/31647867896`.
- Exact `main` CI: `https://github.com/Luskish/afterlight-pack/actions/runs/31652482458`.
- Accepted receipt SHA-256: `ac459fa94c98207b6124ab46f9233cfd1e80e2c5929d3eed191c661c4919f4fa`.
- Accepted transcript SHA-256: `c3568ffd29e2410025e17e14ad22bf514f8521fb885227f394784036fabb5f92`.
- Shane authorized an expedited acceptance on 2026-08-12. The duplicate second local artifact build and duplicate local post-generation CurseForge scan were omitted only after exact artifact bytes matched the successful exact-SHA `dev` CI build. Pages parity, two launcher installation paths, checksums, archive CRCs, backup, and production verification remained required.
- Release hardening now includes replacement-ref-resistant CurseForge and Modrinth commit-tree reconciliation, an upstream-verified 140-record Modrinth manifest lock, typed, quoted, and oversized credential detection, exact automated evidence binding, direct explicit-refspec pushes to one captured production URL, HTTPS-only ordinary and cache-busted Pages parity, rejection of unexpected installed files, accepted-versus-hosted client mod-set and complete payload equality, numeric release ownership without automatic deletion, and authenticated plus unauthenticated byte verification.
- Publication, portal selection, and VPS rollout remain pending until recorded below.

## Signal Companion

- Repository: `https://github.com/Luskish/afterlight-signal`.
- Immutable release source: `a3d95a74a56855a026f9f2786f1e925065a3b151`.
- Documentation evidence child: `1e1a021cb6fdb94f3a05d8437915e9e77bdbe99f`.
- Public release: `https://github.com/Luskish/afterlight-signal/releases/tag/v0.2.0`.
- Release JAR SHA-256: `81387eff5e6f5dad555a936d605c114af8fff1cf69778251cc3a7ec660f15947`.
- Release JAR SHA-512: `902d3f64ac6f2e3302da26daefa29cfd03e19f39d293daa81da7b04cb3f115d3e0ed933da189f2622bd1284e6a3292fd7a4ddc6f8c115e3e43d2123e56f7d74f`.
- Main evidence CI: `https://github.com/Luskish/afterlight-signal/actions/runs/31588113497`.
- The tag remains on the immutable source commit, while `main` contains the evidence-only child.

## Delivered Experience

- Physical ECHO device with custom texture, held model, title presentation, and Signal Reliquary interface.
- Recovered-terminal plus blackbox-cathedral visual language.
- Automatic first delivery, safe recovery command, and repeatable ECHO Protocols quest reward.
- Canonical 169-quest route from Cold Boot through the existing postgame terminal.
- Gate of Return state machine with persisted OPEN state, guaranteed outbound travel, rollback on failed transfer, and safe return routing.
- Custom `afterlight:far_relay` dimension with five physical expedition sites and protected site recovery.
- Gate opening and Far Relay arrival advancements connected to the FTB Quests story route.
- Searchable keybinds, FTB Ultimine in place of VeinMiner, Lootr, SmartBrainLib client closure, and the multiplayer login fix already proven by the friend group.

## Public Delivery

- Portal: `https://rl-labs.org/afterlight/`.
- Website repository: `R-L-Labs/Website`.
- The portal is live and currently falls back to the previous complete release until `1.0.0-rc.1` publishes with all five canonical assets.
- Canonical assets are `AFTERLIGHT-prism-instance.zip`, `AFTERLIGHT-curseforge.zip`, `AFTERLIGHT.mrpack`, `SHA256SUMS`, and `release-metadata.json`.
- Prism uses the stable GitHub Pages Packwiz manifest and updates before launch.
- CurseForge uses complete replacement imports and does not auto-update.

## Release Procedure

From a clean accepted commit on this branch:

```bash
SHA=$(git rev-parse HEAD)
./tools/release-gauntlet.sh "$SHA"
```

Capture the exact printed receipt SHA-256. Then push the feature branch and require exact-head CI. Fast-forward or merge it into a clean local `dev` without rewriting history. Run:

```bash
tools/promote-release.sh "$SHA" "$RECEIPT_SHA256" --confirm
```

The promoter must push branches and the tag directly to the captured production URL, prove HTTPS-only ordinary bare and cache-busted Pages parity, derive accepted client mod-set and complete Packwiz payload SHA-256 values from a clean local install with no unexpected installed files, require a clean production Pages install to match both, and check Pages parity again before creating the tag. The accepted `.mrpack` must match `tools/modrinth-manifest-lock.json`, whose 140 records were independently checked against 138 Modrinth API records and two streamed GitHub release JARs. Populate `docs/releases/1.0.0-rc.1.md` and this handoff with exact prepublication evidence, commit only those documentation files as a distinct child on `dev`, push them, and require exact documentation CI. The publisher machine-checks every canonical evidence line and accepts only that pushed documentation descendant while requiring publication tooling to remain identical to the accepted SHA. Then publish:

```bash
tools/publish-release.sh "$SHA" 1.0.0-rc.1 "$RECEIPT_SHA256" --prerelease --confirm
```

The publisher creates an ID-owned draft, verifies all five assets through authenticated asset-ID downloads, never automatically deletes a release, and then repeats equality through unauthenticated downloads. Any failure after creation preserves the exact numeric release for manual inspection. Confirm that `https://rl-labs.org/afterlight/` selects RC1.

## VPS Preflight

- SSH alias: `afterlight-vps`, persistent root access already works.
- Host: `theboys`, Ubuntu 20.04.6, 8 cores, 23 GiB RAM, and more than 100 GiB free storage at the last preflight.
- Repository: `/opt/afterlight`, owned operationally by user `afterlight`.
- Current live marker before RC1: `7630bccff75b9faeb1415db3070d8f6b9e2aa88e`.
- Memory policy: 6 GiB initial heap, 14 GiB maximum heap, 17 GiB container limit.
- Required whitelist: `NRNJ`, `Liszewski`, `ZSmitt`, and `DylnDark`.
- The daily systemd timer warns for 15 minutes and restarts around 5:00 AM Eastern, even when players are online, only after a verified backup.
- Do not expose RCON. Keep TCP `25565` available and UDP `24454` optional.

## VPS Rollout

1. Confirm zero players through RCON.
2. Confirm at least 30 GiB free and the maintenance timer is healthy.
3. Confirm no Chunky pregeneration is active. Pregen remains deferred.
4. Create a zstd backup, verify its checksum and archive listing, and record the previous marker SHA.
5. Deploy the exact accepted `main` SHA through the documented update command in `docs/SERVER.md`.
6. Preserve the whitelist and memory settings.
7. Verify the server reaches `Done`, Signal loads, the quest counts match, the Far Relay dimension registers, TCP `25565` listens, and the marker equals the accepted SHA.
8. If any check fails, use the documented rollback command to restore the previous marker and verified backup.

## If returning to Claude instead of Codex

Use the same skills-first, fail-closed workflow. Require exact command evidence, do not accept a summary as verification, and continue from the first incomplete item in this file.

## Interruption Prompt

Use this prompt in a new Codex task if recovery is needed:

```text
Open /private/tmp/afterlight-echo-signal-reliquary-20260811 and read /private/tmp/afterlight-echo-signal-reliquary-20260811/AGENTS.md plus /private/tmp/afterlight-echo-signal-reliquary-20260811/docs/HANDOFF.md. Invoke every applicable skill before acting. Continue the first incomplete item in the handoff. Never use em dashes. Do not touch the dirty checkout at /Users/shaneliszewski/MinecraftTest. Do not update the VPS until the exact release is published, no players are online, and a verified backup exists. Run every required gate and report failures verbatim.
```
