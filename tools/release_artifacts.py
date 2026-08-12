#!/usr/bin/env python3

import argparse
import codecs
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
from urllib.parse import urlsplit


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
GAUNTLET_RECEIPT_FORMAT = 1
MAX_RECEIPT_SIZE = 64 * 1024
PUBLIC_RELEASE_NAMES = tuple(
    sorted((*PUBLIC_ARTIFACT_NAMES, RELEASE_METADATA_NAME, CHECKSUMS_NAME))
)
CHECKSUM_TARGET_NAMES = tuple(
    sorted((*PUBLIC_ARTIFACT_NAMES, RELEASE_METADATA_NAME))
)
RELEASE_METADATA_KEYS = frozenset(
    {
        "format",
        "version",
        "git_sha",
        "minecraft",
        "neoforge",
        "pack_url",
        "packwiz",
        "public_artifacts",
    }
)
U2014_BYTES = b"\xe2\x80\x94"
STREAM_CHUNK_SIZE = 1024 * 1024
STREAM_OVERLAP_SIZE = 256
MAX_ARCHIVE_ENTRIES = 4096
MAX_ARCHIVE_MEMBER_SIZE = 256 * 1024 * 1024
MAX_ARCHIVE_TOTAL_UNCOMPRESSED_SIZE = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_COMPRESSION_RATIO = 200
MAX_MANIFEST_SIZE = 1024 * 1024
MAX_TEXT_LINE_SIZE = 1024 * 1024
MAX_UNSIGNED_32 = 4294967295
PRIVATE_KEY_HEADER = re.compile(
    rb"-----BEGIN (?:[A-Z0-9][A-Z0-9 ]* )?PRIVATE KEY(?: BLOCK)?-----"
)
CREDENTIAL_KEY = re.compile(
    r"(?:(?:[A-Za-z0-9]+[._-])+)?"
    r"(?:api[._-]?key|rcon[._-]?password|"
    r"(?:access|auth|private|refresh)[._-]?token|"
    r"(?:client|consumer|signing|webhook)[._-]?secret|"
    r"(?:database|db)[._-]?password|token|password|secret)",
    re.IGNORECASE,
)
CREDENTIAL_DECLARATIONS = frozenset({"const", "export", "let", "var"})
CREDENTIAL_BOUNDARIES = frozenset("\r\n,{")
CREDENTIAL_HORIZONTAL_WHITESPACE = frozenset("\t ")
CREDENTIAL_ASSIGNMENT_WHITESPACE = frozenset("\t \r\n")
TEMPLATE_CREDENTIAL_VALUES = frozenset(
    {
        "0",
        "change-me",
        "change_me",
        "changeme",
        "example",
        "false",
        "none",
        "null",
        "placeholder",
        "replace-me",
        "replace_me",
        "sample",
        "template",
        "true",
        "unset",
    }
)
TEMPLATE_CREDENTIAL_PATTERN = re.compile(
    r"(?:<[A-Za-z_][A-Za-z0-9_.-]*>|\{\{[^{}]+\}\}|"
    r"__[A-Za-z_][A-Za-z0-9_]*__|"
    r"your[._-][A-Za-z0-9_.-]+[._-]here|"
    r"(?:example|sample)[._-][A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
SIMPLE_ENVIRONMENT_REFERENCE = re.compile(
    r"(?:\$env:[A-Za-z_][A-Za-z0-9_]*|%[A-Za-z_][A-Za-z0-9_]*%|"
    r"\$[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
BRACED_ENVIRONMENT_REFERENCE = re.compile(
    r"\$\{[A-Za-z_][A-Za-z0-9_]*"
    r"(?:(?P<operator>:\?|\?|:-|-|:=|=|:\+|\+)(?P<operand>.*))?\}",
    re.DOTALL,
)
WINDOWS_FORBIDDEN_CHARACTERS = frozenset('<>:"|?*')
WINDOWS_RESERVED_BASENAMES = frozenset(
    {
        "aux",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
        "com¹",
        "com²",
        "com³",
        "lpt¹",
        "lpt²",
        "lpt³",
    }
)
CURSEFORGE_MANIFEST_NAME = "manifest.json"
MODRINTH_MANIFEST_NAME = "modrinth.index.json"
JSON_MANIFEST_NAMES = frozenset(
    {CURSEFORGE_MANIFEST_NAME, MODRINTH_MANIFEST_NAME, "mmc-pack.json"}
)
EXPECTED_PACK_NAME = "AFTERLIGHT"
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


def _validate_archive_name(name, allow_directory=False, windows_safe=True):
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
    if windows_safe:
        for part in parts:
            if part.endswith((".", " ")):
                raise ValueError(f"Windows-unsafe archive entry: {name!r}")
            if any(
                ord(character) < 32
                or ord(character) == 127
                or character in WINDOWS_FORBIDDEN_CHARACTERS
                for character in part
            ):
                raise ValueError(f"Windows-unsafe archive entry: {name!r}")
            windows_basename = (
                unicodedata.normalize("NFC", part)
                .rstrip(" .")
                .split(".", 1)[0]
                .rstrip(" ")
                .casefold()
            )
            if windows_basename in WINDOWS_RESERVED_BASENAMES:
                raise ValueError(f"Windows-unsafe archive entry: {name!r}")
    return normalized_name


def _windows_collision_key(name):
    normalized_name = name[:-1] if name.endswith("/") else name
    return "/".join(
        unicodedata.normalize("NFC", part).rstrip(" .").casefold()
        for part in normalized_name.split("/")
    )


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


def _scan_binary_stream(stream, label, reject_u2014=False, max_bytes=None):
    overlap = b""
    total_bytes = 0
    while True:
        read_size = STREAM_CHUNK_SIZE
        if max_bytes is not None:
            read_size = min(read_size, max_bytes - total_bytes + 1)
        chunk = stream.read(read_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if max_bytes is not None and total_bytes > max_bytes:
            raise ValueError(f"stream exceeds the byte limit for {label}")
        combined = overlap + chunk
        if reject_u2014 and U2014_BYTES in combined:
            raise ValueError(f"U+2014 found in {label}")
        if PRIVATE_KEY_HEADER.search(combined):
            raise ValueError(f"private-key header found in {label}")
        overlap = combined[-STREAM_OVERLAP_SIZE:]
    return total_bytes


def _is_template_credential_value(raw_value):
    value = raw_value.strip()
    if len(value) >= 2 and value[:1] == value[-1:] and value[:1] in {'"', "'"}:
        value = value[1:-1].strip()
    if not value:
        return True
    if value.casefold() in TEMPLATE_CREDENTIAL_VALUES:
        return True
    if TEMPLATE_CREDENTIAL_PATTERN.fullmatch(value):
        return True
    if SIMPLE_ENVIRONMENT_REFERENCE.fullmatch(value):
        return True
    environment_reference = BRACED_ENVIRONMENT_REFERENCE.fullmatch(value)
    if environment_reference is None:
        return False
    operator = environment_reference.group("operator")
    if operator is None or operator in {"?", ":?"}:
        return True
    return _is_template_credential_value(environment_reference.group("operand"))


def _is_credential_key_character(character):
    return character.isascii() and (
        character.isalnum() or character in "._-"
    )


def _is_credential_value_delimiter(character):
    return character.isspace() or character in ",#;}"


class _CredentialAssignmentScanner:
    SEEK = "seek"
    LEADING = "leading"
    TOKEN = "token"
    AFTER_DECLARATION = "after_declaration"
    AFTER_KEY = "after_key"
    AFTER_SEPARATOR = "after_separator"
    DOLLAR_VALUE = "dollar_value"
    BRACED_VALUE = "braced_value"
    QUOTED_VALUE = "quoted_value"
    COMPLETE_VALUE = "complete_value"
    UNQUOTED_VALUE = "unquoted_value"

    def __init__(self):
        self.live_credential_found = False
        self.state = self.LEADING
        self.token_characters = []
        self.token_quoted = False
        self.value_characters = []
        self.value_quote = None
        self.value_escaped = False

    def feed(self, data):
        if self.live_credential_found:
            return
        for character in data:
            self._consume(character)
            if self.live_credential_found:
                return

    def finish(self):
        if self.state in {
            self.DOLLAR_VALUE,
            self.BRACED_VALUE,
            self.QUOTED_VALUE,
            self.COMPLETE_VALUE,
            self.UNQUOTED_VALUE,
        }:
            self._resolve_value()
        return self.live_credential_found

    def _consume(self, character):
        if self.state == self.SEEK:
            if character in CREDENTIAL_BOUNDARIES:
                self.state = self.LEADING
            return

        if self.state == self.LEADING:
            if character in CREDENTIAL_HORIZONTAL_WHITESPACE:
                return
            if character in CREDENTIAL_BOUNDARIES:
                return
            if character in {'"', "'"}:
                self._start_token(quoted=True)
                return
            if _is_credential_key_character(character):
                self._start_token(quoted=False)
                self._append_token(character)
                return
            self._reset_for_character(character)
            return

        if self.state == self.TOKEN:
            self._consume_token(character)
            return

        if self.state == self.AFTER_DECLARATION:
            if character in CREDENTIAL_HORIZONTAL_WHITESPACE:
                return
            if character in {'"', "'"}:
                self._start_token(quoted=True)
                return
            if _is_credential_key_character(character):
                self._start_token(quoted=False)
                self._append_token(character)
                return
            self._reset_for_character(character)
            return

        if self.state == self.AFTER_KEY:
            if character in CREDENTIAL_ASSIGNMENT_WHITESPACE:
                return
            if character in ":=":
                self.state = self.AFTER_SEPARATOR
                return
            self._reset_for_character(character)
            return

        if self.state == self.AFTER_SEPARATOR:
            if character in CREDENTIAL_ASSIGNMENT_WHITESPACE:
                return
            if _is_credential_value_delimiter(character):
                self._reset_for_character(character)
                return
            if character in {'"', "'"}:
                self._start_value(self.QUOTED_VALUE, character)
                self.value_quote = character
                return
            if character == "$":
                self._start_value(self.DOLLAR_VALUE, character)
                return
            self._start_value(self.UNQUOTED_VALUE, character)
            return

        if self.state == self.DOLLAR_VALUE:
            if character == "{":
                self._append_value(character)
                self.state = self.BRACED_VALUE
                return
            if _is_credential_value_delimiter(character):
                self._resolve_value()
                self._reset_for_character(character)
                return
            self._append_value(character)
            self.state = self.UNQUOTED_VALUE
            return

        if self.state == self.BRACED_VALUE:
            if character == "}":
                self._append_value(character)
                self.state = self.COMPLETE_VALUE
                return
            if character in "{\r\n":
                self._resolve_value()
                self._reset_for_character(character)
                return
            self._append_value(character)
            return

        if self.state == self.QUOTED_VALUE:
            if self.value_escaped:
                if character in "\r\n":
                    self._resolve_value()
                    self._reset_for_character(character)
                    return
                self._append_value(character)
                self.value_escaped = False
                return
            if character == "\\":
                self._append_value(character)
                self.value_escaped = True
                return
            if character == self.value_quote:
                self._append_value(character)
                self.state = self.COMPLETE_VALUE
                return
            if character in "\r\n":
                self._resolve_value()
                self._reset_for_character(character)
                return
            self._append_value(character)
            return

        if self.state == self.COMPLETE_VALUE:
            if _is_credential_value_delimiter(character):
                self._resolve_value()
                self._reset_for_character(character)
                return
            self._append_value(character)
            self.state = self.UNQUOTED_VALUE
            return

        if self.state == self.UNQUOTED_VALUE:
            if _is_credential_value_delimiter(character):
                self._resolve_value()
                self._reset_for_character(character)
                return
            self._append_value(character)

    def _consume_token(self, character):
        if _is_credential_key_character(character):
            self._append_token(character)
            return

        token = "".join(self.token_characters)
        token_is_key = CREDENTIAL_KEY.fullmatch(token) is not None
        token_is_declaration = (
            not self.token_quoted
            and token.casefold() in CREDENTIAL_DECLARATIONS
        )
        self.token_characters = []

        if character in {'"', "'"}:
            if token_is_key:
                self.state = self.AFTER_KEY
            else:
                self._reset_for_character(character)
            return
        if character in CREDENTIAL_HORIZONTAL_WHITESPACE:
            if token_is_declaration:
                self.state = self.AFTER_DECLARATION
            elif token_is_key:
                self.state = self.AFTER_KEY
            else:
                self._reset_for_character(character)
            return
        if character in "\r\n":
            if token_is_key:
                self.state = self.AFTER_KEY
            else:
                self._reset_for_character(character)
            return
        if character in ":=" and token_is_key:
            self.state = self.AFTER_SEPARATOR
            return
        self._reset_for_character(character)

    def _start_token(self, quoted):
        self.state = self.TOKEN
        self.token_characters = []
        self.token_quoted = quoted

    def _append_token(self, character):
        if len(self.token_characters) >= MAX_TEXT_LINE_SIZE:
            self.token_characters = []
            self.state = self.SEEK
            return
        self.token_characters.append(character)

    def _start_value(self, state, character):
        self.state = state
        self.value_characters = [character]
        self.value_quote = None
        self.value_escaped = False

    def _append_value(self, character):
        if len(self.value_characters) >= MAX_TEXT_LINE_SIZE:
            self.value_characters = []
            self.state = self.SEEK
            return
        self.value_characters.append(character)

    def _resolve_value(self):
        raw_value = "".join(self.value_characters)
        if raw_value and not _is_template_credential_value(raw_value):
            self.live_credential_found = True
        self.value_characters = []

    def _reset_for_character(self, character):
        self.token_characters = []
        self.value_characters = []
        self.value_quote = None
        self.value_escaped = False
        if character in CREDENTIAL_BOUNDARIES:
            self.state = self.LEADING
        else:
            self.state = self.SEEK


def _scan_archive_member_stream(stream, label, max_bytes):
    decoder = codecs.getincrementaldecoder("utf-8-sig")("strict")
    binary_overlap = b""
    credential_scanner = _CredentialAssignmentScanner()
    text_valid = True
    text_line_too_long = False
    current_line_size = 0
    total_bytes = 0
    while True:
        read_size = min(STREAM_CHUNK_SIZE, max_bytes - total_bytes + 1)
        chunk = stream.read(read_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise ValueError(f"stream exceeds the byte limit for {label}")

        combined = binary_overlap + chunk
        if PRIVATE_KEY_HEADER.search(combined):
            raise ValueError(f"private-key header found in {label}")
        binary_overlap = combined[-STREAM_OVERLAP_SIZE:]

        if not text_valid:
            continue
        if b"\x00" in chunk:
            text_valid = False
            credential_scanner = None
            continue

        line_parts = chunk.split(b"\n")
        if len(line_parts) == 1:
            current_line_size += len(chunk)
            text_line_too_long |= current_line_size > MAX_TEXT_LINE_SIZE
        else:
            current_line_size += len(line_parts[0])
            text_line_too_long |= current_line_size > MAX_TEXT_LINE_SIZE
            for line_part in line_parts[1:-1]:
                text_line_too_long |= len(line_part) > MAX_TEXT_LINE_SIZE
            current_line_size = len(line_parts[-1])

        try:
            decoded_chunk = decoder.decode(chunk, final=False)
        except UnicodeDecodeError:
            text_valid = False
            credential_scanner = None
            continue
        credential_scanner.feed(decoded_chunk)

    if text_valid:
        try:
            decoded_tail = decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            text_valid = False
    if text_valid:
        credential_scanner.feed(decoded_tail)
        text_line_too_long |= current_line_size > MAX_TEXT_LINE_SIZE
        if text_line_too_long:
            raise ValueError(f"text line exceeds the byte limit in {label}")
        if credential_scanner.finish():
            raise ValueError(f"credential assignment found in {label}")
    return total_bytes


def _read_bounded_zip_member(archive, name, label, size_limit):
    info = archive.getinfo(name)
    if info.file_size > size_limit:
        raise ValueError(f"{label} exceeds the bounded read limit")
    with archive.open(info, "r") as member:
        data = member.read(size_limit + 1)
        if len(data) > size_limit or member.read(1):
            raise ValueError(f"{label} exceeds the bounded read limit")
    if len(data) != info.file_size:
        raise ValueError(f"{label} uncompressed size does not match ZIP metadata")
    return data


def _hash_zip_member(archive, name, label):
    info = archive.getinfo(name)
    digest = hashlib.sha256()
    total_bytes = 0
    with archive.open(info, "r") as member:
        while chunk := member.read(STREAM_CHUNK_SIZE):
            total_bytes += len(chunk)
            if total_bytes > MAX_ARCHIVE_MEMBER_SIZE:
                raise ValueError(f"{label} exceeds the per-member uncompressed limit")
            digest.update(chunk)
    if total_bytes != info.file_size:
        raise ValueError(f"{label} uncompressed size does not match ZIP metadata")
    return digest.hexdigest(), total_bytes


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
    if len(infos) > MAX_ARCHIVE_ENTRIES:
        raise ValueError("archive exceeds the entry-count limit")
    total_uncompressed_size = 0
    for info in infos:
        if info.is_dir():
            continue
        if info.file_size > MAX_ARCHIVE_MEMBER_SIZE:
            raise ValueError(
                "archive entry exceeds the per-member uncompressed limit: "
                f"{info.filename!r}"
            )
        if info.filename in JSON_MANIFEST_NAMES and info.file_size > MAX_MANIFEST_SIZE:
            raise ValueError(f"launcher manifest exceeds the bounded read limit: {info.filename}")
        total_uncompressed_size += info.file_size
    if total_uncompressed_size > MAX_ARCHIVE_TOTAL_UNCOMPRESSED_SIZE:
        raise ValueError("archive exceeds the total uncompressed limit")
    for info in infos:
        if info.is_dir() or info.file_size == 0:
            continue
        if info.compress_size <= 0 or (
            info.file_size > info.compress_size * MAX_ARCHIVE_COMPRESSION_RATIO
        ):
            raise ValueError(
                "archive entry exceeds the compression ratio limit: "
                f"{info.filename!r}"
            )
    names = []
    seen_names = set()
    for info in infos:
        normalized_name = _validate_archive_name(
            info.filename,
            allow_directory=allow_directories,
        )
        collision_key = _windows_collision_key(normalized_name)
        if collision_key in seen_names:
            raise ValueError(
                "duplicate archive entry after Windows-normalized archive collision: "
                f"{info.filename!r}"
            )
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
                label = f"archive entry {info.filename!r}"
                scanned_size = _scan_archive_member_stream(
                    member,
                    label,
                    info.file_size,
                )
                if scanned_size != info.file_size:
                    raise ValueError(
                        f"archive entry uncompressed size does not match ZIP metadata: {info.filename!r}"
                    )
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

        actual_bootstrap_sha256, _ = _hash_zip_member(
            archive,
            PRISM_BOOTSTRAP_JAR,
            "Packwiz bootstrap",
        )
        if actual_bootstrap_sha256 != expected_bootstrap_sha256:
            raise ValueError(
                "bootstrap SHA-256 mismatch: "
                f"expected {expected_bootstrap_sha256}, got {actual_bootstrap_sha256}"
            )

        actual_installer_sha256, actual_installer_size = _hash_zip_member(
            archive,
            PRISM_INSTALLER_JAR,
            "Packwiz installer",
        )
        if actual_installer_size != expected_installer_size:
            raise ValueError(
                "installer size mismatch: "
                f"expected {expected_installer_size}, got {actual_installer_size}"
            )
        if actual_installer_sha256 != expected_installer_sha256:
            raise ValueError(
                "installer SHA-256 mismatch: "
                f"expected {expected_installer_sha256}, got {actual_installer_sha256}"
            )

        expected_instance_config = _instance_config(pack_url)
        if _read_bounded_zip_member(
            archive,
            "instance.cfg",
            "instance.cfg",
            MAX_MANIFEST_SIZE,
        ) != expected_instance_config:
            raise ValueError("instance.cfg does not use the exact Packwiz launch command")

        expected_mmc_pack = _mmc_pack(
            PRISM_MINECRAFT_VERSION,
            PRISM_NEOFORGE_VERSION,
        )
        if _read_bounded_zip_member(
            archive,
            "mmc-pack.json",
            "mmc-pack.json",
            MAX_MANIFEST_SIZE,
        ) != expected_mmc_pack:
            raise ValueError("mmc-pack.json does not use the exact loader versions")

    return {
        "archive": str(archive_path),
        "bootstrap_sha256": actual_bootstrap_sha256,
        "classification": "public",
        "installer_sha256": actual_installer_sha256,
        "installer_size": actual_installer_size,
        "entries": names,
        "entry_count": len(names),
        "format": "prism",
        "jar_entries": jar_entries,
        "minecraft": PRISM_MINECRAFT_VERSION,
        "neoforge": PRISM_NEOFORGE_VERSION,
        "pack_url": pack_url,
    }


def _read_launcher_manifest(archive, names, manifest_name, label):
    if manifest_name not in names:
        raise ValueError(f"{label} manifest is missing: {manifest_name}")
    try:
        manifest = json.loads(
            _read_bounded_zip_member(
                archive,
                manifest_name,
                f"{label} manifest",
                MAX_MANIFEST_SIZE,
            )
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} manifest is not valid UTF-8 JSON") from error
    if not isinstance(manifest, dict):
        raise ValueError(f"{label} manifest must be a JSON object")
    return manifest


def _launcher_summary(archive_path, names, format_name):
    return {
        "archive": str(archive_path),
        "classification": "public",
        "embedded_jar_count": sum(
            name.casefold().endswith(".jar") for name in names
        ),
        "entry_count": len(names),
        "format": format_name,
        "minecraft": PRISM_MINECRAFT_VERSION,
        "neoforge": PRISM_NEOFORGE_VERSION,
    }


def _validate_modrinth_files(files):
    if not isinstance(files, list) or not files:
        raise ValueError("Modrinth manifest must contain nonempty files")
    seen_paths = set()
    allowed_env_values = {"required", "optional", "unsupported"}
    for record in files:
        if not isinstance(record, dict) or set(record) != {
            "path",
            "hashes",
            "env",
            "downloads",
            "fileSize",
        }:
            raise ValueError("Modrinth file record shape is invalid")

        path = record["path"]
        if not isinstance(path, str):
            raise ValueError("Modrinth file path is invalid")
        try:
            normalized_path = _validate_archive_name(path)
        except ValueError as error:
            raise ValueError(f"Modrinth file path is invalid: {path!r}: {error}") from error
        collision_key = _windows_collision_key(normalized_path)
        if collision_key in seen_paths:
            raise ValueError(f"Modrinth duplicate file path: {path!r}")
        seen_paths.add(collision_key)

        hashes = record["hashes"]
        if not isinstance(hashes, dict) or set(hashes) != {"sha1", "sha512"}:
            raise ValueError(f"Modrinth file hashes are invalid: {path!r}")
        if not isinstance(hashes["sha1"], str) or not re.fullmatch(
            r"[0-9a-f]{40}", hashes["sha1"]
        ):
            raise ValueError(f"Modrinth file SHA-1 is invalid: {path!r}")
        if not isinstance(hashes["sha512"], str) or not re.fullmatch(
            r"[0-9a-f]{128}", hashes["sha512"]
        ):
            raise ValueError(f"Modrinth file SHA-512 is invalid: {path!r}")

        downloads = record["downloads"]
        if not isinstance(downloads, list) or not downloads:
            raise ValueError(f"Modrinth file HTTPS downloads are invalid: {path!r}")
        for download in downloads:
            if not isinstance(download, str) or not download:
                raise ValueError(f"Modrinth file HTTPS download is invalid: {path!r}")
            try:
                parsed_download = urlsplit(download)
            except ValueError as error:
                raise ValueError(
                    f"Modrinth file HTTPS download is invalid: {path!r}"
                ) from error
            if (
                parsed_download.scheme != "https"
                or not parsed_download.hostname
                or parsed_download.username is not None
                or parsed_download.password is not None
                or any(character.isspace() for character in download)
            ):
                raise ValueError(f"Modrinth file HTTPS download is invalid: {path!r}")

        environment = record["env"]
        if not isinstance(environment, dict) or set(environment) != {
            "client",
            "server",
        }:
            raise ValueError(f"Modrinth file environment is invalid: {path!r}")
        if any(value not in allowed_env_values for value in environment.values()):
            raise ValueError(f"Modrinth file environment is invalid: {path!r}")

        file_size = record["fileSize"]
        if type(file_size) is not int or not 1 <= file_size <= MAX_UNSIGNED_32:
            raise ValueError(f"Modrinth fileSize is invalid: {path!r}")


def _validate_curseforge_files(files):
    if not isinstance(files, list) or not files:
        raise ValueError("CurseForge manifest must contain nonempty files")
    seen_files = set()
    for record in files:
        if not isinstance(record, dict) or set(record) != {
            "projectID",
            "fileID",
            "required",
        }:
            raise ValueError("CurseForge file record shape is invalid")
        project_id = record["projectID"]
        file_id = record["fileID"]
        required = record["required"]
        if type(project_id) is not int or not 1 <= project_id <= MAX_UNSIGNED_32:
            raise ValueError("CurseForge projectID must be an unsigned 32-bit integer")
        if type(file_id) is not int or not 1 <= file_id <= MAX_UNSIGNED_32:
            raise ValueError("CurseForge fileID must be an unsigned 32-bit integer")
        if type(required) is not bool:
            raise ValueError("CurseForge required flag must be a boolean")
        file_key = (project_id, file_id)
        if file_key in seen_files:
            raise ValueError("CurseForge duplicate file record")
        seen_files.add(file_key)


def inspect_modrinth_archive(archive_path, version):
    archive_path = Path(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        _, names = _inspect_zip_safety(archive, allow_directories=True)
        manifest = _read_launcher_manifest(
            archive,
            names,
            MODRINTH_MANIFEST_NAME,
            "Modrinth",
        )

    if manifest.get("formatVersion") != 1:
        raise ValueError("Modrinth manifest formatVersion must be 1")
    if manifest.get("game") != "minecraft":
        raise ValueError("Modrinth manifest game must be minecraft")
    if manifest.get("name") != EXPECTED_PACK_NAME:
        raise ValueError("Modrinth manifest pack name does not match AFTERLIGHT")
    if manifest.get("versionId") != version:
        raise ValueError("Modrinth manifest pack version does not match")
    _validate_modrinth_files(manifest.get("files"))
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, dict):
        raise ValueError("Modrinth manifest dependencies are invalid")
    if dependencies.get("minecraft") != PRISM_MINECRAFT_VERSION:
        raise ValueError("Modrinth Minecraft version does not match")
    if set(dependencies) != {"minecraft", "neoforge"}:
        raise ValueError("Modrinth manifest must declare only NeoForge")
    if dependencies.get("neoforge") != PRISM_NEOFORGE_VERSION:
        raise ValueError("Modrinth NeoForge version does not match")

    return _launcher_summary(archive_path, names, "modrinth")


def inspect_curseforge_archive(archive_path, version):
    archive_path = Path(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        _, names = _inspect_zip_safety(archive, allow_directories=True)
        manifest = _read_launcher_manifest(
            archive,
            names,
            CURSEFORGE_MANIFEST_NAME,
            "CurseForge",
        )

    if manifest.get("manifestType") != "minecraftModpack":
        raise ValueError("CurseForge manifest type must be minecraftModpack")
    if manifest.get("manifestVersion") != 1:
        raise ValueError("CurseForge manifest version must be 1")
    if manifest.get("name") != EXPECTED_PACK_NAME:
        raise ValueError("CurseForge manifest pack name does not match AFTERLIGHT")
    if manifest.get("version") != version:
        raise ValueError("CurseForge manifest pack version does not match")
    if manifest.get("overrides") != "overrides":
        raise ValueError("CurseForge manifest overrides directory does not match")
    _validate_curseforge_files(manifest.get("files"))
    minecraft = manifest.get("minecraft")
    if not isinstance(minecraft, dict):
        raise ValueError("CurseForge Minecraft identity is invalid")
    if minecraft.get("version") != PRISM_MINECRAFT_VERSION:
        raise ValueError("CurseForge Minecraft version does not match")
    expected_loaders = [
        {"id": f"neoforge-{PRISM_NEOFORGE_VERSION}", "primary": True}
    ]
    if minecraft.get("modLoaders") != expected_loaders:
        raise ValueError("CurseForge NeoForge identity does not match")

    return _launcher_summary(archive_path, names, "curseforge")


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
            _validate_archive_name(relative_path, windows_safe=False)
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


def _canonical_json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _public_file_records(dist_path):
    records = {}
    for name in PUBLIC_RELEASE_NAMES:
        file_path = dist_path / name
        file_status = _require_regular_file(file_path, f"public release entry {name}")
        records[name] = {
            "sha256": _sha256_file(file_path),
            "size": file_status.st_size,
        }
    return records


def _trusted_packwiz_records(
    bootstrap_version,
    bootstrap_size,
    bootstrap_sha256,
    installer_version,
    installer_size,
    installer_sha256,
):
    records = {}
    for label, version, size, sha256 in (
        ("bootstrap", bootstrap_version, bootstrap_size, bootstrap_sha256),
        ("installer", installer_version, installer_size, installer_sha256),
    ):
        if not isinstance(version, str) or not version:
            raise ValueError(f"trusted Packwiz {label} version is missing")
        records[label] = {
            "version": version,
            "size": _validate_positive_size(size, f"trusted Packwiz {label}"),
            "sha256": _validate_sha256(sha256, f"trusted Packwiz {label}"),
        }
    return records


def _gauntlet_receipt(version, git_sha, pack_url, packwiz, public_files):
    return {
        "format": GAUNTLET_RECEIPT_FORMAT,
        "git_sha": git_sha,
        "pack_url": pack_url,
        "packwiz": packwiz,
        "public_files": public_files,
        "version": version,
    }


def _read_gauntlet_receipt(receipt_path, receipt_sha256):
    receipt_path = Path(receipt_path)
    receipt_status = _require_regular_file(receipt_path, "gauntlet receipt")
    if receipt_status.st_size > MAX_RECEIPT_SIZE:
        raise ValueError("gauntlet receipt exceeds the size limit")
    if not re.fullmatch(r"[0-9a-f]{64}", receipt_sha256):
        raise ValueError("receipt SHA-256 must be exactly 64 lowercase hexadecimal characters")
    actual_sha256 = _sha256_file(receipt_path)
    if actual_sha256 != receipt_sha256:
        raise ValueError(
            "gauntlet receipt SHA-256 mismatch: "
            f"expected {receipt_sha256}, got {actual_sha256}"
        )
    with receipt_path.open("rb") as receipt_file:
        receipt_bytes = receipt_file.read(MAX_RECEIPT_SIZE + 1)
    try:
        receipt = json.loads(receipt_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("gauntlet receipt is not valid UTF-8 JSON") from error
    if not isinstance(receipt, dict):
        raise ValueError("gauntlet receipt must be a JSON object")
    if receipt_bytes != _canonical_json_bytes(receipt):
        raise ValueError("gauntlet receipt is not canonical JSON")
    return receipt


def render_gauntlet_tag_message(receipt_path, receipt_sha256):
    receipt = _read_gauntlet_receipt(receipt_path, receipt_sha256)
    if set(receipt) != {
        "format",
        "git_sha",
        "pack_url",
        "packwiz",
        "public_files",
        "version",
    }:
        raise ValueError("gauntlet receipt fields are invalid")
    if receipt.get("format") != GAUNTLET_RECEIPT_FORMAT:
        raise ValueError("gauntlet receipt format is invalid")
    version = receipt.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("gauntlet receipt version is invalid")
    public_files = receipt.get("public_files")
    if not isinstance(public_files, dict) or set(public_files) != set(
        PUBLIC_RELEASE_NAMES
    ):
        raise ValueError("gauntlet receipt public file inventory is invalid")
    lines = [
        f"AFTERLIGHT {version}",
        "",
        f"Gauntlet-Receipt-SHA256: {receipt_sha256}",
    ]
    for name in PUBLIC_RELEASE_NAMES:
        record = public_files[name]
        if not isinstance(record, dict) or set(record) != {"sha256", "size"}:
            raise ValueError(f"gauntlet receipt public file record is invalid: {name}")
        sha256 = record.get("sha256")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError(f"gauntlet receipt public file SHA-256 is invalid: {name}")
        _validate_positive_size(record.get("size"), f"gauntlet receipt public file {name}")
        lines.append(f"Public-File-SHA256: {sha256}  {name}")
    return "\n".join(lines) + "\n"


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
    if not isinstance(metadata, dict):
        raise ValueError("release metadata must be a JSON object")

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


def _load_release_metadata(dist_path):
    metadata_path = dist_path / RELEASE_METADATA_NAME
    _require_regular_file(metadata_path, "release metadata")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("release metadata is not valid UTF-8 JSON") from error
    if not isinstance(metadata, dict):
        raise ValueError("release metadata must be a JSON object")
    return metadata


def _verify_release_checksums(dist_path):
    checksums_path = dist_path / CHECKSUMS_NAME
    _require_regular_file(checksums_path, "release checksums")
    try:
        checksum_text = checksums_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("release checksums are malformed") from error
    lines = checksum_text.splitlines(keepends=True)
    if len(lines) != len(CHECKSUM_TARGET_NAMES):
        raise ValueError("release checksums are malformed")

    for line, expected_name in zip(lines, CHECKSUM_TARGET_NAMES):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\s]+)\n", line)
        if match is None or match.group(2) != expected_name:
            raise ValueError("release checksums are malformed")
        actual_sha256 = _sha256_file(dist_path / expected_name)
        if match.group(1) != actual_sha256:
            raise ValueError(
                f"release checksum does not match: {expected_name}"
            )


def verify_public_release(
    dist_dir,
    version,
    git_sha,
    pack_url,
    bootstrap_version,
    bootstrap_size,
    bootstrap_sha256,
    installer_version,
    installer_size,
    installer_sha256,
    *,
    receipt_path=None,
    receipt_sha256=None,
    write_receipt=None,
):
    if not isinstance(version, str) or not version:
        raise ValueError("release version is missing")
    if not re.fullmatch(r"[0-9a-f]{40}", git_sha):
        raise ValueError("release SHA must be exactly 40 lowercase hexadecimal characters")
    if not isinstance(pack_url, str) or not pack_url:
        raise ValueError("trusted production Packwiz URL is missing")
    trusted_packwiz = _trusted_packwiz_records(
        bootstrap_version,
        bootstrap_size,
        bootstrap_sha256,
        installer_version,
        installer_size,
        installer_sha256,
    )
    if write_receipt is not None and receipt_path is not None:
        raise ValueError("cannot write and verify a gauntlet receipt together")
    if receipt_path is None and receipt_sha256 is not None:
        raise ValueError("receipt SHA-256 requires a gauntlet receipt")
    if receipt_path is not None and receipt_sha256 is None:
        raise ValueError("gauntlet receipt requires an independently supplied receipt SHA-256")

    dist_path = Path(dist_dir)
    try:
        dist_status = dist_path.lstat()
    except OSError as error:
        raise ValueError(
            f"public release directory is unreadable: {dist_path}"
        ) from error
    if not stat.S_ISDIR(dist_status.st_mode):
        raise ValueError(f"public release path is not a directory: {dist_path}")

    entries = list(os.scandir(dist_path))
    actual_names = tuple(sorted(entry.name for entry in entries))
    if actual_names != PUBLIC_RELEASE_NAMES:
        raise ValueError("public release inventory is incomplete or contains extra entries")
    for name in PUBLIC_RELEASE_NAMES:
        _require_regular_file(dist_path / name, f"public release entry {name}")

    metadata = _load_release_metadata(dist_path)
    if set(metadata) != RELEASE_METADATA_KEYS:
        raise ValueError("release metadata top-level fields are invalid")
    if metadata.get("format") != 3:
        raise ValueError("release metadata format must be 3")
    if metadata.get("version") != version:
        raise ValueError("release metadata version does not match")
    if metadata.get("git_sha") != git_sha:
        raise ValueError("release metadata SHA does not match")
    if metadata.get("minecraft") != PRISM_MINECRAFT_VERSION:
        raise ValueError("release metadata Minecraft version does not match")
    if metadata.get("neoforge") != PRISM_NEOFORGE_VERSION:
        raise ValueError("release metadata NeoForge version does not match")
    if metadata.get("pack_url") != pack_url:
        raise ValueError("release metadata does not match the trusted production Packwiz URL")

    _classified_release_names(dist_path)
    _verify_release_checksums(dist_path)

    packwiz = metadata["packwiz"]
    if packwiz["bootstrap"] != trusted_packwiz["bootstrap"]:
        raise ValueError("release metadata does not match trusted Packwiz bootstrap pins")
    if packwiz["installer"] != trusted_packwiz["installer"]:
        raise ValueError("release metadata does not match trusted Packwiz installer pins")
    bootstrap = trusted_packwiz["bootstrap"]
    installer = trusted_packwiz["installer"]
    prism = inspect_prism_archive(
        dist_path / PRISM_ARTIFACT_NAME,
        pack_url,
        bootstrap["sha256"],
        installer["sha256"],
        installer["size"],
    )
    curseforge = inspect_curseforge_archive(
        dist_path / CURSEFORGE_ARTIFACT_NAME,
        version,
    )
    modrinth = inspect_modrinth_archive(
        dist_path / MRPACK_ARTIFACT_NAME,
        version,
    )

    public_files = _public_file_records(dist_path)
    expected_receipt = _gauntlet_receipt(
        version,
        git_sha,
        pack_url,
        trusted_packwiz,
        public_files,
    )
    summary = {
        "dist_dir": str(dist_path),
        "formats": {
            CURSEFORGE_ARTIFACT_NAME: curseforge["format"],
            PRISM_ARTIFACT_NAME: prism["format"],
            MRPACK_ARTIFACT_NAME: modrinth["format"],
        },
        "git_sha": git_sha,
        "public_files": public_files,
        "version": version,
    }
    if write_receipt is not None:
        receipt_output = Path(write_receipt)
        resolved_dist = dist_path.resolve()
        resolved_receipt = receipt_output.resolve()
        if resolved_receipt.is_relative_to(resolved_dist):
            raise ValueError("gauntlet receipt must remain outside the public directory")
        receipt_bytes = _canonical_json_bytes(expected_receipt)
        _atomic_write_bytes(receipt_output, receipt_bytes)
        summary["receipt"] = str(receipt_output)
        summary["receipt_sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
    elif receipt_path is not None:
        receipt = _read_gauntlet_receipt(receipt_path, receipt_sha256)
        if receipt != expected_receipt:
            raise ValueError("gauntlet receipt does not match the accepted public release")
        summary["receipt"] = str(receipt_path)
        summary["receipt_sha256"] = receipt_sha256
    return summary


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

    modrinth_parser = subparsers.add_parser("inspect-modrinth")
    modrinth_parser.add_argument("--archive", required=True)
    modrinth_parser.add_argument("--version", required=True)

    curseforge_parser = subparsers.add_parser("inspect-curseforge")
    curseforge_parser.add_argument("--archive", required=True)
    curseforge_parser.add_argument("--version", required=True)

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

    verifier_parser = subparsers.add_parser("verify-public-release")
    verifier_parser.add_argument("--dist-dir", required=True)
    verifier_parser.add_argument("--version", required=True)
    verifier_parser.add_argument("--git-sha", required=True)
    verifier_parser.add_argument("--pack-url", required=True)
    verifier_parser.add_argument("--bootstrap-version", required=True)
    verifier_parser.add_argument("--bootstrap-size", required=True, type=int)
    verifier_parser.add_argument("--bootstrap-sha256", required=True)
    verifier_parser.add_argument("--installer-version", required=True)
    verifier_parser.add_argument("--installer-size", required=True, type=int)
    verifier_parser.add_argument("--installer-sha256", required=True)
    verifier_parser.add_argument("--receipt")
    verifier_parser.add_argument("--receipt-sha256")
    verifier_parser.add_argument("--write-receipt")

    tag_message_parser = subparsers.add_parser("render-gauntlet-tag-message")
    tag_message_parser.add_argument("--receipt", required=True)
    tag_message_parser.add_argument("--receipt-sha256", required=True)
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

    if args.command == "inspect-modrinth":
        summary = inspect_modrinth_archive(args.archive, args.version)
        print(json.dumps(summary, sort_keys=True))
        return 0

    if args.command == "inspect-curseforge":
        summary = inspect_curseforge_archive(args.archive, args.version)
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

    if args.command == "verify-public-release":
        summary = verify_public_release(
            args.dist_dir,
            args.version,
            args.git_sha,
            args.pack_url,
            args.bootstrap_version,
            args.bootstrap_size,
            args.bootstrap_sha256,
            args.installer_version,
            args.installer_size,
            args.installer_sha256,
            receipt_path=args.receipt,
            receipt_sha256=args.receipt_sha256,
            write_receipt=args.write_receipt,
        )
        print(json.dumps(summary, sort_keys=True))
        return 0

    if args.command == "render-gauntlet-tag-message":
        sys.stdout.write(
            render_gauntlet_tag_message(args.receipt, args.receipt_sha256)
        )
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
