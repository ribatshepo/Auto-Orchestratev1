"""Unified artifact envelope schema and validator.

Every JSON artifact and Markdown artifact produced anywhere in the
Auto-Orchestrate pipeline wraps a type-specific body in a common envelope
defined by :mod:`schemas`. The :func:`validator.validate` function checks
that an artifact on disk conforms to the envelope and optionally to its
declared ``artifact_type`` body schema.
"""

from __future__ import annotations

from .schemas import (
    ARTIFACT_TYPES,
    ENVELOPE_SCHEMA_VERSION,
    EXCERPT_MAX_CHARS,
    build_envelope,
    envelope_skeleton,
)
from .validator import (
    EnvelopeValidationError,
    validate,
    validate_session,
)

__all__ = [
    "ARTIFACT_TYPES",
    "ENVELOPE_SCHEMA_VERSION",
    "EXCERPT_MAX_CHARS",
    "EnvelopeValidationError",
    "build_envelope",
    "envelope_skeleton",
    "validate",
    "validate_session",
]
