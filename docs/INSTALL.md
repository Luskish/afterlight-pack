# Playing AFTERLIGHT

AFTERLIGHT supports Prism Launcher, the CurseForge App, and compatible `.mrpack` launchers. Prism is the recommended path because its instance checks the stable Packwiz channel before every launch. Shane explicitly authorized public distribution of the current CurseForge ZIP and `.mrpack` on 2026-08-11, superseding earlier friends-only instructions.

## Prism Launcher, Recommended

The public release contains exactly these five files:

- `AFTERLIGHT-prism-instance.zip`: the auto-updating Prism instance.
- `AFTERLIGHT-curseforge.zip`: the public CurseForge import archive.
- `AFTERLIGHT.mrpack`: the public manual launcher fallback.
- `SHA256SUMS`: sorted checksums for all three launcher archives and metadata.
- `release-metadata.json`: the pack, Git commit, loader, Packwiz URL, installer identities, and all three launcher checksum facts.

1. Install [Prism Launcher](https://prismlauncher.org/download/) and sign in with your Microsoft account.
2. Install Java 21. In Prism, open Settings, choose Java, then use Auto-detect or Download Java.
3. Download `AFTERLIGHT-prism-instance.zip` from the AFTERLIGHT GitHub release.
4. In Prism, choose Add Instance, choose Import, select the ZIP, then choose OK.
5. Edit the instance settings and assign 8 to 10 GiB RAM, which is 8192 to 10240 MiB.
6. Launch the instance. The first launch downloads the pack. Later launches check Shane's stable Packwiz channel before Minecraft starts.

The Prism archive bundles exact Packwiz bootstrap `v0.0.3` and main installer `v0.5.14` bytes. It does not look up a mutable latest installer.

## CurseForge App

Download `AFTERLIGHT-curseforge.zip` from the same AFTERLIGHT GitHub release as the checksum and metadata files. Public distribution is explicitly authorized, but source and checksum verification remain required because this archive can embed third-party mod JARs.

Follow the [official CurseForge shared-profile import flow](https://support.curseforge.com/support/solutions/articles/9000197912):

1. Open Minecraft in the CurseForge App and choose Import.
2. Under Import Profile `.zip`, choose Choose `.zip` file.
3. Select `AFTERLIGHT-curseforge.zip`.
4. If CurseForge warns that the pack contains files not hosted on CurseForge, verify that the ZIP came from the official AFTERLIGHT release and compare its SHA-256 with `SHA256SUMS`.
5. After verifying the source and checksum, acknowledge the warning and choose All Files. Choosing CurseForge Files Only omits required pack files.
6. Let CurseForge create the new profile, assign Java 21 and 8 to 10 GiB RAM, then launch it.

CurseForge imports do not auto-update. For a newer AFTERLIGHT release, download and import its canonical replacement ZIP as a new profile. Keep the old profile until the new one reaches the title screen and joins the server.

## Other Public Archive

`AFTERLIGHT.mrpack` is a public manual fallback for compatible launchers. Verify it against `SHA256SUMS` before import. It does not replace the recommended auto-updating Prism ZIP.

## Joining the Server

Get the server address from Shane. The group uses Discord for voice. Simple Voice Chat remains installed for compatibility but is optional and is not required to play.

## First-Launch Troubleshooting

- **Microsoft login:** In Prism, open Accounts, add a Microsoft account, finish the browser login, and select that account before launching.
- **Java selection:** Select a Java 21 runtime and use the launcher's Java test. Do not launch AFTERLIGHT with Java 17 or an older runtime.
- **Memory:** Assign 8192 to 10240 MiB. If the computer has less than 12 GiB total RAM, ask Shane before allocating more.
- **Packwiz download errors:** Check the internet connection, retry once, then send Shane the complete error text and failed URL. Do not bypass Packwiz or add mod JARs manually.
- **CurseForge invalid file:** Confirm the file is named `AFTERLIGHT-curseforge.zip`, came from the official AFTERLIGHT release, and matches `SHA256SUMS`.
- **Crash Assistant:** Use Copy to clipboard and send Shane the complete text. Send text instead of a screenshot so the report remains searchable.
