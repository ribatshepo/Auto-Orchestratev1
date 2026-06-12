# Auto-Orchestrate Pipeline Playbook

Operational guide for running `/auto-orchestrate` end-to-end. For concepts and architecture see [README.md](README.md) and [claude-code/ARCHITECTURE.md](claude-code/ARCHITECTURE.md); for constraint and flag details see [`claude-code/commands/auto-orchestrate.md`](claude-code/commands/auto-orchestrate.md).

`/auto-orchestrate` is the **single user-facing command**. What used to be separate Audit, Debug, Domain analysis, Release, Post-Launch, and Continuous Governance commands now run as **internal phases** inside the single autonomous loop. The internal phase boundaries are: Stage 0–6 execution, Phase 5e (Debug sub-loop), Phase 5v (Compliance Verdict), Phase 5q/5s/5i/5d (domain analysis when scope flags fire), Phase 7 (Release), Phase 8 (Post-Launch), Phase 9 (Continuous Governance) — all controlled by `PHASE-LOOP-001`.

## Table of contents

1. [When to use it](#1-when-to-use-it) — entry-point decision guide
2. [Pre-flight](#2-pre-flight) — first-time and per-session checks
3. [Scenario walkthroughs](#3-scenario-walkthroughs) — common end-to-end flows
4. [Flag cookbook](#4-flag-cookbook) — recipes for common combinations
5. [Reading pipeline output](#5-reading-pipeline-output) — logs, checkpoints, receipts
6. [Failure modes and recovery](#6-failure-modes-and-recovery) — terminal states and what to do
7. [Internal phase escalation](#7-internal-phase-escalation) — Phase 5v / 5e mechanics
8. [Troubleshooting](#8-troubleshooting) — common issues and fixes

---

## 1. When to use it

### Decision table

| You want to... | Run | Notes |
|---------------|-----|-------|
| Ship a feature or complete scope on an existing codebase | `/auto-orchestrate <task>` | Full pipeline; P1–P4 mandatory for all triage tiers |
| Fullstack production-ready build with formal planning artifacts | `/auto-orchestrate S <task>` | Scope flag `S` forces complex triage signals |
| Backend-only or frontend-only work | `/auto-orchestrate B <task>` or `F <task>` | Single-scope hints to the triage classifier |
| Verify a codebase matches a spec | `/auto-orchestrate <task> --audit-spec=<spec.md>` | Audit runs internally as Phase 5v |
| Debug a specific error or failing test | Pass the error in `<task>`; if Stage 5 validation fails, the pipeline auto-enters Phase 5e (Debug) | Debug Entry is a human gate (HUMAN-GATE-001 boundary 5) |
| Trivial one-liner that genuinely doesn't need P1–P4 | `/auto-orchestrate --skip-planning <task>` | `--skip-planning` is the **only** flag-based P1–P4 bypass |
| Resume the most recent in-progress session | `/auto-orchestrate c` | Continues from the last checkpoint |

### Quick decision tree

```
Are you handing off planning artifacts from a prior session?
├─ Yes → /auto-orchestrate c   (handoff reads planning_complete: true from receipt)
└─ No:
    Is this a true one-liner / typo / dependency bump?
    ├─ Yes → /auto-orchestrate --skip-planning <task>
    │           (+ optional --fast-path for 3-stage bypass; --fast-path requires --skip-planning)
    └─ No → /auto-orchestrate [B|F|S] <task>
              (P1–P4 will run; triage tier drives research depth, not planning skip)
```

### Which scope flag?

| Flag | Use when | Triage tier most likely | Research depth default |
|------|----------|--------------------------|------------------------|
| *(none)* | Custom objective, no stack-wide constraints | `trivial` or `medium` based on signals | minimal or normal |
| `B` | Backend-only work (models, APIs, services, migrations) | `medium` | normal |
| `F` | Frontend-only work (pages, forms, UI) | `medium` | normal |
| `S` | Fullstack production-ready build | `complex` | deep |

Triage classification only controls research depth, process scope tier, and enforcement tier. It **does not** control whether planning, gates, or stages execute — those always run unless you pass `--skip-planning`.

---

## 2. Pre-flight

### First-time setup (once per machine)

```bash
# Verify the Claude Code manifest exists and lists the orchestrator
test -f ~/.claude/manifest.json && grep -q '"orchestrator"' ~/.claude/manifest.json \
    && echo "OK" || echo "MISSING — install auto-orchestrate components"

# Verify the artifact-contract templates are installed (ARTIFACT-CONTRACT-001)
test -f ~/.claude/templates/orchestrate-session/manifest.yml \
    && python3 ~/.claude/templates/orchestrate-session/check-completeness.py --lint \
    || echo "MISSING — re-run ./install.sh; the templates tree was added in 2026-05"

# Verify install integrity (read-only drift check, no writes)
./install.sh --check
```

### Per-session checks (before running)

| Check | Command | What "good" looks like |
|-------|---------|------------------------|
| Clean working tree | `git status` | No uncommitted changes that might conflict with pipeline writes |
| On a feature branch (not main) | `git branch --show-current` | `feature/<descriptor>` or similar — **never run on `main`** |
| No stale in-progress session | `ls -la .orchestrate/*/checkpoint.json 2>/dev/null` | Either empty or all have `"status": "completed"` or `"superseded"` |
| Node/Python toolchain present if needed | `node --version`, `python3 --version` | Whatever your project requires |
| Network access for WebSearch | `curl -s https://pypi.org > /dev/null && echo ok` | Required for researcher at `normal`/`deep`/`exhaustive` tiers |

### Session directories the pipeline creates

```
.orchestrate/<session-id>/     # Per-session checkpoint + stage outputs (created in Step 2.0)
  ├── checkpoint.json          # State of truth (read this to inspect progress)
  ├── MANIFEST.jsonl           # Append-only session manifest
  ├── proposed-tasks.json      # Latest task proposals from orchestrator
  ├── continuity-brief.md      # Pre-P1 hand-off context from continuity-scout
  ├── raid-log.json            # Append-only RAID log (RAID-001)
  ├── planning/                # P1-P4 artifacts + sprint-kickoff-receipt
  ├── stage-{0..6}/            # Per-stage outputs + per-deliverable/per-task subdirs (ART-S0-* … ART-S6-*)
  ├── gates/                   # gate-pending/gate-approval/gate-conditional/gate-completeness + gate-history.jsonl
  ├── handovers/               # handover-<from>-to-<to>-<stage>.json receipts
  ├── meetings/                # Multi-Agent Sync minutes + canonical ceremonies (P-027/028/029)
  ├── domain-reviews/          # <agent>-stage-<N>.md (real review per stage; baseline when no ACT rule fires)
  ├── phase-receipts/          # phase-stage-<N>-*.json (every stage close) + sub-phase receipts
  └── reasoning-traces/        # meta-reasoner DECOMPOSE→SOLVE→VERIFY→SYNTHESIZE→REFLECT traces

.pipeline-state/               # Cross-pipeline shared state
  └── command-receipts/        # Per-run command receipts
```

The full per-folder contract — required files, cardinalities, owner agents, schemas — lives in `~/.claude/templates/orchestrate-session/manifest.yml`. The orchestrator runs `check-completeness.py` against this contract at Step 7 (before terminal-state); see §6 for the `INCOMPLETE_ARTIFACTS` terminal state.

---

## 3. Scenario walkthroughs

### Scenario A: New feature on an existing codebase

```bash
git checkout -b feature/add-user-profile-edits
/auto-orchestrate B Add an endpoint POST /users/me/profile that updates first_name and last_name. Validate length 1-50, return 200 with updated user. Add migration if needed.
```

What happens:

- Triage classifies as `medium` (single B scope flag, "add" keyword, 1–2 deliverables).
- Research depth defaults to `normal`.
- P1–P4 planning runs (mandatory). Each planning gate runs a Multi-Agent Sync meeting + meta-reasoner; gates that pass at confidence ≥ 0.8 auto-approve.
- Stage 0 research → Stage 1 decomposition → Stage 2 task specs → Stage 3 implementation → Stage 4 tests → Stage 4.5 refactor metrics → Stage 5 validation (with Phase 5v Compliance Verdict human gate by default) → Stage 6 documentation.

### Scenario B: Fullstack production-ready build

```bash
git checkout -b feature/notifications-mvp
/auto-orchestrate S Build an in-app notifications MVP: backend table + REST endpoints, frontend bell icon + dropdown, real-time push via SSE, unit + integration tests, OpenAPI docs.
```

Scope `S` forces `complex` triage signals; depth defaults to `deep`. P1–P4 runs with reasoning gates; expect Stage 3 to spawn multiple software-engineers in parallel (cap 5) per `PARALLEL-001/002/003`.

### Scenario C: Trivial single-line change

```bash
git checkout -b chore/bump-requests-version
/auto-orchestrate --skip-planning Bump requests from 2.31.0 to 2.32.0 in pyproject.toml.
```

`--skip-planning` is the only flag-based way to bypass P1–P4. Without it, planning runs regardless of triage tier. Pair with `--fast-path` for a 3-stage bypass (researcher → software-engineer → validator skill) when the orchestrator confirms only one agent is needed:

```bash
/auto-orchestrate --skip-planning --fast-path Bump requests from 2.31.0 to 2.32.0 in pyproject.toml.
```

### Scenario D: Stage 5 validation fails → internal Debug

When Stage 5 validation fails 3 fix-verify cycles, the pipeline writes `gates/gate-pending-debug_entry.json` (HUMAN-GATE-001 boundary 5) and polls for `gate-approval-debug_entry.json`. Approve to enter Phase 5e (internal Debug sub-loop). There is **no separate `/auto-debug` command** — Phase 5e is internal per `PHASE-LOOP-001`.

To approve manually mid-session:

```bash
echo '{"decision":"approved","reason":"investigate","decided_by":"user"}' \
    > .orchestrate/<session>/gates/gate-approval-debug_entry.json
```

### Scenario E: Spec compliance audit (internal Phase 5v)

The Phase 5v Compliance Verdict gate fires at the end of Stage 5 (HUMAN-GATE-001 boundary 6). The `auditor` agent runs as part of Phase 5v and writes `compliance-report.md` under `stage-5/`. The reasoning gate produces a `recommended_verdict` (PASS/FAIL/INDETERMINATE) shown in the gate-pending JSON; human signs off via `gate-approval-compliance_verdict.json`. No separate audit command is needed.

### Scenario F: Release pipeline

Pass `--release` (or `release_flag=true` in the task description) to mark the pipeline for release-readiness checks. Stage 5 then includes `sre` and `infra-engineer` participants. Phase 7 Release Readiness is a human gate (HUMAN-GATE-001 boundary 8). CAB Review (boundary 7) fires automatically before Phase 7 when the change is classified HIGH or CRITICAL risk per `CAB-GATE-001`.

```bash
git checkout -b release/v1.2.0
/auto-orchestrate S --release Cut v1.2.0 release with CHANGELOG, release notes, deployment runbook, observability runbook.
```

---

## 4. Flag cookbook

### Cost control

```bash
# Cap total iterations
/auto-orchestrate --max_iterations=80 <task>

# Tighter stall threshold (terminate after 5 zero-progress iterations)
/auto-orchestrate --stall_threshold=5 <task>

# Cap total tasks the orchestrator may propose
/auto-orchestrate --max_tasks=20 <task>
```

### Human-in-the-loop (more oversight)

```bash
# Restore legacy human gating for the four planning gates (Intent Review,
# Scope Lock, Dependency Acceptance, Sprint Readiness). Reasoning gates
# remain the default.
/auto-orchestrate --human-planning-gates <task>

# Restore human gating for the per-deliverable decomposition (Stage 1)
/auto-orchestrate --human-decomposition-gates <task>

# Restore human gating for the per-story task-spec creation (Stage 2)
/auto-orchestrate --human-task-creation-gates <task>
```

### Rigorous research for risky work

```bash
# Force the deep tier regardless of triage
/auto-orchestrate --research-depth=deep <task>

# Top tier — domain-partitioned research (security / performance / operational / UX)
/auto-orchestrate --research-depth=exhaustive <task>
```

### Recovering a stuck session

```bash
# Resume most recent
/auto-orchestrate c

# Raise the iteration cap and resume
/auto-orchestrate --max_iterations=200 c
```

### Trivial fast path

```bash
# Single-stage bypass (researcher → software-engineer → validator skill, 3 spawns total)
/auto-orchestrate --skip-planning --fast-path <task>
```

`--fast-path` requires `--skip-planning`. Triage alone does not trigger fast-path — both flags must be set explicitly.

### Docker validation

```bash
# Force docker-validator participation at Stage 5
/auto-orchestrate --docker <task>
```

---

## 5. Reading pipeline output

### Log prefix reference

While a pipeline runs, bracketed prefixes in output indicate what's happening. The important ones:

| Prefix | Meaning | Action |
|--------|---------|--------|
| `[STAGE N]` / `[P{N}:PLANNING]` | Stage boundary | Informational |
| `[GATE]` | Gate passed/failed | If FAILED, agent retries once |
| `[REASONING-GATE]` | Reasoning gate verdict + confidence | Informational; <0.8 downgrades to human gate |
| `[TRIAGE]` | Complexity classification + T-shirt size | Informational; shapes depth/enforcement tier |
| `[RESEARCH-DEPTH]` | Resolved tier + source | Informational; confirms tier selection |
| `[CHAIN-FIX]` | Auto-fixed missing `blockedBy` | Informational; no action needed |
| `[HUMAN-GATE]` | Pipeline paused for human review | Write the corresponding `gate-approval-<id>.json` |
| `[THRASH-001]` | State hash collision — system alternating | Pipeline will inject diagnostic task |
| `[AO-INEFF-001]` | Task stuck in_progress ≥ 5 iterations | Marked failed; stall counter doesn't reset |
| `[DIMINISH-001]` | Progress delta < 2% for 5 iterations | Warning; approaching auto-termination |
| `[COST-CEIL-001]` | Consumed > 70% of max_iterations | Warning; approaching cost ceiling |
| `[MULTI-SIGNAL]` | 2+ termination signals active | Pipeline auto-terminating with `auto_terminated` |
| `[PHASE-LOOP]` | Internal phase transition (e.g. → 5e, → 5v, → 7) | Informational; gate may follow |
| `[COMPLETE]` | Pipeline finished successfully | Check terminal state + artifacts |

### Key files to inspect

**Mid-session (pipeline still running)**:

```bash
# Checkpoint snapshot (most authoritative)
cat .orchestrate/<session>/checkpoint.json | jq '{iteration, stages_completed, terminal_state, current_phase, triage: .triage.complexity, planning_stages_completed}'

# Orchestrator-proposed tasks for latest iteration
cat .orchestrate/<session>/proposed-tasks.json | jq '.tasks[] | {subject, stage, status}'

# Pending human gate (if any)
ls .orchestrate/<session>/gates/gate-pending-*.json 2>/dev/null
```

**Post-session**:

```bash
# Session command receipt
cat .pipeline-state/command-receipts/auto-orchestrate-<YYYYMMDD>-*.json | jq '.'

# Per-stage work
ls .orchestrate/<session>/stage-3/      # Implementation artifacts
cat .orchestrate/<session>/stage-5/compliance-report.md   # Validator output
cat .orchestrate/<session>/stage-6/     # Documentation produced
```

### Checkpoint schema at a glance

| Field | Indicates |
|-------|-----------|
| `iteration` / `max_iterations` | Budget consumed |
| `stages_completed` | High-water mark: `[0, 1, 2, 3, 4.5, 5, 6]` = fully done |
| `planning_stages_completed` | `["P1","P2","P3","P4"]` once planning is complete |
| `planning_skipped` | `true` only if `--skip-planning` was passed or planning artifacts were reused |
| `current_phase` | `null` during default Stage 0–6 flow; `Phase 5e`/`Phase 5v`/`Phase 7`/etc. inside an internal phase |
| `terminal_state` | `null` = running; see §6 for value meanings |
| `triage.complexity` | `trivial` \| `medium` \| `complex` (drives research depth + enforcement tier only) |
| `triage.tshirt_size` | `XS`-`XL` (drives sprint boundaries) |
| `research_depth.tier` | `minimal`/`normal`/`deep`/`exhaustive` |
| `research_depth.source` | `explicit` \| `handoff` \| `triage-default` \| `escalated` \| `fallback` |
| `thrash_counter` | Non-zero = system has cycled at least once |
| `diminishing_returns_triggered` | `true` = progress has stalled |
| `cost_ceiling_triggered` | `true` = > 70% budget consumed |
| `human_gates` / `human_gate_history` | Configured + consumed human gates |

---

## 6. Failure modes and recovery

### Terminal state reference

| `terminal_state` | Meaning | Recovery |
|-------------------|---------|----------|
| `completed` | All mandatory stages ✓, all tasks ✓ | Nothing to do. Review Stage 6 docs and commit. |
| `completed_stages_incomplete` | Tasks done but stages 0/1/2/4.5/5/6 missing after one retry | Re-run: `/auto-orchestrate c` — mandatory stages will re-inject |
| `max_iterations_reached` | Hit MAX_ITERATIONS cap | Raise: `/auto-orchestrate --max_iterations=200 c` or investigate why progress was slow |
| `stalled` | `STALL_THRESHOLD` iterations with zero progress | Inspect checkpoint. Probably blocked by external dependency or Phase 5e gate left unanswered |
| `all_blocked` | Every task has unmet `blockedBy` | Dependency deadlock. Inspect task graph, manually unblock a task, resume |
| `user_stopped` | You wrote `decision: "stop"` at a human gate | Fresh run, or edit checkpoint and resume |
| `gate_timeout` | Human gate pending > 24h with no `gate-approval-<id>.json` | Write the approval file or change `gate_timeout_seconds` |
| `thrashing` | System alternating between states without net progress | **Don't resume blindly.** Read `thrash_history` — something in the task graph is oscillating. Often a spec/validator disagreement |
| `auto_terminated` | 2+ termination signals fired simultaneously | Same as thrashing — diagnose before resuming |
| `INCOMPLETE_ARTIFACTS` | Step-7 completeness check failed; 3-cycle remediation loop exhausted (ARTIFACT-CHECK-001) | Run `python3 ~/.claude/templates/orchestrate-session/check-completeness.py --session-root .orchestrate/<sid>` for the remediation list; also captured in `gates/gate-completeness-<TS>.json`. Fix the missing artifacts (often by re-spawning the rule-owner agent) and re-run `/auto-orchestrate c` |

### Common patterns

**"I keep hitting max_iterations"** — Either your task is too big (break it up) or the orchestrator is ping-ponging between stages. Check `thrash_counter` in checkpoint.

**"Stage 5 validator fails indefinitely"** — After 3 fix-verify cycles the pipeline writes `gate-pending-debug_entry.json` (Phase 5e entry). Approve it to enter Phase 5e Debug; decline (`"decision":"stop"`) to terminate. To inspect what's failing, read `.orchestrate/<session>/stage-5/compliance-report.md`.

**"Researcher keeps saying partial"** — Either WebSearch is unavailable or the tier contract isn't being met. Check the stage-0 output against the depth tier — it may need `--research-depth=normal` if you forced `minimal` on a non-trivial task.

**"Reasoning gate downgraded to human gate"** — Aggregate confidence stayed below 0.8 after 3 retries. The pipeline writes `gate-conditional-<id>.json` and falls back to legacy human gating for that one gate only. Review the conditional JSON's `key_caveats` to see what blocked confidence.

---

## 7. Internal phase escalation

`/auto-orchestrate` does **not** chain to other commands. Audit, Debug, Domain analysis, Release, and Post-Launch all run as internal phases of the single autonomous loop per `PHASE-LOOP-001`. Internal phase transitions look like:

```
Stage 5 validation fails 3x
    └──[PHASE-LOOP]──► Phase 5e Debug (HUMAN-GATE-001 boundary 5)
                          └──[FIX]──► back to Stage 5 validation
                          └──[STOP]──► terminal_state: user_stopped

Stage 5 validation passes
    └──[PHASE-LOOP]──► Phase 5v Compliance Verdict (HUMAN-GATE-001 boundary 6)
                          └──[APPROVED]──► Stage 6 documentation → Stage 7 release (if release_flag)
                          └──[REJECTED]──► back to Stage 3/5 to remediate

Stage 5 with release_flag=true
    └──[CAB-GATE-001]──► CAB Review if risk ∈ {HIGH, CRITICAL} (HUMAN-GATE-001 boundary 7)
                          └──[APPROVED]──► Phase 7 Release Readiness (boundary 8) → Phase 8 Post-Launch
                          └──[REJECTED]──► remediate or defer
```

Default human gates: 5e (Debug Entry), 5v (Compliance Verdict), CAB Review (conditional), Phase 7 (Release Readiness) — boundaries 5–8. Planning gates 1–4 are reasoning-gated by default; pass `--human-planning-gates` to restore human gating.

---

## 8. Troubleshooting

### Pipeline won't start

| Symptom | Cause | Fix |
|---------|-------|-----|
| `[AO-GAP-002] Manifest missing` | `~/.claude/manifest.json` not present | Re-install or run `./install.sh` |
| `[MANIFEST-001] Mandatory X not found` | Pipeline component missing in manifest | Re-run `./install.sh`; run `./install.sh --check` to confirm parity |
| `[PLAN-GATE-00N]` blocking Stage 0 entry | Planning stage N not completed | Pipeline will execute it automatically; wait for it. P1–P4 is mandatory. |
| `[ARTIFACT-CONTRACT-001] templates missing` | `~/.claude/templates/orchestrate-session/manifest.yml` not present | Re-run `./install.sh` (the templates tree was added — older installs skip it). Verify with `./install.sh --check`. |
| `[MANIFEST-MALFORMED] manifest.yml --lint failed` | Templates copy corrupted or YAML edited unsafely | Run `python3 ~/.claude/templates/orchestrate-session/check-completeness.py --lint` for line/column; re-install from the dev tree if needed. |

### Pipeline starts but doesn't progress

| Symptom | Cause | Fix |
|---------|-------|-----|
| Task stuck `in_progress` for many iterations | Subagent spawning but failing silently | After 5 iterations, `[AO-INEFF-001]` marks it failed. Wait for auto-cleanup or edit checkpoint |
| `[CHAIN-WARN]` every iteration | Orphaned `blockedBy` references | Orchestrator will self-correct; if persistent, edit proposed-tasks.json |
| `[THRASH-001]` collisions | Validator/implementation loop | Inspect last 3 iterations' stage-receipts to find the disagreement |
| Pending human gate ignored | No `gate-approval-<id>.json` written | Write the approval JSON or pass the decision via the gate-pending interactive prompt |

### Research-specific issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Researcher emits `status: "partial"` with `depth_shortfall` | Tier contract not met (below query floor, missing section) | Check tier vs task complexity; if mismatch, re-run with `--research-depth=<right-tier>` |
| `[RESEARCH-DEPTH-WARN] Invalid tier` | Typo in flag value | Valid tiers: `minimal`, `normal`, `deep`, `exhaustive`. Case-insensitive |
| All research output identical across sessions | Cache serving stale entries | Edit `.pipeline-state/research-cache.jsonl` to bump `ttl_hours` or remove entries |
| Researcher never uses WebSearch | RES-008 violation — codebase-only mode | Verify WebSearch is available; if not, expect `status: "partial"` |

### Internal-phase issues (Phase 5e / 5v / 7)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Phase 5e proposes wildly different fixes each iteration | Insufficient context for debugger | Pass a more specific error description in the task; include actual stack trace |
| Phase 5e "docker mode" not detected | No docker keywords in the task description | Pass `--docker` explicitly |
| Phase 5v compliance always < threshold | Spec requirements don't match code conventions | Inspect `stage-5/compliance-report.md`; some requirements may be mis-classified |
| CAB Review fires unexpectedly | Change classified HIGH/CRITICAL risk per `CAB-GATE-001` | Either accept the review or reduce the risk classification in the task scope |

---

## Appendix: Quick command reference

```bash
# Core
/auto-orchestrate <task>                     # Full pipeline; P1–P4 mandatory
/auto-orchestrate <scope> <task>             # Scoped: B/F/S
/auto-orchestrate c                          # Resume most recent

# Planning skip (only flag-based bypass of P1–P4)
--skip-planning                              # Bypass P1–P4
--fast-path                                  # 3-stage bypass (requires --skip-planning)

# Research depth (overrides triage default)
--research-depth=<minimal|normal|deep|exhaustive>

# Reasoning gates → human gates fallback
--human-planning-gates                       # Restore human P1–P4 gates
--human-decomposition-gates                  # Restore human Stage 1 gate
--human-task-creation-gates                  # Restore human Stage 2 gate
--sequential-stages                          # Restore single-validator Stage 5 (no reasoning gate)

# Release / audit
--release                                    # Phase 7 (Release Readiness) + CAB
--audit-spec=<path>                          # Phase 5v reads this spec
--docker                                     # Force docker-validator at Stage 5

# Budget / safety
--max_iterations=<N>
--stall_threshold=<N>
--max_tasks=<N>
--gate_timeout_seconds=<N>
```

---

*For constraint details (AUTO-001 through REASONING-GATE-001), see `claude-code/commands/auto-orchestrate.md`. For architecture, see [README.md](README.md) and [claude-code/ARCHITECTURE.md](claude-code/ARCHITECTURE.md). For changes, see [CHANGELOG.md](CHANGELOG.md).*
