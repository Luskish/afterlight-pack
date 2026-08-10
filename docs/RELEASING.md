# Releasing AFTERLIGHT

Run the gauntlet from a clean `dev` checkout. It accepts only the exact local
`HEAD` SHA and leaves accepted public and friends-only artifacts under
`dist/gauntlet/$SHA/`.

## Promotion

Run these commands in order. Do not substitute another SHA after the local
gauntlet succeeds.

```bash
SHA=$(git rev-parse HEAD)
./tools/release-gauntlet.sh "$SHA"
git push origin dev
DEV_RUN_ID=$(gh run list --workflow pack-ci --branch dev --commit "$SHA" --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$DEV_RUN_ID" --exit-status
git switch main
git merge --ff-only "$SHA"
git push origin main
MAIN_RUN_ID=$(gh run list --workflow pack-ci --branch main --commit "$SHA" --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$MAIN_RUN_ID" --exit-status
curl -fsSL https://luskish.github.io/afterlight-pack/pack.toml | shasum -a 256
curl -fsSL https://luskish.github.io/afterlight-pack/index.toml | shasum -a 256
git tag -a v0.9.0-rc.1 "$SHA" -m "AFTERLIGHT 0.9.0-rc.1"
git push origin v0.9.0-rc.1
gh release create v0.9.0-rc.1 --prerelease --title "AFTERLIGHT 0.9.0-rc.1" --notes-file docs/releases/0.9.0-rc.1.md dist/gauntlet/$SHA/public/AFTERLIGHT-prism-instance.zip dist/gauntlet/$SHA/public/release-metadata.json dist/gauntlet/$SHA/public/SHA256SUMS
git switch dev
```

The GitHub prerelease may contain only the three files from `public/`. The
`.mrpack` and CurseForge ZIP remain in `friends-only/` and must never be
attached to a public release.

## Recovery

If `main` CI fails, do not publish the tag. Leave `main` at its failed
fast-forward, switch back to `dev`, fix forward, rerun the gauntlet for the new
SHA, and promote that new SHA through both CI runs. Never force-push `dev` or
`main`.
