# Playing AFTERLIGHT

AFTERLIGHT supports Prism Launcher, the CurseForge App, and compatible `.mrpack` launchers. Download the newest complete release from [rl-labs.org/afterlight](https://rl-labs.org/afterlight/) or its linked official GitHub release.

## Prism Launcher, Recommended

Download `AFTERLIGHT-prism-instance.zip` from the current release.

1. Install [Prism Launcher](https://prismlauncher.org/download/) and sign in with your Microsoft account.
2. Install Java 21. In Prism, open Settings, choose Java, then use Auto-detect or Download Java.
3. In Prism, choose Add Instance, choose Import, select `AFTERLIGHT-prism-instance.zip`, then choose OK.
4. Edit the instance settings and assign 8 to 10 GiB RAM, which is 8192 to 10240 MiB.
5. Launch the instance. The first launch downloads the pack before Minecraft starts.

### How Prism Updates Work

The Prism instance includes checksum-pinned Packwiz bootstrap `v0.0.3` and Packwiz installer `v0.5.14` files. Before Minecraft starts, the installer reads the stable manifest at `https://luskish.github.io/afterlight-pack/pack.toml`, verifies its index, downloads changed files, removes retired managed files, and then launches NeoForge. Friends do not need to re-import the Prism ZIP for normal pack updates.

If an update is interrupted, launch the same instance again. Packwiz rechecks the indexed files and safely resumes from the accepted stable channel. Do not add or replace mod JARs by hand.

## CurseForge App

Download `AFTERLIGHT-curseforge.zip` from the same release as `SHA256SUMS` and `release-metadata.json`.

1. Open Minecraft in the CurseForge App and choose Import.
2. Under Import Profile `.zip`, choose Choose `.zip` file.
3. Select `AFTERLIGHT-curseforge.zip`.
4. If CurseForge warns that the pack contains files not hosted on CurseForge, verify that the ZIP came from the official AFTERLIGHT release and compare its SHA-256 with `SHA256SUMS`.
5. After verification, acknowledge the warning and choose All Files. Choosing CurseForge Files Only omits required pack files.
6. Let CurseForge create the profile, assign Java 21 and 8 to 10 GiB RAM, then launch it.

CurseForge profiles do not use the automatic Packwiz update path. For a newer AFTERLIGHT release, download and import the new canonical ZIP as a separate profile. Keep the old profile until the replacement reaches the title screen and joins the server.

## Compatible `.mrpack` Launchers

`AFTERLIGHT.mrpack` is the public manual fallback for compatible launchers. Verify it against `SHA256SUMS` before import. Launcher update behavior varies, so use the portal for each announced AFTERLIGHT release.

## Release Inventory

Every current public release contains exactly:

- `AFTERLIGHT-prism-instance.zip`
- `AFTERLIGHT-curseforge.zip`
- `AFTERLIGHT.mrpack`
- `SHA256SUMS`
- `release-metadata.json`

## Joining the Server

Get the server address from Shane. The group uses Discord for voice. Simple Voice Chat remains installed for compatibility but is optional and is not required to play.

On first join, ECHO is delivered automatically. The ECHO Protocols page in the quest book provides a repeatable replacement. Operators can also use the permission-zero `echo recover` command through the normal player command path.

## First-Launch Troubleshooting

- **Microsoft login:** In Prism, open Accounts, add a Microsoft account, finish the browser login, and select that account before launching.
- **Java selection:** Select a Java 21 runtime and use the launcher's Java test. Do not launch AFTERLIGHT with Java 17 or an older runtime.
- **Memory:** Assign 8192 to 10240 MiB. If the computer has less than 12 GiB total RAM, ask Shane before allocating more.
- **Packwiz download errors:** Check the internet connection, retry once, then send Shane the complete error text and failed URL. Do not bypass Packwiz.
- **CurseForge invalid file:** Confirm the file is named `AFTERLIGHT-curseforge.zip`, came from the official AFTERLIGHT release, and matches `SHA256SUMS`.
- **Connection reset or mod mismatch:** Confirm every player and the server use the same release. Prism users should close Minecraft and launch again so Packwiz completes its check.
- **Crash Assistant:** Use Copy to clipboard and send Shane the complete text. Send text instead of a screenshot so the report remains searchable.
