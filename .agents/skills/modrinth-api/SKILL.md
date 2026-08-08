---
name: modrinth-api
description: Use the Modrinth API (v2) to search Minecraft mods, read project metadata, download JARs, and locate source repositories. No API token required for read operations. Use when fetching mod info from Modrinth, searching mods by name/category/loader/version, downloading mod files programmatically, or finding a mod's GitHub/source-code URL.
license: MIT
metadata:
  version: "1.0.0"
---

# Modrinth API

Use this skill to interact with the Modrinth Labrinth API (v2). All read-only endpoints are public — no API token needed. Only creating/editing projects or accessing private data requires authentication.

## Quick Reference

| Task | Endpoint |
|------|----------|
| Search mods | `GET /v2/search` |
| Get one project | `GET /v2/project/{id-or-slug}` |
| Get multiple projects | `GET /v2/projects?ids=["id1","id2"]` |
| List versions | `GET /v2/project/{id}/version` |
| Get one version | `GET /v2/version/{id}` |
| Download JAR | `GET` the `files[].url` from a version |
| Find source repo | Read `source_url` from project |
| Tags (categories/loaders/versions) | `GET /v2/tag/{type}` |

**Base URL**: `https://api.modrinth.com/v2`

## Prerequisites

### User-Agent (Required)

Every request **must** include a unique `User-Agent` header. Generic library names (e.g. `okhttp/4.9.3`) risk being blocked.

```
# Best — includes contact info
User-Agent: github_username/project_name/1.0.0 (contact@example.com)

# Minimum acceptable
User-Agent: my-project-name
```

### Rate Limit

300 requests per minute. Respect `X-Ratelimit-*` response headers.

### Authentication

Not needed for reading public data. Personal Access Tokens (PATs) are only required for:
- Creating/editing projects and versions
- Accessing draft projects, notifications, emails, payouts

Generate a PAT at <https://modrinth.com/settings/account>. Send it as:
```
Authorization: mrp_YOUR_TOKEN_HERE
```

### Identifiers

- Projects, versions, users — 8-character base62 ID (e.g. `AANobbMI`).
- Versions also have per-project `version_number` strings.
- Files — identified by SHA-1 or SHA-512 hash.
- Slugs — human-readable (e.g. `sodium`), can change; IDs are permanent.

---

## Endpoints

### 1. Search Projects

```
GET /v2/search?query={query}&limit={n}&offset={n}&facets={json}
```

**Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | — | Search text (name, description, author) |
| `limit` | int | 10 | Results per page (max 100) |
| `offset` | int | 0 | Pagination offset |
| `facets` | JSON string | — | Filter/OR grouping (see below) |
| `index` | string | `relevance` | Sort: `relevance`, `downloads`, `follows`, `newest`, `updated` |

**Facets format** — JSON-encoded array of AND groups, each inner array is OR:
```
# Mods in category "fabric" or "technology", that are mods (not modpacks)
facets=[["categories:fabric","categories:technology"],["project_type:mod"]]

# Mods for Minecraft 1.21.1 on Fabric loader
facets=[["versions:1.21.1"],["categories:fabric"],["project_type:mod"]]

# Using cURL
curl "https://api.modrinth.com/v2/search?query=sodium&limit=5&facets=%5B%5B%22categories%3Afabric%22%5D%5D"
```

**Response** (key fields):
```json
{
  "hits": [
    {
      "project_id": "AANobbMI",
      "slug": "sodium",
      "title": "Sodium",
      "description": "...",
      "author": "jellysquid3",
      "categories": ["fabric", "neoforge", "optimization"],
      "versions": ["1.21.1", "1.21.4", ...],
      "downloads": 162503459,
      "follows": 36940,
      "icon_url": "https://cdn.modrinth.com/...",
      "date_created": "2021-01-03T00:53:34Z",
      "date_modified": "2026-05-25T13:18:54Z",
      "latest_version": "tVLDCyrm",
      "client_side": "required",
      "server_side": "unsupported",
      "project_type": "mod"
    }
  ],
  "offset": 0,
  "limit": 5,
  "total_hits": 280
}
```

### 2. Get One Project

```
GET /v2/project/{id-or-slug}
```

Works with both the 8-char ID (`AANobbMI`) and slug (`sodium`).

**Response** (full fields — important ones shown):
```json
{
  "id": "AANobbMI",
  "slug": "sodium",
  "title": "Sodium",
  "description": "Short description (plain text)",
  "body": "Full Markdown description...",
  "project_type": "mod",
  "client_side": "required",
  "server_side": "unsupported",
  "categories": ["optimization"],
  "loaders": ["fabric", "neoforge", "quilt"],
  "game_versions": ["1.21.1", "1.21.4", ...],
  "downloads": 162505822,
  "followers": 36940,
  "icon_url": "...",
  "license": {"id": "MIT", "name": "MIT", "url": "https://..."},

  "source_url": "https://github.com/CaffeineMC/sodium",
  "issues_url": "https://github.com/CaffeineMC/sodium/issues",
  "wiki_url": "https://github.com/CaffeineMC/sodium/wiki",
  "discord_url": "https://caffeinemc.net/discord",
  "donation_urls": [
    {"id": "ko-fi", "platform": "Ko-fi", "url": "https://..."}
  ],

  "versions": ["tVLDCyrm", "uheoPKxU", ...],
  "gallery": [{"url": "...", "featured": false, "title": "...", "description": "..."}],
  "status": "approved",
  "published": "2021-01-03T00:53:34Z",
  "updated": "2026-05-25T13:19:01Z"
}
```

`source_url` is the canonical field for the source repository (usually GitHub).

### 3. Get Multiple Projects

```
GET /v2/projects?ids=["AANobbMI","P7dR8mSH"]
```

Returns an array of project objects identical to the single-project response.

### 4. List Versions of a Project

```
GET /v2/project/{id-or-slug}/version?loaders=["fabric"]&game_versions=["1.21.1"]&limit=3
```

**Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `loaders` | JSON array | Filter by loader: `["fabric"]`, `["fabric","neoforge"]` |
| `game_versions` | JSON array | Filter by MC version: `["1.21.1"]` |
| `featured` | bool | Only featured versions |

**Response** — array of version objects (see §5).

### 5. Get One Version

```
GET /v2/version/{id}
```

```json
{
  "id": "uheoPKxU",
  "project_id": "AANobbMI",
  "name": "Sodium 0.8.12-alpha.4 for Fabric 1.21.1",
  "version_number": "mc1.21.1-0.8.12-alpha.4-fabric",
  "changelog": "Markdown changelog...",
  "date_published": "2026-05-25T13:19:01Z",
  "downloads": 133615,
  "version_type": "alpha",
  "game_versions": ["1.21.1"],
  "loaders": ["fabric"],
  "dependencies": [],
  "files": [
    {
      "id": "x96tJq3U",
      "hashes": {
        "sha1": "5db45837af4de14136f8ee6f6f7ba1a4d69b1972",
        "sha512": "cad8769ac8cf..."
      },
      "url": "https://cdn.modrinth.com/data/AANobbMI/versions/uheoPKxU/sodium-fabric-0.8.12-alpha.4%2Bmc1.21.1.jar",
      "filename": "sodium-fabric-0.8.12-alpha.4+mc1.21.1.jar",
      "primary": true,
      "size": 1565263
    }
  ]
}
```

### 6. Download a JAR

The `files[].url` field is a direct CDN download URL. No auth needed.
```
curl -O "https://cdn.modrinth.com/data/AANobbMI/versions/uheoPKxU/sodium-fabric-0.8.12-alpha.4%2Bmc1.21.1.jar"
```

For scripts, construct the URL from version data rather than guessing filenames.

---

### 7. Tags / Enumerations

List available values for filtering.

```
GET /v2/tag/category         # Adventure, combat, fabric, library, optimization, technology, ...
GET /v2/tag/loader           # fabric, forge, neoforge, quilt, ...
GET /v2/tag/game_version     # 1.21.1, 1.21.4, 26.1, 26.2-pre-3, ...
GET /v2/tag/license          # MIT, Apache-2.0, LGPL-3.0, ARR, ...
GET /v2/tag/donation_platform # ko-fi, patreon, github, paypal, ...
```

Each returns an array with `name` (and optionally `project_type`, `icon`, `header`).

---

## Common Recipes

### Find a mod's source code
```bash
# 1. Get project by slug
curl -H "User-Agent: my-tool/1.0" \
  "https://api.modrinth.com/v2/project/sodium" | jq '.source_url'
# => "https://github.com/CaffeineMC/sodium"
```

### Download latest Fabric 1.21.1 JAR for a mod
```bash
#!/bin/bash
PROJECT="sodium"
MC="1.21.1"
LOADER="fabric"
UA="my-tool/1.0 (dev@example.com)"

# Get project to find version IDs
VERSIONS=$(curl -s -H "User-Agent: $UA" \
  "https://api.modrinth.com/v2/project/$PROJECT/version?loaders=[\"$LOADER\"]&game_versions=[\"$MC\"]&limit=1")

# Extract download URL of primary file
URL=$(echo "$VERSIONS" | jq -r '.[0].files[] | select(.primary) | .url')
FNAME=$(echo "$VERSIONS" | jq -r '.[0].files[] | select(.primary) | .filename')

curl -o "$FNAME" "$URL"
```

### Search with facets (Fabric mods, technology category)
```bash
curl -s -H "User-Agent: my-tool/1.0" \
  "https://api.modrinth.com/v2/search?query=optimization&limit=5&facets=%5B%5B%22categories%3Afabric%22%5D%2C%5B%22project_type%3Amod%22%5D%5D" \
  | jq '.hits[] | {title, slug, downloads, source_url}'
```

Note: `source_url` is absent from search hits — only in the full project response. Do a follow-up `GET /v2/project/{slug}` for each result.

### Bulk source-code discovery
```bash
#!/bin/bash
# Search Fabric mods matching a term, then fetch source URLs
QUERY="render"
UA="my-tool/1.0"

curl -s -H "User-Agent: $UA" \
  "https://api.modrinth.com/v2/search?query=$QUERY&limit=10&facets=%5B%5B%22categories%3Afabric%22%5D%5D" \
  | jq -r '.hits[].slug' \
  | while read slug; do
      curl -s -H "User-Agent: $UA" \
        "https://api.modrinth.com/v2/project/$slug" \
        | jq -r "{slug: .slug, title: .title, source: .source_url}"
    done
```

---

## Field Reference

### Project Object (selected fields)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | 8-char base62 permanent ID |
| `slug` | string | Human-readable slug (may change) |
| `title` | string | Display name |
| `description` | string | Short plain-text summary |
| `body` | string | Full Markdown description page |
| `project_type` | string | `mod`, `modpack`, `resourcepack`, `shader`, `datapack`, `plugin` |
| `client_side` | string | `required`, `optional`, `unsupported`, `unknown` |
| `server_side` | string | `required`, `optional`, `unsupported`, `unknown` |
| `categories` | string[] | e.g. `["fabric", "optimization"]` |
| `loaders` | string[] | e.g. `["fabric", "neoforge"]` |
| `game_versions` | string[] | Supported Minecraft versions |
| `downloads` | int | Total download count |
| `followers` | int | Follower count |
| `license` | object | `{id, name, url}` |
| `source_url` | string\|null | Source repository URL |
| `issues_url` | string\|null | Issue tracker URL |
| `wiki_url` | string\|null | Wiki URL |
| `discord_url` | string\|null | Discord invite |
| `donation_urls` | array\|null | `[{id, platform, url}]` |
| `gallery` | array\|null | `[{url, featured, title, description, ordering}]` |
| `versions` | string[] | Version IDs (latest first) |
| `status` | string | `approved`, `archived`, `rejected`, `draft`, `unlisted`, `processing`, `withheld`, `scheduled`, `private`, `unknown` |
| `icon_url` | string\|null | Project icon CDN URL |
| `color` | int\|null | Dominant color as RGB int |
| `monetization_status` | string | `monetized`, `demonetized`, `force-demonetized` |

### Version Object (selected fields)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | 8-char version ID |
| `project_id` | string | Parent project ID |
| `name` | string | Human-readable name |
| `version_number` | string | Semver-like version string |
| `changelog` | string\|null | Markdown changelog |
| `date_published` | string | ISO 8601 timestamp |
| `downloads` | int | Download count for this version |
| `version_type` | string | `release`, `beta`, `alpha` |
| `game_versions` | string[] | MC versions this file targets |
| `loaders` | string[] | Loaders this file targets |
| `dependencies` | array | `[{version_id, project_id, dependency_type}]` |
| `files` | array | `[{id, url, filename, size, hashes: {sha1, sha512}, primary, file_type}]` |
| `status` | string | `listed`, `archived`, `draft`, `unlisted`, `scheduled`, `unknown` |

### Search Hit (subset of Project)

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | string | 8-char ID |
| `slug` | string | Slug |
| `title` | string | Display name |
| `description` | string | Short description |
| `author` | string | Author username |
| `categories` | string[] | Category tags |
| `versions` | string[] | Supported MC versions |
| `downloads` | int | Total downloads |
| `follows` | int | Follower count |
| `icon_url` | string\|null | Icon |
| `date_created` | string | ISO 8601 |
| `date_modified` | string | ISO 8601 |
| `latest_version` | string | Latest version ID |
| `client_side` | string | — |
| `server_side` | string | — |
| `project_type` | string | — |

---

## Facets Quick Reference

Facet field names used in search `facets` and project version filtering:

| Facet key | Example values |
|-----------|---------------|
| `categories` | `fabric`, `forge`, `neoforge`, `quilt`, `optimization`, `library`, `technology`, `adventure`, `utility`, `decoration`, ... |
| `project_type` | `mod`, `modpack`, `resourcepack`, `shader`, `datapack`, `plugin` |
| `versions` | `1.21.1`, `1.20.1`, `1.21.4`, ... |
| `license` | `mit`, `apache-2.0`, `lgpl-3.0`, `arr`, ... |
| `client_side` | `required`, `optional`, `unsupported` |
| `server_side` | `required`, `optional`, `unsupported` |
| `open_source` | `true`, `false` |

---

## Limitations & Tips

1. **`source_url` absent from search results** — search hits are a slim projection. Always follow up with `GET /v2/project/{slug}` for the full object including source/issue/wiki URLs.

2. **Slugs can change** — for persistent storage, use the 8-char `id`, not the slug.

3. **Version list is paginated** — use `limit`/`offset`, or collect all by walking the array in the project's `versions[]` field and calling `GET /v2/version/{id}` individually.

4. **Facets must be JSON-encoded** — the `facets` query parameter expects a JSON array of arrays, URL-encoded. Use `jq -r @uri` to encode: `echo '[["categories:fabric"]]' | jq -r @uri`.

5. **Rate limit** — 300 req/min. Batch with `GET /v2/projects?ids=...` when fetching many projects.

6. **No auth needed for public data** — unlike CurseForge, Modrinth's read API is fully open.

7. **Staging API** — use `https://staging-api.modrinth.com` for testing; production is `https://api.modrinth.com`. The staging API may run a newer Labrinth version.

8. **Files are validated** — Modrinth verifies uploaded JARs contain valid mod metadata (e.g. `fabric.mod.json`, `mods.toml`). Corrupt or non-mod JARs are rejected.
