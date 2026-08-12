from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path


MINECRAFT_VERSION = "1.21.1"
NEOFORGE_VERSION = "21.1.248"
PACK_URL = "https://luskish.github.io/afterlight-pack/pack.toml"
BOOTSTRAP_BYTES = b"Packwiz bootstrap fixture\n"
INSTALLER_BYTES = b"Packwiz installer fixture\n"
BOOTSTRAP_VERSION = "0.0.3-test"
INSTALLER_VERSION = "0.5.14-test"
PUBLIC_RELEASE_NAMES = (
    "AFTERLIGHT-curseforge.zip",
    "AFTERLIGHT-prism-instance.zip",
    "AFTERLIGHT.mrpack",
    "SHA256SUMS",
    "release-metadata.json",
)
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FILE_MODE = stat.S_IFREG | 0o644
AUTHORED_PATH = "config/afterlight-fixture.cfg"
AUTHORED_BYTES = b"fixture=true\n"
SIGNAL_METADATA_PATH = "mods/afterlight-signal.pw.toml"
SIGNAL_FILENAME = "afterlight-signal-fixture.jar"
SIGNAL_BYTES = b"signal fixture jar\n"
SERVER_FILENAME = "server-helper-fixture.jar"
SERVER_BYTES = b"server helper fixture jar\n"
CURSEFORGE_MODS = (
    {
        "filename": "curseforge-main-fixture.jar",
        "jar_bytes": b"curseforge main fixture jar\n",
        "metadata_path": "mods/curseforge-main.pw.toml",
        "name": "CurseForge Main Fixture",
        "project_id": 238222,
        "file_id": 5629847,
    },
    {
        "filename": "curseforge-library-fixture.jar",
        "jar_bytes": b"curseforge library fixture jar\n",
        "metadata_path": "mods/curseforge-library.pw.toml",
        "name": "CurseForge Library Fixture",
        "project_id": 419699,
        "file_id": 8492726,
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _instance_config(pack_url: str = PACK_URL) -> bytes:
    return (
        "InstanceType=OneSix\n"
        "name=AFTERLIGHT\n"
        "iconKey=default\n"
        "OverrideCommands=true\n"
        'PreLaunchCommand="$INST_JAVA" -jar packwiz-installer-bootstrap.jar '
        "--bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g "
        f"{pack_url}\n"
    ).encode("utf-8")


def _mmc_pack() -> bytes:
    manifest = {
        "components": [
            {
                "important": True,
                "uid": "net.minecraft",
                "version": MINECRAFT_VERSION,
            },
            {"uid": "net.neoforged", "version": NEOFORGE_VERSION},
        ],
        "formatVersion": 1,
    }
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_zip(path: Path, entries: dict[str, bytes], *, normalized: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for name in sorted(entries):
            if normalized:
                info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.create_version = 20
                info.extract_version = 20
                info.external_attr = FILE_MODE << 16
                info.internal_attr = 0
                info.flag_bits = 0
                info.extra = b""
                info.comment = b""
                archive.writestr(
                    info,
                    entries[name],
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
            else:
                archive.writestr(name, entries[name])


def _mod_metadata(
    name: str,
    filename: str,
    side: str,
    jar_bytes: bytes,
    *,
    project_id: int | None = None,
    file_id: int | None = None,
) -> bytes:
    lines = [
        f"name = {json.dumps(name)}",
        f"filename = {json.dumps(filename)}",
        f"side = {json.dumps(side)}",
        "",
        "[download]",
        'url = "https://example.invalid/fixture.jar"',
        'hash-format = "sha512"',
        f'hash = "{hashlib.sha512(jar_bytes).hexdigest()}"',
    ]
    if project_id is not None and file_id is not None:
        lines.extend(
            [
                "",
                "[update.curseforge]",
                f"file-id = {file_id}",
                f"project-id = {project_id}",
            ]
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _packwiz_files(version: str) -> dict[str, bytes]:
    tracked_files = {AUTHORED_PATH: AUTHORED_BYTES}
    for mod in CURSEFORGE_MODS:
        tracked_files[mod["metadata_path"]] = _mod_metadata(
            mod["name"],
            mod["filename"],
            "both",
            mod["jar_bytes"],
            project_id=mod["project_id"],
            file_id=mod["file_id"],
        )
    tracked_files[SIGNAL_METADATA_PATH] = _mod_metadata(
        "AFTERLIGHT Signal",
        SIGNAL_FILENAME,
        "both",
        SIGNAL_BYTES,
    )
    tracked_files["mods/server-helper.pw.toml"] = _mod_metadata(
        "Server Helper Fixture",
        SERVER_FILENAME,
        "server",
        SERVER_BYTES,
    )

    index_lines = ['hash-format = "sha256"', ""]
    for relative_path in sorted(tracked_files):
        index_lines.extend(
            [
                "[[files]]",
                f"file = {json.dumps(relative_path)}",
                f'hash = "{hashlib.sha256(tracked_files[relative_path]).hexdigest()}"',
            ]
        )
        if relative_path.endswith(".pw.toml"):
            index_lines.append("metafile = true")
        index_lines.append("")
    index_bytes = "\n".join(index_lines).encode("utf-8")
    tracked_files["index.toml"] = index_bytes
    tracked_files["pack.toml"] = (
        'name = "AFTERLIGHT"\n'
        'author = "Fixture"\n'
        f'version = "{version}"\n'
        'pack-format = "packwiz:1.1.0"\n\n'
        '[index]\n'
        'file = "index.toml"\n'
        'hash-format = "sha256"\n'
        f'hash = "{hashlib.sha256(index_bytes).hexdigest()}"\n\n'
        '[versions]\n'
        f'minecraft = "{MINECRAFT_VERSION}"\n'
        f'neoforge = "{NEOFORGE_VERSION}"\n'
    ).encode("utf-8")
    lock_records = []
    for metadata_path, filename, jar_bytes in (
        (SIGNAL_METADATA_PATH, SIGNAL_FILENAME, SIGNAL_BYTES),
        ("mods/server-helper.pw.toml", SERVER_FILENAME, SERVER_BYTES),
    ):
        lock_records.append(
            {
                "downloads": ["https://example.invalid/fixture.jar"],
                "fileSize": len(jar_bytes),
                "hashes": {
                    "sha1": hashlib.sha1(jar_bytes).hexdigest(),
                    "sha512": hashlib.sha512(jar_bytes).hexdigest(),
                },
                "metadata_path": metadata_path,
                "path": f"mods/{filename}",
            }
        )
    tracked_files["tools/modrinth-manifest-lock.json"] = (
        json.dumps(
            {"files": lock_records, "format": 1},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return tracked_files


def write_packwiz_source(root: Path, version: str) -> str:
    tracked_files = _packwiz_files(version)
    root.mkdir(parents=True, exist_ok=True)
    for relative_path, data in tracked_files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    subprocess.run(
        ["git", "init", "--quiet", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "add", "--", *sorted(tracked_files)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=AFTERLIGHT Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "Create Packwiz fixture",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_prism_archive(
    path: Path,
    installer_bytes: bytes = INSTALLER_BYTES,
    *,
    bootstrap_bytes: bytes = BOOTSTRAP_BYTES,
    pack_url: str = PACK_URL,
) -> None:
    _write_zip(
        path,
        {
            ".minecraft/packwiz-installer-bootstrap.jar": bootstrap_bytes,
            ".minecraft/packwiz-installer.jar": installer_bytes,
            "instance.cfg": _instance_config(pack_url),
            "mmc-pack.json": _mmc_pack(),
        },
        normalized=True,
    )


def write_curseforge_archive(path: Path, version: str) -> None:
    manifest = {
        "minecraft": {
            "version": MINECRAFT_VERSION,
            "modLoaders": [
                {"id": f"neoforge-{NEOFORGE_VERSION}", "primary": True}
            ],
        },
        "manifestType": "minecraftModpack",
        "manifestVersion": 1,
        "name": "AFTERLIGHT",
        "version": version,
        "author": "Shane + ECHO",
        "projectID": 0,
        "files": [
            {
                "projectID": mod["project_id"],
                "fileID": mod["file_id"],
                "required": True,
            }
            for mod in CURSEFORGE_MODS
        ],
        "overrides": "overrides",
    }
    _write_zip(
        path,
        {
            "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode("utf-8"),
            f"overrides/{AUTHORED_PATH}": AUTHORED_BYTES,
            f"overrides/mods/{SIGNAL_FILENAME}": SIGNAL_BYTES,
        },
        normalized=False,
    )


def write_modrinth_archive(path: Path, version: str) -> None:
    manifest = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": version,
        "name": "AFTERLIGHT",
        "files": [
            {
                "path": f"mods/{SIGNAL_FILENAME}",
                "hashes": {
                    "sha1": hashlib.sha1(SIGNAL_BYTES).hexdigest(),
                    "sha512": hashlib.sha512(SIGNAL_BYTES).hexdigest(),
                },
                "env": {
                    "client": "required",
                    "server": "required",
                },
                "downloads": [
                    "https://example.invalid/fixture.jar"
                ],
                "fileSize": len(SIGNAL_BYTES),
            },
            {
                "path": f"mods/{SERVER_FILENAME}",
                "hashes": {
                    "sha1": hashlib.sha1(SERVER_BYTES).hexdigest(),
                    "sha512": hashlib.sha512(SERVER_BYTES).hexdigest(),
                },
                "env": {
                    "client": "unsupported",
                    "server": "required",
                },
                "downloads": ["https://example.invalid/fixture.jar"],
                "fileSize": len(SERVER_BYTES),
            },
        ],
        "dependencies": {
            "minecraft": MINECRAFT_VERSION,
            "neoforge": NEOFORGE_VERSION,
        },
    }
    _write_zip(
        path,
        {
            "modrinth.index.json": (
                json.dumps(manifest, indent=4) + "\n"
            ).encode("utf-8"),
            "overrides/config/afterlight-fixture.cfg": b"fixture=true\n",
            **{
                f'overrides/mods/{mod["filename"]}': mod["jar_bytes"]
                for mod in CURSEFORGE_MODS
            },
        },
        normalized=False,
    )


def rewrite_metadata(public: Path, version: str, git_sha: str) -> None:
    artifacts = (
        public / "AFTERLIGHT-curseforge.zip",
        public / "AFTERLIGHT-prism-instance.zip",
        public / "AFTERLIGHT.mrpack",
    )
    metadata = {
        "format": 3,
        "version": version,
        "git_sha": git_sha,
        "minecraft": MINECRAFT_VERSION,
        "neoforge": NEOFORGE_VERSION,
        "pack_url": PACK_URL,
        "packwiz": {
            "bootstrap": {
                "version": BOOTSTRAP_VERSION,
                "size": len(BOOTSTRAP_BYTES),
                "sha256": hashlib.sha256(BOOTSTRAP_BYTES).hexdigest(),
            },
            "installer": {
                "version": INSTALLER_VERSION,
                "size": len(INSTALLER_BYTES),
                "sha256": hashlib.sha256(INSTALLER_BYTES).hexdigest(),
            },
        },
        "public_artifacts": {
            artifact.name: {
                "sha256": _sha256(artifact),
                "size": artifact.stat().st_size,
            }
            for artifact in artifacts
        },
    }
    (public / "release-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def rewrite_checksums(public: Path) -> None:
    names = (
        "AFTERLIGHT-curseforge.zip",
        "AFTERLIGHT-prism-instance.zip",
        "AFTERLIGHT.mrpack",
        "release-metadata.json",
    )
    (public / "SHA256SUMS").write_text(
        "".join(f"{_sha256(public / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def write_public_release(
    public: Path,
    version: str,
    git_sha: str,
    installer_bytes: bytes = INSTALLER_BYTES,
) -> None:
    public.mkdir(parents=True, exist_ok=True)
    write_curseforge_archive(public / "AFTERLIGHT-curseforge.zip", version)
    write_prism_archive(public / "AFTERLIGHT-prism-instance.zip", installer_bytes)
    write_modrinth_archive(public / "AFTERLIGHT.mrpack", version)
    rewrite_metadata(public, version, git_sha)
    if installer_bytes != INSTALLER_BYTES:
        metadata_path = public / "release-metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["packwiz"]["installer"]["size"] = len(installer_bytes)
        metadata["packwiz"]["installer"]["sha256"] = hashlib.sha256(
            installer_bytes
        ).hexdigest()
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    rewrite_checksums(public)


def trusted_release_arguments() -> list[str]:
    return [
        "--pack-url",
        PACK_URL,
        "--bootstrap-version",
        BOOTSTRAP_VERSION,
        "--bootstrap-size",
        str(len(BOOTSTRAP_BYTES)),
        "--bootstrap-sha256",
        hashlib.sha256(BOOTSTRAP_BYTES).hexdigest(),
        "--installer-version",
        INSTALLER_VERSION,
        "--installer-size",
        str(len(INSTALLER_BYTES)),
        "--installer-sha256",
        hashlib.sha256(INSTALLER_BYTES).hexdigest(),
    ]


def write_release_policy(path: Path) -> None:
    path.write_text(
        f'RELEASE_PACK_URL="{PACK_URL}"\n'
        f'RELEASE_PACKWIZ_BOOTSTRAP_VERSION="{BOOTSTRAP_VERSION}"\n'
        f'RELEASE_PACKWIZ_BOOTSTRAP_SIZE="{len(BOOTSTRAP_BYTES)}"\n'
        "RELEASE_PACKWIZ_BOOTSTRAP_SHA256="
        f'"{hashlib.sha256(BOOTSTRAP_BYTES).hexdigest()}"\n'
        f'RELEASE_PACKWIZ_INSTALLER_VERSION="{INSTALLER_VERSION}"\n'
        f'RELEASE_PACKWIZ_INSTALLER_SIZE="{len(INSTALLER_BYTES)}"\n'
        "RELEASE_PACKWIZ_INSTALLER_SHA256="
        f'"{hashlib.sha256(INSTALLER_BYTES).hexdigest()}"\n',
        encoding="utf-8",
    )


def public_file_records(public: Path) -> dict[str, dict[str, int | str]]:
    return {
        name: {
            "sha256": _sha256(public / name),
            "size": (public / name).stat().st_size,
        }
        for name in PUBLIC_RELEASE_NAMES
    }


def write_gauntlet_receipt(accepted: Path, version: str, git_sha: str) -> str:
    public = accepted / "public"
    receipt = {
        "format": 1,
        "git_sha": git_sha,
        "pack_url": PACK_URL,
        "packwiz": {
            "bootstrap": {
                "version": BOOTSTRAP_VERSION,
                "size": len(BOOTSTRAP_BYTES),
                "sha256": hashlib.sha256(BOOTSTRAP_BYTES).hexdigest(),
            },
            "installer": {
                "version": INSTALLER_VERSION,
                "size": len(INSTALLER_BYTES),
                "sha256": hashlib.sha256(INSTALLER_BYTES).hexdigest(),
            },
        },
        "public_files": public_file_records(public),
        "version": version,
    }
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    (accepted / "gauntlet-receipt.json").write_bytes(receipt_bytes)
    return hashlib.sha256(receipt_bytes).hexdigest()


def expected_tag_message(accepted: Path, receipt_sha256: str) -> str:
    receipt = json.loads(
        (accepted / "gauntlet-receipt.json").read_text(encoding="utf-8")
    )
    lines = [
        f'AFTERLIGHT {receipt["version"]}',
        "",
        f"Gauntlet-Receipt-SHA256: {receipt_sha256}",
    ]
    for name in PUBLIC_RELEASE_NAMES:
        lines.append(
            "Public-File-SHA256: "
            f'{receipt["public_files"][name]["sha256"]}  {name}'
        )
    return "\n".join(lines) + "\n"


def write_empty_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w"):
        pass


if __name__ == "__main__":
    output = Path(sys.argv[1])
    fixture_version = sys.argv[2]
    fixture_sha = sys.argv[3]
    marker = sys.argv[4].encode("utf-8") if len(sys.argv) > 4 else INSTALLER_BYTES
    write_public_release(output, fixture_version, fixture_sha, marker)
