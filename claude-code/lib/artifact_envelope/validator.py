"""Envelope validation for JSON and Markdown artifacts.

Markdown artifacts are expected to carry a YAML front-matter block
delimited by ``---`` lines holding envelope fields. JSON artifacts hold
the envelope as their top-level object.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import (
    ALLOWED_STATUS,
    ALLOWED_VERDICT,
    ARTIFACT_TYPES,
    ENVELOPE_SCHEMA_VERSION,
    REQUIRED_FIELDS,
)


class EnvelopeValidationError(ValueError):
    """Raised when an artifact does not conform to the envelope schema."""


def _parse_yaml_front_matter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        raise EnvelopeValidationError(
            "Markdown artifact missing YAML front-matter (no leading '---')."
        )
    end = text.find("\n---", 3)
    if end == -1:
        raise EnvelopeValidationError(
            "Markdown artifact has unterminated YAML front-matter."
        )
    block = text[3:end].strip()
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return _naive_yaml_to_dict(block)
    parsed = yaml.safe_load(block)
    if not isinstance(parsed, dict):
        raise EnvelopeValidationError(
            "Front-matter must parse to a mapping at the top level."
        )
    return parsed


def _naive_yaml_to_dict(block: str) -> dict[str, Any]:
    """Minimal YAML-ish parser for environments without PyYAML.

    Handles the simple subset our envelopes use: top-level key: value
    pairs where values are strings, ints, floats, or short lists in
    flow syntax. Falls back to leaving values as strings.
    """
    result: dict[str, Any] = {}
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not value:
            result[key] = ""
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            result[key] = [v.strip().strip("\"'") for v in inner.split(",") if v.strip()]
            continue
        if (value.startswith("\"") and value.endswith("\"")) or (
            value.startswith("'") and value.endswith("'")
        ):
            result[key] = value[1:-1]
            continue
        try:
            result[key] = int(value)
            continue
        except ValueError:
            pass
        try:
            result[key] = float(value)
            continue
        except ValueError:
            pass
        result[key] = value
    return result


def _load_envelope(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json" or path.suffix == ".jsonl":
        if path.suffix == ".jsonl":
            first = text.partition("\n")[0].strip()
            if not first:
                raise EnvelopeValidationError(f"{path}: empty JSONL artifact")
            return json.loads(first)
        return json.loads(text)
    if path.suffix in {".md", ".markdown"}:
        return _parse_yaml_front_matter(text)
    raise EnvelopeValidationError(
        f"Unsupported artifact extension: {path.suffix}"
    )


def validate(path: str | Path, expected_type: str | None = None) -> dict[str, Any]:
    """Validate the envelope of the artifact at ``path``.

    Returns the parsed envelope on success. Raises
    :class:`EnvelopeValidationError` on any structural problem.
    """
    p = Path(path)
    if not p.exists():
        raise EnvelopeValidationError(f"Artifact not found: {p}")
    env = _load_envelope(p)
    missing = [f for f in REQUIRED_FIELDS if f not in env]
    if missing:
        raise EnvelopeValidationError(
            f"{p}: missing required envelope fields: {missing}"
        )
    if env["schema_version"] != ENVELOPE_SCHEMA_VERSION:
        raise EnvelopeValidationError(
            f"{p}: schema_version '{env['schema_version']}' "
            f"!= expected '{ENVELOPE_SCHEMA_VERSION}'"
        )
    if env["artifact_type"] not in ARTIFACT_TYPES:
        raise EnvelopeValidationError(
            f"{p}: unknown artifact_type '{env['artifact_type']}'"
        )
    if expected_type is not None and env["artifact_type"] != expected_type:
        raise EnvelopeValidationError(
            f"{p}: artifact_type '{env['artifact_type']}' != expected '{expected_type}'"
        )
    if env.get("status") not in ALLOWED_STATUS:
        raise EnvelopeValidationError(
            f"{p}: invalid status '{env.get('status')}'"
        )
    if "verdict" in env and env["verdict"] not in ALLOWED_VERDICT:
        raise EnvelopeValidationError(
            f"{p}: invalid verdict '{env['verdict']}'"
        )
    return env


def validate_session(session_dir: str | Path) -> dict[str, list[str]]:
    """Walk a session directory and validate every artifact.

    Returns a report dict with ``ok`` and ``errors`` keys. The orchestrator
    and ``workflow-end`` skill call this at session close.
    """
    root = Path(session_dir)
    if not root.exists():
        raise EnvelopeValidationError(f"Session dir not found: {root}")
    ok: list[str] = []
    errors: list[str] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix not in {".json", ".md"}:
            continue
        if p.name in {"checkpoint.json", "proposed-tasks.json", "raid-log.json"}:
            continue
        try:
            validate(p)
            ok.append(str(p))
        except EnvelopeValidationError as exc:
            errors.append(str(exc))
    return {"ok": ok, "errors": errors}


def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m claude_code.lib.artifact_envelope.validator <session_dir>")
        return 2
    report = validate_session(argv[1])
    print(f"OK: {len(report['ok'])}")
    print(f"ERRORS: {len(report['errors'])}")
    for err in report["errors"]:
        print(f"  - {err}")
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv))
