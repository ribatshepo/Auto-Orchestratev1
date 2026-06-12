"""Unit tests for the artifact_envelope package.

Covers the previously-untested public surface: envelope_skeleton/build_envelope
construction, validate()/validate_session() on disk, and both YAML front-matter
parse paths (PyYAML and the naive fallback).
"""

from __future__ import annotations

import json

import pytest

from lib.artifact_envelope import (
    ARTIFACT_TYPES,
    ENVELOPE_SCHEMA_VERSION,
    EXCERPT_MAX_CHARS,
    EnvelopeValidationError,
    build_envelope,
    envelope_skeleton,
    validate,
    validate_session,
)
from lib.artifact_envelope.schemas import REQUIRED_FIELDS
from lib.artifact_envelope.validator import (
    _naive_yaml_to_dict,
    _parse_yaml_front_matter,
)


def _good_envelope(**overrides):
    base = dict(
        artifact_type="stage_receipt",
        artifact_id="art-1",
        session_id="sess-1",
        stage="3",
        producer_agent="software-engineer",
        body={"summary": "done"},
    )
    base.update(overrides)
    return build_envelope(**base)


# --------------------------------------------------------------------------- #
# envelope_skeleton / build_envelope
# --------------------------------------------------------------------------- #

def test_skeleton_populates_all_required_fields():
    env = envelope_skeleton("gate", "g1", "s1", "2", "qa-engineer")
    for field in REQUIRED_FIELDS:
        assert field in env, f"missing required field {field}"
    assert env["schema_version"] == ENVELOPE_SCHEMA_VERSION == "1.0.0"
    assert env["created_at"].endswith("Z")
    assert env["status"] == "ok"
    assert env["body"] == {}


def test_skeleton_rejects_unknown_artifact_type():
    with pytest.raises(ValueError, match="Unknown artifact_type"):
        envelope_skeleton("not_a_type", "x", "s", "1", "agent")


def test_skeleton_rejects_invalid_status():
    with pytest.raises(ValueError, match="Invalid status"):
        envelope_skeleton("gate", "x", "s", "1", "agent", status="bogus")


def test_build_envelope_wraps_body_and_sets_fields():
    env = build_envelope(
        "audit_finding", "a1", "s1", "5", "auditor",
        body={"finding": "gap"}, status="warn", verdict="conditional",
        inputs=[{"ref": "in"}], outputs=[{"ref": "out"}],
    )
    assert env["body"] == {"finding": "gap"}
    assert env["status"] == "warn"
    assert env["verdict"] == "conditional"
    assert env["inputs"] == [{"ref": "in"}]
    assert env["outputs"] == [{"ref": "out"}]


def test_build_envelope_rejects_invalid_verdict():
    with pytest.raises(ValueError, match="Invalid verdict"):
        build_envelope("gate", "g", "s", "1", "agent", body={}, verdict="maybe")


# --------------------------------------------------------------------------- #
# CONTEXT-DIET-001: excerpt / excerpt_pointers
# --------------------------------------------------------------------------- #

def test_skeleton_has_empty_excerpt_fields():
    env = envelope_skeleton("gate", "g1", "s1", "2", "qa-engineer")
    assert env["excerpt"] == ""
    assert env["excerpt_pointers"] == []


def test_build_envelope_populates_excerpt_and_pointers():
    env = build_envelope(
        "audit_finding", "a1", "s1", "5", "auditor", body={"gaps": []},
        excerpt="Compliance 82%: 1 FAIL (REQ-009 authz).",
        excerpt_pointers=["body.gaps[]", "body.compliance_score"],
    )
    assert env["excerpt"].startswith("Compliance 82%")
    assert env["excerpt_pointers"] == ["body.gaps[]", "body.compliance_score"]


def test_excerpt_is_truncated_to_max_chars():
    env = build_envelope(
        "gate", "g", "s", "1", "agent", body={}, excerpt="x" * 5000
    )
    assert len(env["excerpt"]) == EXCERPT_MAX_CHARS
    # The body is never touched by excerpt truncation.
    assert env["body"] == {}


def test_omitted_excerpt_defaults_empty_and_validates(tmp_path):
    p = tmp_path / "art.json"
    p.write_text(json.dumps(_good_envelope()), encoding="utf-8")
    env = validate(p)
    assert env["excerpt"] == ""  # default present, validation clean


def test_validate_rejects_non_string_excerpt(tmp_path):
    env = _good_envelope()
    env["excerpt"] = {"not": "a string"}
    p = tmp_path / "art.json"
    p.write_text(json.dumps(env), encoding="utf-8")
    with pytest.raises(EnvelopeValidationError, match="excerpt must be a string"):
        validate(p)


def test_validate_rejects_non_list_excerpt_pointers(tmp_path):
    env = _good_envelope()
    env["excerpt_pointers"] = "body.x"
    p = tmp_path / "art.json"
    p.write_text(json.dumps(env), encoding="utf-8")
    with pytest.raises(EnvelopeValidationError, match="excerpt_pointers must be a list"):
        validate(p)


def test_validate_does_not_fail_on_overlong_excerpt(tmp_path):
    # Fidelity: an over-long excerpt that somehow reached disk is accepted, not rejected.
    env = _good_envelope()
    env["excerpt"] = "y" * 5000
    p = tmp_path / "art.json"
    p.write_text(json.dumps(env), encoding="utf-8")
    assert validate(p)["excerpt"] == "y" * 5000


# --------------------------------------------------------------------------- #
# validate() on JSON
# --------------------------------------------------------------------------- #

def test_validate_accepts_good_json(tmp_path):
    p = tmp_path / "art.json"
    p.write_text(json.dumps(_good_envelope()), encoding="utf-8")
    env = validate(p)
    assert env["artifact_type"] == "stage_receipt"


def test_validate_expected_type_match_and_mismatch(tmp_path):
    p = tmp_path / "art.json"
    p.write_text(json.dumps(_good_envelope()), encoding="utf-8")
    assert validate(p, expected_type="stage_receipt")["artifact_id"] == "art-1"
    with pytest.raises(EnvelopeValidationError, match="!= expected 'gate'"):
        validate(p, expected_type="gate")


def test_validate_missing_file_raises(tmp_path):
    with pytest.raises(EnvelopeValidationError, match="not found"):
        validate(tmp_path / "nope.json")


def test_validate_rejects_missing_required_fields(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"schema_version": "1.0.0"}), encoding="utf-8")
    with pytest.raises(EnvelopeValidationError, match="missing required envelope fields"):
        validate(p)


def test_validate_rejects_wrong_schema_version(tmp_path):
    env = _good_envelope()
    env["schema_version"] = "9.9.9"
    p = tmp_path / "art.json"
    p.write_text(json.dumps(env), encoding="utf-8")
    with pytest.raises(EnvelopeValidationError, match="schema_version"):
        validate(p)


def test_validate_rejects_unknown_artifact_type(tmp_path):
    env = _good_envelope()
    env["artifact_type"] = "frobnicate"
    p = tmp_path / "art.json"
    p.write_text(json.dumps(env), encoding="utf-8")
    with pytest.raises(EnvelopeValidationError, match="unknown artifact_type"):
        validate(p)


def test_validate_rejects_bad_status(tmp_path):
    env = _good_envelope()
    env["status"] = "exploded"
    p = tmp_path / "art.json"
    p.write_text(json.dumps(env), encoding="utf-8")
    with pytest.raises(EnvelopeValidationError, match="invalid status"):
        validate(p)


def test_validate_rejects_unsupported_extension(tmp_path):
    p = tmp_path / "art.txt"
    p.write_text("whatever", encoding="utf-8")
    with pytest.raises(EnvelopeValidationError, match="Unsupported artifact extension"):
        validate(p)


# --------------------------------------------------------------------------- #
# Markdown front-matter parsing (both PyYAML and naive paths)
# --------------------------------------------------------------------------- #

_MD_ARTIFACT = """---
schema_version: "1.0.0"
artifact_type: domain_review
artifact_id: dr-1
session_id: sess-1
stage: "2"
producer_agent: qa-engineer
created_at: "2026-01-01T00:00:00.000000Z"
status: ok
---

# Domain review body
"""


def test_validate_accepts_markdown_front_matter(tmp_path):
    p = tmp_path / "review.md"
    p.write_text(_MD_ARTIFACT, encoding="utf-8")
    env = validate(p)
    assert env["artifact_type"] == "domain_review"
    assert env["schema_version"] == "1.0.0"


def test_markdown_missing_front_matter_raises(tmp_path):
    p = tmp_path / "review.md"
    p.write_text("# no front matter here\n", encoding="utf-8")
    with pytest.raises(EnvelopeValidationError, match="missing YAML front-matter"):
        validate(p)


def test_markdown_unterminated_front_matter_raises(tmp_path):
    p = tmp_path / "review.md"
    p.write_text("---\nartifact_type: gate\n", encoding="utf-8")
    with pytest.raises(EnvelopeValidationError, match="unterminated"):
        validate(p)


def test_naive_yaml_parser_handles_scalar_subset():
    block = (
        'name: "quoted string"\n'
        "count: 7\n"
        "ratio: 0.25\n"
        "tags: [a, b, c]\n"
        "empty:\n"
        "# a comment line\n"
        "plain: hello\n"
    )
    parsed = _naive_yaml_to_dict(block)
    assert parsed["name"] == "quoted string"
    assert parsed["count"] == 7
    assert parsed["ratio"] == 0.25
    assert parsed["tags"] == ["a", "b", "c"]
    assert parsed["empty"] == ""
    assert parsed["plain"] == "hello"
    assert "# a comment line" not in parsed


def test_parse_front_matter_returns_mapping():
    parsed = _parse_yaml_front_matter(_MD_ARTIFACT)
    assert isinstance(parsed, dict)
    assert parsed["artifact_type"] == "domain_review"


# --------------------------------------------------------------------------- #
# validate_session
# --------------------------------------------------------------------------- #

def test_validate_session_partitions_ok_and_errors(tmp_path):
    (tmp_path / "good.json").write_text(json.dumps(_good_envelope()), encoding="utf-8")
    (tmp_path / "bad.json").write_text(json.dumps({"schema_version": "1.0.0"}), encoding="utf-8")
    # Explicitly skipped by name — must not appear in either bucket.
    (tmp_path / "checkpoint.json").write_text(json.dumps({"anything": True}), encoding="utf-8")

    report = validate_session(tmp_path)
    assert any("good.json" in entry for entry in report["ok"])
    assert report["errors"], "expected the malformed artifact to be reported"
    assert not any("checkpoint.json" in entry for entry in report["ok"])


def test_validate_session_missing_dir_raises(tmp_path):
    with pytest.raises(EnvelopeValidationError, match="Session dir not found"):
        validate_session(tmp_path / "absent")


def test_artifact_types_frozenset_is_nonempty():
    assert isinstance(ARTIFACT_TYPES, frozenset)
    assert "stage_receipt" in ARTIFACT_TYPES
