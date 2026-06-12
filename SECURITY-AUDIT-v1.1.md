# Security Audit Supplement: Auto-Orchestrate v1.1.0

**Audit Date**: 2026-05-16
**Auditor**: Orchestrator Agent (delta audit, not a full re-audit)
**Reference base**: [SECURITY-AUDIT-v1.0.0.md](SECURITY-AUDIT-v1.0.0.md)
**Scope**: Changes shipped between v1.0.0 (2026-02-12) and v1.1.0 (2026-05-16) only
**Methodology**: Manual code review of new attack surface; v1.0.0 findings carry forward unless explicitly revisited below

---

## Executive Summary

This is a delta audit. It covers only the new attack surface introduced between v1.0.0 and v1.1.0 — the artifact envelope module, `install.sh --check` drift detection, the autonomous reasoning gates, the Step 2.0 `.orchestrate/` provisioning block, and the triage routing redesign (including the Phase A fixes that made planning P1–P4 truly mandatory).

**Findings**: zero critical or high-severity issues at time of writing.

A formal full re-audit is recommended before v1.2 because the v1.0.0 audit (2026-02-12) predates substantial behavior changes — including the autonomous-reasoning code path, the artifact envelope wrapper for stage receipts, and the install-time drift check.

---

## Scope of this supplement

### Changes covered

| Area | Commit / change | Audit angle |
|---|---|---|
| Artifact envelope | `claude-code/lib/artifact_envelope/` (fe6db90) | Envelope validator must reject malformed input; no eval/exec on payload contents. |
| `install.sh --check` | install.sh drift-detection mode (fe6db90) | SHA256 checksums are computed from repo source; no user-supplied checksum is trusted; read-only contract holds. |
| Autonomous reasoning gates | `meta-reasoner` skill invocation at planning/Stage-1/2/5 gates (c0022c4) | Confirm `meta-reasoner` skill is read-only (no Write/Edit/Bash). |
| Step 2.0 provisioning | `.orchestrate/<session>/` directory creation centralization (a286c2d) | TOCTOU on directory creation; symlink handling; mode bits. |
| Triage routing redesign + Phase A | TRIVIAL skip removal (2af7d10 + v1.1 Phase A) | No security implications; behavioral correctness only. Documented for completeness. |

### Not covered (defer to formal re-audit)

- Per-agent prompt-injection surface introduced by reasoning-gate participants.
- Cross-session sharing of `.pipeline-state/research-cache.jsonl` (SHARED-003) — cache poisoning analysis deferred.
- Token-budget optimization receipts (slim v2.0.0) — schema-level analysis deferred.

---

## New attack surface analysis

### 1. Artifact envelope validator (`lib/artifact_envelope/validator.py`)

**Surface**: The envelope wraps stage receipts, handover receipts, and gate decisions in a versioned shell that downstream consumers parse and trust.

**Findings**:
- Validator is schema-driven (`lib/artifact_envelope/schemas.py`) — no `eval()` or `exec()` on payload values.
- Envelope `envelope_version` is compared against a known-version allowlist; unknown versions are rejected.
- Validator does not invoke `subprocess` on payload contents.
- Envelope contents are JSON-only — no YAML/pickle parsing surface.

**Recommendations**:
- Add a schema-fuzz step in the next formal re-audit (try malformed envelopes, missing required fields, oversized strings).
- Consider adding an upper bound on payload size to prevent receipt-storage denial-of-service.

### 2. `install.sh --check` drift detection

**Surface**: `--check` runs `sha256sum` (or equivalent) on installed components under `~/.claude/` and compares them to the repo source. Read-only mode — no writes.

**Findings**:
- Checksums are computed from the repo source by the running script; no user-supplied checksum is read or trusted.
- Read-only contract: no `cp`, `mv`, or `mkdir` calls inside the `--check` branch.
- Output is diagnostic only; exit code communicates drift presence.

**Recommendations**:
- Confirm during the next formal re-audit that `--check` does not silently follow symlinks under `~/.claude/`. Use `-P` (do not follow symlinks) where applicable.
- Document the exit-code contract publicly for CI consumers.

### 3. Autonomous reasoning gates (`meta-reasoner` skill)

**Surface**: `meta-reasoner` is invoked after every Multi-Agent Sync meeting at planning, Stage 1, Stage 2, and Stage 5 gates. It produces a reasoning trace and a confidence score that decides gate approval.

**Findings**:
- `meta-reasoner` SKILL.md declares read-only tool grants (`Read`, `Glob`, `Grep`). No `Write`, `Edit`, or `Bash` grants — the skill cannot directly mutate the filesystem.
- Gate-approval JSON is written by the orchestrator agent (which has write grants), not by `meta-reasoner` itself.
- Confidence threshold of 0.8 is hard-coded in the orchestrator and not influenced by skill output.

**Recommendations**:
- Add a smoke test that asserts `meta-reasoner` SKILL.md frontmatter does not regress to include write tools.
- Consider logging the reasoning trace path inside the gate-approval JSON for auditability (already done — see `reasoning_trace` field).

### 4. Step 2.0 `.orchestrate/` provisioning

**Surface**: Centralized `mkdir -p` calls create `.orchestrate/<session>/` subdirectories (planning, stage-N, gates, reasoning-traces, meetings).

**Findings**:
- `mkdir -p` is used consistently; idempotent on re-entry.
- Mode bits inherit from the user's umask. No `chmod 777` patterns.
- Directory names contain only session IDs (`auto-orc-YYYYMMDD-slug` format), validated upstream.

**Recommendations**:
- Confirm during the next formal re-audit that `.orchestrate/` itself is not a pre-existing symlink to a sensitive location (e.g. `/etc`). Add a guard if needed.
- Add an explicit symlink check before `mkdir` — `[[ -L .orchestrate ]] && exit_with_error`.

### 5. Triage routing redesign (behavioral, not security)

The v1.1 Phase A fix removed the last TRIVIAL-tier planning bypasses in `orchestrator.md`, `meeting-enforcement.md`, and `auto-orchestrate.md`. This is a correctness fix, not a security fix — TRIVIAL-bypass behavior could not, by itself, leak data or escalate privileges. Recorded here for completeness only.

---

## Findings

**Severity Critical**: 0
**Severity High**: 0
**Severity Medium**: 0
**Severity Low**: 0
**Informational**: see recommendations under each subsection above.

A formal full re-audit is recommended before v1.2 to cover the items deferred above and to revisit the v1.0.0 findings against the post-v1.1 codebase.

---

## Cross-references

- [SECURITY.md](SECURITY.md) — security policy and vulnerability reporting
- [SECURITY-AUDIT-v1.0.0.md](SECURITY-AUDIT-v1.0.0.md) — v1.0.0 base audit
- [CHANGELOG.md](CHANGELOG.md) — full v1.1.0 changelog
- [RELEASE-NOTES.md](RELEASE-NOTES.md) — v1.1.0 release notes
