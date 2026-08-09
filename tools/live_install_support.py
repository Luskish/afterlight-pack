from __future__ import annotations

import hashlib
import os
import unittest
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, TypeVar


REQUIRE_LIVE_ENV = "AFTERLIGHT_REQUIRE_LIVE_TESTS"
LIVE_RUN_ID_ENV = "AFTERLIGHT_LIVE_RUN_ID"
READY_MARKER = PurePosixPath("afterlight-live-tests-ready.txt")
BASE_REQUIRED_PATHS = (
    PurePosixPath("packwiz.json"),
    PurePosixPath("afterlight-audit-nonce.txt"),
    PurePosixPath("afterlight-server-exit-status.txt"),
    PurePosixPath("logs/latest.log"),
    PurePosixPath("logs/debug.log"),
    PurePosixPath("boot.log"),
)


@dataclass(frozen=True)
class LiveInstallDecision:
    ready: bool
    reason: str


Decorated = TypeVar("Decorated", bound=Callable | type)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _not_ready(reason: str, require: bool) -> LiveInstallDecision:
    message = f"fresh authenticated server-test install unavailable: {reason}"
    if require:
        raise RuntimeError(f"{REQUIRE_LIVE_ENV}=1 but {message}")
    return LiveInstallDecision(False, message)


def live_install_decision(
    root: Path | str,
    *,
    require: bool | None = None,
    required_paths: tuple[PurePosixPath, ...] = (),
) -> LiveInstallDecision:
    require_live = (
        os.environ.get(REQUIRE_LIVE_ENV) == "1" if require is None else require
    )
    root_path = Path(root).resolve()
    install = root_path / "server-test"
    expected_run_id = os.environ.get(LIVE_RUN_ID_ENV, "")
    if not expected_run_id:
        return _not_ready(f"{LIVE_RUN_ID_ENV} is not set", require_live)
    marker = install / READY_MARKER
    if not marker.is_file():
        return _not_ready(f"missing {READY_MARKER.as_posix()}", require_live)
    try:
        marker_lines = marker.read_text(encoding="utf-8").splitlines()
        values = dict(line.split("=", 1) for line in marker_lines)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return _not_ready(f"invalid ready marker: {error}", require_live)
    if set(values) != {"run_id", "nonce", "pack_sha256", "index_sha256"}:
        return _not_ready("ready marker fields changed", require_live)
    if values["run_id"] != expected_run_id:
        return _not_ready("ready marker run ID is stale", require_live)
    nonce_path = install / "afterlight-audit-nonce.txt"
    try:
        nonce = nonce_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        return _not_ready(f"cannot read live nonce: {error}", require_live)
    if not nonce or nonce != values["nonce"]:
        return _not_ready("ready marker nonce is stale", require_live)
    for relative in BASE_REQUIRED_PATHS + required_paths:
        if not (install / relative).is_file():
            return _not_ready(f"missing {relative.as_posix()}", require_live)
    if _sha256(root_path / "pack.toml") != values["pack_sha256"]:
        return _not_ready("pack.toml changed after live authentication", require_live)
    if _sha256(root_path / "index.toml") != values["index_sha256"]:
        return _not_ready("index.toml changed after live authentication", require_live)
    return LiveInstallDecision(True, f"authenticated live run {expected_run_id}")


def requires_live_install(
    root: Path | str, *required_paths: str
) -> Callable[[Decorated], Decorated]:
    relative_paths = tuple(PurePosixPath(path) for path in required_paths)
    decision = live_install_decision(root, required_paths=relative_paths)
    if decision.ready:
        return lambda decorated: decorated
    return unittest.skip(decision.reason)
