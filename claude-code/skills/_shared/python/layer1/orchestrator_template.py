"""
Orchestrator template extractor (TEMPLATE-EXTRACT-001).

Token-budget optimization #1: instead of injecting the full ~33k-token
`agents/orchestrator.md` into every orchestrator spawn, extract only:
  - the always-needed CORE (constraints, boot sequence, execution loop, skill
    selection, error recovery — the "operating manual"), and
  - the active stage/phase/meeting template for the current spawn.

This avoids restructuring `orchestrator.md` into many files (which would risk
drift between core and templates). The single source-of-truth file is
preserved; sections are carved on demand.

Section markers:
  - CORE: H2 sections from "## Core Constraints" through "## Skill Selection"
    plus "## Error Recovery" and "## References".
  - STAGE: H3 inside "## Per-Stage Spawn Templates" matching `### Stage <N>:`
  - PHASE: H3 inside "## Domain Phase Spawn Templates" or "## Special PHASE
    Templates" matching the requested phase name.
  - MEETING: H3 inside "## Meeting Spawn Templates" matching meeting kind.

If the active section is unknown, the helper returns the entire file (safe
fallback equivalent to flag-off behavior).
"""

from __future__ import annotations

import re
from pathlib import Path

_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_H3_RE = re.compile(r"^### (.+)$", re.MULTILINE)


# Sections that always belong in CORE
_CORE_H2_TITLES = (
    "Core Constraints",
    "Tool Availability",
    "Boot Sequence",
    "Pipeline Stages & Turn Limits",
    "Planning Phase Routing",
    "Progress Output",
    "Skill Selection",
    "Execution Loop",
    "Domain Expert Review Findings",
    # Stage-Close Protocol is the MAIN-017 implementation — it spawns the
    # baseline qa-engineer / engineering-manager and writes phase-receipts /
    # reasoning-traces. Dropping it from CORE leaves the orchestrator with
    # no instructions for any stage-close fan-out.
    "Stage-Close Protocol",
    # CI Feedback Hooks are referenced by Boot Sequence and Execution Loop
    # (both already in CORE), so they must travel with CORE to avoid
    # dangling cross-references.
    "CI Feedback Hooks: PDCA",
    "CI Feedback Hooks: OODA",
    "CI Feedback Hooks: Stage Telemetry",
    "CI Feedback Hooks: research_completeness_score",
    "Backward Compatibility",
    "Self-Audit Gate",
    "Error Recovery",
    "References",
)


def _split_h2_sections(text: str) -> list[tuple[str, str]]:
    """Split a markdown document into a list of (h2_title, body) tuples.

    The body of each section includes the H2 line and everything up to the
    next H2 (or EOF).
    """
    matches = list(_H2_RE.finditer(text))
    if not matches:
        return [("", text)]
    out: list[tuple[str, str]] = []
    # Pre-H2 preamble (frontmatter + intro)
    if matches[0].start() > 0:
        out.append(("__preamble__", text[: matches[0].start()]))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((title, text[m.start() : end]))
    return out


def _split_h3_subsections(section_body: str) -> list[tuple[str, str]]:
    """Split an H2 section body into H3 subsections."""
    matches = list(_H3_RE.finditer(section_body))
    if not matches:
        return [("", section_body)]
    out: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        out.append(("__intro__", section_body[: matches[0].start()]))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_body)
        out.append((title, section_body[m.start() : end]))
    return out


def _is_core_h2(title: str) -> bool:
    return any(title.startswith(prefix) for prefix in _CORE_H2_TITLES)


def extract_core(orchestrator_md_path: str | Path) -> str:
    """Return the CORE-only slice of orchestrator.md (~4k tokens)."""
    text = Path(orchestrator_md_path).read_text(encoding="utf-8")
    sections = _split_h2_sections(text)
    return "".join(body for title, body in sections if title == "__preamble__" or _is_core_h2(title))


def _h2_intro(body: str) -> str:
    """Return the preamble of an H2 section — everything before the first H3.

    The Common block and Common Handover Block live in the H2 preamble of
    `## Per-Stage Spawn Templates`. They must reach every spawn, so the
    extractor prepends this intro to whichever H3 it returns.
    """
    parts = _split_h3_subsections(body)
    for h3_title, h3_body in parts:
        if h3_title == "__intro__":
            return h3_body
    return ""


def extract_stage_template(
    orchestrator_md_path: str | Path, stage: str | int
) -> str | None:
    """Return the H3 subsection for the requested stage (e.g. "3", "4.5", "P2").

    Looks under "## Per-Stage Spawn Templates" and "## Planning Phase Spawn Templates"
    (the latter is nested under Per-Stage's intro region in the current file).
    The H2 intro (Common block + Common Handover Block, HANDOVER-001/002/003)
    is prepended to the returned body so every spawn receives it.
    Returns None if no matching subsection is found.
    """
    text = Path(orchestrator_md_path).read_text(encoding="utf-8")
    sections = _split_h2_sections(text)
    stage_str = str(stage)
    for title, body in sections:
        if title.startswith("Per-Stage Spawn Templates") or title.startswith(
            "Planning Phase Spawn Templates"
        ):
            intro = _h2_intro(body)
            for h3_title, h3_body in _split_h3_subsections(body):
                if h3_title == "__intro__":
                    continue
                # H3 patterns: "Stage 3: software-engineer", "Stage P1: product-manager", etc.
                matched = (
                    re.match(rf"^Stage\s+{re.escape(stage_str)}\b", h3_title, re.IGNORECASE)
                    or h3_title.startswith(f"Stage {stage_str}:")
                    or h3_title.startswith(f"Stage {stage_str} ")
                )
                if matched:
                    return (intro + "\n" + h3_body) if intro else h3_body
    return None


def extract_phase_template(
    orchestrator_md_path: str | Path, phase: str
) -> str | None:
    """Return the H3 subsection for the requested phase (e.g. "5q", "5s", "7", "8", "9").

    Like extract_stage_template, the H2 intro is prepended so the spawn carries
    the Common block + Common Handover Block (HANDOVER-001/002/003).

    "Meeting Spawn Templates" is included in the search targets because the
    loop controller routinely calls `extract_phase_template(orch, "SPRINT_REVIEW")`
    etc. for `Agent(orchestrator, PHASE: SPRINT_REVIEW)` spawns — those meeting
    phases are documented under that H2.
    """
    text = Path(orchestrator_md_path).read_text(encoding="utf-8")
    sections = _split_h2_sections(text)
    targets = (
        "Domain Phase Spawn Templates",
        "Special PHASE Templates",
        "Domain Review Spawn Templates",
        "Meeting Spawn Templates",
    )
    for title, body in sections:
        if any(title.startswith(t) for t in targets):
            intro = _h2_intro(body)
            for h3_title, h3_body in _split_h3_subsections(body):
                if h3_title == "__intro__":
                    continue
                # First try "phase 5q" / "Phase 5q:" patterns; then fall back
                # to a generic word-boundary match for tokens like "REMEDIATE_ARTIFACTS".
                if re.search(rf"\bphase\s+{re.escape(phase)}\b", h3_title, re.IGNORECASE):
                    return (intro + "\n" + h3_body) if intro else h3_body
                if re.search(rf"\b{re.escape(phase)}\b", h3_title, re.IGNORECASE):
                    return (intro + "\n" + h3_body) if intro else h3_body
    return None


def _normalize_separator(s: str) -> str:
    """Normalize dashes/underscores so 'daily-standup' and 'DAILY_STANDUP' compare equal."""
    return s.lower().replace("_", "-")


def extract_meeting_template(
    orchestrator_md_path: str | Path, meeting_kind: str
) -> str | None:
    """Return the H3 subsection for the requested meeting kind.

    Meeting kind tokens like 'daily-standup' must match H3 titles like
    'PHASE: DAILY_STANDUP (P-026 — Multi-Agent Sync)'. Both sides are
    normalized to dash-form lowercase so dash/underscore-and-case
    differences don't block extraction.

    The H2 intro is prepended so the spawn carries the Common block + Common
    Handover Block (HANDOVER-001/002/003).
    """
    text = Path(orchestrator_md_path).read_text(encoding="utf-8")
    sections = _split_h2_sections(text)
    target = _normalize_separator(meeting_kind)
    for title, body in sections:
        if title.startswith("Meeting Spawn Templates"):
            intro = _h2_intro(body)
            for h3_title, h3_body in _split_h3_subsections(body):
                if h3_title == "__intro__":
                    continue
                if target in _normalize_separator(h3_title):
                    return (intro + "\n" + h3_body) if intro else h3_body
    return None


def build_spawn_prompt_body(
    orchestrator_md_path: str | Path,
    *,
    stage: str | int | None = None,
    phase: str | None = None,
    meeting_kind: str | None = None,
    enabled: bool = True,
) -> str:
    """
    Build the orchestrator section of the spawn prompt.

    When `enabled=False`, returns the full file contents (verbose mode = legacy
    behavior). When `enabled=True`, returns CORE + the active template
    section. Falls back to the full file if the requested section can't be
    located (safe degradation).
    """
    full = Path(orchestrator_md_path).read_text(encoding="utf-8")
    if not enabled:
        return full

    core = extract_core(orchestrator_md_path)
    template: str | None = None
    label = "core-only"
    if stage is not None:
        template = extract_stage_template(orchestrator_md_path, stage)
        label = f"core+stage-{stage}"
    elif phase is not None:
        template = extract_phase_template(orchestrator_md_path, phase)
        label = f"core+phase-{phase}"
    elif meeting_kind is not None:
        template = extract_meeting_template(orchestrator_md_path, meeting_kind)
        label = f"core+meeting-{meeting_kind}"

    if template is None and (stage or phase or meeting_kind):
        # Safe fallback: requested but not found → return full file
        return full

    parts = [core]
    if template:
        parts.append("\n")
        parts.append(template)
    return "".join(parts).strip() + "\n"


def estimate_tokens(text: str) -> int:
    return len(text) // 4
