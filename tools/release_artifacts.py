#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import stat
import struct
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath


EXPECTED_PRISM_NAMES = (
    ".minecraft/packwiz-installer-bootstrap.jar",
    ".minecraft/packwiz-installer.jar",
    "instance.cfg",
    "mmc-pack.json",
)
PRISM_BOOTSTRAP_JAR = ".minecraft/packwiz-installer-bootstrap.jar"
PRISM_INSTALLER_JAR = ".minecraft/packwiz-installer.jar"
APPROVED_PRISM_JARS = (PRISM_BOOTSTRAP_JAR, PRISM_INSTALLER_JAR)
PRISM_MINECRAFT_VERSION = "1.21.1"
PRISM_NEOFORGE_VERSION = "21.1.248"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FILE_MODE = stat.S_IFREG | 0o644
DEFLATE_LEVEL = 9
UTF8_FLAG = 0x800
ENCRYPTED_FLAG = 0x1
PRISM_ARTIFACT_NAME = "AFTERLIGHT-prism-instance.zip"
CURSEFORGE_ARTIFACT_NAME = "AFTERLIGHT-curseforge.zip"
MRPACK_ARTIFACT_NAME = "AFTERLIGHT.mrpack"
PUBLIC_ARTIFACT_NAMES = tuple(
    sorted(
        (
            CURSEFORGE_ARTIFACT_NAME,
            PRISM_ARTIFACT_NAME,
            MRPACK_ARTIFACT_NAME,
        )
    )
)
RELEASE_METADATA_NAME = "release-metadata.json"
CHECKSUMS_NAME = "SHA256SUMS"
U2014_BYTES = b"\xe2\x80\x94"
STREAM_CHUNK_SIZE = 1024 * 1024
STREAM_OVERLAP_SIZE = 256
PRIVATE_KEY_HEADER = re.compile(
    rb"-----BEGIN (?:[A-Z0-9][A-Z0-9 ]* )?PRIVATE KEY(?: BLOCK)?-----"
)
SECRET_PATH_COMPONENTS = frozenset(
    {"secret", "token", "credential", "credentials", ".env", "rcon_password"}
)
SECRET_BASENAME_MARKER = re.compile(
    r"(?<![a-z0-9])(?:secret|token|credentials?|rcon_password)(?![a-z0-9])",
    re.IGNORECASE,
)
ENV_BASENAME_MARKER = re.compile(r"\.env(?:$|[^a-z0-9])", re.IGNORECASE)
RUNTIME_PATH_PREFIXES = (
    ("dist",),
    ("server-test",),
    ("server", "data"),
    ("server", "backups"),
)
LOCAL_FILE_HEADER = struct.Struct("<4s5H3L2H")
LOCAL_FILE_HEADER_SIGNATURE = b"PK\x03\x04"


def _instance_config(pack_url):
    return (
        "InstanceType=OneSix\n"
        "name=AFTERLIGHT\n"
        "iconKey=default\n"
        "OverrideCommands=true\n"
        'PreLaunchCommand="$INST_JAVA" -jar packwiz-installer-bootstrap.jar '
        "--bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g "
        f"{pack_url}\n"
    ).encode("utf-8")


def _mmc_pack(minecraft_version, neoforge_version):
    payload = {
        "components": [
            {
                "important": True,
                "uid": "net.minecraft",
                "version": minecraft_version,
            },
            {"uid": "net.neoforged", "version": neoforge_version},
        ],
        "formatVersion": 1,
    }
    return (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _validate_archive_name(name, allow_directory=False):
    if not name:
        raise ValueError("archive entry name is empty")
    if "\\" in name:
        raise ValueError(f"archive entry uses a backslash: {name!r}")
    is_directory = name.endswith("/")
    if is_directory and not allow_directory:
        raise ValueError(f"archive directory entry is not allowed: {name!r}")
    normalized_name = name[:-1] if is_directory else name
    if not normalized_name:
        raise ValueError("archive entry name is empty")
    if (
        normalized_name.startswith("/")
        or PurePosixPath(normalized_name).is_absolute()
        or re.match(r"^[A-Za-z]:", normalized_name)
    ):
        raise ValueError(f"archive entry uses an absolute path: {name!r}")
    parts = normalized_name.split("/")
    if ".." in parts:
        raise ValueError(f"archive entry uses parent traversal: {name!r}")
    if any(part in {"", "."} for part in parts):
        raise ValueError(f"archive entry is not canonical: {name!r}")
    if PurePosixPath(normalized_name).as_posix() != normalized_name:
        raise ValueError(f"archive entry is not canonical: {name!r}")
    return normalized_name


def _is_secret_bearing_path(name):
    normalized_name = name[:-1] if name.endswith("/") else name
    parts = normalized_name.split("/")
    if any(part.casefold() in SECRET_PATH_COMPONENTS for part in parts):
        return True
    basename = parts[-1]
    return bool(
        SECRET_BASENAME_MARKER.search(basename)
        or ENV_BASENAME_MARKER.search(basename)
    )


def _scan_binary_stream(stream, label, reject_u2014=False):
    overlap = b""
    while True:
        chunk = stream.read(STREAM_CHUNK_SIZE)
        if not chunk:
            break
        combined = overlap + chunk
        if reject_u2014 and U2014_BYTES in combined:
            raise ValueError(f"U+2014 found in {label}")
        if PRIVATE_KEY_HEADER.search(combined):
            raise ValueError(f"private-key header found in {label}")
        overlap = combined[-STREAM_OVERLAP_SIZE:]


def _local_file_header_flags(archive, info):
    if archive.fp is None:
        raise ValueError("archive file is closed")
    try:
        archive.fp.seek(info.header_offset)
        header = archive.fp.read(LOCAL_FILE_HEADER.size)
    except (OSError, ValueError) as error:
        raise ValueError(
            f"cannot read local file header: {info.filename!r}"
        ) from error
    if len(header) != LOCAL_FILE_HEADER.size:
        raise ValueError(f"truncated local file header: {info.filename!r}")
    fields = LOCAL_FILE_HEADER.unpack(header)
    if fields[0] != LOCAL_FILE_HEADER_SIGNATURE:
        raise ValueError(f"invalid local file header: {info.filename!r}")
    return fields[2]


def _inspect_zip_safety(archive, allow_directories):
    if archive.comment:
        raise ValueError("archive comment is not allowed")

    infos = archive.infolist()
    names = []
    seen_names = set()
    for info in infos:
        normalized_name = _validate_archive_name(
            info.filename,
            allow_directory=allow_directories,
        )
        collision_key = unicodedata.normalize("NFC", normalized_name).casefold()
        if collision_key in seen_names:
            raise ValueError(f"duplicate archive entry: {info.filename!r}")
        seen_names.add(collision_key)
        names.append(info.filename)

        if _is_secret_bearing_path(info.filename):
            raise ValueError(f"secret-bearing path in archive: {info.filename!r}")
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError(f"symlink archive entry: {info.filename!r}")
        local_flags = _local_file_header_flags(archive, info)
        if (local_flags ^ info.flag_bits) & ~ENCRYPTED_FLAG:
            raise ValueError(
                f"local and central ZIP flags differ: {info.filename!r}"
            )
        if local_flags & ENCRYPTED_FLAG:
            raise ValueError(f"encrypted archive entry: {info.filename!r}")
        if info.flag_bits & ENCRYPTED_FLAG:
            raise ValueError(f"encrypted archive entry: {info.filename!r}")

    for info in infos:
        if info.is_dir():
            continue
        try:
            with archive.open(info, "r") as member:
                _scan_binary_stream(member, f"archive entry {info.filename!r}")
        except (EOFError, NotImplementedError, RuntimeError) as error:
            raise ValueError(
                f"cannot safely read archive entry {info.filename!r}: {error}"
            ) from error

    return infos, names


def _normalized_zip_info(name):
    _validate_archive_name(name)
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
    return info


def _write_prism_archive(archive_path, entries):
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=DEFLATE_LEVEL,
        strict_timestamps=True,
    ) as archive:
        for name in sorted(entries):
            archive.writestr(
                _normalized_zip_info(name),
                entries[name],
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=DEFLATE_LEVEL,
            )


def build_prism_archive(
    bootstrap_path,
    installer_path,
    output_path,
    pack_url,
    minecraft_version,
    neoforge_version,
):
    bootstrap_path = Path(bootstrap_path)
    installer_path = Path(installer_path)
    output_path = Path(output_path)
    if not bootstrap_path.is_file():
        raise ValueError(f"bootstrap JAR is not a regular file: {bootstrap_path}")
    if not installer_path.is_file():
        raise ValueError(f"installer JAR is not a regular file: {installer_path}")

    entries = {
        PRISM_BOOTSTRAP_JAR: bootstrap_path.read_bytes(),
        PRISM_INSTALLER_JAR: installer_path.read_bytes(),
        "instance.cfg": _instance_config(pack_url),
        "mmc-pack.json": _mmc_pack(minecraft_version, neoforge_version),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    with tempfile.NamedTemporaryFile(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        _write_prism_archive(temporary_path, entries)
        inspect_prism_archive(
            temporary_path,
            pack_url,
            hashlib.sha256(entries[PRISM_BOOTSTRAP_JAR]).hexdigest(),
            hashlib.sha256(entries[PRISM_INSTALLER_JAR]).hexdigest(),
            len(entries[PRISM_INSTALLER_JAR]),
        )
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return output_path


def _validate_zip_metadata(info):
    if info.date_time != FIXED_TIMESTAMP:
        raise ValueError(f"archive entry timestamp is not normalized: {info.filename!r}")
    if info.create_system != 3:
        raise ValueError(f"archive entry is not Unix metadata: {info.filename!r}")
    if info.external_attr != FILE_MODE << 16:
        raise ValueError(
            f"archive entry external attributes are not normalized: {info.filename!r}"
        )
    if info.compress_type != zipfile.ZIP_DEFLATED:
        raise ValueError(f"archive entry is not deflated: {info.filename!r}")
    if info.flag_bits & UTF8_FLAG:
        raise ValueError(f"ASCII archive entry has the UTF-8 flag set: {info.filename!r}")
    if info.flag_bits != 0:
        raise ValueError(f"archive entry has unsupported flags: {info.filename!r}")
    if info.extra or info.comment:
        raise ValueError(f"archive entry has non-normalized metadata: {info.filename!r}")


def _validate_sha256(value, label):
    if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError(
            f"{label} SHA-256 must be exactly 64 hexadecimal characters"
        )
    return value.lower()


def _validate_positive_size(value, label):
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} size must be a positive integer")
    return value


def inspect_prism_archive(
    archive_path,
    pack_url,
    bootstrap_sha256,
    installer_sha256,
    installer_size,
):
    archive_path = Path(archive_path)
    expected_bootstrap_sha256 = _validate_sha256(bootstrap_sha256, "bootstrap")
    expected_installer_sha256 = _validate_sha256(installer_sha256, "installer")
    expected_installer_size = _validate_positive_size(installer_size, "installer")

    with zipfile.ZipFile(archive_path) as archive:
        infos, names = _inspect_zip_safety(archive, allow_directories=False)

        jar_entries = [name for name in names if name.lower().endswith(".jar")]
        disallowed_jars = [
            name for name in jar_entries if name not in APPROVED_PRISM_JARS
        ]
        if disallowed_jars:
            raise ValueError(f"disallowed JAR in Prism archive: {disallowed_jars[0]!r}")
        if tuple(jar_entries) != APPROVED_PRISM_JARS:
            raise ValueError("Prism archive must contain exactly two approved JARs")
        if tuple(names) != EXPECTED_PRISM_NAMES:
            raise ValueError(
                "Prism archive entries must be exactly sorted as "
                f"{EXPECTED_PRISM_NAMES!r}"
            )

        for info in infos:
            _validate_zip_metadata(info)

        bootstrap_bytes = archive.read(PRISM_BOOTSTRAP_JAR)
        actual_bootstrap_sha256 = hashlib.sha256(bootstrap_bytes).hexdigest()
        if actual_bootstrap_sha256 != expected_bootstrap_sha256:
            raise ValueError(
                "bootstrap SHA-256 mismatch: "
                f"expected {expected_bootstrap_sha256}, got {actual_bootstrap_sha256}"
            )

        installer_bytes = archive.read(PRISM_INSTALLER_JAR)
        actual_installer_size = len(installer_bytes)
        if actual_installer_size != expected_installer_size:
            raise ValueError(
                "installer size mismatch: "
                f"expected {expected_installer_size}, got {actual_installer_size}"
            )
        actual_installer_sha256 = hashlib.sha256(installer_bytes).hexdigest()
        if actual_installer_sha256 != expected_installer_sha256:
            raise ValueError(
                "installer SHA-256 mismatch: "
                f"expected {expected_installer_sha256}, got {actual_installer_sha256}"
            )

        expected_instance_config = _instance_config(pack_url)
        if archive.read("instance.cfg") != expected_instance_config:
            raise ValueError("instance.cfg does not use the exact Packwiz launch command")

        expected_mmc_pack = _mmc_pack(
            PRISM_MINECRAFT_VERSION,
            PRISM_NEOFORGE_VERSION,
        )
        if archive.read("mmc-pack.json") != expected_mmc_pack:
            raise ValueError("mmc-pack.json does not use the exact loader versions")

    return {
        "archive": str(archive_path),
        "bootstrap_sha256": actual_bootstrap_sha256,
        "installer_sha256": actual_installer_sha256,
        "installer_size": actual_installer_size,
        "entries": names,
        "entry_count": len(names),
        "jar_entries": jar_entries,
        "pack_url": pack_url,
    }


def inspect_public_launcher_archive(archive_path):
    archive_path = Path(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        _, names = _inspect_zip_safety(archive, allow_directories=True)

    embedded_jar_count = sum(name.casefold().endswith(".jar") for name in names)
    return {
        "archive": str(archive_path),
        "classification": "public",
        "embedded_jar_count": embedded_jar_count,
        "entry_count": len(names),
    }


def _tracked_paths(root_path):
    result = subprocess.run(
        ["git", "-C", str(root_path), "ls-files", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git ls-files failed: {error or 'unknown error'}")
    if result.stdout and not result.stdout.endswith(b"\0"):
        raise ValueError("git ls-files returned a malformed NUL-delimited inventory")

    raw_paths = result.stdout.split(b"\0")[:-1] if result.stdout else []
    if len(raw_paths) != len(set(raw_paths)):
        raise ValueError("git ls-files returned duplicate tracked paths")

    tracked_paths = []
    for raw_path in raw_paths:
        if U2014_BYTES in raw_path:
            raise ValueError(f"U+2014 found in tracked path: {raw_path!r}")
        try:
            relative_path = raw_path.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise ValueError(f"tracked path is not valid UTF-8: {raw_path!r}") from error
        try:
            _validate_archive_name(relative_path)
        except ValueError as error:
            raise ValueError(f"invalid tracked path {relative_path!r}: {error}") from error
        tracked_paths.append((raw_path, relative_path))
    return tracked_paths


def _tracked_index_entries(root_path, tracked_paths):
    result = subprocess.run(
        ["git", "-C", str(root_path), "ls-files", "--stage", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git ls-files --stage failed: {error or 'unknown error'}")
    if result.stdout and not result.stdout.endswith(b"\0"):
        raise ValueError("git ls-files --stage returned a malformed inventory")

    records = result.stdout.split(b"\0")[:-1] if result.stdout else []
    index_entries = []
    for record in records:
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_id, stage = metadata.split(b" ")
        except ValueError as error:
            raise ValueError("git ls-files --stage returned a malformed entry") from error
        if mode not in {b"100644", b"100755", b"120000"}:
            raise ValueError(f"tracked index entry is not blob-backed: {raw_path!r}")
        if not re.fullmatch(rb"(?:[0-9a-f]{40}|[0-9a-f]{64})", object_id):
            raise ValueError(f"tracked index object ID is malformed: {raw_path!r}")
        if stage != b"0":
            raise ValueError(f"tracked index entry is unmerged: {raw_path!r}")
        index_entries.append((raw_path, object_id.decode("ascii")))

    expected_raw_paths = [raw_path for raw_path, _ in tracked_paths]
    actual_raw_paths = [raw_path for raw_path, _ in index_entries]
    if actual_raw_paths != expected_raw_paths:
        raise ValueError("tracked index inventory changed during scan")

    return [
        (relative_path, object_id)
        for (_, relative_path), (_, object_id) in zip(tracked_paths, index_entries)
    ]


def _is_runtime_path(parts):
    return any(parts[: len(prefix)] == prefix for prefix in RUNTIME_PATH_PREFIXES)


def _scan_tracked_blob(root_path, relative_path, object_id):
    parts = tuple(relative_path.split("/"))
    if _is_runtime_path(parts):
        raise ValueError(f"tracked runtime path: {relative_path!r}")
    if relative_path.casefold().endswith(".jar"):
        raise ValueError(f"tracked JAR is forbidden: {relative_path!r}")

    process = subprocess.Popen(
        [
            "git",
            "-C",
            str(root_path),
            "cat-file",
            "blob",
            object_id,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        raise ValueError(f"cannot read tracked index blob: {relative_path!r}")

    try:
        _scan_binary_stream(
            process.stdout,
            f"tracked index blob {relative_path!r}",
            reject_u2014=True,
        )
        error = process.stderr.read().decode("utf-8", errors="replace").strip()
        returncode = process.wait()
    except BaseException:
        process.kill()
        process.wait()
        raise
    finally:
        process.stdout.close()
        process.stderr.close()

    if returncode != 0:
        raise ValueError(
            f"git cat-file failed for tracked path {relative_path!r}: "
            f"{error or 'unknown error'}"
        )


def scan_repository(root):
    root_path = Path(root)
    try:
        root_status = root_path.lstat()
    except OSError as error:
        raise ValueError(f"repository root is unreadable: {root_path}") from error
    if not stat.S_ISDIR(root_status.st_mode):
        raise ValueError(f"repository root is not a directory: {root_path}")
    root_path = root_path.resolve(strict=True)

    tracked_paths = _tracked_paths(root_path)
    index_entries = _tracked_index_entries(root_path, tracked_paths)
    for relative_path, object_id in index_entries:
        _scan_tracked_blob(root_path, relative_path, object_id)
    return {
        "root": str(root_path),
        "tracked_file_count": len(index_entries),
    }


def _require_regular_file(path, label, positive_size=True):
    path = Path(path)
    try:
        file_status = path.lstat()
    except FileNotFoundError as error:
        raise ValueError(f"{label} is missing: {path}") from error
    except OSError as error:
        raise ValueError(f"{label} is unreadable: {path}") from error
    if not stat.S_ISREG(file_status.st_mode):
        raise ValueError(f"{label} is not a regular file: {path}")
    if positive_size and file_status.st_size <= 0:
        raise ValueError(f"{label} must have a positive size: {path}")
    return file_status


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as artifact:
        while chunk := artifact.read(STREAM_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
        temporary_file.write(data)
        temporary_file.flush()
        os.fsync(temporary_file.fileno())

    try:
        temporary_path.chmod(0o644)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_release_metadata(
    dist_dir,
    version,
    git_sha,
    minecraft,
    neoforge,
    pack_url,
    bootstrap_version,
    bootstrap_size,
    bootstrap_sha256,
    installer_version,
    installer_size,
    installer_sha256,
):
    if not re.fullmatch(r"[0-9a-f]{40}", git_sha):
        raise ValueError("GIT_SHA must be exactly 40 lowercase hexadecimal characters")

    dist_path = Path(dist_dir)
    artifact_records = {}
    for artifact_name in PUBLIC_ARTIFACT_NAMES:
        artifact_path = dist_path / artifact_name
        artifact_status = _require_regular_file(
            artifact_path,
            f"public artifact {artifact_name}",
        )
        artifact_records[artifact_name] = {
            "sha256": _sha256_file(artifact_path),
            "size": artifact_status.st_size,
        }

    installer_records = {}
    for label, installer_version_value, size, sha256 in (
        ("bootstrap", bootstrap_version, bootstrap_size, bootstrap_sha256),
        ("installer", installer_version, installer_size, installer_sha256),
    ):
        if not isinstance(installer_version_value, str) or not installer_version_value:
            raise ValueError(f"Packwiz {label} version is missing")
        installer_records[label] = {
            "version": installer_version_value,
            "size": _validate_positive_size(size, f"Packwiz {label}"),
            "sha256": _validate_sha256(sha256, f"Packwiz {label}"),
        }

    metadata = {
        "format": 3,
        "version": version,
        "git_sha": git_sha,
        "minecraft": minecraft,
        "neoforge": neoforge,
        "pack_url": pack_url,
        "packwiz": installer_records,
        "public_artifacts": artifact_records,
    }
    metadata_path = dist_path / RELEASE_METADATA_NAME
    _atomic_write_bytes(
        metadata_path,
        (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return metadata_path


def _classified_release_names(dist_path):
    metadata_path = dist_path / RELEASE_METADATA_NAME
    _require_regular_file(metadata_path, "release metadata")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("release metadata is not valid UTF-8 JSON") from error

    version = metadata.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("release metadata version is missing")
    public_artifacts = metadata.get("public_artifacts")
    if not isinstance(public_artifacts, dict) or set(public_artifacts) != set(
        PUBLIC_ARTIFACT_NAMES
    ):
        raise ValueError("release metadata public artifact classification is invalid")
    if "private_artifacts" in metadata:
        raise ValueError("release metadata public artifact classification is invalid")

    if metadata.get("format") != 3:
        raise ValueError("release metadata format must be 3")
    packwiz = metadata.get("packwiz")
    if not isinstance(packwiz, dict) or set(packwiz) != {"bootstrap", "installer"}:
        raise ValueError("release metadata Packwiz classification is invalid")
    for label in ("bootstrap", "installer"):
        record = packwiz[label]
        if not isinstance(record, dict) or set(record) != {
            "version",
            "size",
            "sha256",
        }:
            raise ValueError(f"release metadata Packwiz {label} record is invalid")
        if not isinstance(record["version"], str) or not record["version"]:
            raise ValueError(f"release metadata Packwiz {label} version is invalid")
        _validate_positive_size(record["size"], f"release metadata Packwiz {label}")
        _validate_sha256(record["sha256"], f"release metadata Packwiz {label}")

    artifact_labels = {
        CURSEFORGE_ARTIFACT_NAME: "CurseForge",
        PRISM_ARTIFACT_NAME: "Prism",
        MRPACK_ARTIFACT_NAME: "mrpack",
    }
    for artifact_name in PUBLIC_ARTIFACT_NAMES:
        artifact_label = artifact_labels[artifact_name]
        artifact_record = public_artifacts[artifact_name]
        if not isinstance(artifact_record, dict) or set(artifact_record) != {
            "sha256",
            "size",
        }:
            raise ValueError(f"release metadata {artifact_label} record is invalid")
        recorded_sha256 = artifact_record["sha256"]
        if not isinstance(recorded_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}",
            recorded_sha256,
        ):
            raise ValueError(
                f"release metadata {artifact_label} SHA-256 is invalid"
            )
        recorded_size = artifact_record["size"]
        if type(recorded_size) is not int or recorded_size <= 0:
            raise ValueError(
                f"release metadata {artifact_label} size must be a positive integer"
            )

        artifact_path = dist_path / artifact_name
        artifact_status = _require_regular_file(
            artifact_path,
            f"public artifact {artifact_name}",
        )
        if artifact_status.st_size != recorded_size:
            raise ValueError(
                f"release metadata {artifact_label} size mismatch: "
                f"expected {recorded_size}, got {artifact_status.st_size}"
            )
        actual_sha256 = _sha256_file(artifact_path)
        if actual_sha256 != recorded_sha256:
            raise ValueError(
                f"release metadata {artifact_label} SHA-256 mismatch: "
                f"expected {recorded_sha256}, got {actual_sha256}"
            )

    return {
        *PUBLIC_ARTIFACT_NAMES,
        RELEASE_METADATA_NAME,
    }


def _validate_release_inventory(dist_path):
    try:
        dist_status = dist_path.lstat()
    except OSError as error:
        raise ValueError(f"release output directory is unreadable: {dist_path}") from error
    if not stat.S_ISDIR(dist_status.st_mode):
        raise ValueError(f"release output path is not a directory: {dist_path}")

    classified_names = _classified_release_names(dist_path)
    actual_names = {entry.name for entry in os.scandir(dist_path)}
    unclassified_names = sorted(actual_names - classified_names - {CHECKSUMS_NAME})
    if unclassified_names:
        raise ValueError(f"unclassified release output: {unclassified_names[0]!r}")
    missing_names = sorted(classified_names - actual_names)
    if missing_names:
        raise ValueError(f"classified release output is missing: {missing_names[0]!r}")
    if CHECKSUMS_NAME in actual_names:
        _require_regular_file(
            dist_path / CHECKSUMS_NAME,
            "release checksums",
            positive_size=False,
        )


def write_release_checksums(dist_dir):
    dist_path = Path(dist_dir)
    _validate_release_inventory(dist_path)
    artifact_names = sorted((*PUBLIC_ARTIFACT_NAMES, RELEASE_METADATA_NAME))
    lines = []
    for artifact_name in artifact_names:
        artifact_path = dist_path / artifact_name
        _require_regular_file(artifact_path, f"public artifact {artifact_name}")
        lines.append(f"{_sha256_file(artifact_path)}  {artifact_name}\n")

    checksums_path = dist_path / CHECKSUMS_NAME
    _atomic_write_bytes(checksums_path, "".join(lines).encode("utf-8"))
    return checksums_path


def _parser():
    parser = argparse.ArgumentParser(description="Build and inspect AFTERLIGHT artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build-prism")
    build_parser.add_argument("--bootstrap", required=True)
    build_parser.add_argument("--installer", required=True)
    build_parser.add_argument("--output", required=True)
    build_parser.add_argument("--pack-url", required=True)
    build_parser.add_argument("--minecraft-version", required=True)
    build_parser.add_argument("--neoforge-version", required=True)

    inspect_parser = subparsers.add_parser("inspect-prism")
    inspect_parser.add_argument("--archive", required=True)
    inspect_parser.add_argument("--pack-url", required=True)
    inspect_parser.add_argument("--bootstrap-sha256", required=True)
    inspect_parser.add_argument("--installer-sha256", required=True)
    inspect_parser.add_argument("--installer-size", required=True, type=int)

    public_launcher_parser = subparsers.add_parser("inspect-public-launcher")
    public_launcher_parser.add_argument("--archive", required=True)

    repository_parser = subparsers.add_parser("scan-repository")
    repository_parser.add_argument("--root", default=".")

    metadata_parser = subparsers.add_parser("write-metadata")
    metadata_parser.add_argument("--dist-dir", required=True)
    metadata_parser.add_argument("--version", required=True)
    metadata_parser.add_argument("--git-sha", required=True)
    metadata_parser.add_argument("--minecraft", required=True)
    metadata_parser.add_argument("--neoforge", required=True)
    metadata_parser.add_argument("--pack-url", required=True)
    metadata_parser.add_argument("--bootstrap-version", required=True)
    metadata_parser.add_argument("--bootstrap-size", required=True, type=int)
    metadata_parser.add_argument("--bootstrap-sha256", required=True)
    metadata_parser.add_argument("--installer-version", required=True)
    metadata_parser.add_argument("--installer-size", required=True, type=int)
    metadata_parser.add_argument("--installer-sha256", required=True)

    checksums_parser = subparsers.add_parser("write-checksums")
    checksums_parser.add_argument("--dist-dir", required=True)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.command == "build-prism":
        archive_path = build_prism_archive(
            args.bootstrap,
            args.installer,
            args.output,
            args.pack_url,
            args.minecraft_version,
            args.neoforge_version,
        )
        print(json.dumps({"archive": str(archive_path)}, sort_keys=True))
        return 0

    if args.command == "inspect-prism":
        summary = inspect_prism_archive(
            args.archive,
            args.pack_url,
            args.bootstrap_sha256,
            args.installer_sha256,
            args.installer_size,
        )
        print(json.dumps(summary, sort_keys=True))
        return 0

    if args.command == "inspect-public-launcher":
        summary = inspect_public_launcher_archive(args.archive)
        print(json.dumps(summary, sort_keys=True))
        return 0

    if args.command == "scan-repository":
        summary = scan_repository(args.root)
        print(json.dumps(summary, sort_keys=True))
        return 0

    if args.command == "write-metadata":
        output_path = write_release_metadata(
            args.dist_dir,
            args.version,
            args.git_sha,
            args.minecraft,
            args.neoforge,
            args.pack_url,
            args.bootstrap_version,
            args.bootstrap_size,
            args.bootstrap_sha256,
            args.installer_version,
            args.installer_size,
            args.installer_sha256,
        )
        print(json.dumps({"output": str(output_path)}, sort_keys=True))
        return 0

    output_path = write_release_checksums(args.dist_dir)
    print(json.dumps({"output": str(output_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
