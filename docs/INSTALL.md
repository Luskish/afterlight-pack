# Playing AFTERLIGHT

AFTERLIGHT supports Prism Launcher and the CurseForge App. Prism is the recommended path because its instance checks the stable Packwiz channel before every launch. CurseForge is supported through a friends-only ZIP and requires a fresh import for each pack update.

## Prism Launcher, Recommended

The public release contains exactly these three files:

- `AFTERLIGHT-prism-instance.zip`: the auto-updating Prism instance.
- `release-metadata.json`: the pack, Git commit, loader, Packwiz URL, both installer identities, and Prism checksum facts.
- `SHA256SUMS`: sorted checksums for the Prism ZIP and metadata file.

1. Install [Prism Launcher](https://prismlauncher.org/download/) and sign in with your Microsoft account.
2. Install Java 21. In Prism, open Settings, choose Java, then use Auto-detect or Download Java.
3. Download `AFTERLIGHT-prism-instance.zip` from the AFTERLIGHT GitHub release.
4. In Prism, choose Add Instance, choose Import, select the ZIP, then choose OK.
5. Edit the instance settings and assign 8 to 10 GiB RAM, which is 8192 to 10240 MiB.
6. Launch the instance. The first launch downloads the pack. Later launches check Shane's stable Packwiz channel before Minecraft starts.

The Prism archive bundles exact Packwiz bootstrap `v0.0.3` and main installer `v0.5.14` bytes. It does not look up a mutable latest installer.

## CurseForge App

Shane shares `AFTERLIGHT-0.9.0-rc.3-curseforge.zip` directly through a private channel. This archive embeds third-party mod JARs, is friends-only, and must never be re-uploaded or attached to a public release.

Follow the [official CurseForge shared-profile import flow](https://support.curseforge.com/support/solutions/articles/9000197912):

1. Open Minecraft in the CurseForge App and choose Import.
2. Under Import Profile `.zip`, choose Choose `.zip` file.
3. Select `AFTERLIGHT-0.9.0-rc.3-curseforge.zip`.
4. If CurseForge warns that the manually shared pack contains files not hosted on CurseForge, verify that the ZIP came directly from Shane and compare its SHA-256 with Shane's release handoff.
5. After verifying the source and checksum, acknowledge the warning and choose All Files. Choosing CurseForge Files Only omits required pack files.
6. Let CurseForge create the new profile, assign Java 21 and 8 to 10 GiB RAM, then launch it.

CurseForge imports do not auto-update. When Shane shares a newer AFTERLIGHT ZIP, import that replacement as a new profile. Keep the old profile until the new one reaches the title screen and joins the server.

## Other Friends-Only Archive

`AFTERLIGHT-0.9.0-rc.3.mrpack` is a manual fallback for compatible launchers. It is friends-only in this project because the current export embeds third-party mod JARs. It does not replace the recommended auto-updating Prism ZIP.

## Joining the Server

Get the server address from Shane. The group uses Discord for voice. Simple Voice Chat remains installed for compatibility but is optional and is not required to play.

## First-Launch Troubleshooting

- **Microsoft login:** In Prism, open Accounts, add a Microsoft account, finish the browser login, and select that account before launching.
- **Java selection:** Select a Java 21 runtime and use the launcher's Java test. Do not launch AFTERLIGHT with Java 17 or an older runtime.
- **Memory:** Assign 8192 to 10240 MiB. If the computer has less than 12 GiB total RAM, ask Shane before allocating more.
- **Packwiz download errors:** Check the internet connection, retry once, then send Shane the complete error text and failed URL. Do not bypass Packwiz or add mod JARs manually.
- **CurseForge invalid file:** Confirm the file ends in `.zip`, came directly from Shane, and is the CurseForge archive rather than the Prism ZIP or `.mrpack`.
- **Crash Assistant:** Use Copy to clipboard and send Shane the complete text. Send text instead of a screenshot so the report remains searchable.
