#!/usr/bin/env python3
"""
extend.py - One-step extension of the auto-orchestrate workflow.

Scaffolds a new skill or agent, registers it in manifest.json (entry + stats
bump), optionally wires a skill to an agent, and updates the related prose docs
(agents/README.md, ARCHITECTURE.md). Validates the manifest before writing and
rolls back on failure. stdlib-only.

Usage:
    extend.py skill <name> [--description STR] [--triggers "a,b"]
                           [--for-agent AGENT] [--scripts] [--references]
                           [--dry-run] [--root DIR]
    extend.py agent <name> [--description STR] [--triggers "a,b"]
                           [--model sonnet|opus|haiku] [--tools "Read,Write,..."]
                           [--category implementation|coordination|pipeline]
                           [--skills "a,b"] [--dry-run] [--root DIR]

Examples:
    extend.py skill cost-forecaster --description "Forecast cloud spend." \\
        --triggers "cost forecast,spend projection" --for-agent infra-engineer
    extend.py agent perf-analyst --model opus --category implementation \\
        --description "Analyzes runtime performance hotspots."
"""

import argparse
import difflib
import json
import re
import sys
import tempfile
from pathlib import Path

# extend.py lives in skills/_shared/python — put that dir on the path so the
# shared helper layers and the manifest validator import cleanly.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from layer0 import EXIT_ERROR, EXIT_INVALID_ARGS, EXIT_SUCCESS  # noqa: E402
from layer1 import emit_error, emit_info, emit_warning  # noqa: E402
import validate_manifest as vm  # noqa: E402

VALID_MODELS = ("sonnet", "opus", "haiku")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# README.md agent category -> section heading substring
README_CATEGORY_HEADINGS = {
    "implementation": "### Implementation Agents",
    "coordination": "### Coordination & Advisory Agents",
    "pipeline": "### Pipeline Support Agents",
}

DEFAULT_AGENT_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #

def _title(name: str) -> str:
    return " ".join(w.capitalize() for w in name.split("-"))


def _constraint_prefix(name: str) -> str:
    """Derive an UPPER constraint-ID prefix from the agent name (e.g. perf-analyst -> PA)."""
    letters = [w[0] for w in name.split("-") if w]
    prefix = "".join(letters).upper()
    return prefix if len(prefix) >= 2 else name[:2].upper()


SKILL_TEMPLATE = """---
name: {name}
description: >
  {description}
  Use when the user says {trigger_hint}.
triggers:
{trigger_lines}
---

# {title}

## Overview

[TODO: 1-2 sentences on what this skill enables and when it should fire.]

## Workflow

[TODO: the step-by-step procedure this skill performs. Keep "when to use"
context in the frontmatter `description` above — under SKILL-FRONTMATTER-001
only the frontmatter is loaded at discovery time; this body loads on invocation.]

## Output

[TODO: describe the artifact(s) this skill produces and where they are written.]
"""

AGENT_TEMPLATE = """---
name: {name}
description: {description}
tools: {tools_csv}
model: {model}
triggers:
{trigger_lines}
---

# {title}

> **PREAMBLE (PREAMBLE-001..004):** Before anything else, read
> `.orchestrate/<sid>/continuity-brief.md` (HOT core + your slice) so you never
> start empty. Load the slim protocol pack `_shared/protocols/spawn-core.md`.

## Core Rules (IMMUTABLE)

| ID | Rule |
|----|------|
| {prefix}-001 | [TODO: primary constraint this agent must always honour.] |
| {prefix}-002 | [TODO: scope boundary — what this agent must NOT do.] |

## When invoked

{description}

## Mandatory Skills

| Skill | When | How |
|-------|------|-----|
{skills_rows}

## Workflow

1. **Understand** — read the continuity brief and the task spec.
2. **Act** — [TODO: the core work this agent performs.]
3. **Self-review** — verify against the Core Rules above.
4. **Emit** — write the artifact described below; do not finish without it.

## Artifact Emission Contract

[TODO: name the artifact(s) this agent writes under `.orchestrate/<sid>/` and
the schema/template they follow.]
"""


# --------------------------------------------------------------------------- #
# Manifest helpers
# --------------------------------------------------------------------------- #

def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_manifest(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def name_exists(manifest: dict, kind: str, name: str) -> bool:
    key = "skills" if kind == "skill" else "agents"
    return any(e.get("name") == name for e in manifest.get(key, []))


def build_skill_entry(name: str, description: str, triggers: list, has_scripts: bool,
                      has_references: bool, chaining: dict | None) -> dict:
    entry = {
        "name": name,
        "description": description,
        "dispatch_triggers": triggers,
        "has_scripts": has_scripts,
        "has_references": has_references,
        "path": f"skills/{name}/SKILL.md",
    }
    if chaining:
        entry["chaining"] = chaining
    return entry


def build_agent_entry(name: str, description: str, model: str, tools: list,
                      triggers: list, skills: list) -> dict:
    entry = {
        "name": name,
        "description": description,
        "model": model,
        "tools": tools,
        "dispatch_triggers": triggers,
        "capabilities": {},
        "path": f"agents/{name}.md",
    }
    if skills:
        entry["skills_orchestrated"] = skills
    return entry


# --------------------------------------------------------------------------- #
# Prose-doc editing (best-effort; warns when a target can't be located)
# --------------------------------------------------------------------------- #

def bump_first_count(text: str, pattern: str, delta: int = 1) -> tuple[str, bool]:
    """Increment the first integer captured by `pattern` (one capture group)."""
    m = re.search(pattern, text)
    if not m:
        return text, False
    new_val = str(int(m.group(1)) + delta)
    start, end = m.span(1)
    return text[:start] + new_val + text[end:], True


def append_row_after_heading(text: str, heading_substr: str, row: str) -> tuple[str, bool]:
    """Insert `row` after the last contiguous table row following a heading."""
    lines = text.splitlines()
    hi = next((i for i, ln in enumerate(lines) if heading_substr in ln), None)
    if hi is None:
        return text, False
    # Find the table body that follows the heading.
    i = hi + 1
    n = len(lines)
    while i < n and not lines[i].lstrip().startswith("|"):
        if lines[i].strip().startswith("#"):  # next heading before any table
            return text, False
        i += 1
    if i >= n:
        return text, False
    last_row = i
    while i < n and lines[i].lstrip().startswith("|"):
        last_row = i
        i += 1
    lines.insert(last_row + 1, row)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True


def edit_readme_for_agent(text: str, name: str, description: str, category: str,
                          warnings: list) -> str:
    text, ok = bump_first_count(text, r"(\d+) agents")
    if not ok:
        warnings.append("agents/README.md: could not find the 'N agents' count to bump.")
    heading = README_CATEGORY_HEADINGS[category]
    row = f"| [{_title(name)}]({name}.md) | `{name}.md` | {description} |"
    text, ok = append_row_after_heading(text, heading, row)
    if not ok:
        warnings.append(f"agents/README.md: could not locate the '{heading}' table; "
                        f"add this row manually:\n    {row}")
    warnings.append("agents/README.md: the prose sub-breakdown (e.g. 'N role-based … M "
                    "pipeline') was NOT auto-derived — review the Overview line.")
    return text


def edit_architecture_for_agent(text: str, name: str, description: str, tools: list,
                                warnings: list) -> str:
    text, ok = bump_first_count(text, r"## 7\. Agent inventory \((\d+)\)")
    if not ok:
        warnings.append("ARCHITECTURE.md: could not bump '## 7. Agent inventory (N)'.")
    text, ok = bump_first_count(text, r"Remaining (\d+) agents")
    if not ok:
        warnings.append("ARCHITECTURE.md: could not bump the 'Remaining N agents' count.")
    row = f"| {name} | {description} | {', '.join(tools)} | (lazy-dispatched) |"
    text, ok = append_row_after_heading(text, "## 7. Agent inventory", row)
    if not ok:
        warnings.append("ARCHITECTURE.md: could not locate the agent inventory table; "
                        f"add this row manually:\n    {row}")
    return text


def edit_architecture_for_skill(text: str, name: str, description: str,
                                warnings: list) -> str:
    text, ok = bump_first_count(text, r"## 8\. Skill inventory \((\d+)\)")
    if not ok:
        warnings.append("ARCHITECTURE.md: could not bump '## 8. Skill inventory (N)'.")
    text, ok = bump_first_count(text, r"Remaining \d+ agents \+ (\d+) skills")
    if not ok:
        warnings.append("ARCHITECTURE.md: could not bump the 'N skills' lazy-dispatch count.")
    # Skill inventory has 5 category sub-tables; don't guess. Emit the row text.
    row = f"| {name} | {description} |"
    warnings.append("ARCHITECTURE.md §8: choose a skill category sub-table and add this "
                    f"row manually:\n    {row}")
    return text


# --------------------------------------------------------------------------- #
# Scaffolding
# --------------------------------------------------------------------------- #

def _trigger_lines(triggers: list) -> str:
    return "\n".join(f"  - {t}" for t in triggers)


def render_skill_md(name: str, description: str, triggers: list) -> str:
    hint = ", ".join(f'"{t}"' for t in triggers[:3]) or f'"{name}"'
    return SKILL_TEMPLATE.format(
        name=name, title=_title(name), description=description.rstrip("."),
        trigger_hint=hint, trigger_lines=_trigger_lines(triggers),
    )


def render_agent_md(name: str, description: str, model: str, tools: list,
                    triggers: list, skills: list) -> str:
    if skills:
        skills_rows = "\n".join(f"| {s} | [TODO: when] | Skill tool |" for s in skills)
    else:
        skills_rows = "| [TODO: skill] | [TODO: when] | Skill tool |"
    return AGENT_TEMPLATE.format(
        name=name, title=_title(name), description=description, model=model,
        tools_csv=", ".join(tools), trigger_lines=_trigger_lines(triggers),
        prefix=_constraint_prefix(name), skills_rows=skills_rows,
    )


# --------------------------------------------------------------------------- #
# Core driver
# --------------------------------------------------------------------------- #

class Plan:
    """Accumulates staged file changes for dry-run preview and atomic apply."""

    def __init__(self):
        # path -> (old_text, new_text); old_text == "" means a new file.
        self.changes: dict[Path, tuple[str, str]] = {}

    def stage(self, path: Path, new_text: str):
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        self.changes[path] = (old, new_text)

    def diff(self) -> str:
        out = []
        for path, (old, new) in self.changes.items():
            label = str(path)
            d = difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True),
                fromfile=f"a/{label}" + (" (new)" if old == "" else ""),
                tofile=f"b/{label}", n=2,
            )
            rendered = "".join(d)
            if not rendered:
                rendered = (f"--- {label}: (new empty file)\n" if old == ""
                            else f"--- {label}: (no textual change)\n")
            out.append(rendered)
        return "\n".join(out)

    def apply(self):
        written: list[Path] = []
        try:
            for path, (_old, new) in self.changes.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(new, encoding="utf-8")
                written.append(path)
        except Exception:
            # Roll back everything written so far.
            for path in written:
                old = self.changes[path][0]
                if old == "":
                    path.unlink(missing_ok=True)
                else:
                    path.write_text(old, encoding="utf-8")
            raise


def validate_candidate_manifest(manifest: dict) -> list:
    """Run the repo's manifest validator against the candidate manifest."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=True) as tf:
        tf.write(dump_manifest(manifest))
        tf.flush()
        return vm.validate_manifest(Path(tf.name))


def run(args) -> int:
    root = Path(args.root).resolve() if args.root else _HERE.parents[2]
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        emit_error(EXIT_ERROR, f"manifest.json not found at {manifest_path}",
                   "Pass --root pointing at the claude-code/ directory.")
        return EXIT_ERROR

    name = args.name
    if not NAME_RE.match(name) or len(name) > 40:
        emit_error(EXIT_INVALID_ARGS, f"Invalid name '{name}'.",
                   "Use kebab-case (lowercase, digits, hyphens), max 40 chars.")
        return EXIT_INVALID_ARGS

    manifest = load_manifest(manifest_path)
    warnings: list = []
    plan = Plan()

    # --- conflict checks -------------------------------------------------- #
    if name_exists(manifest, args.kind, name):
        emit_error(EXIT_ERROR, f"A {args.kind} named '{name}' already exists in the manifest.")
        return EXIT_ERROR

    triggers = [t.strip() for t in (args.triggers or "").split(",") if t.strip()]
    if not triggers:
        triggers = [name.replace("-", " ")]
    description = (args.description or "").strip() or f"TODO: describe the {name} {args.kind}."

    if args.kind == "skill":
        skill_dir = root / "skills" / name
        if skill_dir.exists():
            emit_error(EXIT_ERROR, f"Skill directory already exists: {skill_dir}")
            return EXIT_ERROR
        has_scripts = bool(args.scripts)
        has_references = bool(args.references)
        chaining = None
        if args.for_agent:
            chaining = {"produces": [], "consumes_from": [], "chains_to": [],
                        "chains_from": [], "patterns": []}
        # Scaffold files
        plan.stage(skill_dir / "SKILL.md", render_skill_md(name, description, triggers))
        if has_scripts:
            plan.stage(skill_dir / "scripts" / "__init__.py", "")
        if has_references:
            plan.stage(skill_dir / "references" / "README.md",
                       f"# {_title(name)} — references\n\n[TODO: reference material]\n")
        # Manifest entry + stats
        manifest.setdefault("skills", []).append(
            build_skill_entry(name, description, triggers, has_scripts, has_references, chaining))
        manifest["stats"]["total_skills"] = manifest["stats"].get("total_skills", 0) + 1
        # Wire skill -> agent
        if args.for_agent:
            agent = next((a for a in manifest.get("agents", [])
                          if a.get("name") == args.for_agent), None)
            if agent is None:
                emit_error(EXIT_ERROR, f"--for-agent: no agent named '{args.for_agent}'.")
                return EXIT_ERROR
            agent.setdefault("skills_orchestrated", [])
            if name not in agent["skills_orchestrated"]:
                agent["skills_orchestrated"].append(name)
            warnings.append(f"agents/{args.for_agent}.md: add a row for '{name}' to the "
                            f"agent's 'Mandatory Skills' table.")
        # Prose docs
        arch_path = root / "ARCHITECTURE.md"
        if arch_path.exists():
            plan.stage(arch_path, edit_architecture_for_skill(
                arch_path.read_text(encoding="utf-8"), name, description, warnings))

    else:  # agent
        agent_file = root / "agents" / f"{name}.md"
        if agent_file.exists():
            emit_error(EXIT_ERROR, f"Agent file already exists: {agent_file}")
            return EXIT_ERROR
        model = args.model or "sonnet"
        if model not in VALID_MODELS:
            emit_error(EXIT_INVALID_ARGS, f"Invalid --model '{model}'.",
                       f"Choose one of {', '.join(VALID_MODELS)}.")
            return EXIT_INVALID_ARGS
        tools = ([t.strip() for t in args.tools.split(",") if t.strip()]
                 if args.tools else list(DEFAULT_AGENT_TOOLS))
        skills = [s.strip() for s in (args.skills or "").split(",") if s.strip()]
        category = args.category or "pipeline"
        # Validate referenced skills exist (cross-ref integrity).
        known_skills = {s.get("name") for s in manifest.get("skills", [])}
        missing = [s for s in skills if s not in known_skills]
        if missing:
            emit_error(EXIT_ERROR, f"--skills references unknown skill(s): {', '.join(missing)}.")
            return EXIT_ERROR
        # Scaffold file
        plan.stage(agent_file, render_agent_md(name, description, model, tools, triggers, skills))
        # Manifest entry + stats
        manifest.setdefault("agents", []).append(
            build_agent_entry(name, description, model, tools, triggers, skills))
        manifest["stats"]["total_agents"] = manifest["stats"].get("total_agents", 0) + 1
        # Prose docs
        readme_path = root / "agents" / "README.md"
        if readme_path.exists():
            plan.stage(readme_path, edit_readme_for_agent(
                readme_path.read_text(encoding="utf-8"), name, description, category, warnings))
        arch_path = root / "ARCHITECTURE.md"
        if arch_path.exists():
            plan.stage(arch_path, edit_architecture_for_agent(
                arch_path.read_text(encoding="utf-8"), name, description, tools, warnings))

    # --- stage the manifest + validate ----------------------------------- #
    plan.stage(manifest_path, dump_manifest(manifest))
    errors = validate_candidate_manifest(manifest)
    if errors:
        emit_error(EXIT_ERROR, "Manifest validation failed — no files written.",
                   "\n".join(errors[:20]))
        return EXIT_ERROR

    if args.dry_run:
        emit_info(f"[DRY-RUN] would create/modify {len(plan.changes)} file(s):")
        print(plan.diff())
        for w in warnings:
            emit_warning(w)
        return EXIT_SUCCESS

    plan.apply()
    emit_info(f"Added {args.kind} '{name}'. Files written: {len(plan.changes)}.")
    for w in warnings:
        emit_warning(w)
    emit_info("Next: run `./install.sh` then `./install.sh --check` to deploy and verify.")
    return EXIT_SUCCESS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="extend.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="kind", required=True)

    def common(sp):
        sp.add_argument("name")
        sp.add_argument("--description", default="")
        sp.add_argument("--triggers", default="", help='comma-separated trigger phrases')
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--root", default="", help="path to claude-code/ (default: auto)")

    sk = sub.add_parser("skill", help="add a new skill")
    common(sk)
    sk.add_argument("--for-agent", default="", help="wire the skill into this agent")
    sk.add_argument("--scripts", action="store_true", help="create a scripts/ dir")
    sk.add_argument("--references", action="store_true", help="create a references/ dir")

    ag = sub.add_parser("agent", help="add a new agent")
    common(ag)
    ag.add_argument("--model", default="sonnet", choices=VALID_MODELS)
    ag.add_argument("--tools", default="", help="comma-separated tool names")
    ag.add_argument("--category", default="pipeline",
                    choices=list(README_CATEGORY_HEADINGS))
    ag.add_argument("--skills", default="", help="comma-separated skills_orchestrated")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    # argparse stores --for-agent as for_agent etc.; normalize optional attrs.
    for attr in ("for_agent", "scripts", "references", "model", "tools", "category", "skills"):
        if not hasattr(args, attr):
            setattr(args, attr, None)
    try:
        return run(args)
    except Exception as e:  # noqa: BLE001
        emit_error(EXIT_ERROR, f"Unexpected failure: {e}")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
