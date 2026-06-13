"""Unit tests for extend.py — the skill/agent scaffolder + manifest updater.

All tests operate on a temporary copy of a minimal claude-code tree so the real
repo manifest and docs are never mutated.
"""

import argparse
import json
import sys
from pathlib import Path

import pytest

# Make the shared python dir importable (extend, layer0, layer1, validate_manifest).
_PYDIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PYDIR))

import extend  # noqa: E402


def _args(kind, name, **kw):
    ns = argparse.Namespace(
        kind=kind, name=name, description=kw.get("description", "Test thing."),
        triggers=kw.get("triggers", "trigger one,trigger two"),
        dry_run=kw.get("dry_run", False), root=str(kw["root"]),
        for_agent=kw.get("for_agent", ""), scripts=kw.get("scripts", False),
        references=kw.get("references", False), model=kw.get("model", "sonnet"),
        tools=kw.get("tools", ""), category=kw.get("category", "pipeline"),
        skills=kw.get("skills", ""),
    )
    return ns


MINIMAL_MANIFEST = {
    "schema_version": "1.0.0",
    "name": "test",
    "description": "test manifest",
    "updated_at": "2026-06-13",
    "stats": {
        "total_skills": 1, "total_agents": 1, "total_commands": 0,
        "total_protocols": 0, "total_templates": 0, "total_style_guides": 0,
    },
    "agents": [{
        "name": "infra-engineer", "description": "Builds infra.", "model": "sonnet",
        "tools": ["Read", "Write"], "dispatch_triggers": ["infra"],
        "capabilities": {}, "path": "agents/infra-engineer.md",
    }],
    "skills": [{
        "name": "existing-skill", "description": "An existing skill.",
        "dispatch_triggers": ["existing"], "has_scripts": False,
        "has_references": False, "path": "skills/existing-skill/SKILL.md",
    }],
    "commands": [],
    "shared": {
        "protocols": [], "templates": [], "style_guides": [], "tokens": [],
        "references": [],
        "python_library": {
            "base_path": "skills/_shared/python", "layers": ["layer0"],
            "test_directory": "skills/_shared/python/tests",
        },
    },
}

README_TEXT = """# Engineering Team Agents Reference

## Overview

1 agents (per manifest). 1 role-based.

## Agent Index

### Pipeline Support Agents (Sonnet)

| Agent | File | Primary Scope |
|-------|------|---------------|
| [Infra Engineer](infra-engineer.md) | `infra-engineer.md` | infra |

### Removed Agents (historical record)

| Agent | Status | Successor |
|-------|--------|-----------|
"""

ARCH_TEXT = """# Architecture

## 2. Component inventory at a glance

  Remaining 1 agents + 1 skills are lazy-dispatched by the orchestrator.

## 7. Agent inventory (1)

| Agent | Purpose | Tools | Primary pipeline role |
|-------|---------|-------|-----------------------|
| infra-engineer | Builds infra. | Read, Write | builder |

## 8. Skill inventory (1)

### Pipeline core

| Skill | Purpose |
|-------|---------|
| existing-skill | An existing skill. |
"""


@pytest.fixture
def tree(tmp_path):
    """A minimal claude-code/ tree."""
    (tmp_path / "manifest.json").write_text(json.dumps(MINIMAL_MANIFEST, indent=2) + "\n")
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "README.md").write_text(README_TEXT)
    (tmp_path / "skills").mkdir()
    (tmp_path / "ARCHITECTURE.md").write_text(ARCH_TEXT)
    return tmp_path


def _manifest(tree):
    return json.loads((tree / "manifest.json").read_text())


# --------------------------------------------------------------------------- #

def test_add_agent_writes_file_and_registers(tree):
    rc = extend.run(_args("agent", "perf-analyst", root=tree, category="implementation",
                          description="Analyzes perf."))
    assert rc == extend.EXIT_SUCCESS
    assert (tree / "agents" / "perf-analyst.md").exists()
    m = _manifest(tree)
    entry = next(a for a in m["agents"] if a["name"] == "perf-analyst")
    assert entry["model"] == "sonnet"
    assert entry["path"] == "agents/perf-analyst.md"
    assert entry["capabilities"] == {}
    assert m["stats"]["total_agents"] == 2  # bumped


def test_add_agent_bumps_readme_and_architecture_counts(tree):
    extend.run(_args("agent", "perf-analyst", root=tree, category="pipeline"))
    readme = (tree / "agents" / "README.md").read_text()
    assert "2 agents" in readme
    assert "[Perf Analyst](perf-analyst.md)" in readme  # row appended
    arch = (tree / "ARCHITECTURE.md").read_text()
    assert "## 7. Agent inventory (2)" in arch
    assert "Remaining 2 agents" in arch
    assert "| perf-analyst |" in arch


def test_add_skill_registers_and_bumps_stats(tree):
    rc = extend.run(_args("skill", "cost-forecaster", root=tree, scripts=True))
    assert rc == extend.EXIT_SUCCESS
    assert (tree / "skills" / "cost-forecaster" / "SKILL.md").exists()
    assert (tree / "skills" / "cost-forecaster" / "scripts" / "__init__.py").exists()
    m = _manifest(tree)
    entry = next(s for s in m["skills"] if s["name"] == "cost-forecaster")
    assert entry["has_scripts"] is True
    assert entry["has_references"] is False
    assert m["stats"]["total_skills"] == 2
    arch = (tree / "ARCHITECTURE.md").read_text()
    assert "## 8. Skill inventory (2)" in arch
    assert "Remaining 1 agents + 2 skills" in arch


def test_wire_skill_to_agent(tree):
    extend.run(_args("skill", "cost-forecaster", root=tree, for_agent="infra-engineer"))
    m = _manifest(tree)
    agent = next(a for a in m["agents"] if a["name"] == "infra-engineer")
    assert "cost-forecaster" in agent["skills_orchestrated"]
    skill = next(s for s in m["skills"] if s["name"] == "cost-forecaster")
    assert "chaining" in skill  # chaining scaffold added when wiring


def test_wire_to_unknown_agent_fails(tree):
    rc = extend.run(_args("skill", "x-skill", root=tree, for_agent="nope"))
    assert rc == extend.EXIT_ERROR
    # nothing written
    assert not (tree / "skills" / "x-skill").exists()
    assert _manifest(tree)["stats"]["total_skills"] == 1


def test_agent_skills_must_exist(tree):
    rc = extend.run(_args("agent", "x-agent", root=tree, skills="does-not-exist"))
    assert rc == extend.EXIT_ERROR
    assert not (tree / "agents" / "x-agent.md").exists()


def test_conflict_refused(tree):
    rc = extend.run(_args("skill", "existing-skill", root=tree))
    assert rc == extend.EXIT_ERROR
    assert _manifest(tree)["stats"]["total_skills"] == 1  # unchanged


def test_invalid_name_refused(tree):
    rc = extend.run(_args("agent", "Bad_Name", root=tree))
    assert rc == extend.EXIT_INVALID_ARGS


def test_dry_run_writes_nothing(tree):
    before = (tree / "manifest.json").read_text()
    rc = extend.run(_args("agent", "ghost-agent", root=tree, dry_run=True))
    assert rc == extend.EXIT_SUCCESS
    assert not (tree / "agents" / "ghost-agent.md").exists()
    assert (tree / "manifest.json").read_text() == before  # untouched


def test_post_edit_manifest_validates(tree):
    extend.run(_args("agent", "perf-analyst", root=tree))
    extend.run(_args("skill", "cost-forecaster", root=tree))
    errors = extend.vm.validate_manifest(tree / "manifest.json")
    assert errors == []
