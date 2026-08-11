from __future__ import annotations

import hashlib
import json
import stat
import sys
import zipfile
from pathlib import Path


MINECRAFT_VERSION = "1.21.1"
NEOFORGE_VERSION = "21.1.248"
PACK_URL = "https://luskish.github.io/afterlight-pack/pack.toml"
BOOTSTRAP_BYTES = b"Packwiz bootstrap fixture\n"
INSTALLER_BYTES = b"Packwiz installer fixture\n"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FILE_MODE = stat.S_IFREG | 0o644


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _instance_config() -> bytes:
    return (
        "InstanceType=OneSix\n"
        "name=AFTERLIGHT\n"
        "iconKey=default\n"
        "OverrideCommands=true\n"
        'PreLaunchCommand="$INST_JAVA" -jar packwiz-installer-bootstrap.jar '
        "--bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g "
        f"{PACK_URL}\n"
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


def write_prism_archive(path: Path, installer_bytes: bytes = INSTALLER_BYTES) -> None:
    _write_zip(
        path,
        {
            ".minecraft/packwiz-installer-bootstrap.jar": BOOTSTRAP_BYTES,
            ".minecraft/packwiz-installer.jar": installer_bytes,
            "instance.cfg": _instance_config(),
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
        "files": [],
        "overrides": "overrides",
    }
    _write_zip(
        path,
        {
            "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode("utf-8"),
            "overrides/config/afterlight-fixture.cfg": b"fixture=true\n",
        },
        normalized=False,
    )


def write_modrinth_archive(path: Path, version: str) -> None:
    manifest = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": version,
        "name": "AFTERLIGHT",
        "files": [],
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
                "version": "0.0.3-test",
                "size": len(BOOTSTRAP_BYTES),
                "sha256": hashlib.sha256(BOOTSTRAP_BYTES).hexdigest(),
            },
            "installer": {
                "version": "0.5.14-test",
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


def write_empty_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w"):
        pass


if __name__ == "__main__":
    output = Path(sys.argv[1])
    fixture_version = sys.argv[2]
    fixture_sha = sys.argv[3]
    marker = sys.argv[4].encode("utf-8") if len(sys.argv) > 4 else INSTALLER_BYTES
    write_public_release(output, fixture_version, fixture_sha, marker)
