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
```

The gauntlet accepts only the exact clean `HEAD`. It runs the full Python suite, Packwiz verification, a fresh dedicated-server boot, Compose rendering, ShellCheck, two release builds, byte comparison, and a clean two-pass client install from the built Prism bytes. The accepted five-file public inventory is stored flat under `dist/gauntlet/$SHA/public/`.

## Promotion

Promote only the SHA accepted by the local gauntlet:

```bash
tools/promote-release.sh "$SHA" --confirm
```

The promoter pushes `dev`, waits for that exact push CI, fast-forwards `main`, waits for exact `main` CI, requires GitHub Pages byte parity, creates and pushes the annotated `TAG`, and returns to `dev`. Any missing or red gate stops before the next transition.

## Evidence

Record the promoter's exact SHA, CI URLs, Pages hashes, tool versions, and five artifact hashes in `RELEASE_DOC`. Populate every automated evidence field. The automated evidence through the public artifact section must contain no automated `NOT RUN` value. Manual acceptance remains `NOT RUN` until a player or VPS operator actually observes it.

Commit the populated evidence on `dev` with the required agent trailer, push it, and require that exact documentation commit's `pack-ci` push run to pass.

## Publication

The publisher verifies the requested version against current `pack.toml`, the accepted commit's `pack.toml`, metadata, canonical filenames, release-note title, annotated local and remote tag, and the requested mode. It also requires the exact flat inventory and complete public checksums before invoking GitHub.

For a release candidate:

```bash
tools/publish-release.sh "$SHA" "$VERSION" --prerelease --confirm
```

For final `1.0.0` after the complete manual matrix passes:

```bash
tools/publish-release.sh "$SHA" "$VERSION" --confirm
```

The GitHub release may contain only:

```text
AFTERLIGHT-prism-instance.zip
AFTERLIGHT-curseforge.zip
AFTERLIGHT.mrpack
SHA256SUMS
release-metadata.json
```

All five files are attached to GitHub. Release directories reject friends-only subdirectories, versioned public archive names, missing checksums, extra entries, and links. Every archive must pass path, traversal, secret, private-key, and malformed-ZIP inspection before metadata and checksums are written. No unclassified file may be published.

## Recovery

If `dev` CI, `main` CI, Pages parity, publication, or a manual gate fails, fix forward through a new candidate SHA. Never force-push `dev` or `main`, and never move a published tag.
