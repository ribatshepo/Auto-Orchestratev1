"""Shared UTC timestamp helpers.

Single source of truth for the ISO-8601 timestamp formats used across the
``lib`` package. Previously each module defined its own ``_utc_now_iso`` helper
(10 near-identical copies in two precision variants); they now delegate here.

Three precisions are exposed because callers historically differed:

* :func:`utc_now_iso`     -> ``2026-06-12T14:03:09Z``           (seconds)
* :func:`utc_now_iso_ms`  -> ``2026-06-12T14:03:09.123Z``       (milliseconds)
* :func:`utc_now_iso_us`  -> ``2026-06-12T14:03:09.123456Z``    (microseconds)

Preserve the exact precision a call site already used when migrating — the
suffix width is part of some persisted/validated artifact formats.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 with second precision and ``Z`` suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now_iso_ms() -> str:
    """Return current UTC time as ISO 8601 with millisecond precision and ``Z`` suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def utc_now_iso_us() -> str:
    """Return current UTC time as ISO 8601 with microsecond precision and ``Z`` suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
