"""One-shot migration: flatten .domain/, .audit/, .pipeline-state/ under .orchestrate/.

Idempotent. Re-runs detect prior completion via the marker file
``.orchestrate/.migration-v1.done``. Use ``--keep-symlinks`` to leave
backwards-compat symlinks at the legacy roots for one release window.

Usage::

    python -m claude_code.scripts.migrate_to_unified_orchestrate \
        [--project-root .] [--keep-symlinks] [--dry-run] [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

LEGACY_ROOTS: dict[str, str] = {
    ".domain": "domain",
    ".audit": "audit",
    ".pipeline-state": "pipeline-state",
}

MARKER_NAME = ".migration-v1.done"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _count_lines(path: Path) -> int:
    if not path.exists() or path.is_dir():
        return 0
    with path.open("rb") as fh:
        return sum(1 for _ in fh)


def _merge_tree(src: Path, dst: Path, dry_run: bool) -> list[str]:
    """Copy contents of ``src`` into ``dst``, preserving JSONL line counts."""
    moves: list[str] = []
    for entry in src.rglob("*"):
        rel = entry.relative_to(src)
        target = dst / rel
        if entry.is_dir():
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
            continue
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            if entry.suffix == ".jsonl" and target.exists():
                src_lines = _count_lines(entry)
                dst_lines = _count_lines(target)
                with target.open("ab") as out, entry.open("rb") as inp:
                    out.write(inp.read())
                after_lines = _count_lines(target)
                if after_lines != src_lines + dst_lines:
                    raise RuntimeError(
                        f"JSONL line count mismatch after merge for {target}: "
                        f"expected {src_lines + dst_lines}, got {after_lines}"
                    )
            else:
                shutil.copy2(entry, target)
        moves.append(f"{entry} -> {target}")
    return moves


def _verify_post_merge(src: Path, dst: Path) -> None:
    """For JSONL files, assert dst >= src line counts."""
    for entry in src.rglob("*.jsonl"):
        rel = entry.relative_to(src)
        target = dst / rel
        if not target.exists():
            raise RuntimeError(f"Missing post-merge: {target}")
        if _count_lines(target) < _count_lines(entry):
            raise RuntimeError(
                f"Line count regression: {target} has fewer lines than {entry}"
            )


def _make_symlink(legacy: Path, new: Path) -> None:
    if legacy.exists() or legacy.is_symlink():
        return
    rel_target = os.path.relpath(new, start=legacy.parent)
    os.symlink(rel_target, legacy)


def migrate(
    project_root: Path,
    keep_symlinks: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, object]:
    project_root = project_root.resolve()
    base = project_root / ".orchestrate"
    marker = base / MARKER_NAME
    report: dict[str, object] = {
        "project_root": str(project_root),
        "started_at": _utc_now_iso(),
        "dry_run": dry_run,
        "keep_symlinks": keep_symlinks,
        "moves": {},
        "skipped": [],
        "status": "pending",
    }
    if marker.exists() and not force:
        report["status"] = "already_complete"
        report["marker_path"] = str(marker)
        return report
    if not dry_run:
        base.mkdir(parents=True, exist_ok=True)
        for sub in ("domain", "audit", "pipeline-state"):
            (base / sub).mkdir(parents=True, exist_ok=True)
        for sub in ("workflow", "command-receipts", "process-log",
                    "baselines", "improvement-recommender"):
            (base / "pipeline-state" / sub).mkdir(parents=True, exist_ok=True)
    for legacy_name, new_subname in LEGACY_ROOTS.items():
        legacy = project_root / legacy_name
        new = base / new_subname
        if not legacy.exists():
            report["skipped"].append(legacy_name)  # type: ignore[union-attr]
            continue
        moves = _merge_tree(legacy, new, dry_run)
        report["moves"][legacy_name] = moves  # type: ignore[index]
        if not dry_run:
            _verify_post_merge(legacy, new)
            shutil.rmtree(legacy)
            if keep_symlinks:
                _make_symlink(legacy, new)
    if not dry_run:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            json.dumps({"completed_at": _utc_now_iso(), "version": "1"}),
            encoding="utf-8",
        )
    report["status"] = "complete" if not dry_run else "dry_run"
    report["completed_at"] = _utc_now_iso()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-root", default=".", type=Path)
    parser.add_argument("--keep-symlinks", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Re-run even if marker is present")
    args = parser.parse_args(argv)
    try:
        report = migrate(
            project_root=args.project_root,
            keep_symlinks=args.keep_symlinks,
            dry_run=args.dry_run,
            force=args.force,
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure
        print(f"MIGRATION FAILED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
