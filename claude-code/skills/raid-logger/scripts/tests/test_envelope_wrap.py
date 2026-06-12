"""Tests for the artifact-envelope wrap added to ``append_raid.py``.

Covers:
- envelope-wrapped append round-trip
- dual-mode read (legacy raw entries still parseable)
- ``--validate`` exits 0 on a healthy mixed log
- ``--validate`` exits non-zero when a line has a wrong envelope schema_version
- ``--validate`` exits non-zero when a line has a wrong artifact_type
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = SCRIPT_DIR.parent.parent.parent / "lib"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(LIB_DIR))

import append_raid as ar  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def session_id() -> str:
    return "auto-orc-20260515-tests"


@pytest.fixture
def session_dir(project_root: Path, session_id: str) -> Path:
    sd = project_root / ".orchestrate" / session_id
    sd.mkdir(parents=True)
    return sd


def _entry(idx: int, **overrides) -> dict:
    base = {
        "id": f"raid-{idx:03d}",
        "type": "Risk",
        "severity": "HIGH",
        "status": "open",
        "owner": "orchestrator",
        "source_process": "P-010",
        "timestamp": "2026-05-15T12:00:00Z",
        "description": f"Test risk number {idx} long enough to satisfy validate.",
        "mitigation": "Mitigation plan placeholder for the test.",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Envelope wrap on append
# ---------------------------------------------------------------------------


class TestEnvelopeRoundTrip:
    def test_appended_entries_are_envelope_wrapped(
        self, session_dir: Path, session_id: str
    ) -> None:
        rc = ar.main(["--session", session_id,
                      "--entry-json", json.dumps(_entry(1))])
        assert rc == 0
        log = session_dir / "raid-log.json"
        line = log.read_text(encoding="utf-8").strip()
        obj = json.loads(line)
        assert ar._is_envelope(obj)
        assert obj["artifact_type"] == "audit_finding"
        assert obj["session_id"] == session_id
        assert obj["producer_agent"] == "skill:raid-logger"
        assert obj["stage"] == "cross-session"
        assert obj["body"]["id"] == "raid-001"

    def test_envelope_status_maps_from_severity(
        self, session_dir: Path, session_id: str
    ) -> None:
        rc = ar.main(["--session", session_id,
                      "--entry-json", json.dumps(_entry(1, severity="HIGH"))])
        assert rc == 0
        log = session_dir / "raid-log.json"
        obj = json.loads(log.read_text(encoding="utf-8").strip())
        assert obj["status"] == "warn"

        rc = ar.main(["--session", session_id, "--entry-json",
                      json.dumps(_entry(2, type="Assumption",
                                        severity=None, status="accepted",
                                        mitigation=None))])
        assert rc == 0
        # Second line is the assumption with low/null severity → status "ok"
        last_line = log.read_text(encoding="utf-8").splitlines()[-1]
        obj = json.loads(last_line)
        assert obj["status"] == "ok"

    def test_envelope_links_carry_source_process(
        self, session_dir: Path, session_id: str
    ) -> None:
        rc = ar.main(["--session", session_id, "--entry-json",
                      json.dumps(_entry(1, source_process="P-074"))])
        assert rc == 0
        log = session_dir / "raid-log.json"
        obj = json.loads(log.read_text(encoding="utf-8").strip())
        assert "P-074" in obj["links"]["related_processes"]


# ---------------------------------------------------------------------------
# Dual-mode reading
# ---------------------------------------------------------------------------


class TestDualModeRead:
    def test_list_current_peels_envelope(
        self, session_dir: Path, session_id: str, capsys: pytest.CaptureFixture
    ) -> None:
        ar.main(["--session", session_id,
                 "--entry-json", json.dumps(_entry(1))])
        capsys.readouterr()  # discard append output
        rc = ar.main(["--session", session_id, "--list-current"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 1
        assert out["entries"][0]["id"] == "raid-001"
        assert out["entries"][0]["type"] == "Risk"

    def test_list_current_handles_legacy_raw_entries(
        self, session_dir: Path, session_id: str, capsys: pytest.CaptureFixture
    ) -> None:
        log = session_dir / "raid-log.json"
        with log.open("w", encoding="utf-8") as f:
            f.write(json.dumps(_entry(99)) + "\n")
        rc = ar.main(["--session", session_id, "--list-current"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 1
        assert out["entries"][0]["id"] == "raid-099"

    def test_list_current_mixed_legacy_and_envelope(
        self, session_dir: Path, session_id: str, capsys: pytest.CaptureFixture
    ) -> None:
        log = session_dir / "raid-log.json"
        with log.open("w", encoding="utf-8") as f:
            f.write(json.dumps(_entry(99)) + "\n")  # legacy raw
        ar.main(["--session", session_id,
                 "--entry-json", json.dumps(_entry(1))])  # envelope
        capsys.readouterr()
        rc = ar.main(["--session", session_id, "--list-current"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        ids = {e["id"] for e in out["entries"]}
        assert ids == {"raid-099", "raid-001"}

    def test_load_existing_ids_peels_envelope(
        self, session_dir: Path, session_id: str
    ) -> None:
        ar.main(["--session", session_id,
                 "--entry-json", json.dumps(_entry(1))])
        ar.main(["--session", session_id,
                 "--entry-json", json.dumps(_entry(2))])
        log = session_dir / "raid-log.json"
        assert ar.load_existing_ids(log) == {"raid-001", "raid-002"}


# ---------------------------------------------------------------------------
# --validate
# ---------------------------------------------------------------------------


class TestValidate:
    def test_validate_empty_log(
        self, session_dir: Path, session_id: str, capsys: pytest.CaptureFixture
    ) -> None:
        rc = ar.main(["--session", session_id, "--validate"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is True
        assert out["entries"] == 0

    def test_validate_healthy_envelope_log(
        self, session_dir: Path, session_id: str, capsys: pytest.CaptureFixture
    ) -> None:
        ar.main(["--session", session_id,
                 "--entry-json", json.dumps(_entry(1))])
        capsys.readouterr()
        rc = ar.main(["--session", session_id, "--validate"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is True
        assert out["envelope_lines"] == 1
        assert out["legacy_lines"] == 0

    def test_validate_accepts_mixed_legacy_and_envelope(
        self, session_dir: Path, session_id: str, capsys: pytest.CaptureFixture
    ) -> None:
        log = session_dir / "raid-log.json"
        with log.open("w", encoding="utf-8") as f:
            f.write(json.dumps(_entry(99)) + "\n")
        ar.main(["--session", session_id,
                 "--entry-json", json.dumps(_entry(1))])
        capsys.readouterr()
        rc = ar.main(["--session", session_id, "--validate"])
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is True
        assert out["envelope_lines"] == 1
        assert out["legacy_lines"] == 1

    def test_validate_rejects_wrong_schema_version(
        self, session_dir: Path, session_id: str, capsys: pytest.CaptureFixture
    ) -> None:
        ar.main(["--session", session_id,
                 "--entry-json", json.dumps(_entry(1))])
        log = session_dir / "raid-log.json"
        text = log.read_text(encoding="utf-8")
        obj = json.loads(text.strip())
        obj["schema_version"] = "0.9"
        log.write_text(json.dumps(obj) + "\n", encoding="utf-8")
        capsys.readouterr()
        rc = ar.main(["--session", session_id, "--validate"])
        assert rc != 0
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is False
        assert "schema_version" in out["error"]

    def test_validate_rejects_wrong_artifact_type(
        self, session_dir: Path, session_id: str, capsys: pytest.CaptureFixture
    ) -> None:
        ar.main(["--session", session_id,
                 "--entry-json", json.dumps(_entry(1))])
        log = session_dir / "raid-log.json"
        obj = json.loads(log.read_text(encoding="utf-8").strip())
        obj["artifact_type"] = "meeting_minutes"
        log.write_text(json.dumps(obj) + "\n", encoding="utf-8")
        capsys.readouterr()
        rc = ar.main(["--session", session_id, "--validate"])
        assert rc != 0
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is False
        assert "artifact_type" in out["error"]
