# Releasing AFTERLIGHT

Run every release from a clean `dev` checkout. Every published release and tag is immutable and must never be moved, replaced, or force-pushed. Shane explicitly authorized public distribution of the current CurseForge ZIP and `.mrpack` on 2026-08-11, superseding earlier friends-only release instructions.

## Local Acceptance

Derive every release identity from `pack.toml`:

```bash
set -euo pipefail
VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open("pack.toml", "rb"))["version"])')
TAG="v$VERSION"
RELEASE_DOC="docs/releases/$VERSION.md"
SHA=$(git rev-parse HEAD)
test -f "$RELEASE_DOC"
./tools/release-gauntlet.sh "$SHA"
# Copy the exact digest printed by GAUNTLET RECEIPT SHA-256.
RECEIPT_SHA256='paste-the-printed-64-character-digest-here'
test "$(shasum -a 256 "dist/gauntlet/$SHA/gauntlet-receipt.json" | awk '{print $1}')" = "$RECEIPT_SHA256"
```

The gauntlet accepts only the exact clean `HEAD`. It runs the full Python suite, Packwiz verification, a fresh dedicated-server boot, Compose rendering, ShellCheck, two release builds, byte comparison, and a clean two-pass client install from the built Prism bytes. The accepted five-file public inventory is stored flat under `dist/gauntlet/$SHA/public/`.

The gauntlet also writes canonical nonpublic evidence to `dist/gauntlet/$SHA/gauntlet-receipt.json`. The receipt binds the accepted commit, version, production Packwiz URL, tracked installer pins, and SHA-256 plus size for all five public files. Capture the printed receipt digest when the gauntlet completes. Do not recalculate a replacement digest at promotion or publication time. The receipt is evidence only and must never become a public release asset.

## Promotion

Promote only the SHA accepted by the local gauntlet:

```bash
tools/promote-release.sh "$SHA" "$RECEIPT_SHA256" --confirm
```

Before any push, merge, or tag, the promoter requires the single fetch URL and single push URL for `origin` to identify the production repository. Every branch and tag push targets that captured production URL directly with an explicit refspec. It verifies the independently supplied receipt digest, all five current public bytes, metadata and checksums, format-specific archive contents, and the trusted values in `tools/release-policy.env`. Both CurseForge and Modrinth archives are reconciled against the accepted commit's exact Packwiz tree. Modrinth SHA-1 and file-size fields must also match the accepted `tools/modrinth-manifest-lock.json`; the lock binds each record to its Packwiz metadata path, URL, archive path, and SHA-512 identity. It then pushes `dev`, waits for that exact push CI, fast-forwards `main`, waits for exact `main` CI, and requires ordinary bare and cache-busted GitHub Pages byte parity through curl with local configuration disabled and HTTPS-only redirects. It derives accepted client mod-set and complete Packwiz payload SHA-256 values from a clean local install, rejects any unexpected installed file outside the three pinned Packwiz installer infrastructure files, completes another clean install directly from the public Pages URL, requires both installed mod sets and payloads to be byte-identical, and checks Pages parity again. Only then does it create and push the annotated `TAG` and return to `dev`. The annotated tag message binds the receipt digest and all five accepted public-file hashes. Any missing or red gate stops before the next transition.

Whenever a non-CurseForge mod changes, regenerate `tools/modrinth-manifest-lock.json` from independently verified upstream metadata. Modrinth records must match the public v2 version API. Direct-download records must be streamed and hashed locally. Never copy unchecked SHA-1 or file-size values from an exported `.mrpack` into the lock.

## Evidence

Record the promoter's exact SHA, receipt digest, transcript digest, accepted `dev` and `main` CI URLs, Pages hashes, tool versions, and five artifact hashes in `RELEASE_DOC`. Populate every prepublication automated evidence field. The automated evidence through the public artifact section must contain no automated `NOT RUN` and must contain no automated `PENDING` value. The publisher independently requires each canonical prepublication evidence line exactly once and derives its expected values from the accepted receipt, transcript, repository files, and exact accepted GitHub Actions runs. It also requires the distinct documentation evidence commit's exact CI run at publication time and prints that run URL for postpublication recording. Requiring that future run URL inside its own commit would be circular. Publication-only values belong in the postpublication section. Manual acceptance remains pending until a player or VPS operator actually observes it.

Commit only `docs/HANDOFF.md` and the populated release document on `dev` with the required agent trailer, push the distinct documentation evidence commit, and require that exact commit's `pack-ci` push run to pass.

## Publication

The publisher requires the same independently captured `RECEIPT_SHA256`, the production repository origin, and remote `main` at the accepted SHA. The current `dev` HEAD must be a distinct pushed descendant of the accepted SHA. Only `docs/HANDOFF.md` and the matching release document may differ, publication tooling and policy must remain byte-identical to the accepted SHA, and the exact accepted `dev`, accepted `main`, and documentation evidence CI runs must be green. The publisher also verifies the requested version against current `pack.toml`, the accepted commit's `pack.toml`, metadata, canonical filenames, release-note title, annotated local and remote tag objects, and the requested mode. It proves that the annotated tag message binds the supplied receipt digest and all five receipt hashes, then revalidates the receipt and every public byte immediately before invoking GitHub.

For a release candidate:

```bash
tools/publish-release.sh "$SHA" "$VERSION" "$RECEIPT_SHA256" --prerelease --confirm
```

For final `1.0.0` after the complete manual matrix passes:

```bash
tools/publish-release.sh "$SHA" "$VERSION" "$RECEIPT_SHA256" --confirm
```

The GitHub release may contain only:

```text
AFTERLIGHT-prism-instance.zip
AFTERLIGHT-curseforge.zip
AFTERLIGHT.mrpack
SHA256SUMS
release-metadata.json
```

The publisher creates a draft GitHub release without assets through the GitHub API and captures its numeric release ID from that same response. Every upload, authenticated download, state check, and publication request is scoped to that ID. It uploads exactly these five files and verifies their inventory and bytes through authenticated asset-ID downloads. After GitHub confirms publication, it repeats inventory and byte verification through unauthenticated downloads with local curl configuration disabled. The publisher never automatically deletes a release. Any failure after creation preserves the draft or published release and prints the numeric ID for manual inspection, which avoids deleting a release another actor may have published concurrently. If release creation itself returns an ambiguous or malformed result, the publisher reports the tag for manual inspection and never deletes by tag or by an untrusted ID. Release directories reject friends-only subdirectories, versioned public archive names, missing checksums, extra entries, and links. Every archive must pass path, traversal, Windows safety, secret, private-key, JWT-shaped value, bounded decompression, manifest-record, exact Packwiz reconciliation, and malformed-ZIP inspection before metadata and checksums are written. No unclassified file may be published. `gauntlet-receipt.json` remains outside this five-file inventory.

## Recovery

If `dev` CI, `main` CI, Pages parity, publication, or a manual gate fails, fix forward through a new candidate SHA. Never force-push `dev` or `main`, and never move a published tag.

## Server Deployment

Artifact publication does not authorize an unsafe server update. For a revision with any quest corpus change, derive the exact deployed SHA from the accepted release and run `sudo server/afterlight-quest-safe-update.sh "$SHA" --confirm` on the VPS only after the repository checkout equals that SHA. Ordinary `server/afterlight-server.sh update` is reserved for non-quest revisions.

The quest-safe transaction holds the maintenance lock and external connection gate through two zero-player checks, a direct verified backup, the candidate's first start and clean stop, canonical FTB Quests and FTB Teams comparison, whitelist verification, and the second healthy start. Any durable quarantine marker blocks ordinary updates and scheduled maintenance. Follow `server/README.md` exactly for quarantine recovery, and remove only the transaction's exact owned firewall rule after the restored release passes every recovery proof.
