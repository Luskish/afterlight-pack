#!/usr/bin/env python3

import argparse
import base64
import binascii
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
import tomllib
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
MAX_PACKWIZ_METADATA_SIZE = 16 * 1024 * 1024
MAX_TEXT_LINE_SIZE = 1024 * 1024
MAX_CREDENTIAL_CONTAINER_DEPTH = 1024
MAX_CREDENTIAL_CONTEXT_SIZE = 512
MAX_JWT_HEADER_SIZE = 16 * 1024
MAX_UNSIGNED_32 = 4294967295
PRIVATE_KEY_HEADER = re.compile(
    rb"-----BEGIN (?:[A-Z0-9][A-Z0-9 ]* )?PRIVATE KEY(?: BLOCK)?-----"
)
JWT_URLSAFE_BYTES = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
)
CREDENTIAL_KEY = re.compile(
    r"(?:(?:[A-Za-z0-9]+[._-])+)?"
    r"(?:api[._-]?key|rcon[._-]?password|"
    r"(?:access|auth|private|refresh)[._-]?token|"
    r"(?:client|consumer|signing|webhook)[._-]?secret|"
    r"(?:database|db)[._-]?password|token|password|secret)",
    re.IGNORECASE,
)
CREDENTIAL_DECLARATIONS = frozenset(
    {
        "const",
        "export",
        "final",
        "internal",
        "lateinit",
        "let",
        "private",
        "protected",
        "public",
        "readonly",
        "static",
        "string",
        "val",
        "var",
    }
)
CREDENTIAL_BOUNDARIES = frozenset("\x00\r\n,{([;:)}]<>+=*/%!?&|^~$@")
CREDENTIAL_HORIZONTAL_WHITESPACE = frozenset("\t ")
CREDENTIAL_ASSIGNMENT_WHITESPACE = frozenset("\t \r\n")
PARAMETER_LIST_PREFIX = re.compile(
    r"(?:^|[^A-Za-z0-9_$])(?:"
    r"(?:async\s+)?def\s+[A-Za-z_][A-Za-z0-9_]*"
    r"(?:\s*\[[^\]\r\n]{1,256}\])?|"
    r"function(?:\s*\*)?(?:\s+[A-Za-z_$][A-Za-z0-9_$]*)?"
    r"(?:\s*<[^>\r\n]{1,256}>)?|"
    r"fun(?:\s*<[^>\r\n]{1,256}>)?\s+[A-Za-z_][A-Za-z0-9_]*|"
    r"fn\s+[A-Za-z_][A-Za-z0-9_]*(?:\s*<[^>\r\n]{1,256}>)?"
    r")\s*$"
)
TEMPLATE_CREDENTIAL_VALUES = frozenset(
    {
        "0",
        "-",
        "-example-signing-secret",
        "-placeholder",
        "?required",
        "change-me",
        "change_me",
        "changeme",
        "example",
        "false",
        "file:",
        "none",
        "null",
        "placeholder",
        "replace-me",
        "replace_me",
        "sample",
        "template",
        "token",
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
CODE_CREDENTIAL_REFERENCE = re.compile(
    r"(?:System\.getenv\([\"'][A-Za-z_][A-Za-z0-9_]*[\"']\)|"
    r"(?:self|this|super|process|os|config|settings|environment|env|"
    r"secrets|credentials)"
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*)+"
    r"(?:(?:\([^\"'\r\n]*\))|(?:\[[^\]\r\n]+\]))*|"
    r"[\"']{2}(?:\.[A-Za-z_][A-Za-z0-9_]*)+"
    r"(?:(?:\([^\"'\r\n]*\))|(?:\[[^\]\r\n]+\]))+|"
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+"
    r"(?:(?:\([^\"'\r\n]*\))|(?:\[[^\]\r\n]+\]))+|"
    r"[A-Za-z_][A-Za-z0-9_]*(?:_value|_reference|_ref)|"
    r"(?:kwargs|params|options|arguments)\[[^\]\r\n]+\]|"
    r"(?:get|load|read|resolve|fetch)_[A-Za-z_][A-Za-z0-9_]*"
    r"\([^\"'\r\n]*\))"
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
CURSEFORGE_MODLIST_NAME = "modlist.html"
MODRINTH_MANIFEST_NAME = "modrinth.index.json"
MODRINTH_MANIFEST_LOCK_PATH = "tools/modrinth-manifest-lock.json"
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


def _is_template_credential_value(raw_value, *, allow_code_reference=True):
    value = raw_value.strip()
    quoted = (
        len(value) >= 2
        and value[:1] == value[-1:]
        and value[:1] in {'"', "'"}
    )
    if quoted:
        value = value[1:-1].strip()
    if not value:
        return True
    if value.casefold() in TEMPLATE_CREDENTIAL_VALUES:
        return True
    if TEMPLATE_CREDENTIAL_PATTERN.fullmatch(value):
        return True
    if SIMPLE_ENVIRONMENT_REFERENCE.fullmatch(value):
        return True
    if allow_code_reference and not quoted and CODE_CREDENTIAL_REFERENCE.fullmatch(value):
        return True
    environment_reference = BRACED_ENVIRONMENT_REFERENCE.fullmatch(value)
    if environment_reference is None:
        return False
    operator = environment_reference.group("operator")
    if operator is None or operator in {"?", ":?"}:
        return True
    return _is_template_credential_value(
        environment_reference.group("operand"),
        allow_code_reference=False,
    )


def _is_credential_key_character(character):
    return character.isascii() and (
        character.isalnum() or character in "._-"
    )


def _is_credential_value_delimiter(character):
    return character.isspace() or character in ",#;}"


def _is_credential_boundary(character):
    return character in CREDENTIAL_BOUNDARIES or character == "\ufffd"


class _JwtShapeScanner:
    def __init__(self):
        self.state = "seek"
        self.header = bytearray()
        self.segment_size = 0
        self.previous_urlsafe = False
        self.found = False

    def feed(self, data):
        if self.found:
            return
        for byte in data:
            previous_urlsafe = self.previous_urlsafe
            self._consume(byte, previous_urlsafe)
            self.previous_urlsafe = byte in JWT_URLSAFE_BYTES
            if self.found:
                return

    def finish(self):
        if self.state == "third" and self.segment_size >= 8:
            self.found = True
        return self.found

    def _restart(self, byte, previous_urlsafe):
        self.header = bytearray()
        self.segment_size = 0
        if byte in JWT_URLSAFE_BYTES and not previous_urlsafe:
            self.state = "header"
            self.header.append(byte)
        else:
            self.state = "seek"

    def _header_is_jwt(self):
        if len(self.header) >= 8 and self.header.startswith(b"eyJ"):
            return True
        try:
            padding = b"=" * (-len(self.header) % 4)
            decoded = base64.b64decode(
                bytes(self.header) + padding,
                altchars=b"-_",
                validate=True,
            )
            value = json.loads(decoded.decode("utf-8"))
        except (binascii.Error, UnicodeDecodeError, ValueError, json.JSONDecodeError):
            return False
        return (
            isinstance(value, dict)
            and isinstance(value.get("alg"), str)
            and bool(value["alg"])
        )

    def _consume(self, byte, previous_urlsafe):
        if self.state == "seek":
            self._restart(byte, previous_urlsafe)
            return
        if self.state == "header":
            if byte in JWT_URLSAFE_BYTES:
                if len(self.header) >= MAX_JWT_HEADER_SIZE:
                    self.state = "header_overflow"
                    self.header = bytearray()
                else:
                    self.header.append(byte)
                return
            if byte == ord(".") and self._header_is_jwt():
                self.state = "second"
                self.segment_size = 0
                return
            self._restart(byte, previous_urlsafe)
            return
        if self.state == "header_overflow":
            if byte not in JWT_URLSAFE_BYTES:
                self._restart(byte, previous_urlsafe)
            return
        if self.state == "second":
            if byte in JWT_URLSAFE_BYTES:
                self.segment_size += 1
                return
            if byte == ord(".") and self.segment_size >= 8:
                self.state = "third"
                self.segment_size = 0
                return
            self._restart(byte, previous_urlsafe)
            return
        if byte in JWT_URLSAFE_BYTES:
            self.segment_size += 1
            return
        if self.segment_size >= 8:
            self.found = True
            return
        self._restart(byte, previous_urlsafe)


class _CredentialAssignmentScanner:
    SEEK = "seek"
    LEADING = "leading"
    TOKEN = "token"
    AFTER_DECLARATION = "after_declaration"
    AFTER_KEY = "after_key"
    AFTER_ANNOTATION = "after_annotation"
    AFTER_SEPARATOR = "after_separator"
    DOLLAR_VALUE = "dollar_value"
    BRACED_VALUE = "braced_value"
    QUOTED_VALUE = "quoted_value"
    COMPLETE_VALUE = "complete_value"
    UNQUOTED_VALUE = "unquoted_value"

    def __init__(self, template_value_predicate=None):
        self.live_credential_found = False
        self.template_value_predicate = (
            template_value_predicate or _is_template_credential_value
        )
        self.state = self.LEADING
        self.leading_boundary = None
        self.container_stack = []
        self.container_recent_characters = []
        self.container_quote = None
        self.container_quote_mode = None
        self.container_quote_run = 0
        self.container_quote_escaped = False
        self.container_line_comment = False
        self.container_block_comment = False
        self.container_block_comment_star = False
        self.container_pending_slash = False
        self.token_characters = []
        self.token_boundary = None
        self.token_parameter_context = False
        self.token_quoted = False
        self.token_escape_state = None
        self.token_escape_characters = []
        self.value_characters = []
        self.value_quote = None
        self.value_escaped = False
        self.value_line_comment = False
        self.value_block_comment = False
        self.value_block_comment_star = False
        self.value_pending_slash = False
        self.annotation_brackets = []
        self.annotation_quote = None
        self.annotation_escaped = False
        self.annotation_characters = []
        self.annotation_has_nonwhitespace = False
        self.annotation_boundary = None
        self.annotation_parameter_context = False
        self.annotation_line_comment = False
        self.annotation_block_comment = False
        self.annotation_block_comment_star = False
        self.annotation_pending_slash = False

    def feed(self, data):
        if self.live_credential_found:
            return
        for character in data:
            self._consume(character)
            self._update_container_context(character)
            if self.live_credential_found:
                return

    def finish(self):
        if self.state == self.AFTER_ANNOTATION:
            if self.annotation_pending_slash:
                self._append_annotation("/")
                self.annotation_pending_slash = False
            self._resolve_annotation_value()
        if self.state == self.AFTER_SEPARATOR and self.value_pending_slash:
            self.value_characters = ["/"]
            self._resolve_value()
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
            if _is_credential_boundary(character):
                self.state = self.LEADING
                self.leading_boundary = character
            return

        if self.state == self.LEADING:
            if character in CREDENTIAL_HORIZONTAL_WHITESPACE:
                return
            if _is_credential_boundary(character):
                self.leading_boundary = character
                return
            if character == "-":
                self.state = self.AFTER_DECLARATION
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
            if (
                character in CREDENTIAL_ASSIGNMENT_WHITESPACE
                or character == "\ufffd"
                or character in "])}"
            ):
                return
            if character in ":=":
                self.state = self.AFTER_SEPARATOR
                return
            self._reset_for_character(character)
            return

        if self.state == self.AFTER_ANNOTATION:
            self._consume_annotation(character)
            return

        if self.state == self.AFTER_SEPARATOR:
            if self.value_line_comment:
                if character in "\r\n":
                    self.value_line_comment = False
                return
            if self.value_block_comment:
                if self.value_block_comment_star and character == "/":
                    self.value_block_comment = False
                    self.value_block_comment_star = False
                    return
                self.value_block_comment_star = character == "*"
                return
            if self.value_pending_slash:
                self.value_pending_slash = False
                if character == "/":
                    self.value_line_comment = True
                    return
                if character == "*":
                    self.value_block_comment = True
                    self.value_block_comment_star = False
                    return
                self._start_value(self.UNQUOTED_VALUE, "/")
                if _is_credential_value_delimiter(character):
                    self._resolve_value()
                    self._reset_for_character(character)
                else:
                    self._append_value(character)
                return
            if character in CREDENTIAL_ASSIGNMENT_WHITESPACE:
                return
            if character == "#":
                self.value_line_comment = True
                return
            if character == "/":
                self.value_pending_slash = True
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
        if self.token_escape_state == "unicode":
            if character not in "0123456789abcdefABCDEF":
                self._reset_for_character(character)
                return
            self.token_escape_characters.append(character)
            if len(self.token_escape_characters) == 4:
                decoded_character = chr(
                    int("".join(self.token_escape_characters), 16)
                )
                self.token_escape_state = None
                self.token_escape_characters = []
                if not _is_credential_key_character(decoded_character):
                    self._reset_for_character(decoded_character)
                    return
                self._append_token(decoded_character)
            return
        if self.token_escape_state == "backslash":
            self.token_escape_state = None
            if character == "u":
                self.token_escape_state = "unicode"
                self.token_escape_characters = []
                return
            if _is_credential_key_character(character):
                self._append_token(character)
                return
            self._reset_for_character(character)
            return
        if character == "\\":
            self.token_escape_state = "backslash"
            self.token_escape_characters = []
            return
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
            elif not self.token_quoted and token.endswith("."):
                self._start_token(quoted=True)
            else:
                self._reset_for_character(character)
            return
        if character in CREDENTIAL_HORIZONTAL_WHITESPACE:
            if token_is_declaration:
                self.state = self.AFTER_DECLARATION
            elif token_is_key:
                if "." in token:
                    self.state = self.AFTER_SEPARATOR
                else:
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
        if character == "\ufffd" and token_is_key:
            self.state = self.AFTER_KEY
            return
        if character in ":=" and token_is_key:
            if character == ":" and not self.token_quoted:
                self.state = self.AFTER_ANNOTATION
                self.annotation_brackets = []
                self.annotation_quote = None
                self.annotation_escaped = False
                self.annotation_characters = []
                self.annotation_has_nonwhitespace = False
                self.annotation_boundary = self.token_boundary
                self.annotation_parameter_context = self.token_parameter_context
                self.annotation_line_comment = False
                self.annotation_block_comment = False
                self.annotation_block_comment_star = False
                self.annotation_pending_slash = False
                return
            self.state = self.AFTER_SEPARATOR
            return
        self._reset_for_character(character)

    def _consume_annotation(self, character):
        if self.annotation_line_comment:
            if character in "\r\n":
                self.annotation_line_comment = False
                self._append_annotation(character)
            return

        if self.annotation_block_comment:
            if self.annotation_block_comment_star and character == "/":
                self.annotation_block_comment = False
                self.annotation_block_comment_star = False
                return
            self.annotation_block_comment_star = character == "*"
            return

        if self.annotation_pending_slash:
            self.annotation_pending_slash = False
            if character == "/":
                self.annotation_line_comment = True
                return
            if character == "*":
                self.annotation_block_comment = True
                self.annotation_block_comment_star = False
                return
            self._append_annotation("/")

        if self.annotation_quote is not None:
            self._append_annotation(character)
            if character in "\r\n":
                self._resolve_annotation_value()
                self._reset_for_character(character)
                return
            if self.annotation_escaped:
                self.annotation_escaped = False
                return
            if character == "\\":
                self.annotation_escaped = True
                return
            if character == self.annotation_quote:
                self.annotation_quote = None
                return
            return

        if character in {'"', "'"}:
            self._append_annotation(character)
            self.annotation_quote = character
            return
        if character in "[({":
            self._append_annotation(character)
            self.annotation_brackets.append({"[": "]", "(": ")", "{": "}"}[character])
            return
        if self.annotation_brackets:
            self._append_annotation(character)
            if character == self.annotation_brackets[-1]:
                self.annotation_brackets.pop()
            return
        if self.annotation_parameter_context and character == "#":
            self.annotation_line_comment = True
            return
        if self.annotation_parameter_context and character == "/":
            self.annotation_pending_slash = True
            return
        if character == "=" and self.annotation_parameter_context:
            self.annotation_characters = []
            self.annotation_has_nonwhitespace = False
            self.state = self.AFTER_SEPARATOR
            return
        if character in ",);}" or character in "\r\n":
            if (
                character in "\r\n"
                and self.annotation_parameter_context
                and self.annotation_has_nonwhitespace
            ):
                self._append_annotation(character)
                return
            if character in "\r\n" and not self.annotation_has_nonwhitespace:
                self.state = self.AFTER_SEPARATOR
                self.annotation_characters = []
                self.annotation_has_nonwhitespace = False
                return
            self._resolve_annotation_value()
            self._reset_for_character(character)
            return
        self._append_annotation(character)

    def _append_annotation(self, character):
        if len(self.annotation_characters) >= MAX_TEXT_LINE_SIZE:
            self.live_credential_found = True
            return
        self.annotation_characters.append(character)
        if not character.isspace():
            self.annotation_has_nonwhitespace = True

    def _resolve_annotation_value(self):
        if not self.annotation_parameter_context:
            raw_value = "".join(self.annotation_characters)
            if raw_value and not _is_template_credential_value(
                raw_value,
                allow_code_reference=False,
            ):
                self.live_credential_found = True
        self.annotation_characters = []
        self.annotation_has_nonwhitespace = False

    def _start_token(self, quoted):
        self.state = self.TOKEN
        self.token_characters = []
        self.token_quoted = quoted
        self.token_boundary = self.leading_boundary
        self.token_parameter_context = self._in_parameter_context()
        self.token_escape_state = None
        self.token_escape_characters = []

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
        self.value_line_comment = False
        self.value_block_comment = False
        self.value_block_comment_star = False
        self.value_pending_slash = False

    def _append_value(self, character):
        if len(self.value_characters) >= MAX_TEXT_LINE_SIZE:
            self.live_credential_found = True
            return
        self.value_characters.append(character)

    def _resolve_value(self):
        raw_value = "".join(self.value_characters)
        if raw_value and not self.template_value_predicate(raw_value):
            self.live_credential_found = True
        self.value_characters = []

    def _reset_for_character(self, character):
        self.token_characters = []
        self.token_boundary = None
        self.token_parameter_context = False
        self.token_escape_state = None
        self.token_escape_characters = []
        self.value_characters = []
        self.value_quote = None
        self.value_escaped = False
        self.value_line_comment = False
        self.value_block_comment = False
        self.value_block_comment_star = False
        self.value_pending_slash = False
        self.annotation_brackets = []
        self.annotation_quote = None
        self.annotation_escaped = False
        self.annotation_characters = []
        self.annotation_has_nonwhitespace = False
        self.annotation_boundary = None
        self.annotation_parameter_context = False
        self.annotation_line_comment = False
        self.annotation_block_comment = False
        self.annotation_block_comment_star = False
        self.annotation_pending_slash = False
        if _is_credential_boundary(character):
            self.state = self.LEADING
            self.leading_boundary = character
        else:
            self.state = self.SEEK
            self.leading_boundary = None

    def _in_parameter_context(self):
        if (
            self.container_quote is not None
            or self.container_line_comment
            or self.container_block_comment
            or self.container_pending_slash
            or not self.container_stack
        ):
            return False
        opener, parameter_context = self.container_stack[-1]
        return opener == "(" and parameter_context

    def _append_container_recent(self, character):
        self.container_recent_characters.append(character)
        if len(self.container_recent_characters) > MAX_CREDENTIAL_CONTEXT_SIZE:
            del self.container_recent_characters[
                : len(self.container_recent_characters) - MAX_CREDENTIAL_CONTEXT_SIZE
            ]

    def _start_container_quote(self, character):
        self.container_quote = character
        self.container_quote_mode = "opening"
        self.container_quote_run = 1
        self.container_quote_escaped = False
        self._append_container_recent(" ")

    def _clear_container_quote(self):
        self.container_quote = None
        self.container_quote_mode = None
        self.container_quote_run = 0
        self.container_quote_escaped = False
        self._append_container_recent(" ")

    def _consume_container_quote(self, character):
        if self.container_quote_mode == "opening":
            if character == self.container_quote:
                self.container_quote_run += 1
                if self.container_quote_run == 3:
                    self.container_quote_mode = "triple"
                    self.container_quote_run = 0
                return True
            if self.container_quote_run == 2:
                self._clear_container_quote()
                return False
            self.container_quote_mode = "single"

        if self.container_quote_mode == "triple":
            if character == self.container_quote:
                self.container_quote_run += 1
                if self.container_quote_run == 3:
                    self._clear_container_quote()
                return True
            self.container_quote_run = 0
            return True

        if self.container_quote_escaped:
            self.container_quote_escaped = False
            return True
        if character == "\\":
            self.container_quote_escaped = True
            return True
        if character == self.container_quote:
            self._clear_container_quote()
        return True

    def _update_container_context(self, character):
        if self.container_line_comment:
            if character in "\r\n":
                self.container_line_comment = False
                self._append_container_recent(character)
            return

        if self.container_block_comment:
            if self.container_block_comment_star and character == "/":
                self.container_block_comment = False
                self.container_block_comment_star = False
                self._append_container_recent(" ")
                return
            self.container_block_comment_star = character == "*"
            return

        if self.container_quote is not None:
            if self._consume_container_quote(character):
                return

        if self.container_pending_slash:
            self.container_pending_slash = False
            if character == "/":
                self.container_line_comment = True
                self._append_container_recent(" ")
                return
            if character == "*":
                self.container_block_comment = True
                self.container_block_comment_star = False
                self._append_container_recent(" ")
                return
            self._append_container_recent("/")

        if character == "/":
            self.container_pending_slash = True
            return
        if character == "#":
            self.container_line_comment = True
            self._append_container_recent(" ")
            return
        if character in {'"', "'", "`"}:
            self._start_container_quote(character)
            return
        if character in "([{":
            if len(self.container_stack) >= MAX_CREDENTIAL_CONTAINER_DEPTH:
                self.live_credential_found = True
                return
            parameter_context = (
                character == "("
                and PARAMETER_LIST_PREFIX.search(
                    "".join(self.container_recent_characters)
                )
                is not None
            )
            self.container_stack.append((character, parameter_context))
            self._append_container_recent(character)
            return
        expected_opener = {")": "(", "]": "[", "}": "{"}.get(character)
        if expected_opener is not None:
            if (
                self.container_stack
                and self.container_stack[-1][0] == expected_opener
            ):
                self.container_stack.pop()
            else:
                self.container_stack.clear()
        self._append_container_recent(character)


def _scan_archive_member_stream(
    stream,
    label,
    max_bytes=None,
    *,
    reject_u2014=False,
    template_value_predicate=None,
):
    strict_decoder = codecs.getincrementaldecoder("utf-8-sig")("strict")
    scanner_decoder = codecs.getincrementaldecoder("utf-8-sig")("replace")
    binary_overlap = b""
    jwt_scanner = _JwtShapeScanner()
    credential_scanner = _CredentialAssignmentScanner(template_value_predicate)
    text_valid = True
    text_line_too_long = False
    current_line_size = 0
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

        combined = binary_overlap + chunk
        if reject_u2014 and U2014_BYTES in combined:
            raise ValueError(f"U+2014 found in {label}")
        if PRIVATE_KEY_HEADER.search(combined):
            raise ValueError(f"private-key header found in {label}")
        jwt_scanner.feed(chunk)
        if jwt_scanner.found:
            raise ValueError(f"JWT-shaped token found in {label}")
        binary_overlap = combined[-STREAM_OVERLAP_SIZE:]

        credential_scanner.feed(scanner_decoder.decode(chunk, final=False))

        if not text_valid:
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
            strict_decoder.decode(chunk, final=False)
        except UnicodeDecodeError:
            text_valid = False
            continue

    credential_scanner.feed(scanner_decoder.decode(b"", final=True))
    if jwt_scanner.finish():
        raise ValueError(f"JWT-shaped token found in {label}")
    if credential_scanner.finish():
        raise ValueError(f"credential assignment found in {label}")
    if text_valid:
        try:
            strict_decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            text_valid = False
    if text_valid:
        text_line_too_long |= current_line_size > MAX_TEXT_LINE_SIZE
        if text_line_too_long:
            raise ValueError(f"text line exceeds the byte limit in {label}")
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


def _hash_zip_member(archive, name, label, hash_name="sha256"):
    info = archive.getinfo(name)
    digest = hashlib.new(hash_name)
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


def _canonicalize_curseforge_modlist(payload):
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ValueError("CurseForge mod list is not valid UTF-8") from error
    if (
        len(lines) < 2
        or lines[0] != "<ul>"
        or lines[-1] != "</ul>"
        or any(
            not line.startswith("<li>") or not line.endswith("</li>")
            for line in lines[1:-1]
        )
    ):
        raise ValueError("CurseForge mod list has an unexpected structure")
    sorted_entries = sorted(lines[1:-1])
    return (
        "<ul>\r\n" + "\r\n".join(sorted_entries) + "\r\n</ul>\r\n"
    ).encode("utf-8")


def _canonical_curseforge_members(archive, names):
    if CURSEFORGE_MANIFEST_NAME not in names:
        return {}
    try:
        manifest = json.loads(
            _read_bounded_zip_member(
                archive,
                CURSEFORGE_MANIFEST_NAME,
                "CurseForge manifest",
                MAX_MANIFEST_SIZE,
            )
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if (
        not isinstance(manifest, dict)
        or manifest.get("manifestType") != "minecraftModpack"
    ):
        return {}

    files = manifest.get("files")
    _validate_curseforge_files(files)
    canonical_manifest = dict(manifest)
    canonical_manifest["files"] = sorted(
        files,
        key=lambda record: (
            record["projectID"],
            record["fileID"],
            record["required"],
        ),
    )
    canonical_members = {
        CURSEFORGE_MANIFEST_NAME: _canonical_json_bytes(canonical_manifest),
    }
    if CURSEFORGE_MODLIST_NAME in names:
        canonical_members[CURSEFORGE_MODLIST_NAME] = (
            _canonicalize_curseforge_modlist(
                _read_bounded_zip_member(
                    archive,
                    CURSEFORGE_MODLIST_NAME,
                    "CurseForge mod list",
                    MAX_MANIFEST_SIZE,
                )
            )
        )
    return canonical_members


def normalize_launcher_archive(archive_path):
    archive_path = Path(archive_path)
    _require_regular_file(archive_path, "launcher archive")
    with tempfile.NamedTemporaryFile(
        prefix=f".{archive_path.name}.",
        suffix=".tmp",
        dir=archive_path.parent,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        with zipfile.ZipFile(archive_path) as source_archive:
            source_infos, _ = _inspect_zip_safety(
                source_archive,
                allow_directories=True,
            )
            source_files = sorted(
                (info for info in source_infos if not info.is_dir()),
                key=lambda info: info.filename,
            )
            if not source_files:
                raise ValueError("launcher archive contains no files")
            source_names = tuple(info.filename for info in source_files)
            canonical_members = _canonical_curseforge_members(
                source_archive,
                source_names,
            )

            with zipfile.ZipFile(
                temporary_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=DEFLATE_LEVEL,
                strict_timestamps=True,
            ) as normalized_archive:
                for source_info in source_files:
                    target_info = _normalized_zip_info(source_info.filename)
                    canonical_payload = canonical_members.get(source_info.filename)
                    if canonical_payload is not None:
                        normalized_archive.writestr(
                            target_info,
                            canonical_payload,
                            compress_type=zipfile.ZIP_DEFLATED,
                            compresslevel=DEFLATE_LEVEL,
                        )
                        continue
                    target_info.file_size = source_info.file_size
                    written_size = 0
                    with source_archive.open(source_info, "r") as source_member:
                        with normalized_archive.open(target_info, "w") as target_member:
                            while chunk := source_member.read(STREAM_CHUNK_SIZE):
                                target_member.write(chunk)
                                written_size += len(chunk)
                    if written_size != source_info.file_size:
                        raise ValueError(
                            "launcher archive member size changed during normalization: "
                            f"{source_info.filename!r}"
                        )

        temporary_path.chmod(0o644)
        with temporary_path.open("rb") as normalized_file:
            os.fsync(normalized_file.fileno())

        expected_names = source_names
        with zipfile.ZipFile(temporary_path) as normalized_archive:
            normalized_infos, normalized_names = _inspect_zip_safety(
                normalized_archive,
                allow_directories=False,
            )
            if tuple(normalized_names) != expected_names:
                raise ValueError("normalized launcher archive inventory changed")
            for info in normalized_infos:
                _validate_zip_metadata(info)

        os.replace(temporary_path, archive_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return {
        "archive": str(archive_path),
        "entry_count": len(source_files),
        "sha256": _sha256_file(archive_path),
    }


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


def inspect_modrinth_archive(
    archive_path,
    version,
    pack_root=None,
    git_sha=None,
):
    if (pack_root is None) != (git_sha is None):
        raise ValueError("Modrinth Packwiz inspection requires pack root and git SHA")
    archive_path = Path(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        _, names = _inspect_zip_safety(archive, allow_directories=False)
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

    summary = _launcher_summary(archive_path, names, "modrinth")
    if pack_root is not None:
        with zipfile.ZipFile(archive_path) as archive:
            summary.update(
                _verify_modrinth_packwiz_completeness(
                    archive,
                    manifest,
                    pack_root,
                    version,
                    git_sha,
                )
            )
    return summary


def inspect_curseforge_archive(
    archive_path,
    version,
    pack_root=None,
    git_sha=None,
):
    if (pack_root is None) != (git_sha is None):
        raise ValueError("CurseForge Packwiz inspection requires pack root and git SHA")
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

    summary = _launcher_summary(archive_path, names, "curseforge")
    if pack_root is not None:
        with zipfile.ZipFile(archive_path) as archive:
            summary.update(
                _verify_curseforge_packwiz_completeness(
                    archive,
                    manifest,
                    pack_root,
                    version,
                    git_sha,
                )
            )
    return summary


def _tracked_paths(root_path):
    result = subprocess.run(
        ["git", "-C", str(root_path), "ls-files", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_object_environment(),
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
        env=_git_object_environment(),
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


def _tracked_commit_entries(root_path, git_sha):
    if not re.fullmatch(r"[0-9a-f]{40}", git_sha):
        raise ValueError("Packwiz commit SHA must be exactly 40 lowercase hexadecimal characters")
    commit_result = subprocess.run(
        [
            "git",
            "-C",
            str(root_path),
            "rev-parse",
            "--verify",
            f"{git_sha}^{{commit}}",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_object_environment(),
    )
    if commit_result.returncode != 0:
        error = commit_result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Packwiz commit is unavailable: {error or 'unknown error'}")
    resolved_commit = commit_result.stdout.decode("ascii", errors="strict").strip()
    if resolved_commit != git_sha:
        raise ValueError("Packwiz git SHA does not identify the exact commit")

    result = subprocess.run(
        [
            "git",
            "-C",
            str(root_path),
            "ls-tree",
            "-rz",
            "--full-tree",
            git_sha,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_git_object_environment(),
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git ls-tree failed: {error or 'unknown error'}")
    if result.stdout and not result.stdout.endswith(b"\0"):
        raise ValueError("git ls-tree returned a malformed NUL-delimited inventory")

    entries = []
    seen_paths = set()
    for record in result.stdout.split(b"\0")[:-1] if result.stdout else []:
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.split(b" ")
        except ValueError as error:
            raise ValueError("git ls-tree returned a malformed entry") from error
        if mode not in {b"100644", b"100755", b"120000"} or object_type != b"blob":
            raise ValueError(f"tracked commit entry is not blob-backed: {raw_path!r}")
        if not re.fullmatch(rb"(?:[0-9a-f]{40}|[0-9a-f]{64})", object_id):
            raise ValueError(f"tracked commit object ID is malformed: {raw_path!r}")
        if raw_path in seen_paths:
            raise ValueError("git ls-tree returned duplicate tracked paths")
        seen_paths.add(raw_path)
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
        entries.append((relative_path, object_id.decode("ascii")))
    return entries


def _resolve_repository_root(root, label):
    root_path = Path(root)
    try:
        root_status = root_path.lstat()
    except OSError as error:
        raise ValueError(f"{label} is unreadable: {root_path}") from error
    if not stat.S_ISDIR(root_status.st_mode):
        raise ValueError(f"{label} is not a directory: {root_path}")
    return root_path.resolve(strict=True)


def _git_object_environment():
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return environment


def _start_tracked_blob(root_path, relative_path, object_id):
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
        env=_git_object_environment(),
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        raise ValueError(f"cannot read tracked index blob: {relative_path!r}")
    return process


def _read_tracked_blob(root_path, relative_path, object_id, size_limit):
    process = _start_tracked_blob(root_path, relative_path, object_id)
    try:
        data = process.stdout.read(size_limit + 1)
        if len(data) > size_limit:
            process.kill()
            process.wait()
            raise ValueError(
                f"tracked Packwiz metadata exceeds the bounded read limit: "
                f"{relative_path!r}"
            )
        error = process.stderr.read(size_limit + 1).decode(
            "utf-8",
            errors="replace",
        ).strip()
        returncode = process.wait()
    except BaseException:
        if process.poll() is None:
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
    return data


def _hash_tracked_blob(root_path, relative_path, object_id, hash_name):
    process = _start_tracked_blob(root_path, relative_path, object_id)
    digest = hashlib.new(hash_name)
    try:
        while chunk := process.stdout.read(STREAM_CHUNK_SIZE):
            digest.update(chunk)
        error = process.stderr.read(MAX_PACKWIZ_METADATA_SIZE + 1).decode(
            "utf-8",
            errors="replace",
        ).strip()
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
    return digest.hexdigest()


def _parse_packwiz_toml(data, label):
    try:
        document = tomllib.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"{label} is not valid UTF-8 TOML") from error
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be a TOML table")
    return document


def _packwiz_hash_name(value, label):
    if value not in {"sha1", "sha256", "sha512"}:
        raise ValueError(f"{label} uses an unsupported hash format")
    return value


def _validate_packwiz_hash(value, hash_name, label):
    digest_size = hashlib.new(hash_name).digest_size * 2
    if not isinstance(value, str) or not re.fullmatch(
        rf"[0-9a-f]{{{digest_size}}}",
        value,
    ):
        raise ValueError(f"{label} has an invalid {hash_name.upper()} hash")
    return value


def _tracked_packwiz_inventory(pack_root, version, git_sha):
    root_path = _resolve_repository_root(pack_root, "Packwiz source root")
    tracked_blobs = dict(_tracked_commit_entries(root_path, git_sha))

    def tracked_object_id(relative_path):
        object_id = tracked_blobs.get(relative_path)
        if object_id is None:
            raise ValueError(f"tracked Packwiz source is missing: {relative_path!r}")
        return object_id

    pack_path = "pack.toml"
    pack = _parse_packwiz_toml(
        _read_tracked_blob(
            root_path,
            pack_path,
            tracked_object_id(pack_path),
            MAX_PACKWIZ_METADATA_SIZE,
        ),
        "tracked pack.toml",
    )
    if pack.get("name") != EXPECTED_PACK_NAME:
        raise ValueError("tracked Packwiz pack name does not match AFTERLIGHT")
    if pack.get("version") != version:
        raise ValueError("tracked Packwiz version does not match the archive")
    versions = pack.get("versions")
    if not isinstance(versions, dict):
        raise ValueError("tracked Packwiz loader identity is invalid")
    if versions.get("minecraft") != PRISM_MINECRAFT_VERSION:
        raise ValueError("tracked Packwiz Minecraft version does not match")
    if versions.get("neoforge") != PRISM_NEOFORGE_VERSION:
        raise ValueError("tracked Packwiz NeoForge version does not match")

    index_reference = pack.get("index")
    if not isinstance(index_reference, dict):
        raise ValueError("tracked Packwiz index reference is invalid")
    index_path = index_reference.get("file")
    if not isinstance(index_path, str):
        raise ValueError("tracked Packwiz index path is invalid")
    try:
        index_path = _validate_archive_name(index_path, windows_safe=False)
    except ValueError as error:
        raise ValueError("tracked Packwiz index path is invalid") from error
    index_reference_hash_name = _packwiz_hash_name(
        index_reference.get("hash-format"),
        "tracked Packwiz index reference",
    )
    index_reference_hash = _validate_packwiz_hash(
        index_reference.get("hash"),
        index_reference_hash_name,
        "tracked Packwiz index reference",
    )
    index_bytes = _read_tracked_blob(
        root_path,
        index_path,
        tracked_object_id(index_path),
        MAX_PACKWIZ_METADATA_SIZE,
    )
    if hashlib.new(index_reference_hash_name, index_bytes).hexdigest() != (
        index_reference_hash
    ):
        raise ValueError("tracked Packwiz index hash does not match pack.toml")

    index = _parse_packwiz_toml(index_bytes, "tracked Packwiz index")
    index_hash_name = _packwiz_hash_name(
        index.get("hash-format"),
        "tracked Packwiz index",
    )
    file_records = index.get("files")
    if not isinstance(file_records, list) or not file_records:
        raise ValueError("tracked Packwiz index files are invalid")

    authored_files = {}
    all_mods = []
    client_mods = []
    seen_index_paths = set()
    seen_index_collisions = set()
    seen_mod_filenames = set()
    seen_curseforge_records = set()
    seen_modrinth_records = set()
    signal_mod = None
    server_mod_count = 0
    for record in file_records:
        if not isinstance(record, dict) or not {"file", "hash"}.issubset(record):
            raise ValueError("tracked Packwiz index file record is invalid")
        if set(record) - {"file", "hash", "metafile", "preserve"}:
            raise ValueError("tracked Packwiz index file record is invalid")
        relative_path = record["file"]
        if not isinstance(relative_path, str):
            raise ValueError("tracked Packwiz index file path is invalid")
        try:
            relative_path = _validate_archive_name(
                relative_path,
                windows_safe=False,
            )
        except ValueError as error:
            raise ValueError("tracked Packwiz index file path is invalid") from error
        collision_key = _windows_collision_key(relative_path)
        if relative_path in seen_index_paths or collision_key in seen_index_collisions:
            raise ValueError(f"tracked Packwiz index path is duplicated: {relative_path!r}")
        seen_index_paths.add(relative_path)
        seen_index_collisions.add(collision_key)
        expected_hash = _validate_packwiz_hash(
            record["hash"],
            index_hash_name,
            f"tracked Packwiz index record {relative_path!r}",
        )
        metafile = record.get("metafile", False)
        if type(metafile) is not bool:
            raise ValueError("tracked Packwiz metafile flag is invalid")
        if "preserve" in record and type(record["preserve"]) is not bool:
            raise ValueError("tracked Packwiz preserve flag is invalid")
        object_id = tracked_object_id(relative_path)

        if not metafile:
            actual_hash = _hash_tracked_blob(
                root_path,
                relative_path,
                object_id,
                index_hash_name,
            )
            if actual_hash != expected_hash:
                raise ValueError(
                    f"tracked Packwiz source hash mismatch: {relative_path!r}"
                )
            authored_files[relative_path] = {
                "hash": expected_hash,
                "hash_name": index_hash_name,
            }
            continue

        if not relative_path.startswith("mods/") or not relative_path.endswith(
            ".pw.toml"
        ):
            raise ValueError(
                f"unsupported tracked Packwiz metafile: {relative_path!r}"
            )
        metadata_bytes = _read_tracked_blob(
            root_path,
            relative_path,
            object_id,
            MAX_PACKWIZ_METADATA_SIZE,
        )
        if hashlib.new(index_hash_name, metadata_bytes).hexdigest() != expected_hash:
            raise ValueError(
                f"tracked Packwiz source hash mismatch: {relative_path!r}"
            )
        metadata = _parse_packwiz_toml(
            metadata_bytes,
            f"tracked Packwiz mod metadata {relative_path!r}",
        )
        side = metadata.get("side")
        if side not in {"client", "server", "both"}:
            raise ValueError(
                f"tracked Packwiz mod side is not deliberate: {relative_path!r}"
            )
        name = metadata.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"tracked Packwiz mod name is invalid: {relative_path!r}")
        filename = metadata.get("filename")
        if (
            not isinstance(filename, str)
            or PurePosixPath(filename).name != filename
            or not filename.casefold().endswith(".jar")
        ):
            raise ValueError(
                f"tracked Packwiz mod filename is invalid: {relative_path!r}"
            )
        try:
            _validate_archive_name(f"mods/{filename}")
        except ValueError as error:
            raise ValueError(
                f"tracked Packwiz mod filename is invalid: {relative_path!r}"
            ) from error
        filename_collision = _windows_collision_key(filename)
        if filename_collision in seen_mod_filenames:
            raise ValueError(f"tracked Packwiz mod filename is duplicated: {filename!r}")
        seen_mod_filenames.add(filename_collision)

        download = metadata.get("download")
        if not isinstance(download, dict):
            raise ValueError(
                f"tracked Packwiz mod download is invalid: {relative_path!r}"
            )
        mod_hash_name = _packwiz_hash_name(
            download.get("hash-format"),
            f"tracked Packwiz mod {relative_path!r}",
        )
        mod_hash = _validate_packwiz_hash(
            download.get("hash"),
            mod_hash_name,
            f"tracked Packwiz mod {relative_path!r}",
        )
        download_url = download.get("url")
        if download_url is not None:
            if not isinstance(download_url, str) or not download_url:
                raise ValueError(
                    f"tracked Packwiz mod download URL is invalid: {relative_path!r}"
                )
            try:
                parsed_download = urlsplit(download_url)
            except ValueError as error:
                raise ValueError(
                    f"tracked Packwiz mod download URL is invalid: {relative_path!r}"
                ) from error
            if (
                parsed_download.scheme != "https"
                or not parsed_download.hostname
                or parsed_download.username is not None
                or parsed_download.password is not None
                or any(character.isspace() for character in download_url)
            ):
                raise ValueError(
                    f"tracked Packwiz mod download URL is invalid: {relative_path!r}"
                )

        curseforge_record = None
        update = metadata.get("update", {})
        if not isinstance(update, dict):
            raise ValueError(
                f"tracked Packwiz update metadata is invalid: {relative_path!r}"
            )
        curseforge = update.get("curseforge")
        if curseforge is not None:
            if not isinstance(curseforge, dict):
                raise ValueError(
                    f"tracked CurseForge metadata is invalid: {relative_path!r}"
                )
            project_id = curseforge.get("project-id")
            file_id = curseforge.get("file-id")
            if (
                type(project_id) is not int
                or not 1 <= project_id <= MAX_UNSIGNED_32
                or type(file_id) is not int
                or not 1 <= file_id <= MAX_UNSIGNED_32
            ):
                raise ValueError(
                    f"tracked CurseForge metadata is invalid: {relative_path!r}"
                )
            curseforge_record = (project_id, file_id)
            if curseforge_record in seen_curseforge_records:
                raise ValueError("tracked CurseForge project and file record is duplicated")
            seen_curseforge_records.add(curseforge_record)

        modrinth_record = None
        modrinth = update.get("modrinth")
        if modrinth is not None:
            if not isinstance(modrinth, dict) or set(modrinth) != {
                "mod-id",
                "version",
            }:
                raise ValueError(
                    f"tracked Modrinth metadata is invalid: {relative_path!r}"
                )
            mod_id = modrinth.get("mod-id")
            version_id = modrinth.get("version")
            if (
                not isinstance(mod_id, str)
                or not mod_id
                or not isinstance(version_id, str)
                or not version_id
            ):
                raise ValueError(
                    f"tracked Modrinth metadata is invalid: {relative_path!r}"
                )
            modrinth_record = (mod_id, version_id)
            if modrinth_record in seen_modrinth_records:
                raise ValueError("tracked Modrinth project and version is duplicated")
            seen_modrinth_records.add(modrinth_record)
        if curseforge_record is None and download_url is None:
            raise ValueError(
                f"tracked Packwiz mod download URL is missing: {relative_path!r}"
            )

        mod = {
            "curseforge_record": curseforge_record,
            "download_url": download_url,
            "filename": filename,
            "hash": mod_hash,
            "hash_name": mod_hash_name,
            "metadata_path": relative_path,
            "modrinth_record": modrinth_record,
            "name": name,
            "override_path": f"overrides/mods/{filename}",
            "side": side,
        }
        if relative_path == "mods/afterlight-signal.pw.toml":
            signal_mod = mod
        all_mods.append(mod)
        if side == "server":
            server_mod_count += 1
        else:
            client_mods.append(mod)

    if signal_mod is None or signal_mod["side"] == "server":
        raise ValueError("tracked AFTERLIGHT Signal client metadata is missing")
    if signal_mod["hash_name"] != "sha512":
        raise ValueError("AFTERLIGHT Signal metadata must use SHA-512")

    lock_bytes = _read_tracked_blob(
        root_path,
        MODRINTH_MANIFEST_LOCK_PATH,
        tracked_object_id(MODRINTH_MANIFEST_LOCK_PATH),
        MAX_PACKWIZ_METADATA_SIZE,
    )
    try:
        manifest_lock = json.loads(lock_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("tracked Modrinth manifest lock is not valid UTF-8 JSON") from error
    if not isinstance(manifest_lock, dict) or set(manifest_lock) != {
        "files",
        "format",
    }:
        raise ValueError("tracked Modrinth manifest lock shape is invalid")
    if type(manifest_lock["format"]) is not int or manifest_lock["format"] != 1:
        raise ValueError("tracked Modrinth manifest lock format is unsupported")
    lock_records = manifest_lock["files"]
    if not isinstance(lock_records, list) or not lock_records:
        raise ValueError("tracked Modrinth manifest lock files are invalid")

    direct_mods = {
        mod["metadata_path"]: mod
        for mod in all_mods
        if mod["curseforge_record"] is None
    }
    seen_lock_metadata_paths = set()
    seen_lock_archive_paths = set()
    for record in lock_records:
        if not isinstance(record, dict) or set(record) != {
            "downloads",
            "fileSize",
            "hashes",
            "metadata_path",
            "path",
        }:
            raise ValueError("tracked Modrinth manifest lock record shape is invalid")
        metadata_path = record["metadata_path"]
        if not isinstance(metadata_path, str) or metadata_path not in direct_mods:
            raise ValueError(
                "tracked Modrinth manifest lock metadata path is invalid"
            )
        if metadata_path in seen_lock_metadata_paths:
            raise ValueError(
                "tracked Modrinth manifest lock metadata path is duplicated"
            )
        seen_lock_metadata_paths.add(metadata_path)
        mod = direct_mods[metadata_path]
        expected_archive_path = f"mods/{mod['filename']}"
        if record["path"] != expected_archive_path:
            raise ValueError(
                f"tracked Modrinth manifest lock path mismatch: {metadata_path!r}"
            )
        archive_collision = _windows_collision_key(expected_archive_path)
        if archive_collision in seen_lock_archive_paths:
            raise ValueError("tracked Modrinth manifest lock path is duplicated")
        seen_lock_archive_paths.add(archive_collision)
        if record["downloads"] != [mod["download_url"]]:
            raise ValueError(
                f"tracked Modrinth manifest lock URL mismatch: {metadata_path!r}"
            )
        hashes = record["hashes"]
        if not isinstance(hashes, dict) or set(hashes) != {"sha1", "sha512"}:
            raise ValueError(
                f"tracked Modrinth manifest lock hashes are invalid: {metadata_path!r}"
            )
        sha1_hash = hashes["sha1"]
        sha512_hash = hashes["sha512"]
        if not isinstance(sha1_hash, str) or not re.fullmatch(
            r"[0-9a-f]{40}", sha1_hash
        ):
            raise ValueError(
                f"tracked Modrinth manifest lock SHA-1 is invalid: {metadata_path!r}"
            )
        if mod["hash_name"] != "sha512" or sha512_hash != mod["hash"]:
            raise ValueError(
                f"tracked Modrinth manifest lock SHA-512 mismatch: {metadata_path!r}"
            )
        file_size = record["fileSize"]
        if type(file_size) is not int or not 1 <= file_size <= MAX_UNSIGNED_32:
            raise ValueError(
                f"tracked Modrinth manifest lock file size is invalid: {metadata_path!r}"
            )
        mod["manifest_sha1"] = sha1_hash
        mod["manifest_file_size"] = file_size

    missing_lock_records = sorted(set(direct_mods) - seen_lock_metadata_paths)
    if missing_lock_records:
        raise ValueError(
            "tracked Modrinth manifest lock is missing: "
            f"{missing_lock_records[0]!r}"
        )

    expected_collisions = {
        _windows_collision_key(f"overrides/{path}") for path in authored_files
    }
    for mod in all_mods:
        collision_key = _windows_collision_key(mod["override_path"])
        if collision_key in expected_collisions:
            raise ValueError(
                f"tracked Packwiz client path is duplicated: {mod['override_path']!r}"
            )
        expected_collisions.add(collision_key)

    return {
        "all_mods": all_mods,
        "authored_files": authored_files,
        "client_mods": client_mods,
        "root": root_path,
        "server_mod_count": server_mod_count,
    }


def _expected_modrinth_environment(side):
    if side == "both":
        return {"client": "required", "server": "required"}
    if side == "client":
        return {"client": "required", "server": "unsupported"}
    if side == "server":
        return {"client": "unsupported", "server": "required"}
    raise ValueError(f"invalid Modrinth side: {side!r}")


def _verify_modrinth_packwiz_completeness(
    archive,
    manifest,
    pack_root,
    version,
    git_sha,
):
    inventory = _tracked_packwiz_inventory(pack_root, version, git_sha)
    archive_names = {info.filename for info in archive.infolist()}
    manifest_records = {record["path"]: record for record in manifest["files"]}
    consumed_records = set()
    consumed_overrides = set()

    for relative_path, expected in inventory["authored_files"].items():
        archive_name = f"overrides/{relative_path}"
        if archive_name not in archive_names:
            raise ValueError(f"missing authored override: {relative_path!r}")
        actual_hash, _ = _hash_zip_member(
            archive,
            archive_name,
            f"authored override {relative_path!r}",
            expected["hash_name"],
        )
        if actual_hash != expected["hash"]:
            raise ValueError(f"authored override hash mismatch: {relative_path!r}")
        consumed_overrides.add(archive_name)

    for mod in inventory["all_mods"]:
        record_path = f"mods/{mod['filename']}"
        record = manifest_records.get(record_path)
        embedded_path = mod["override_path"]
        embedded = embedded_path in archive_names
        expects_record = mod["curseforge_record"] is None
        if expects_record:
            if record is None:
                raise ValueError(f"missing client mod: {mod['name']}")
            if embedded:
                raise ValueError(
                    f"duplicate client mod representation: {mod['name']}"
                )
            if record["hashes"]["sha512"] != mod["hash"]:
                if mod["metadata_path"] == "mods/afterlight-signal.pw.toml":
                    raise ValueError("AFTERLIGHT Signal SHA-512 mismatch")
                raise ValueError(
                    f"Modrinth file SHA-512 mismatch: {mod['metadata_path']!r}"
                )
            if record["hashes"]["sha1"] != mod["manifest_sha1"]:
                raise ValueError(
                    f"Modrinth file SHA-1 mismatch: {mod['metadata_path']!r}"
                )
            if record["fileSize"] != mod["manifest_file_size"]:
                raise ValueError(
                    f"Modrinth file size mismatch: {mod['metadata_path']!r}"
                )
            if record["downloads"] != [mod["download_url"]]:
                raise ValueError(
                    f"Modrinth download URL mismatch: {mod['metadata_path']!r}"
                )
            if record["env"] != _expected_modrinth_environment(mod["side"]):
                raise ValueError(
                    f"Modrinth environment mismatch: {mod['metadata_path']!r}"
                )
            consumed_records.add(record_path)
            continue

        if record is not None:
            raise ValueError(f"duplicate client mod representation: {mod['name']}")
        if not embedded:
            raise ValueError(f"missing embedded mod: {mod['name']}")
        actual_hash, _ = _hash_zip_member(
            archive,
            embedded_path,
            f"embedded mod {mod['metadata_path']!r}",
            mod["hash_name"],
        )
        if actual_hash != mod["hash"]:
            raise ValueError(
                f"embedded mod hash mismatch: {mod['metadata_path']!r}"
            )
        consumed_overrides.add(embedded_path)

    extra_records = sorted(set(manifest_records) - consumed_records)
    if extra_records:
        raise ValueError(f"extra Modrinth file record: {extra_records[0]!r}")
    allowed_names = {MODRINTH_MANIFEST_NAME, *consumed_overrides}
    extra_names = sorted(archive_names - allowed_names)
    if extra_names:
        if extra_names[0].startswith("overrides/"):
            raise ValueError(f"extra override file: {extra_names[0]!r}")
        raise ValueError(f"extra Modrinth archive file: {extra_names[0]!r}")

    return {
        "packwiz_authored_file_count": len(inventory["authored_files"]),
        "packwiz_client_mod_count": len(inventory["client_mods"]),
        "packwiz_server_mod_count": inventory["server_mod_count"],
    }


def _verify_curseforge_packwiz_completeness(
    archive,
    manifest,
    pack_root,
    version,
    git_sha,
):
    inventory = _tracked_packwiz_inventory(pack_root, version, git_sha)
    directory_names = sorted(
        info.filename for info in archive.infolist() if info.is_dir()
    )
    if directory_names:
        raise ValueError(
            f"extra CurseForge directory entry: {directory_names[0]!r}"
        )
    archive_names = {
        info.filename for info in archive.infolist() if not info.is_dir()
    }
    manifest_records = {
        (record["projectID"], record["fileID"]): record
        for record in manifest["files"]
    }
    embedded_mod_names = {
        name
        for name in archive_names
        if name.startswith("overrides/mods/") and name.casefold().endswith(".jar")
    }
    consumed_records = set()
    consumed_overrides = set()

    for relative_path, expected in inventory["authored_files"].items():
        archive_name = f"overrides/{relative_path}"
        if archive_name not in archive_names:
            raise ValueError(f"missing authored override: {relative_path!r}")
        actual_hash, _ = _hash_zip_member(
            archive,
            archive_name,
            f"authored override {relative_path!r}",
            expected["hash_name"],
        )
        if actual_hash != expected["hash"]:
            raise ValueError(
                f"authored override SHA-256 mismatch: {relative_path!r}"
            )
        consumed_overrides.add(archive_name)

    for mod in inventory["client_mods"]:
        curseforge_record = mod["curseforge_record"]
        has_record = (
            curseforge_record is not None and curseforge_record in manifest_records
        )
        has_embedded_jar = mod["override_path"] in embedded_mod_names
        if has_record and manifest_records[curseforge_record]["required"] is not True:
            raise ValueError(
                f"CurseForge client mod must be required: {mod['metadata_path']!r}"
            )
        if has_embedded_jar:
            actual_hash, _ = _hash_zip_member(
                archive,
                mod["override_path"],
                f"embedded mod {mod['metadata_path']!r}",
                mod["hash_name"],
            )
            if actual_hash != mod["hash"]:
                if mod["metadata_path"] == "mods/afterlight-signal.pw.toml":
                    raise ValueError("AFTERLIGHT Signal SHA-512 mismatch")
                raise ValueError(
                    f"embedded mod hash mismatch: {mod['metadata_path']!r}"
                )
        if mod["metadata_path"] == "mods/afterlight-signal.pw.toml" and not (
            has_embedded_jar
        ):
            raise ValueError("missing client mod: AFTERLIGHT Signal")
        representation_count = int(has_record) + int(has_embedded_jar)
        if representation_count == 0:
            raise ValueError(f"missing client mod: {mod['name']}")
        if representation_count != 1:
            raise ValueError(
                f"duplicate client mod representation: {mod['name']}"
            )
        if has_record:
            consumed_records.add(curseforge_record)
        if has_embedded_jar:
            consumed_overrides.add(mod["override_path"])

    extra_records = sorted(set(manifest_records) - consumed_records)
    if extra_records:
        raise ValueError("extra CurseForge file record")
    extra_embedded_mods = sorted(embedded_mod_names - consumed_overrides)
    if extra_embedded_mods:
        raise ValueError(f"extra embedded mod: {extra_embedded_mods[0]!r}")

    allowed_names = {
        CURSEFORGE_MANIFEST_NAME,
        *consumed_overrides,
    }
    if CURSEFORGE_MODLIST_NAME in archive_names:
        allowed_names.add(CURSEFORGE_MODLIST_NAME)
    extra_names = sorted(archive_names - allowed_names)
    if extra_names:
        if extra_names[0].startswith("overrides/"):
            raise ValueError(f"extra override file: {extra_names[0]!r}")
        raise ValueError(f"extra CurseForge archive file: {extra_names[0]!r}")

    return {
        "packwiz_authored_file_count": len(inventory["authored_files"]),
        "packwiz_client_mod_count": len(inventory["client_mods"]),
        "packwiz_server_mod_count": inventory["server_mod_count"],
    }


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
        env=_git_object_environment(),
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        raise ValueError(f"cannot read tracked index blob: {relative_path!r}")

    try:
        _scan_archive_member_stream(
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
    pack_root,
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
        pack_root,
        git_sha,
    )
    modrinth = inspect_modrinth_archive(
        dist_path / MRPACK_ARTIFACT_NAME,
        version,
        pack_root,
        git_sha,
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
    modrinth_parser.add_argument("--pack-root")
    modrinth_parser.add_argument("--git-sha")

    curseforge_parser = subparsers.add_parser("inspect-curseforge")
    curseforge_parser.add_argument("--archive", required=True)
    curseforge_parser.add_argument("--version", required=True)
    curseforge_parser.add_argument("--pack-root")
    curseforge_parser.add_argument("--git-sha")

    normalize_parser = subparsers.add_parser("normalize-archive")
    normalize_parser.add_argument("--archive", required=True)

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
    verifier_parser.add_argument("--pack-root", required=True)
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
        summary = inspect_modrinth_archive(
            args.archive,
            args.version,
            args.pack_root,
            args.git_sha,
        )
        print(json.dumps(summary, sort_keys=True))
        return 0

    if args.command == "inspect-curseforge":
        summary = inspect_curseforge_archive(
            args.archive,
            args.version,
            args.pack_root,
            args.git_sha,
        )
        print(json.dumps(summary, sort_keys=True))
        return 0

    if args.command == "normalize-archive":
        summary = normalize_launcher_archive(args.archive)
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
            pack_root=args.pack_root,
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
