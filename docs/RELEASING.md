# Releasing AFTERLIGHT

Run the gauntlet from a clean `dev` checkout. It accepts only the exact local
`HEAD` SHA and leaves accepted public and friends-only artifacts under
`dist/gauntlet/$SHA/`.

## Promotion

Run the fail-closed promoter from the clean `dev` checkout that owns the
accepted gauntlet output. Do not substitute another SHA after the local
gauntlet succeeds. The promoter pushes `dev`, waits for its exact push-event CI
run, fast-forwards `main`, waits for the exact `main` run, requires Pages byte
parity, publishes the annotated tag, and returns to `dev`. Any missing or red
gate stops before the next transition.

```bash
SHA=$(git rev-parse HEAD)
./tools/release-gauntlet.sh "$SHA"
tools/promote-release.sh "$SHA" --confirm
```

Record the promoter's exact SHA, CI URLs, and Pages hashes in
`docs/releases/0.9.0-rc.1.md`. Populate every automated evidence field and the
five artifact hashes before publication. The automated evidence through the
friends-only artifact section must contain no automated `NOT RUN` values.
Manual acceptance stays `NOT RUN` until a player or host observes it.

Commit the populated evidence on `dev` with the required agent trailer, push
it, and require that exact docs commit's `pack-ci` run to succeed. Then publish
only the accepted public files in one fail-closed shell:

```bash
set -euo pipefail
SHA=REPLACE_WITH_ACCEPTED_CODE_SHA
if sed -n '/^## Automated Evidence$/,/^## Known Boundaries$/p' docs/releases/0.9.0-rc.1.md | grep -Fq 'NOT RUN'; then
  printf '%s\n' 'release notes still contain automated NOT RUN evidence' >&2
  exit 1
fi
REMOTE_TAG_SHA=$(git ls-remote origin 'refs/tags/v0.9.0-rc.1^{}' | awk '{print $1}')
[ "$REMOTE_TAG_SHA" = "$SHA" ] || exit 1
gh release create v0.9.0-rc.1 --verify-tag --prerelease --title "AFTERLIGHT 0.9.0-rc.1" --notes-file docs/releases/0.9.0-rc.1.md "dist/gauntlet/$SHA/public/AFTERLIGHT-prism-instance.zip" "dist/gauntlet/$SHA/public/release-metadata.json" "dist/gauntlet/$SHA/public/SHA256SUMS"
EXPECTED_ASSETS=$'AFTERLIGHT-prism-instance.zip\nSHA256SUMS\nrelease-metadata.json'
ACTUAL_ASSETS=$(gh release view v0.9.0-rc.1 --json assets --jq '.assets[].name' | sort)
[ "$ACTUAL_ASSETS" = "$EXPECTED_ASSETS" ] || exit 1
```

The GitHub prerelease may contain only the three files from `public/`. The
`.mrpack` and CurseForge ZIP remain in `friends-only/` and must never be
attached to a public release.

## Recovery

If `main` CI fails, the promoter does not publish the tag. It returns to `dev`
and leaves `main` at its failed fast-forward. Fix forward, rerun the gauntlet
for the new SHA, and promote that new SHA through both CI runs. Never
force-push `dev` or `main`.
