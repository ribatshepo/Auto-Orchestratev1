#!/usr/bin/env python3
"""Deterministic-artifact completeness checker for auto-orchestrate sessions.

Reads manifest.yml (the contract) and validates a session folder against it.
Emits gates/gate-completeness-<TS>.json. Exits 0 on PASS, non-zero on FAIL.

Usage:
    python3 check-completeness.py --session-root .orchestrate/<sid> [--manifest path/to/manifest.yml]
    python3 check-completeness.py --lint               # validate manifest only

The checker treats every rule in manifest.yml as required unless required=false.
For one-per-deliverable / one-per-task cardinality, it cross-references
proposed-tasks.json so it can flag missing per-entity artifacts.

The script has zero non-stdlib dependencies — it parses manifest.yml with a
minimal YAML reader sufficient for the simple key:value / list-of-maps shape
used in this contract.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Minimal YAML loader (only handles the shapes used in manifest.yml)
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict[str, Any]:
    """Tiny YAML reader for our manifest shape.

    Supports:
      - top-level scalars
      - list of maps under a key (rules: / consistency_checks:)
      - per-list-item scalar key:value lines
      - block scalars with `|` for the description field
      - comment lines starting with #
    """
    text = path.read_text(encoding="utf-8")
    out: dict[str, Any] = {}
    current_list_key: str | None = None
    current_item: dict[str, Any] | None = None
    block_target: tuple[dict, str] | None = None
    block_lines: list[str] = []
    block_indent: int | None = None

    def flush_block() -> None:
        nonlocal block_target, block_lines, block_indent
        if block_target is not None:
            obj, key = block_target
            obj[key] = "\n".join(block_lines).rstrip()
        block_target = None
        block_lines = []
        block_indent = None

    for raw in text.splitlines():
        if block_target is not None:
            stripped = raw.rstrip()
            if not stripped:
                block_lines.append("")
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if block_indent is None:
                block_indent = indent
            if indent >= block_indent and stripped[0] != "#":
                block_lines.append(raw[block_indent:])
                continue
            flush_block()
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if indent == 0 and content.endswith(":"):
            key = content[:-1].strip()
            if key in ("rules", "consistency_checks"):
                out[key] = []
                current_list_key = key
                current_item = None
            else:
                current_list_key = None
                out[key] = ""
            continue
        if indent == 0 and ":" in content and not content.startswith("- "):
            key, _, value = content.partition(":")
            out[key.strip()] = _coerce(value.strip().strip('"'))
            current_list_key = None
            continue
        if current_list_key is not None and content.startswith("- "):
            current_item = {}
            out[current_list_key].append(current_item)
            content = content[2:]
            if ":" in content:
                key, _, value = content.partition(":")
                _assign(current_item, key.strip(), value.strip())
            continue
        if current_item is not None and ":" in content:
            key, _, value = content.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "|":
                block_target = (current_item, key)
                block_lines = []
                block_indent = None
            else:
                _assign(current_item, key, value)
    flush_block()
    return out


def _coerce(v: str) -> Any:
    if v == "true":
        return True
    if v == "false":
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v.strip('"')


def _assign(obj: dict[str, Any], key: str, value: str) -> None:
    obj[key] = _coerce(value.strip('"'))


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------

@dataclass
class RuleResult:
    rule_id: str
    path_pattern: str
    cardinality: str
    required: bool
    owner: str = ""
    template: str = ""
    matches: list[str] = field(default_factory=list)
    expected_min: int = 1
    missing: bool = False
    note: str = ""


@dataclass
class CheckReport:
    session_root: Path
    rules_total: int
    rules_satisfied: int
    rules_missing: list[RuleResult] = field(default_factory=list)
    consistency_failures: list[str] = field(default_factory=list)
    extra_paths: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        return "PASS" if not self.rules_missing and not self.consistency_failures else "FAIL"


def evaluate_rule(rule: dict[str, Any], session_root: Path, deliverables: list[str], tasks: list[str]) -> RuleResult:
    path_pattern = str(rule.get("path", ""))
    cardinality = str(rule.get("cardinality", "one"))
    required = bool(rule.get("required", True))
    rule_id = str(rule.get("id", "?"))
    owner = str(rule.get("owner", ""))
    template = str(rule.get("template", ""))

    expansions: list[str] = []
    if "{deliverable}" in path_pattern:
        for d in deliverables:
            expansions.append(path_pattern.replace("{deliverable}", d))
    if "{task}" in path_pattern:
        if not expansions:
            base = [path_pattern]
        else:
            base = expansions
            expansions = []
        for p in base:
            for t in tasks:
                expansions.append(p.replace("{task}", t))
    if not expansions:
        expansions = [path_pattern]
    for tok in ("{sid}", "{date}", "{ts}", "{stage}", "{gate}", "{process}", "{category}"):
        expansions = [p.replace(tok, "*") for p in expansions]
    matches: list[str] = []
    for pattern in expansions:
        for found in session_root.rglob("*"):
            rel = found.relative_to(session_root).as_posix()
            if fnmatch.fnmatch(rel, pattern):
                matches.append(rel)
    matches = sorted(set(matches))

    if cardinality == "one":
        expected_min = 1
    elif cardinality.startswith("one-per-"):
        if "deliverable" in cardinality:
            expected_min = max(1, len(deliverables))
        elif "task" in cardinality:
            expected_min = max(1, len(tasks))
        else:
            expected_min = 1
    elif cardinality == "one-or-more":
        expected_min = 1
    else:
        expected_min = 1

    missing = required and len(matches) < expected_min
    return RuleResult(
        rule_id=rule_id,
        path_pattern=path_pattern,
        cardinality=cardinality,
        required=required,
        owner=owner,
        template=template,
        matches=matches,
        expected_min=expected_min,
        missing=missing,
        note=f"found {len(matches)} of expected ≥ {expected_min}",
    )


def discover_deliverables_and_tasks(session_root: Path) -> tuple[list[str], list[str]]:
    proposed = session_root / "proposed-tasks.json"
    if not proposed.exists():
        return [], []
    try:
        data = json.loads(proposed.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], []
    deliverables: list[str] = []
    tasks: list[str] = []
    for t in data.get("tasks", []) or []:
        if isinstance(t, dict) and t.get("_template_example"):
            continue
        tid = t.get("id") if isinstance(t, dict) else None
        if isinstance(tid, str):
            tasks.append(tid)
        d = t.get("deliverable") if isinstance(t, dict) else None
        if isinstance(d, str) and d not in deliverables:
            deliverables.append(d)
    return sorted(deliverables), sorted(tasks)


def run_consistency_checks(
    deliverables: list[str],
    tasks: list[str],
    session_root: Path,
    allow_unrooted: bool = False,
) -> list[str]:
    failures: list[str] = []
    for d in deliverables:
        for required_path in (
            f"stage-0/{d}/research.md",
            f"stage-0/{d}/stage-receipt.json",
            f"stage-1/{d}/proposed-tasks.json",
            f"stage-1/{d}/stage-receipt.json",
        ):
            if not (session_root / required_path).exists():
                failures.append(f"CONS-001 missing for {d}: {required_path}")
        approvals = list((session_root / "stage-1" / d).glob(f"gate-approval-decomposition-{d}-*.json"))
        if not approvals:
            failures.append(f"CONS-001 missing for {d}: stage-1/{d}/gate-approval-decomposition-{d}-*.json")
    for t in tasks:
        for required_path in (
            f"stage-2/{t}/spec.md",
            f"stage-2/{t}/stage-receipt.json",
            f"stage-3/{t}/stage-receipt.json",
            f"stage-3/{t}/changes.md",
        ):
            if not (session_root / required_path).exists():
                failures.append(f"CONS-002 missing for {t}: {required_path}")
        approvals = list((session_root / "stage-2" / t).glob(f"gate-approval-task-creation-{t}-*.json"))
        if not approvals:
            failures.append(f"CONS-002 missing for {t}: stage-2/{t}/gate-approval-task-creation-{t}-*.json")
    for stage in ("stage-0", "stage-1", "stage-2", "stage-3", "stage-4", "stage-4.5", "stage-5", "stage-6"):
        receipts = list((session_root / "phase-receipts").glob(f"phase-{stage}-*.json"))
        if not receipts:
            failures.append(f"CONS-003 missing: phase-receipts/phase-{stage}-*.json")

    # CONS-004: domain-reviews/ must contain >=1 real review per stage in {2,3,5,6}.
    # Baseline qa-engineer reviews count; sentinel "*-none-*" files do not (ARTIFACT-COMPLETENESS-001).
    for stage in ("2", "3", "5", "6"):
        reviews = [
            p for p in (session_root / "domain-reviews").glob(f"*-stage-{stage}*.md")
            if "-none-" not in p.name
        ]
        if not reviews:
            failures.append(
                f"CONS-004 missing: domain-reviews/*-stage-{stage}*.md "
                f"(no real review fired; baseline qa-engineer review required per MAIN-017)"
            )

    # CONS-005: meetings/ must contain >=1 real meeting receipt; sentinels excluded.
    meetings = [
        p for p in (session_root / "meetings").glob("*.json")
        if "-none-" not in p.name
    ]
    if not meetings:
        failures.append(
            "CONS-005 missing: meetings/*.json "
            "(no real meeting receipt; sentinels excluded per ARTIFACT-COMPLETENESS-001)"
        )

    # CONS-006: reasoning-traces/ must contain >=1 trace (real or baseline).
    traces = list((session_root / "reasoning-traces").glob("*.json"))
    if not traces:
        failures.append("CONS-006 missing: reasoning-traces/*.json")

    # CONS-007: session root must live under .orchestrate/ (LAYOUT-GATE-001 / ORCHESTRATE-FLAT-001).
    if not allow_unrooted and session_root.parent.name != ".orchestrate":
        failures.append(
            f"CONS-007 layout: session_root {session_root} is not under .orchestrate/; "
            f"violates LAYOUT-GATE-001 / ORCHESTRATE-FLAT-001 (re-run with --allow-unrooted to bypass)"
        )

    return failures


def write_gate_artifact(session_root: Path, report: CheckReport) -> Path:
    gates_dir = session_root / "gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = gates_dir / f"gate-completeness-{ts}.json"
    payload = {
        "schema_version": "1.0.0",
        "artifact_type": "gate_completeness",
        "session_id": session_root.name,
        "gate_id": "completeness",
        "produced_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "decided_by": "check-completeness.py",
        "verdict": report.verdict,
        "rules_total": report.rules_total,
        "rules_satisfied": report.rules_satisfied,
        "rules_missing": [
            {
                "rule_id": r.rule_id,
                "owner": r.owner,
                "template": r.template,
                "path_pattern": r.path_pattern,
                "cardinality": r.cardinality,
                "expected_min": r.expected_min,
                "found": len(r.matches),
                "note": r.note,
            }
            for r in report.rules_missing
        ],
        "consistency_failures": report.consistency_failures,
        "extra_paths": report.extra_paths,
        "remediation": _remediation(report),
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


_CONS_REMEDIATION: dict[str, str] = {
    "CONS-001": "Spawn researcher (project-wide) and/or product-manager to fill the missing per-deliverable stage-0/stage-1 slots; cite ARTIFACT-CONTRACT-001.",
    "CONS-002": "Spawn spec-creator (stage-2) + software-engineer (stage-3) for the missing per-task slots; cite ARTIFACT-CONTRACT-001.",
    "CONS-003": "Orchestrator writes phase-receipts/phase-stage-<N>-<TS>.json from templates/orchestrate-session/phase-receipts/phase-receipt.json (MAIN-017 Stage-Close Protocol Part 1.1).",
    "CONS-004": "Spawn qa-engineer for baseline domain review (MAIN-017 Stage-Close Protocol Part 1.2 else-branch); template templates/orchestrate-session/domain-reviews/domain-review.md.",
    "CONS-005": "Spawn engineering-manager for baseline stage-close check-in meeting (MAIN-017 Stage-Close Protocol Part 1.4); template templates/orchestrate-session/meetings/meeting-baseline-stage.json.",
    "CONS-006": "Orchestrator writes a baseline reasoning trace (MAIN-017 Stage-Close Protocol Part 1.3); template templates/orchestrate-session/reasoning-traces/reasoning-trace-baseline.json.",
    "CONS-007": "Session is misplaced outside .orchestrate/; run `mv <sid> .orchestrate/<sid>` (LAYOUT-GATE-001 self-heal in auto-orchestrate.md Step 3.0).",
}


def _remediation(report: CheckReport) -> list[str]:
    out: list[str] = []
    for r in report.rules_missing:
        owner = r.owner or "<unknown>"
        template = r.template or "<see manifest>"
        out.append(
            f"Spawn {owner} to emit {r.path_pattern} "
            f"({r.cardinality}, ≥ {r.expected_min}); "
            f"template templates/orchestrate-session/{template}; "
            f"rule {r.rule_id}"
        )
    for f in report.consistency_failures:
        code = f.split(" ", 1)[0] if " " in f else ""
        hint = _CONS_REMEDIATION.get(code, "")
        out.append(f"{f}{(' — ' + hint) if hint else ''}")
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Deterministic-artifact completeness checker.")
    parser.add_argument("--session-root", type=Path, help="Path to .orchestrate/<sid>/")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).parent / "manifest.yml")
    parser.add_argument("--lint", action="store_true", help="Validate manifest only; no session check")
    parser.add_argument(
        "--allow-unrooted",
        action="store_true",
        help="Forensic standalone runs: do not fail CONS-007 when session_root is outside .orchestrate/",
    )
    args = parser.parse_args(argv)

    manifest = _load_yaml(args.manifest)
    rules = manifest.get("rules", []) or []
    if args.lint:
        ok = True
        for r in rules:
            for k in ("id", "path", "template", "owner", "cardinality"):
                if k not in r:
                    print(f"[LINT] rule missing key '{k}': {r}", file=sys.stderr)
                    ok = False
        if ok:
            print(f"[LINT] manifest OK: {len(rules)} rules")
            return 0
        return 1

    if args.session_root is None:
        print("--session-root is required (unless --lint).", file=sys.stderr)
        return 2

    session_root = args.session_root.resolve()
    if not session_root.exists():
        print(f"[ERROR] session root does not exist: {session_root}", file=sys.stderr)
        return 2

    deliverables, tasks = discover_deliverables_and_tasks(session_root)
    results: list[RuleResult] = []
    for r in rules:
        results.append(evaluate_rule(r, session_root, deliverables, tasks))
    missing = [r for r in results if r.missing]
    consistency = run_consistency_checks(deliverables, tasks, session_root, allow_unrooted=args.allow_unrooted)
    report = CheckReport(
        session_root=session_root,
        rules_total=len(results),
        rules_satisfied=len(results) - len(missing),
        rules_missing=missing,
        consistency_failures=consistency,
    )
    out_path = write_gate_artifact(session_root, report)
    print(f"verdict: {report.verdict}")
    print(f"rules: {report.rules_satisfied}/{report.rules_total} satisfied")
    print(f"consistency_failures: {len(report.consistency_failures)}")
    print(f"gate artifact written: {out_path}")
    if report.verdict == "FAIL":
        print("\nMissing artifacts (rule_id | owner | path | note):")
        for r in report.rules_missing:
            owner = r.owner or "<unknown>"
            print(f"  - [{r.rule_id}] owner={owner}  {r.path_pattern}  ({r.note})")
        if report.consistency_failures:
            print("\nConsistency failures:")
            for f in report.consistency_failures:
                print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
