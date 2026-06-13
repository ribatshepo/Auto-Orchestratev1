"""Shared JSON / JSONL file-I/O helpers for the ci_engine package.

Single source of truth for the atomic-write, append, and load primitives that
were previously duplicated (in divergent variants) across `baseline_manager`,
`improvement_recommender`, `knowledge_store_writer`, `retrospective_analyzer`,
and `ooda_controller`. The behavioural differences between those copies are
preserved here as explicit parameters rather than separate implementations:

* envelope unwrapping  -> ``peel`` callable (kept module-local; passed in)
* missing-file policy   -> ``missing_ok`` (read_jsonl) / ``default`` (load_json_safe)
* read-error policy     -> ``swallow`` (load_json_safe)

This module is pure I/O — it has no dependency on the artifact-envelope logic;
callers that need envelope peeling pass their own ``_peel`` as the ``peel`` arg.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


def atomic_write_json(target_path: Path, data: dict[str, Any]) -> None:
    """Write ``data`` as pretty JSON atomically (tmp-then-rename, with fsync).

    Robust superset of the prior variants: always creates the parent directory,
    uses a unique temp file (``tempfile.mkstemp``) to avoid concurrent-writer
    collisions, fsyncs before swapping, and uses ``os.replace`` for an atomic
    overwrite. Output bytes are identical to the legacy implementations.
    """
    os.makedirs(target_path.parent, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(dir=str(target_path.parent), suffix=".tmp")
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(str(tmp_path), str(target_path))
    except BaseException:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def append_jsonl(target_path: Path, record: dict[str, Any]) -> None:
    """Append a single JSON record to a JSONL file with flush and fsync."""
    os.makedirs(target_path.parent, exist_ok=True)
    with open(target_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False))
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())


def load_json_safe(
    path: Path,
    *,
    peel: Callable[[Any], Any] | None = None,
    swallow: bool = False,
    default: Any = None,
    missing_ok: bool = True,
) -> Any:
    """Load a JSON file.

    Missing file: returns ``default`` if ``missing_ok`` (default), else raises
    ``FileNotFoundError``. ``peel`` (when given) is applied to the parsed object
    — used by callers that store artifacts inside envelopes. ``swallow=True``
    logs and returns ``default`` on a JSON/OS error (of an existing file)
    instead of propagating it.
    """
    if not path.is_file():
        if missing_ok:
            return default
        raise FileNotFoundError(f"Required file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        if swallow:
            logger.warning("Failed to load %s: %s", path, exc)
            return default
        raise
    return peel(obj) if peel is not None else obj


def read_jsonl(
    path: Path,
    *,
    peel: Callable[[Any], Any] | None = None,
    missing_ok: bool = True,
) -> list[dict[str, Any]]:
    """Read JSONL records, skipping corrupt lines (with a warning).

    When the file is absent: returns ``[]`` if ``missing_ok`` (default), else
    raises ``FileNotFoundError``. ``peel`` (when given) is applied per record.
    """
    records: list[dict[str, Any]] = []
    if not path.is_file():
        if missing_ok:
            return records
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                logger.warning("Skipping corrupt JSONL line %d in %s", line_num, path)
                continue
            records.append(peel(obj) if peel is not None else obj)
    return records
