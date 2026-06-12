"""Legacy-path compatibility shim for the .orchestrate/* flatten migration.

Before migration: ``.domain/``, ``.audit/``, ``.pipeline-state/`` lived at the
project root. After migration they live as subfolders of ``.orchestrate/``.
Any code that still references the legacy paths is routed here.

A single ``[DEPRECATED]`` warning is emitted per process per legacy root.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

LEGACY_TO_NEW: dict[str, str] = {
    ".domain": ".orchestrate/domain",
    ".audit": ".orchestrate/audit",
    ".pipeline-state": ".orchestrate/pipeline-state",
}

_WARNED: set[str] = set()


def _emit_deprecation(legacy_root: str, target_root: str) -> None:
    if legacy_root in _WARNED:
        return
    _WARNED.add(legacy_root)
    logger.warning(
        "[DEPRECATED] '%s/' is the legacy path; use '%s/' instead. "
        "Resolving via path_compat for backwards compatibility.",
        legacy_root,
        target_root,
    )


def resolve_legacy_path(path: str | Path) -> Path:
    """Translate a legacy-rooted path to its new ``.orchestrate/*`` equivalent.

    Examples:
        ``.domain/research_ledger.jsonl`` -> ``.orchestrate/domain/research_ledger.jsonl``
        ``.audit/findings-ledger.jsonl``  -> ``.orchestrate/audit/findings-ledger.jsonl``
        ``.pipeline-state/baselines/x``   -> ``.orchestrate/pipeline-state/baselines/x``

    Non-legacy paths pass through unchanged.
    """
    p = Path(path)
    parts = p.parts
    if not parts:
        return p
    first = parts[0]
    if first in LEGACY_TO_NEW:
        new_root = LEGACY_TO_NEW[first]
        _emit_deprecation(first, new_root)
        return Path(new_root, *parts[1:])
    return p


def is_legacy_path(path: str | Path) -> bool:
    """Return True if the path is rooted at a legacy folder."""
    p = Path(path)
    return bool(p.parts) and p.parts[0] in LEGACY_TO_NEW


def domain_dir(project_root: str | Path = ".") -> Path:
    """Canonical domain dir under ``project_root``."""
    root = Path(project_root)
    new = root / ".orchestrate" / "domain"
    if new.exists():
        return new
    legacy = root / ".domain"
    if legacy.exists():
        _emit_deprecation(".domain", ".orchestrate/domain")
        return legacy
    return new


def audit_dir(project_root: str | Path = ".") -> Path:
    """Canonical audit dir under ``project_root``."""
    root = Path(project_root)
    new = root / ".orchestrate" / "audit"
    if new.exists():
        return new
    legacy = root / ".audit"
    if legacy.exists():
        _emit_deprecation(".audit", ".orchestrate/audit")
        return legacy
    return new


def pipeline_state_dir(project_root: str | Path = ".") -> Path:
    """Canonical pipeline-state dir under ``project_root``."""
    root = Path(project_root)
    new = root / ".orchestrate" / "pipeline-state"
    if new.exists():
        return new
    legacy = root / ".pipeline-state"
    if legacy.exists():
        _emit_deprecation(".pipeline-state", ".orchestrate/pipeline-state")
        return legacy
    return new


def ensure_unified_layout(project_root: str | Path = ".") -> dict[str, Path]:
    """Create the unified ``.orchestrate/`` layout if missing.

    Returns a mapping of logical name -> absolute path for the four
    canonical roots.
    """
    root = Path(project_root)
    base = root / ".orchestrate"
    paths = {
        "orchestrate": base,
        "domain": base / "domain",
        "audit": base / "audit",
        "pipeline_state": base / "pipeline-state",
    }
    for p in paths.values():
        os.makedirs(p, exist_ok=True)
    for sub in ("workflow", "command-receipts", "process-log",
                "baselines", "improvement-recommender"):
        os.makedirs(paths["pipeline_state"] / sub, exist_ok=True)
    return paths
