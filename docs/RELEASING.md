# Releasing AFTERLIGHT

Run every release from a clean `dev` checkout. `v0.9.0-rc.1` is immutable rollback evidence and must never be moved, replaced, or force-pushed.

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

The gauntlet accepts only the exact clean `HEAD`. It runs the full Python suite, Packwiz verification, a fresh dedicated-server boot, Compose rendering, ShellCheck, two release builds, byte comparison, and a clean two-pass client install from the built Prism bytes. Accepted public and friends-only artifacts are stored under `dist/gauntlet/$SHA/`.

## Promotion

Promote only the SHA accepted by the local gauntlet:

```bash
tools/promote-release.sh "$SHA" --confirm
```

The promoter pushes `dev`, waits for that exact push CI, fast-forwards `main`, waits for exact `main` CI, requires GitHub Pages byte parity, creates and pushes the annotated `TAG`, and returns to `dev`. Any missing or red gate stops before the next transition.

## Evidence

Record the promoter's exact SHA, CI URLs, Pages hashes, tool versions, and five artifact hashes in `RELEASE_DOC`. Populate every automated evidence field. The automated evidence through the friends-only artifact section must contain no automated `NOT RUN` value. Manual acceptance remains `NOT RUN` until a player or VPS operator actually observes it.

Commit the populated evidence on `dev` with the required agent trailer, push it, and require that exact documentation commit's `pack-ci` push run to pass.

## Publication

The publisher verifies the requested version against current `pack.toml`, the accepted commit's `pack.toml`, metadata, filenames, release-note title, annotated local and remote tag, and the requested mode. It also checks both artifact inventories and public checksums before invoking GitHub.

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
release-metadata.json
SHA256SUMS
```

The `.mrpack` and CurseForge ZIP remain under `dist/gauntlet/$SHA/friends-only/`. Share them directly with trusted friends. Never attach them to a public release or CI artifact.

## Recovery

If `dev` CI, `main` CI, Pages parity, publication, or a manual gate fails, fix forward through a new candidate SHA. Never force-push `dev` or `main`, and never move a published tag.
