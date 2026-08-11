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

Before any push, merge, or tag, the promoter verifies the independently supplied receipt digest, all five current public bytes, metadata and checksums, format-specific archive contents, and the trusted values in `tools/release-policy.env`. It then pushes `dev`, waits for that exact push CI, fast-forwards `main`, waits for exact `main` CI, requires GitHub Pages byte parity, creates and pushes the annotated `TAG`, and returns to `dev`. The annotated tag message binds the receipt digest and all five accepted public-file hashes. Any missing or red gate stops before the next transition.

## Evidence

Record the promoter's exact SHA, receipt digest, CI URLs, Pages hashes, tool versions, and five artifact hashes in `RELEASE_DOC`. Populate every automated evidence field. The automated evidence through the public artifact section must contain no automated `NOT RUN` value. Manual acceptance remains `NOT RUN` until a player or VPS operator actually observes it.

Commit the populated evidence on `dev` with the required agent trailer, push it, and require that exact documentation commit's `pack-ci` push run to pass.

## Publication

The publisher requires the same independently captured `RECEIPT_SHA256`. It verifies the requested version against current `pack.toml`, the accepted commit's `pack.toml`, metadata, canonical filenames, release-note title, annotated local and remote tag objects, and the requested mode. It proves that the annotated tag message binds the supplied receipt digest and all five receipt hashes, then revalidates the receipt and every public byte immediately before invoking GitHub.

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

All five files are attached to GitHub. Release directories reject friends-only subdirectories, versioned public archive names, missing checksums, extra entries, and links. Every archive must pass path, traversal, Windows safety, secret, private-key, bounded decompression, manifest-record, and malformed-ZIP inspection before metadata and checksums are written. No unclassified file may be published. `gauntlet-receipt.json` remains outside this five-file inventory.

## Recovery

If `dev` CI, `main` CI, Pages parity, publication, or a manual gate fails, fix forward through a new candidate SHA. Never force-push `dev` or `main`, and never move a published tag.
