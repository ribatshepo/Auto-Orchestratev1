"""Envelope schema definitions for pipeline artifacts.

The envelope is content-type agnostic. JSON artifacts use the structure
directly; Markdown artifacts encode the same fields as YAML front-matter.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ENVELOPE_SCHEMA_VERSION = "1.0.0"

ARTIFACT_TYPES: frozenset[str] = frozenset({
    "stage_receipt",
    "gate",
    "meeting_minutes",
    "handover",
    "domain_review",
    "phase_receipt",
    "reasoning_trace",
    "continuity_brief",
    "planning_doc",
    "audit_finding",
    "pipeline_state_delta",
    "learnings",
})

REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "session_id",
    "stage",
    "producer_agent",
    "created_at",
    "status",
)

ALLOWED_STATUS = frozenset({"ok", "warn", "fail", "in_progress", "blocked"})
ALLOWED_VERDICT = frozenset({"approve", "conditional", "reject", "n/a"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def envelope_skeleton(
    artifact_type: str,
    artifact_id: str,
    session_id: str,
    stage: str,
    producer_agent: str,
    status: str = "ok",
) -> dict[str, Any]:
    """Return a minimal envelope dict with required fields pre-populated."""
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(
            f"Unknown artifact_type '{artifact_type}'. Allowed: {sorted(ARTIFACT_TYPES)}"
        )
    if status not in ALLOWED_STATUS:
        raise ValueError(
            f"Invalid status '{status}'. Allowed: {sorted(ALLOWED_STATUS)}"
        )
    return {
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "artifact_id": artifact_id,
        "session_id": session_id,
        "stage": stage,
        "producer_agent": producer_agent,
        "created_at": _utc_now_iso(),
        "inputs": [],
        "outputs": [],
        "status": status,
        "verdict": "n/a",
        "links": {
            "prior_session_artifacts": [],
            "related_raid": [],
            "related_meetings": [],
            "related_processes": [],
        },
        "body": {},
    }


def build_envelope(
    artifact_type: str,
    artifact_id: str,
    session_id: str,
    stage: str,
    producer_agent: str,
    body: dict[str, Any],
    *,
    status: str = "ok",
    verdict: str = "n/a",
    inputs: list[dict[str, Any]] | None = None,
    outputs: list[dict[str, Any]] | None = None,
    confidence: dict[str, Any] | None = None,
    links: dict[str, list[Any]] | None = None,
) -> dict[str, Any]:
    """Build a complete envelope dict ready to serialize."""
    if verdict not in ALLOWED_VERDICT:
        raise ValueError(
            f"Invalid verdict '{verdict}'. Allowed: {sorted(ALLOWED_VERDICT)}"
        )
    env = envelope_skeleton(
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        session_id=session_id,
        stage=stage,
        producer_agent=producer_agent,
        status=status,
    )
    env["verdict"] = verdict
    env["inputs"] = inputs or []
    env["outputs"] = outputs or []
    env["body"] = body
    if confidence is not None:
        env["confidence"] = confidence
    if links is not None:
        env["links"].update({k: list(v) for k, v in links.items()})
    return env
