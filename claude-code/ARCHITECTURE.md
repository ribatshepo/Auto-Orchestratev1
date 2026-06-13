# Auto-Orchestrate Architecture

**Last Updated**: 2026-05-18
**Scope**: complete pipeline — from `/auto-orchestrate` invocation through Phase 9 governance.
**Audience**: contributors editing agent/skill/protocol files; reviewers tracing why an artifact appeared; future sessions reading the deterministic contract.

---

## 1. Overview

Auto-Orchestrate is an **11-stage hybrid autonomous pipeline** driven by a single user-facing slash command (`/auto-orchestrate`). The command is a **loop controller** — it never writes project code itself. It spawns a single `orchestrator` agent per iteration; the orchestrator in turn delegates every stage to a specialised subagent or skill, then either advances the pipeline or hands off to a gate.

The 11 stages split into:

- **Four planning gates** (P1 Intent Review → P2 Scope Lock → P3 Dependency Acceptance → P4 Sprint Readiness) — autonomous reasoning gates by default per REASONING-GATE-001.
- **Seven technical stages** (Stage 0 Research → Stage 1 Decomposition → Stage 2 Spec Creation → Stage 3 Implementation → Stage 4 Tests → Stage 4.5 Refactor/Metrics → Stage 5 Validation → Stage 6 Documentation).

Six conditional sub-phases (5v Audit, 5e Debug, 5q Quality, 5s Security, 5i Infra/SRE, 5d Data/ML) fire when triage flags or stage outcomes require them. After Stage 6, a Sprint Closure sequence (P-027 → P-028 → P-029) always runs; Phase 7 (Release Prep) fires when `release_flag=true`; Phase 8 (Post-Launch) and Phase 9 (Governance) follow conditionally.

Every artifact a session emits is governed by a **deterministic contract** (`templates/orchestrate-session/manifest.yml`, 100 rules) and validated at session close by `check-completeness.py`. A session cannot terminate in the `completed` state without a passing gate-completeness check (ARTIFACT-CHECK-001).

What changed recently (see §16): autonomous reasoning gates replaced human gates for P1–P4; the artifact contract + completeness checker landed in commit `5d6e081`; the MAIN-017 Stage-Close Protocol that wires the always-populate handlers for `phase-receipts/`, `domain-reviews/`, `reasoning-traces/`, and `meetings/` was just implemented today (2026-05-18).

---

## 2. Component inventory at a glance

```
Pipeline:
  1 user-facing command         (/auto-orchestrate — loop controller)
  1 orchestrator agent          (spawned per iteration; enforces MAIN-001..MAIN-017)
  22 agents                     (per claude-code/manifest.json — includes 4 continuity scouts under CONT-007)
  49 skills                     (per claude-code/manifest.json)
  28 process files              (manifest entries; cover the P-001 .. P-093 process catalog)
  13 shared protocols           (claude-code/_shared/protocols/*.md — includes spawn-core.md)
  3 lib packages + 2 modules    (artifact_envelope/, ci_engine/, domain_memory/; path_compat.py + _time.py)

Artifact contract:
  100 artifact rules            (templates/orchestrate-session/manifest.yml)
  7 consistency checks          (CONS-001..007 in check-completeness.py)
  ~87 templates + 18 schemas    (templates/orchestrate-session/)

Pre-flight ratio (PREFLIGHT-001):
  11/11 critical agents          (orchestrator, researcher, session-manager, continuity-scout,
                                  product-manager, technical-program-manager, engineering-manager,
                                  software-engineer, technical-writer, auditor, debugger)
  11/11 critical skills          (spec-creator, validator, codebase-stats, refactor-analyzer,
                                  dependency-analyzer, production-code-workflow, dev-workflow,
                                  spec-compliance, docs-lookup, docs-write, meta-reasoner)
  Remaining 7 agents + 38 skills are lazy-dispatched by the orchestrator at spawn time.

Checkpoint schema: 1.10.0
```

---

## 3. The big picture

```
                                User prompt
                                     │
                                     ▼
                ┌──────────────────────────────────────┐
                │  /auto-orchestrate (loop controller) │
                │  Steps 0..7; never spawns workers    │
                │  except orchestrator (AUTO-001)      │
                └──────────────────────────────────────┘
                                     │
                                     ▼  spawn (always orchestrator)
                ┌──────────────────────────────────────┐
                │  Step −0.5  continuity-scout (CONT-001)
                │  Step  0    session-manager (boot infra)
                │  Step  2.0  mkdir .orchestrate/<sid>/* (LAYOUT-GATE-001)
                │  Step  3.0a misplaced-session self-heal
                └──────────────────────────────────────┘
                                     │
        ┌─── Planning gates (autonomous reasoning by default) ───┐
        ▼                                                       │
   P1 Intent Review ─► P2 Scope Lock ─► P3 Dep Acceptance ─► P4 Sprint Readiness
        │   each: Multi-Agent Sync + meta-reasoner aggregate; <0.8 → human fallback
        ▼
   PRE-RESEARCH-GATE  (require planning_gate_statuses == all PASSED)
        │
        ▼
   Stage 0a  researcher (project-wide research)
        │
        ▼  Stage 0b per-deliverable researcher fanout (PER-STORY-RESEARCH-001, cap 5)
   Stage 1   product-manager + Multi-Agent Sync (DECOMP-REASONING-001 per deliverable)
        │
        ▼
   Stage 2   spec-creator + Multi-Agent Sync (TASK-CREATION-REASONING-001 per story)
        │
        ▼
   Stage 3   software-engineer × N parallel (PARALLEL-001/002/003, cap 5 per group)
        │
        ▼
   Stage 4   test-writer-pytest × N parallel (PARALLEL-STAGE-001)
        │
        ▼
   Stage 4.5 codebase-stats + refactor-analyzer + dependency-analyzer (3-skill fanout)
        │
        ▼
   Stage 5   validator + Multi-Agent Sync (VALIDATION-REASONING-001)
        │       recommended_verdict feeds Phase 5v human gate
        │
        ├──► (compliance < threshold) Phase 5v Audit ── auditor + spec-compliance loop
        ├──► (verdict = FAIL)          Phase 5e Debug ── debugger ► software-engineer
        ├──► (domain flags fire)       Phase 5q/5s/5i/5d ── domain leads
        │
        ▼
   Stage 6   technical-writer × 6 categories (api/integration/ops-runbook/adr/user-guide/changelog)
        │
        ▼  Stage-Close Protocol fires at every stage close (MAIN-017 Parts 1.1–1.4)
        │
        ▼
   ARTIFACT-CHECK-001 (Step 7 — check-completeness.py runs; MUST pass or remediate)
        │
        ▼  terminal_state = "completed" (only if PASS)
   Sprint Closure: P-027 Sprint Review ► P-028 Sprint Retro ► P-029 Backlog Refinement
        │
        ├──► (release_flag) Phase 7 — CAB Review (HIGH/CRITICAL risk) + Release Readiness gate
        │                   Phase 8 — Post-Launch SLO/OKR/30-60-90 tracking
        │                   Phase 9 — Governance (audit/risk/comms/capacity/tech-excellence/onboarding)
```

Human-in-the-loop boundaries (HUMAN-GATE-001) live at: (5) Stage 5 → Phase 5e Debug Entry, (6) Phase 5v Compliance Verdict, (7) CAB Review (conditional), (8) Phase 7 Release Readiness. Everything else is autonomous unless a reasoning gate downgrades to human on <0.8 confidence after 3 retries.

---

## 4. Pipeline reference

### 4.1 Planning gates P1–P4

All four planning gates run as **autonomous reasoning gates** by default per REASONING-GATE-001. Each runs a Multi-Agent Sync meeting between the gate's participants, then invokes `meta-reasoner` to aggregate the DECOMPOSE → SOLVE → VERIFY → SYNTHESIZE → REFLECT trace. Confidence ≥ 0.8 → auto-approve; <0.8 after 3 retries → downgrade THIS gate to a HUMAN-GATE-001 file-polled fallback. The `--human-planning-gates` flag restores legacy human-gated planning for all four.

| Gate                     | Process | Lead facilitator          | Output                                                |
| ------------------------ | ------- | ------------------------- | ----------------------------------------------------- |
| P1 Intent Review         | P-004   | engineering-manager       | `planning/P1-intent-brief.md`                       |
| P2 Scope Lock            | P-013   | product-manager           | `planning/P2-scope-contract.md` + RAID seed (P-010) |
| P3 Dependency Acceptance | P-019   | technical-program-manager | `planning/P3-dependency-charter.md`                 |
| P4 Sprint Readiness      | P-025   | engineering-manager       | `planning/P4-sprint-kickoff-brief.md`               |

Gate artifacts: `gates/gate-approval-<gate-id>-<TS>.json` (≥0.8) or `gates/gate-conditional-<gate-id>-<TS>.json` (downgrade). Reasoning trace: `reasoning-traces/reasoning-trace-<gate-id>-<TS>.json`. Meeting minutes: `meetings/minutes-<process>-multi-agent-sync-<TS>.json`.

After P4 approves, **PRE-RESEARCH-GATE** verifies `planning_stages_completed == ["P1","P2","P3","P4"]` and `planning_gate_statuses` all `"PASSED"` before Stage 0 may begin. Bypass: `--skip-planning` flag or `planning_skipped: true` in checkpoint (resume case).

### 4.2 Technical stages 0–6

#### Stage 0a — Project-wide research

**Lead**: `researcher` (WebSearch + WebFetch enabled). **Trigger**: P4 gate approval. **Outputs**: `stage-0/<YYYY-MM-DD>_<slug>-research.md` (ART-S0-001) + `stage-0/stage-receipt.json` (ART-S0-002). **Mandatory**. Reads P2 Scope Contract, P3 Dependency Charter, P4 Sprint Kickoff Brief. Produces RES-001..010 compliant findings (evidence-based, current sources, CVE checks, Risks & Remedies).

#### Stage 0b — Per-deliverable research (PER-STORY-RESEARCH-001)

**Lead**: `researcher` spawned per `P2.Deliverables` entry, parallel subject to PARALLEL-003 cap (default 5). **Trigger**: Stage 0a complete. **Outputs** per deliverable D: `stage-0/<D>/research.md` (ART-S0-003) + `stage-0/<D>/stage-receipt.json` (ART-S0-004). **Skipped** when `Deliverables.length == 1`. Per-deliverable research is the input for that deliverable's Stage 1 decomposition meeting.

#### Stage 1 — Decomposition (DECOMP-REASONING-001)

**Lead**: `product-manager` (facilitator) + Multi-Agent Sync with `technical-program-manager`, `software-engineer`, `qa-engineer`, `staff-principal-engineer`, and scope-conditional domain agents. **Trigger**: Stage 0 complete. **Outputs**: per-deliverable `stage-1/<D>/proposed-tasks.json` (ART-S1-003) + receipt (ART-S1-004) + `stage-1/<D>/gate-approval-decomposition-<D>-<TS>.json` (ART-S1-005); merged session-level `proposed-tasks.json` (ART-ROOT-005). **Mandatory**. Meta-reasoner verifies four sub-questions (story sizing ≤ M/8pt, acyclic dep graph, testable AC, independent implementability); ≥0.8 auto-approves, <0.8 after 3 retries falls back to legacy single-agent product-manager for that deliverable only. Override: `--human-decomposition-gates`.

#### Stage 2 — Spec creation (TASK-CREATION-REASONING-001)

**Lead**: `software-engineer` (facilitator) + Multi-Agent Sync with `qa-engineer`, `technical-program-manager`, `staff-principal-engineer`; `spec-creator` skill invoked inline. **Trigger**: Stage 1 gate approval per task. **Outputs** per task T: `stage-2/<T>/spec.md` (ART-S2-002) + receipt (ART-S2-003) + `stage-2/<T>/gate-approval-task-creation-<T>-<TS>.json` (ART-S2-004). **Mandatory**. Six sub-questions verify ENG-STD-001 size limits (§8 ≤300 lines/type, ≤40 lines/function), testing contract, dependency declaration, type safety, data-class args, error handling. Override: `--human-task-creation-gates`.

#### Stage 3 — Implementation

**Lead**: `software-engineer`, parallel across independence groups (PARALLEL-001/002/003), one task per group FIFO, cap 5 simultaneous spawns. **Trigger**: Stage 2 spec approved for that task. **Outputs** per task T: `stage-3/<T>/stage-receipt.json` (ART-S3-003, captures `files_modified`, `test_files_created`, `eng_std_001` sub-checks, `ac_verification`) + `stage-3/<T>/changes.md` (ART-S3-004, extracted from DONE block — **task cannot complete without this file**). Aggregate: `stage-3/stage-receipt.json` (ART-S3-001) + `stage-3/changes.md` (ART-S3-002). **Mandatory** per task. Post-implementation fix loop: max 3 validator → fix iterations (MAIN-006); failure after 3 → manual-fix task.

#### Stage 4 — Tests

**Lead**: `test-writer-pytest` skill, parallel per independence group (PARALLEL-STAGE-001, cap 5). **Trigger**: Stage 3 complete. **Outputs**: per-task receipt (ART-S4-003); aggregate `stage-4/stage-receipt.json` (ART-S4-001) + `stage-4/changes.md` (ART-S4-002) **always written** even when `stage_4_tasks == []` (the empty-tasks branch records "no test-only tasks decomposed" — a real artifact, not a sentinel, per ARTIFACT-COMPLETENESS-001).

#### Stage 4.5 — Refactor & metrics

**Lead**: three skills in parallel: `codebase-stats` (ART-S45-001), `refactor-analyzer` (ART-S45-002), `dependency-analyzer` (ART-S45-003). **Trigger**: Stage 4 complete. **Output**: `stage-4.5/stage-receipt.json` (ART-S45-004). **Mandatory**. Produces ENG-STD-001 violation counts (overall_score < 0.9 → Stage 5 FAIL recommended_verdict), refactor recommendations, and circular-dependency report.

#### Stage 5 — Validation (VALIDATION-REASONING-001)

**Lead**: `qa-engineer` (facilitator) + Multi-Agent Sync with `validator` skill (inline), `docker-validator` (when Docker available), `security-engineer` (when security scope), `sre` (when `release_flag`), `auditor` (read-only). **Trigger**: Stage 4.5 complete. **Outputs**: `stage-5/validation-report.json` (ART-S5-001) + `.md` (ART-S5-002) + `compliance-report.json` (ART-S5-003) + receipt (ART-S5-004). **Mandatory**. Six sub-questions: spec AC met, user journeys pass, ENG-STD-001 overall_score ≥ 0.9, docker-validator no blocking errors, security findings within tolerance, release-readiness signals (if `release_flag`). Output: `recommended_verdict` (PASS/FAIL/INDETERMINATE) feeds Phase 5v Compliance Verdict human gate (HUMAN-GATE-001 boundary 6).

#### Stage 6 — Documentation

**Lead**: `technical-writer`, 6-category fanout (api / integration / ops-runbook / adr / user-guide / changelog) parallel per PARALLEL-STAGE-001. Co-agents: `sre` (P-059 Runbook), `software-engineer` (P-060 ADR). **Trigger**: Stage 5 PASS. **Outputs**: per-category folders under `stage-6/`; aggregate `stage-6/changes.md` (ART-S6-007) + `stage-6/stage-receipt.json` (ART-S6-008). **Mandatory** — all 6 categories required (N/A categories produce a canonical no-*.md doc rather than being skipped). Skills invoked inline: `docs-lookup`, `docs-write`, `docs-review`.

### 4.3 Sub-phases (fire conditionally)

| Phase                  | Trigger                                                                                      | Lead                                                                       | Output                                                                      | Notes                                                                                                 |
| ---------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **5v Audit**     | Stage 5 PASS but `spec-compliance` weighted score < `compliance_threshold` (default 90%) | `auditor` (+ `spec-compliance` skill)                                  | `phase-receipts/phase-5v-audit-<TS>.json` + per-cycle `gap-report.json` | Max 5 audit cycles; human gate `compliance-verdict` decides per cycle                               |
| **5e Debug**     | Stage 5 FAIL after 3 fix iterations                                                          | `debugger` → respawn `software-engineer`                              | Re-entry into Stage 3 → 4.5 → 5                                           | Max 2 cycles per session (REGRESS-002); human gate `debug-entry`; thrashing detection (REGRESS-003) |
| **5q Quality**   | Triage `domain_flags` includes quality OR scope flags qa                                   | `qa-engineer` (+ co-agent `product-manager` for P-036 AC verification) | `phase-receipts/phase-5q-quality-<TS>.json` + findings.md                 | Owns P-032..P-035, P-037                                                                              |
| **5s Security**  | Scope flags security OR P-038..P-043 HIGH/CRITICAL                                           | `security-engineer`                                                      | `phase-receipts/phase-5s-security-<TS>.json` + findings.md                | Owns P-038..P-043; invokes `threat-modeler`, `security-auditor`, `raid-logger`                  |
| **5i Infra/SRE** | Scope flags infra OR Stage 5 fails with infra keywords                                       | `infra-engineer` + `sre` (joint)                                       | `phase-receipts/phase-5i-infra-<TS>.json` + findings.md                   | Co-agents:`technical-program-manager` (P-048), `security-engineer` (P-039 CI co-ownership)        |
| **5d Data/ML**   | Scope flags data_ml OR P-049..P-053 HIGH/CRITICAL                                            | `data-engineer` + `ml-engineer` (joint)                                | `phase-receipts/phase-5d-data-ml-<TS>.json` + findings.md                 | Pipeline quality, schema migration, drift monitoring                                                  |

Each sub-phase writes a phase receipt to `phase-receipts/phase-<name>-<TS>.json` per PHASE-LOOP-002 and a handover receipt to the next consumer per HANDOVER-001.

### 4.4 Post-termination — Sprint Closure → Phases 7/8/9

After Stage 6 closes and Step 7 (ARTIFACT-CHECK-001) returns PASS, three meeting phases always run inline (no human pause):

| Sequence                   | Handler            | Lead                                                                    | Output                                                  |
| -------------------------- | ------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------- |
| P-027 Sprint Review        | Multi-Agent Sync   | engineering-manager (chair) + product-manager + software-engineer       | `meetings/meeting-p-027-sprint-review-<TS>.json`      |
| P-028 Sprint Retrospective | Multi-Agent Sync   | engineering-manager (facilitator) + product-manager + software-engineer | `meetings/meeting-p-028-sprint-retro-<TS>.json`       |
| P-029 Backlog Refinement   | Async Single-Agent | product-manager                                                         | `meetings/meeting-p-029-backlog-refinement-<TS>.json` |

**Phase 7 — Release Prep** fires when `checkpoint.release_flag == true`. Two human gates:

- **CAB Review** (CAB-GATE-001, HUMAN-GATE-001 #7): fires only when TPM classifies risk as HIGH/CRITICAL. Output: `phase-7/cab-decision-record.md`.
- **Release Readiness** (HUMAN-GATE-001 #8): aggregates P-035/P-044..P-048/P-059/P-061 acknowledgments + CAB conditions. Output: `phase-receipts/phase-7-release-<TS>.json`.

**Phase 8 — Post-Launch** fires after Phase 7 APPROVED (or when `triage.mode == "post_launch"`). Runs inline, no human gate. Coordinates `sre` (SLO snapshot via `slo-definer`, P-055 incident readiness, P-057 on-call), `product-manager` (P-070 post-mortem, P-072 OKR retro via `okr-retrospective-tracker`, P-073 30/60/90 outcome measurement), `engineering-manager` (P-071 quarterly process health). Output: `phase-receipts/phase-8-post-launch-<TS>.json`.

**Phase 9 — Governance** runs autonomously per trigger, parallel to main flow, does not block stage progression. Cap: 2 sub-routines per iteration. Sub-routines:

- **Audit** (P-062..P-069) — tech_debt > 30% OR duplication > 15%.
- **Risk** (P-074..P-077) — CRITICAL RAID items present.
- **Comms** (P-078..P-081) — OKR cadence boundary.
- **Capacity** (P-082..P-084) — sprint cadence boundary.
- **Tech Excellence** (P-085..P-089) — RFC needed / pattern review.
- **Onboarding** (P-090..P-093) — new team member.

All sub-routines append to `raid-log.json` per RAID-001. Output: `phase-receipts/phase-9-governance-<sub_routine>-<TS>.json`.

### 4.5 Summary table — Stage / Phase entry & exit

> **Canonical sources (keep in sync).** This table is the human-facing *entry/exit*
> view (input triggers + receipt paths). The **operative** dispatch parameters — lead
> agent, process-owned co-agents, and `max_turns` — are owned by the orchestrator's own
> table at `agents/orchestrator.md` § "Pipeline Stages & Turn Limits" (that copy is part
> of the orchestrator's runtime prompt and is authoritative for lead/co-agents/max_turns).
> Update both when the pipeline changes.

| Stage / Phase | Lead Agent                                                  | Input Trigger                                        | Receipt Path                                            | Mandatory?                             | Max Turns           |
| ------------- | ----------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------- | -------------------------------------- | ------------------- |
| 0a            | researcher                                                  | P4 gate approval                                     | `stage-0/stage-receipt.json`                          | Mandatory                              | 20                  |
| 0b            | researcher (parallel per deliverable)                       | Stage 0a complete + >1 deliverable                   | `stage-0/<D>/stage-receipt.json`                      | Conditional                            | 20                  |
| 1             | product-manager (DECOMP-REASONING-001)                      | Stage 0 complete                                     | `stage-1/<D>/gate-approval-decomposition-*.json`      | Mandatory                              | 20                  |
| 2             | spec-creator (TASK-CREATION-REASONING-001)                  | Stage 1 approval per task                            | `stage-2/<T>/gate-approval-task-creation-*.json`      | Mandatory                              | 20                  |
| 3             | software-engineer (PARALLEL-001/002/003)                    | Stage 2 approval per task                            | `stage-3/<T>/stage-receipt.json` + aggregate          | Mandatory per task                     | 30                  |
| 4             | test-writer-pytest (PARALLEL-STAGE-001)                     | Stage 3 complete                                     | `stage-4/stage-receipt.json` (always emitted)         | Conditional per task; aggregate always | 30                  |
| 4.5           | codebase-stats + refactor-analyzer + dependency-analyzer    | Stage 4 complete                                     | `stage-4.5/stage-receipt.json`                        | Mandatory                              | 15                  |
| 5             | qa-engineer + validator (VALIDATION-REASONING-001)          | Stage 4.5 complete                                   | `stage-5/stage-receipt.json`                          | Mandatory                              | 15                  |
| 5q            | qa-engineer                                                 | Domain flag quality OR Stage 3 complete              | `phase-receipts/phase-5q-quality-<TS>.json`           | Conditional                            | 20                  |
| 5s            | security-engineer                                           | Domain flag security OR HIGH/CRITICAL finding        | `phase-receipts/phase-5s-security-<TS>.json`          | Conditional                            | 20                  |
| 5i            | infra-engineer + sre                                        | Domain flag infra OR Stage 5 infra-keyword fail      | `phase-receipts/phase-5i-infra-<TS>.json`             | Conditional                            | 20                  |
| 5d            | data-engineer + ml-engineer                                 | Domain flag data_ml OR P-049..P-053 HIGH             | `phase-receipts/phase-5d-data-ml-<TS>.json`           | Conditional                            | 20                  |
| 5v            | auditor (+ spec-compliance)                                 | Stage 5 PASS but compliance < threshold              | `phase-receipts/phase-5v-audit-<TS>.json`             | Conditional                            | 25 / max 5 cycles   |
| 5e            | debugger → software-engineer                               | Stage 5 FAIL after 3 fix iter                        | per re-entry                                            | Conditional                            | 25 / max 2 cycles   |
| 6             | technical-writer (6-category fanout)                        | Stage 5 PASS                                         | `stage-6/stage-receipt.json`                          | Mandatory (all 6 categories)           | 15                  |
| P-027         | orchestrator → engineering-manager                         | Stage 6 complete                                     | `meetings/meeting-p-027-sprint-review-<TS>.json`      | Always post-completion                 | 15                  |
| P-028         | orchestrator → engineering-manager                         | P-027 complete                                       | `meetings/meeting-p-028-sprint-retro-<TS>.json`       | Always post-Review                     | 15                  |
| P-029         | orchestrator → product-manager                             | P-028 complete                                       | `meetings/meeting-p-029-backlog-refinement-<TS>.json` | Always post-Retro                      | 20                  |
| 7             | orchestrator (CAB + release-readiness)                      | `release_flag == true`                             | `phase-receipts/phase-7-release-<TS>.json`            | Conditional                            | 25 (2 human gates)  |
| 8             | orchestrator → sre + product-manager + engineering-manager | Phase 7 APPROVED OR `triage.mode == "post_launch"` | `phase-receipts/phase-8-post-launch-<TS>.json`        | Conditional                            | 20                  |
| 9             | orchestrator → domain-specific per sub-routine             | Triggers per category                                | `phase-receipts/phase-9-governance-<sub>-<TS>.json`   | Conditional                            | 20 / max 2 per iter |

---

## 5. Gates & reasoning

### 5.1 Meta-reasoner skill (REASONER-001 / REASONER-002)

The `meta-reasoner` skill implements a 5-phase loop:

```
DECOMPOSE   → break the decision into sub-questions
SOLVE       → score each sub-question (per-participant verdicts; confidence floats)
VERIFY      → consistency, outlier, cycle checks
SYNTHESIZE  → aggregate confidence (mean of per-question means)
REFLECT     → final_confidence + recommended_action
```

**Retry rule**: aggregate confidence < 0.8 → retry with sharper sub-questions; max 3 retries (REASONER-002). On exhaustion, the calling gate downgrades only that gate to a human fallback.

**Skipped** for simple tasks (`should_skip()` returns true when no canonical hook condition is met: ≤3 candidate approaches, no spec-analyzer ambiguity, no conflicting Stage 5 findings, no gate rejections, no dependency cycle, draft self-confidence ≥ 0.7).

Output: `reasoning-traces/reasoning-trace-<gate_id>-<TS>.json` (envelope `reasoning_trace`).

### 5.2 Reasoning-gated planning (REASONING-GATE-001)

P1–P4 are reasoning-gated by default. The orchestrator spawns a Multi-Agent Sync meeting (participants per the Gate Participant Matrix), records minutes, then invokes `meta-reasoner` to aggregate. Outputs:

- `gates/gate-approval-<gate-id>-<TS>.json` when aggregate ≥ 0.8 — body contains `answer`, `confidence`, `key_caveats` (OUTPUT-TRIPLET-001).
- `gates/gate-conditional-<gate-id>-<TS>.json` when <0.8 after 3 retries — body contains the weakest sub-questions and unresolved participant concerns; this single gate then writes a `gate-pending-<gate-id>.json` and falls back to HUMAN-GATE-001 (the other three planning gates continue autonomously).

Flag `--human-planning-gates` restores pre-Phase-8 human-gated planning for all four.

### 5.3 Per-unit reasoning gates

| Gate                        | Scope                             | Lead facilitator              | Fallback                                                                                                                  |
| --------------------------- | --------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| DECOMP-REASONING-001        | One per P2 deliverable in Stage 1 | product-manager               | Legacy single-agent product-manager for THAT deliverable only on <0.8 after 3 retries; or `--human-decomposition-gates` |
| TASK-CREATION-REASONING-001 | One per Stage 1 story in Stage 2  | software-engineer (tech-lead) | Legacy inline spec-creator for THAT story only on <0.8 after 3 retries; or `--human-task-creation-gates`                |
| VALIDATION-REASONING-001    | Once per Stage 5                  | qa-engineer                   | `--sequential-stages`                                                                                                   |

### 5.4 Human gates (HUMAN-GATE-001)

Four boundaries remain human-gated by default:

| # | Gate ID                | Trigger                                       | Decision body                                             |
| - | ---------------------- | --------------------------------------------- | --------------------------------------------------------- |
| 5 | `debug-entry`        | Stage 5 FAIL → Phase 5e Debug entry          | User chooses approve / reject / stop                      |
| 6 | `compliance-verdict` | Phase 5v compliance score < threshold         | User chooses approve / approve-acceptable / reject / stop |
| 7 | `cab-review`         | Phase 7 prelude, conditional per CAB-GATE-001 | User reviews CAB Decision Record                          |
| 8 | `release-readiness`  | Phase 7 closing                               | User approves release                                     |

The loop controller writes `gates/gate-pending-<gate-id>.json` and polls `gates/gate-approval-<gate-id>.json` every `gate_poll_interval_seconds` (default 30s) up to `gate_timeout_seconds` (default 86400s / 24h). On timeout: `terminal_state = "gate_timeout"`.

### 5.5 AUTO-EVAL-001 + OUTPUT-TRIPLET-001

At every formal gate (planning + execution), a deterministic checklist evaluator produces a `recommended_verdict` (PASS / FAIL / INDETERMINATE) BEFORE any human or reasoning gate runs. For planning gates this verdict is one of the meta-reasoner's SOLVE inputs; for execution gates it appears in the gate-pending file shown to the human. Both the auto-eval verdict and the final decision are recorded in `gate-state.json` for audit traceability.

Every reasoning-gated artifact carries the **Output Triplet**: `answer` (one-paragraph synthesis), `confidence` (float 0–1), `key_caveats` (list). Applies to REASONING-GATE-001, DECOMP-REASONING-001, TASK-CREATION-REASONING-001, and VALIDATION-REASONING-001 outputs.

### 5.6 CAB-GATE-001

The CAB Review gate (Gate 7) fires conditionally — only when `release_flag == true` AND the CAB co-agent (`technical-program-manager`) classifies the change as HIGH or CRITICAL risk. If LOW/MEDIUM, the gate is skipped (logged as `[CAB-SKIP]`) and Phase 7 proceeds straight to the release-readiness gate.

---

## 6. Meetings & ceremonies

### 6.1 Three handler types (MEETING-001)

| Handler                      | When                                                                                                                        | Output                                                                         |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **Human-Gated**        | CAB Review (P-076 conditional)                                                                                              | `meetings/minutes-cab-review-<TS>.json` + gate-approval/rejected file        |
| **Multi-Agent Sync**   | Every reasoning gate; daily/dependency standups; sprint review + retro; ad-hoc syncs (≥2 agents in parallel for synthesis) | `meetings/minutes-<process>-<type>-<TS>.json` (envelope `meeting_minutes`) |
| **Async Single-Agent** | Backlog Refinement (P-029)                                                                                                  | `meetings/meeting-p-029-backlog-refinement-<TS>.json`                        |

### 6.2 Canonical meeting catalog

| Process | Meeting                     | Cadence                               | Handler                               | Facilitator               |
| ------- | --------------------------- | ------------------------------------- | ------------------------------------- | ------------------------- |
| P-004   | Intent Review               | Every session                         | Multi-Agent Sync + REASONING-GATE-001 | engineering-manager       |
| P-013   | Scope Lock                  | Every session                         | Multi-Agent Sync + REASONING-GATE-001 | product-manager           |
| P-019   | Dependency Acceptance       | Every session                         | Multi-Agent Sync + REASONING-GATE-001 | technical-program-manager |
| P-025   | Sprint Readiness            | Every session                         | Multi-Agent Sync + REASONING-GATE-001 | engineering-manager       |
| P-020   | Dependency Standup          | When `cross_team_impact=true`       | Multi-Agent Sync                      | technical-program-manager |
| P-026   | Daily Standup               | Every 5 iter (L) / 3 iter (XL)        | Multi-Agent Sync                      | product-manager           |
| P-027   | Sprint Review               | After Stage 6                         | Multi-Agent Sync                      | engineering-manager       |
| P-028   | Sprint Retrospective        | After P-027                           | Multi-Agent Sync                      | engineering-manager       |
| P-029   | Backlog Refinement          | After P-028 (unrefined items remain)  | Async Single-Agent                    | product-manager           |
| P-076   | CAB / Change Advisory Board | `release_flag` + HIGH/CRITICAL risk | Human-Gated                           | technical-program-manager |

Plus reasoning-gated per-unit syncs (Stage 1 per-deliverable decomposition, Stage 2 per-story task-creation, Stage 5 validation).

### 6.3 Meeting completeness gate (MEETING-GATE-001)

Step 4.8d.5 of `auto-orchestrate.md` runs `gate-meeting-completeness` at every stage transition. If a mandatory meeting's minutes are missing → write `gates/gate-rejected-meeting-completeness-<TS>.json` and **HALT** with `[MEETING-MISSING]`.

**MEETING-GATE-003 (rewritten)**: when no canonical meeting fires for a stage in {2, 3, 5, 6}, the orchestrator MUST spawn `engineering-manager` for a baseline check-in and write `meetings/meeting-baseline-stage-<N>-<TS>.json` from `templates/orchestrate-session/meetings/meeting-baseline-stage.json`. **Sentinel `*-none-*.json` placeholders are forbidden** per ARTIFACT-COMPLETENESS-001 — the baseline IS the meeting record. (The prior sentinel-mandate version of MEETING-GATE-003 was removed when MAIN-017 Stage-Close Protocol Part 1.4 landed.)

---

## 7. Agent inventory (22)

| Agent                               | Purpose                                                                                                                                                     | Tools                                       | Primary pipeline role                                                                                                                 |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **orchestrator**              | Coordinates workflows by delegating to subagents while protecting context. Enforces MAIN-001 through MAIN-017.                                              | Read, Glob, Grep, Bash, Task                | Spawned every iteration; the conductor; never implements                                                                              |
| **researcher**                | Internet-enabled research agent. Produces structured findings for downstream agents.                                                                        | Read, Write, Glob, Grep, Bash, WebSearch, WebFetch | Stage 0a + Stage 0b per-deliverable fanout                                                                                            |
| **continuity-scout**          | Pre-P1 context scout. Reads `.orchestrate/domain/*`, prior 3 sessions, baselines, audit ledger.                                                           | Read, Glob, Grep, Bash, Write               | Step −0.5 boot; writes `continuity-brief.md`                                                                                       |
| **session-manager**           | Coordinates work session lifecycle, task focus, boot infrastructure.                                                                                        | Read, Glob, Grep, Bash, Task                | Step 0 boot                                                                                                                           |
| **product-manager**           | User stories, backlogs, acceptance criteria, OKR key results, roadmaps, sprint ceremonies.                                                                  | Read, Write, Edit, Glob, Grep               | P1/P2 lead; Stage 1 facilitator (DECOMP-REASONING-001); P-029 lead                                                                    |
| **technical-program-manager** | Cross-team dependencies, RAID, milestones, PI planning, go/no-go decisions, program-level risks.                                                            | Read, Write, Edit, Glob, Grep, Bash         | P3 lead; CAB chair; Phase 5i co-agent (P-048)                                                                                         |
| **engineering-manager**       | Sprint planning, team health, DORA, capacity, OKR, performance reviews, impediments.                                                                        | Read, Write, Glob, Grep, Bash               | P1/P4 lead; Sprint Review + Retro facilitator;**MAIN-017 Part 1.4 baseline check-in lead**                                      |
| **staff-principal-engineer**  | Cross-team architecture, RFCs, ADRs, architecture review, technical standards. Advisory.                                                                    | Read, Glob, Grep, Bash, Task                | Reasoning-gate participant (Stage 1, Stage 2 when architectural concerns flagged)                                                     |
| **software-engineer**         | Production code, unit tests, code review, technical design (L3-L5 IC + Tech Lead).                                                                          | Read, Write, Edit, Bash, Glob, Grep, Task   | Stage 2 facilitator (TASK-CREATION-REASONING-001); Stage 3 lead; Stage 6 co-agent (P-060 ADR)                                         |
| **spec-creator**              | (skill, invoked inline) — Specification and protocol documents.                                                                                            | (skill)                                     | Stage 2 spec drafting                                                                                                                 |
| **qa-engineer**               | Test architectures, regression, coverage gaps, performance testing, acceptance criteria, DoD enforcement.                                                   | Read, Write, Bash, Glob, Grep, Task         | Stage 4 (test-writer wrapper); Stage 5 facilitator (VALIDATION-REASONING-001);**MAIN-017 Part 1.2 baseline domain review lead** |
| **security-engineer**         | Security reviews, SAST/DAST, threat modeling, CVE triage, compliance (SOC2/ISO27001/GDPR), IAM review. Read-only on project code; writes findings only.    | Read, Write, Bash, Glob, Grep               | Phase 5s lead; Stage 5 co-agent (when security scope); CAB participant                                                                |
| **sre**                       | SLOs, error budgets, incident response, post-mortems, observability (OpenTelemetry/Grafana/Datadog), alerting. Operates production.                         | Read, Write, Bash, Glob, Grep, Task         | Phase 5i co-lead (with infra-engineer); Stage 6 co-agent (P-059 Runbook); Phase 8 lead                                                |
| **infra-engineer**            | CI/CD, IaC (Terraform/CDK/Bicep/Pulumi), container orchestration, golden paths, FinOps, IAM. Builds + provisions; does NOT operate.                         | Read, Write, Edit, Bash, Glob, Grep, Task   | Phase 5i co-lead (with sre); Phase 7 release-prep participant                                                                         |
| **data-engineer**             | Data pipelines (ETL/ELT), data warehouse schemas, dbt, streaming (Kafka/Spark/Flink), data quality, schema migrations.                                      | Read, Write, Edit, Bash, Glob, Grep, Task   | Phase 5d co-lead (with ml-engineer)                                                                                                   |
| **ml-engineer**               | ML pipelines, model training infrastructure, feature stores, model serving (TorchServe/Triton/BentoML), experiment tracking, drift monitoring.              | Read, Write, Edit, Bash, Glob, Grep, Task   | Phase 5d co-lead (with data-engineer)                                                                                                 |
| **auditor**                   | Spec compliance auditor. Reads specs + codebase, produces compliance reports with gap analysis. Read-only on project code; writes audit findings only.     | Read, Write, Glob, Grep, Bash               | Phase 5v audit loop lead                                                                                                              |
| **debugger**                  | Autonomous debugging agent. Triage → research → fix → verify cycle for runtime / Docker / test / build / config failures. May spawn researcher subagent. | Read, Grep, Glob, Bash, Write, Edit         | Phase 5e debug loop lead                                                                                                              |
| **technical-writer**          | API docs, developer guides, runbooks, release notes, SDK samples, architecture docs, KB content. Documentation-first; maintain over duplicate.              | Read, Write, Edit, Glob, Grep               | Stage 6 lead (6-category fanout)                                                                                                      |
| **scout-jsonl**               | Continuity scout — reads the domain JSONL stores (research_ledger, decision_log, pattern_library, fix_registry).                                            | Read, Glob, Grep, Bash, Write               | Step −0.5 continuity fan-out (CONT-007); writes a brief part for `continuity-scout` to merge                                         |
| **scout-sessions**            | Continuity scout — reads the 3 newest prior `.orchestrate/auto-orc-*` sessions (checkpoints, receipts, learnings).                                          | Read, Glob, Grep, Bash, Write               | Step −0.5 continuity fan-out (CONT-007); writes a brief part for `continuity-scout` to merge                                         |
| **scout-pipeline**            | Continuity scout — reads baselines, improvement-recommender state, and the audit findings ledger.                                                          | Read, Glob, Grep, Bash, Write               | Step −0.5 continuity fan-out (CONT-007); writes a brief part for `continuity-scout` to merge                                         |
| **scout-context**             | Continuity scout — reads user_preferences + codebase_analysis stores.                                                                                       | Read, Glob, Grep, Bash, Write               | Step −0.5 continuity fan-out (CONT-007); writes a brief part for `continuity-scout` to merge                                         |

Note: the table lists all **22 agents** in `claude-code/agents/` (16 role agents + `orchestrator` + the `continuity-scout` consolidator + its 4 source scouts). `spec-creator` is technically a skill (lives under `skills/spec-creator/`), listed here only because it leads Stage 2's spec drafting when invoked inline by the Multi-Agent Sync — it is not counted among the 22.

---

## 8. Skill inventory (49)

Skills are atomic capabilities invoked by agents (or by the loop controller for `workflow-*`). Grouped by category:

### Pipeline core (validation, compliance, planning)

| Skill                       | Purpose                                                                                              |
| --------------------------- | ---------------------------------------------------------------------------------------------------- |
| validator                   | Compliance validation; verifies systems / documents / code against requirements, schemas, standards. |
| spec-compliance             | Requirement-to-implementation mapping + compliance scoring against spec docs.                        |
| spec-creator                | Specification creation; protocol documents; API contracts.                                           |
| spec-analyzer               | Spec analysis, validation, multi-phase implementation planning.                                      |
| meta-reasoner               | Universal meta-cognitive reasoning at flagged complex decision points (DSVSR loop).                  |
| codebase-stats              | Codebase statistics + technical debt tracking.                                                       |
| dependency-analyzer         | Circular dependency detection + architecture layer validation.                                       |
| dependency-matrix-generator | Cross-team dependency registers, critical paths, resource conflicts.                                 |
| refactor-analyzer           | Refactor analysis + planning (interactive).                                                          |
| refactor-executor           | Script splitting / modularisation execution.                                                         |

### Code & testing

| Skill                      | Purpose                                                                 |
| -------------------------- | ----------------------------------------------------------------------- |
| production-code-workflow   | Multi-language production code patterns; placeholder detection; review. |
| library-implementer-python | Python library / lib module / helper utilities implementation.          |
| python-venv-manager        | venv creation, package install, Python runtime.                         |
| test-writer-pytest         | pytest test writing; integration + unit tests.                          |
| test-gap-analyzer          | Test coverage gap analysis + missing test generation.                   |
| debug-diagnostics          | Error parsing, categorisation, structured diagnostic reports.           |
| error-standardizer         | Convert inconsistent error patterns to `emit_error()`.                |
| hierarchy-unifier          | Consolidate scattered parent/child task operations.                     |
| schema-migrator            | JSON schema version upgrades + data validation.                         |

### Workflow & dev (loop-controller invoked)

| Skill            | Purpose                                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------ |
| workflow-start   | Start a work session with task overview.                                                   |
| workflow-end     | End session with status review + wrap-up.                                                  |
| workflow-focus   | Show / set task focus (single-task discipline).                                            |
| workflow-next    | Suggest next task based on dependencies + state.                                           |
| workflow-dash    | Project task dashboard / overview.                                                         |
| workflow-plan    | Plan-mode prompt optimisation + task tracking.                                             |
| dev-workflow     | Atomic commits, conventional commit messages, release management.                          |
| cicd-workflow    | CI/CD pipelines for GitHub Actions + GitLab CI; deployment troubleshooting.                |
| docker-workflow  | Docker image building, container execution, debugging patterns.                            |
| docker-validator | Docker environment validation (Stage 5 compliance); Compose build / HTTP endpoint probing. |
| task-executor    | Generic task execution agent (catch-all).                                                  |

### Docs & comms

| Skill                   | Purpose                                                         |
| ----------------------- | --------------------------------------------------------------- |
| docs-lookup             | Library / framework docs lookup via Context7.                   |
| docs-write              | Markdown / MDX / README authoring per style guide.              |
| docs-review             | Documentation review against style guide + PR review mode.      |
| release-notes-generator | Categorised release notes from git history (P-061).             |
| adr-publisher           | ADR authoring per MADR template (P-060).                        |
| sprint-goal-linker      | Sprint Goal authoring + intent trace validation (P-022, P-023). |
| story-generator         | INVEST stories from deliverables (P-024, P-029).                |
| skill-creator           | Create / update / package new skills.                           |
| skill-lookup            | Search / install Agent Skills from prompts.chat.                |

### Domain & governance

| Skill                     | Purpose                                                                                                     |
| ------------------------- | ----------------------------------------------------------------------------------------------------------- |
| accessibility-check       | WCAG 2.1 AA/AAA compliance checking for UI / web.                                                           |
| security-auditor          | Security vulnerability scanning for shell scripts (TOCTOU, symlink, injection).                             |
| threat-modeler            | STRIDE threat enumeration for security-critical changes (P-038).                                            |
| cab-reviewer              | Pre-Launch Risk Review (CAB Decision Record) for HIGH/CRITICAL releases (P-076).                            |
| slo-definer               | SLO definitions + error budget calculations for new / modified services (P-054).                            |
| observability-setup       | Monitoring, alerting, dashboards, distributed tracing configuration.                                        |
| okr-retrospective-tracker | OKR scoring + 30/60/90 retrospective templates (P-072, P-073).                                              |
| cost-estimator            | Cloud infrastructure cost estimation (FinOps).                                                              |
| raid-logger               | Append-only RAID log management (P-010, P-074, P-075).                                                      |
| researcher                | Research + investigation skill for multi-source fact-finding (mirrors the researcher agent at skill level). |

Three "always-on" skills fire before stage routing: `meta-reasoner` (REASONER-001), `continuity-scout`'s read sequence (CONT-001 anchor), and `session-manager`'s boot infrastructure.

---

## 9. Routing & MANIFEST-001

### 9.1 The manifest registry

`claude-code/manifest.json` is the single source of truth for component discovery. Top-level totals: **22 agents, 49 skills, 1 command (`/auto-orchestrate`), 28 processes**. The 22 agents include the 4 source-category continuity scouts (`scout-jsonl`, `scout-sessions`, `scout-pipeline`, `scout-context`) added by CONT-007 (SCOUT-FANOUT-001) — they run in parallel at Step -0.5 and the existing `continuity-scout` is now the consolidator that merges their 4 parts into the canonical `continuity-brief.md`. Every agent has a matching `claude-code/agents/<name>.md`; every skill has a matching `claude-code/skills/<name>/SKILL.md`. The orchestrator looks up agents/skills by name from this JSON at spawn time. Missing entries log warnings; the orchestrator still attempts the spawn (best-effort dispatch).

The user's installed registry lives at `~/.claude/manifest.json` (deployed by `install.sh`). The two should be content-identical; `install.sh --check` reports drift.

### 9.2 PREFLIGHT-001 — pipeline-critical subset

Pre-flight verifies a curated subset of components rather than the full inventory. The subset is 11 agents + 11 skills enumerated in the Pipeline Component Matrix:

**11 critical agents**: orchestrator, researcher, session-manager, continuity-scout, product-manager, technical-program-manager, engineering-manager, software-engineer, technical-writer, auditor, debugger.

**11 critical skills**: spec-creator, validator, codebase-stats, refactor-analyzer, dependency-analyzer, production-code-workflow, dev-workflow, spec-compliance, docs-lookup, docs-write, meta-reasoner.

The remaining 7 team agents and 38 conditional skills are lazy-dispatched and validated by the orchestrator at spawn time. Output MUST be phrased as `11/11` with full manifest totals in a parenthetical so readers don't misread the subset as a count of all registered components.

Three "always-on" entries (session-manager, continuity-scout, meta-reasoner) are mandatory because they fire at Step 0 / Step −0.5 / complexity-hook sites BEFORE stage routing.

### 9.3 AUTO-001 — loop controller spawns only orchestrators

The `/auto-orchestrate` loop controller may **only** spawn the orchestrator agent. Per-phase exceptions are dispatched BY the orchestrator (or by the loop controller for explicit phase overrides documented in the Execution Guard at the top of `auto-orchestrate.md`):

- Default: orchestrator
- Phase 5v: auditor (orchestrator transition)
- Phase 5e: debugger (orchestrator transition)
- Phases 5q/5s/5i/5d: matching domain lead + co-agents
- Stage 6 / Phase 7-9: phase-lead matrix per Pipeline Stage Reference

The Execution Guard at the top of `auto-orchestrate.md` enforces that the loop controller never reads project files, identifies services, creates implementation tasks (other than the single Step 2c parent tracking task), or skips human gates.

---

## 10. Constraints reference (MAIN-001..017)

Summary of the orchestrator's immutable constraint table (full text in `claude-code/agents/orchestrator.md` lines 32-50):

| ID       | One-line rule                                                                                                                                                                                                                                                              |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| MAIN-001 | Stay high-level; delegate ALL implementation work to subagents.                                                                                                                                                                                                            |
| MAIN-002 | Spawn subagents via the `Agent` tool only (never the legacy `Task` form).                                                                                                                                                                                              |
| MAIN-003 | Pass `subagent_type` matching `manifest.agents[*].name`.                                                                                                                                                                                                               |
| MAIN-004 | Never reuse subagent context across stages (fresh spawn per stage / per task).                                                                                                                                                                                             |
| MAIN-005 | Read stage-receipts to learn what happened; do not re-read project files yourself.                                                                                                                                                                                         |
| MAIN-006 | Implementation fix-loop cap: 3 validator→fix iterations per task.                                                                                                                                                                                                         |
| MAIN-007 | Token budget cap per spawn; check `REMAINING_BUDGET` before each spawn.                                                                                                                                                                                                  |
| MAIN-008 | Mandatory stage receipt per stage close.                                                                                                                                                                                                                                   |
| MAIN-009 | Handover receipt at every agent boundary (per HANDOVER-001/002/003).                                                                                                                                                                                                       |
| MAIN-010 | Append (never overwrite) RAID log (RAID-001).                                                                                                                                                                                                                              |
| MAIN-011 | Read CLAUDE.md / continuity-brief.md as preamble per PREAMBLE-001..004.                                                                                                                                                                                                    |
| MAIN-012 | Forbidden rationalisations: no self-diagnosed "agent unavailable" without real attempted spawn failure (Fallback Protocol).                                                                                                                                                |
| MAIN-013 | Decomposition gate: NEVER spawn software-engineer without `dispatch_hint`.                                                                                                                                                                                               |
| MAIN-014 | No auto-commit; no git write operations; surface commit messages at session end.                                                                                                                                                                                           |
| MAIN-015 | Always-visible processing: output progress before/after every spawn. Silence = perceived crash.                                                                                                                                                                            |
| MAIN-016 | **Deterministic artifact contract + remediation dispatch**. Read newest `gate-completeness-<TS>.json` → iterate `rules_missing[]` → spawn each owner with template → re-run checker → cap 3 cycles → terminal_state `INCOMPLETE_ARTIFACTS` on exhaustion. |
| MAIN-017 | **Always populate `domain-reviews/`, `phase-receipts/`, `reasoning-traces/`, `meetings/`** via the Stage-Close Protocol (Parts 1.1–1.4) — see §11.4.                                                                                                      |

Plus auto-orchestrate.md's own table (lines 380-410): PREFLIGHT-001, PRE-RESEARCH-GATE, WORKFLOW-SYNC-001/002, ENFORCE-UPGRADE-001, RAID-001, AUTO-EVAL-001, REASONING-GATE-001, OUTPUT-TRIPLET-001, PER-STORY-RESEARCH-001, DECOMP-REASONING-001, TASK-CREATION-REASONING-001, HUMAN-GATE-001, CAB-GATE-001, HANDOVER-001/002/003, TASK-ARG-001, AUTO-PACING-001, ENG-STD-001, MEETING-001, MEETING-GATE-001, LAYOUT-GATE-001, ORCHESTRATE-FLAT-001, ARTIFACT-ENVELOPE-001, ARTIFACT-COMPLETENESS-001, ARTIFACT-CONTRACT-001, ARTIFACT-CHECK-001, CONT-001, REASONER-001. Token-optimization constraints (§15): CONTEXT-DIET-001, DOMAIN-QUERY-001, PROTOCOL-PACK-SLIM-001, CONTINUITY-TIER-001 (joining the existing SKILL-FRONTMATTER-001, MANIFEST-DIGEST-001, TEMPLATE-EXTRACT-001, STAGE-RECEIPT-DIET-001, HANDOVER-COMPRESS-001). The full enumerated index lives in `_shared/references/CONSTRAINTS-REGISTRY.md`.

---

## 11. Artifact contract

### 11.1 `manifest.yml` — 100 rules

`claude-code/templates/orchestrate-session/manifest.yml` is the deterministic per-session contract. It declares every required path with:

- `id` — rule ID (e.g. ART-S3-004)
- `path` — glob with placeholders
- `template` — seed file under `templates/orchestrate-session/`
- `owner` — the agent or skill that produces it
- `cardinality` — `one` / `one-per-deliverable` / `one-per-task` / `one-per-stage` / `one-per-category` / `one-per-gate` / `one-per-process` / `one-or-more`
- `schema` — JSON-schema path under `templates/orchestrate-session/schemas/`
- `required` — true / false

Placeholder tokens: `{sid}`, `{deliverable}`, `{task}`, `{stage}`, `{ts}`, `{date}`, `{gate}`, `{process}`, `{category}`.

Rule-ID prefix → folder mapping:

| Prefix                    | Folder                      | Example                                                                                  |
| ------------------------- | --------------------------- | ---------------------------------------------------------------------------------------- |
| ART-ROOT-*                | `<sid>/`                  | checkpoint.json, MANIFEST.jsonl, continuity-brief.md, raid-log.json, proposed-tasks.json |
| ART-PLAN-*                | `<sid>/planning/`         | P1-P4 + sprint-kickoff-receipt                                                           |
| ART-S0-* through ART-S6-* | `<sid>/stage-N/`          | per-stage and per-deliverable / per-task artifacts                                       |
| ART-S45-*                 | `<sid>/stage-4.5/`        | codebase-stats, refactor-analyzer, dependency-analyzer                                   |
| ART-GATE-*                | `<sid>/gates/`            | gate-approval / gate-pending / gate-rejected / gate-completeness / gate-history.jsonl    |
| ART-MTG-*                 | `<sid>/meetings/`         | minutes per canonical meeting + baseline check-ins                                       |
| ART-DR-*                  | `<sid>/domain-reviews/`   | per-stage domain reviews                                                                 |
| ART-PR-*                  | `<sid>/phase-receipts/`   | phase-stage-N-* + per-sub-phase receipts                                                 |
| ART-RT-*                  | `<sid>/reasoning-traces/` | meta-reasoner traces + baselines                                                         |
| ART-HO-*                  | `<sid>/handovers/`        | per-boundary handover receipts                                                           |

### 11.2 `check-completeness.py` — the validator

`templates/orchestrate-session/check-completeness.py` reads `manifest.yml` and validates a session folder. CLI:

```
python3 templates/orchestrate-session/check-completeness.py \
    --session-root .orchestrate/<sid>       # validate a session
    [--manifest path/to/manifest.yml]       # default: sibling manifest.yml
    [--lint]                                # validate manifest only
    [--allow-unrooted]                      # forensic standalone runs on misplaced sessions
```

Exit codes: `0` = PASS, `1` = FAIL (missing artifacts / consistency failures), `2` = usage / IO error.

Writes `gates/gate-completeness-<TS>.json` with `verdict`, `rules_missing[]` (each entry has `rule_id`, `owner`, `template`, `path_pattern`, `cardinality`, `expected_min`, `found`, `note`), `consistency_failures[]`, and `remediation[]` (each consistency failure carries an inline CONS-* remediation hint mapped to the responsible MAIN-017 Stage-Close Protocol part).

Seven consistency checks:

| ID       | What it verifies                                                                                                                                   |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| CONS-001 | Every deliverable D in proposed-tasks.json has stage-0/`<D>`/, stage-1/`<D>`/, and stage-1/`<D>`/gate-approval-decomposition-`<D>`-*.json. |
| CONS-002 | Every task T has stage-2/`<T>`/, stage-3/`<T>`/, and stage-2/`<T>`/gate-approval-task-creation-`<T>`-*.json.                               |
| CONS-003 | Every stage 0..6 has a `phase-receipts/phase-stage-<N>-*.json`.                                                                                  |
| CONS-004 | Every stage in {2,3,5,6} has ≥1 real `domain-reviews/*-stage-<N>*.md` (baseline qa-engineer counts; sentinels don't).                           |
| CONS-005 | `meetings/` has ≥1 real `.json` (sentinels `*-none-*.json` excluded).                                                                       |
| CONS-006 | `reasoning-traces/` has ≥1 `.json` (real or baseline).                                                                                        |
| CONS-007 | Session root is under `.orchestrate/` (LAYOUT-GATE-001 / ORCHESTRATE-FLAT-001). Bypass via `--allow-unrooted`.                                 |

### 11.3 Step 7 (ARTIFACT-CHECK-001) + remediation dispatch (MAIN-016)

The loop controller MUST execute Step 7 before writing `checkpoint.terminal_state`. Pseudocode-free imperative procedure (in `auto-orchestrate.md` lines ~3978-4015):

```
7.1  Bash:  python3 templates/orchestrate-session/check-completeness.py --session-root .orchestrate/<sid>
7.2  Parse gates/gate-completeness-<newest TS>.json#verdict.
7.3  IF verdict != "PASS":
       cycle = 0
       while verdict != "PASS" and cycle < 3:
           cycle += 1
           Spawn(orchestrator, PHASE: "REMEDIATE_ARTIFACTS",
                 payload: {rules_missing, consistency_failures})
           # The orchestrator iterates and dispatches per rule.owner per MAIN-016.
           Re-run 7.1; re-parse 7.2.
       After 3 FAIL cycles → terminal_state = "INCOMPLETE_ARTIFACTS"; do NOT write "completed".
7.4  ONLY IF verdict == "PASS": proceed to terminal-state decision.
```

A hard pre-write assertion at the start of the terminal-state decision block requires a current `gate-completeness-*.json verdict=PASS` produced within the last 10 minutes; missing → self-abort with `[ARTIFACT-CHECK-001-MISSING]` and rewind to 7.1.

### 11.4 MAIN-017 Stage-Close Protocol (Parts 1.1–1.4)

The orchestrator executes the Stage-Close Protocol at every stage close in {0..6} before the next stage opens. This is the always-populate implementation (the section that was missing before today and produced the empty-directory bug fixed by today's wiring). Full body in `claude-code/agents/orchestrator.md` after the loop body (~line 489).

| Part | When                                               | What                                                                                                                | Output template                                                                                                                  |
| ---- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1.1  | Every stage 0..6                                   | Orchestrator writes phase-receipt (Bash, not delegated)                                                             | `templates/orchestrate-session/phase-receipts/phase-receipt.json` → `phase-receipts/phase-stage-<N>-<TS>.json`              |
| 1.2  | Stages {2,3,5,6}                                   | Evaluate `manifest.agents[*].activation_rules[]`; spawn matching agents OR baseline qa-engineer (zero rules fire) | `templates/orchestrate-session/domain-reviews/domain-review.md` → `domain-reviews/qa-engineer-stage-<N>-baseline.md`        |
| 1.3  | Every stage close where meta-reasoner did not fire | Orchestrator writes baseline reasoning trace                                                                        | `templates/orchestrate-session/reasoning-traces/reasoning-trace-baseline.json` → `reasoning-traces/stage-<N>-baseline.json` |
| 1.4  | Stages {2,3,5,6} where no canonical meeting fired  | Spawn engineering-manager for baseline check-in                                                                     | `templates/orchestrate-session/meetings/meeting-baseline-stage.json` → `meetings/meeting-baseline-stage-<N>-<TS>.json`      |

The baseline qa-engineer review (Part 1.2 else-branch) is a real spot-check + verdict (PASS / CONCERN / FAIL) with 3-5 findings against the stage's primary artifact — NOT a placeholder.

### 11.5 ARTIFACT-ENVELOPE-001 — unified envelope

Every JSON artifact and every Markdown artifact under `.orchestrate/<sid>/**` wraps a type-specific body in the envelope defined by `claude-code/lib/artifact_envelope/schemas.py`. JSON artifacts hold the envelope as their top-level object; Markdown artifacts encode it as YAML front-matter. The orchestrator validates via `artifact_envelope.validate(path, expected_type)` before accepting; `workflow-end` validates the whole session at close. Invalid envelopes HALT with `[ENVELOPE-INVALID]`.

The envelope also carries two optional digest fields (CONTEXT-DIET-001): **`excerpt`** — a bounded ≤600-char one-paragraph summary — and **`excerpt_pointers`** — body-section paths (e.g. `["body.gaps[]"]`) telling a reader where to deep-read. They are populated by the producer via `build_envelope(...)` when `checkpoint.optimizations.artifact_excerpt` is on; the full `body` is **never** truncated, and the validator treats `excerpt` as optional (type-checked, never length-failed). See §15.

### 11.6 ARTIFACT-COMPLETENESS-001 — no sentinels

`meetings/`, `handovers/`, `domain-reviews/`, `phase-receipts/`, `reasoning-traces/`, and every per-stage folder MUST contain real per-run artifacts. Sentinel `*-none-*.json` placeholders are NOT acceptable. When a folder is driven by conditional activation rules and no rule fires, the orchestrator MUST emit a baseline real artifact via the Stage-Close Protocol. Empty folders at session close fail with `[ARTIFACT-MISSING]` and append to `.orchestrate/audit/findings-ledger.jsonl`.

---

## 12. Session layout — `.orchestrate/` tree

```
.orchestrate/
├── domain/                          (JSONL stores — cross-session knowledge: context, learnings)
├── audit/
│   └── findings-ledger.jsonl        (append-only audit ledger; [ARTIFACT-MISSING] failures land here)
├── knowledge_store/                 (long-term knowledge persistence)
├── pipeline-state/
│   ├── workflow/                    (task-board.json — single source of truth while /auto-orchestrate active)
│   ├── command-receipts/
│   ├── process-log/
│   ├── baselines/
│   └── improvement-recommender/
└── <session-id>/                    (one per session; e.g. auto-orc-20260518-mmexec)
    ├── checkpoint.json              ART-ROOT-001  (updated every iteration; schema 1.10.0)
    ├── MANIFEST.jsonl               ART-ROOT-002  (append-only event log; enriched into a discovery index with artifact_type/status/excerpt under CONTEXT-DIET-001 — see §15)
    ├── continuity-brief.md          ART-ROOT-003  (written by continuity-scout pre-P1; HOT core + Slice Index under CONTINUITY-TIER-001 — see §15)
    ├── raid-log.json                ART-ROOT-004  (RAID-001; single log, append-only)
    ├── proposed-tasks.json          ART-ROOT-005  (merged at end of Stage 1)
    ├── planning/                    ART-PLAN-*    (P1-P4 + sprint-kickoff-receipt)
    ├── stage-0/                     ART-S0-*      (researcher: project-wide + per-deliverable)
    ├── stage-1/                     ART-S1-*      (product-manager: per-deliverable + merged)
    ├── stage-2/                     ART-S2-*      (spec-creator: per-task spec.md + receipts)
    ├── stage-3/                     ART-S3-*      (software-engineer: per-task changes.md + aggregate)
    ├── stage-4/                     ART-S4-*      (test-writer-pytest: per-task + aggregate)
    ├── stage-4.5/                   ART-S45-*     (codebase-stats + refactor-analyzer + dependency-analyzer)
    ├── stage-5/                     ART-S5-*      (validator + compliance + sub-phase findings)
    ├── stage-6/                     ART-S6-*      (technical-writer: api/integration/ops-runbook/adr/user-guide/changelog)
    ├── gates/                       ART-GATE-*    (gate-approval-*, gate-pending-*, gate-rejected-*,
    │                                                gate-completeness-*, gate-history.jsonl)
    ├── meetings/                    ART-MTG-*     (canonical meeting minutes + baseline check-ins)
    ├── handovers/                   ART-HO-*      (handover-<from>-to-<to>-<TS>.json + ack-*)
    ├── domain-reviews/              ART-DR-*      (<agent>-stage-<N>.md per stage in {2,3,5,6})
    ├── phase-receipts/              ART-PR-*      (phase-stage-N-*, phase-5v/5e/5q/5s/5i/5d/7/8/9-*)
    └── reasoning-traces/            ART-RT-*      (meta-reasoner traces + baselines)
```

LAYOUT-GATE-001 verifies this tree exists before any spawn (Step 3.0 in `auto-orchestrate.md`). Step 3.0a self-heals misplaced sessions: if `./<sid>/` exists at repo root but `.orchestrate/<sid>/` does not, the loop controller `mv`s it; if both exist, it aborts with `[LAYOUT-GATE-001-ERROR]` and requires manual reconciliation.

---

## 13. Templates tree

`claude-code/templates/orchestrate-session/` mirrors the session layout — each subdirectory holds the seed files agents copy from when emitting artifacts.

```
templates/orchestrate-session/
├── README.md
├── manifest.yml                          (100 rules + 7 consistency_checks)
├── check-completeness.py                 (the validator; CONS-001..007 + --lint + --allow-unrooted)
├── session/                              (root artifact templates: checkpoint.json, MANIFEST.jsonl,
│                                          continuity-brief.md, raid-log.json, proposed-tasks.json)
├── planning/                             (P1-P4 + sprint-kickoff-receipt + per-review templates)
├── stage-0/                              (project-wide + per-deliverable research + receipts)
├── stage-1/                              (per-deliverable + merged proposed-tasks)
├── stage-2/                              (per-task spec.md + receipt)
├── stage-3/                              (per-task changes.md + receipt + aggregate)
├── stage-4/                              (per-task receipt + aggregate; "no test-only tasks" branch)
├── stage-4_5/                            (codebase-stats, refactor-analyzer, dependency-analyzer)
├── stage-5/                              (validation-report.{md,json} + compliance-report.json)
├── stage-6/                              (api / integration / ops-runbook / adr / user-guide / changelog topic templates)
├── gates/                                (gate-approval, gate-pending, gate-completeness, gate-history.jsonl)
├── meetings/                             (meeting-ceremony.json, minutes-multi-agent-sync.json,
│                                          role-perspective.md, meeting-baseline-stage.json [NEW today])
├── handovers/                            (handover.json envelope)
├── domain-reviews/                       (domain-review.md template — used for both activated + baseline)
├── phase-receipts/                       (phase-receipt.json template — used by MAIN-017 Part 1.1)
├── reasoning-traces/                     (reasoning-trace.json + reasoning-trace-baseline.json [NEW today])
└── schemas/                              (18 JSON schemas: _envelope, checkpoint, stage-receipt,
                                           phase-receipt, gate, handover, meeting-minutes, raid-log,
                                           compliance-report, validation-report, codebase-stats,
                                           dependency-analyzer, refactor-analyzer, manifest-entry,
                                           gate-history-entry, proposed-tasks, reasoning-trace,
                                           sprint-kickoff-receipt, meeting-ceremony)
```

The two NEW templates added today (when MAIN-017 Stage-Close Protocol was wired): `reasoning-traces/reasoning-trace-baseline.json` (skipped-trace envelope) and `meetings/meeting-baseline-stage.json` (engineering-manager baseline check-in receipt).

---

## 14. Cross-cutting protocols

### 14.1 Continuity (CONT-001)

The `continuity-scout` agent is spawned at Step −0.5 of every session (before P1). It reads `.orchestrate/domain/*` JSONL stores, the last 3 prior sessions' planning + learnings, baselines, and the audit ledger, then writes `.orchestrate/<sid>/continuity-brief.md`. Every spawned agent reads this file per `agent-preamble.md` (PREAMBLE-001..004) so no agent ever starts from a cold context. Refreshed pre-Stage-0 with P3 dependency-charter tag filters.

### 14.2 Handovers (HANDOVER-001/002/003)

Every agent boundary emits a handover receipt:

- **HANDOVER-001**: producer writes `handovers/handover-<from>-to-<to>-<YYYYMMDD>-<HHMMSS>.json` on completion. Required fields: `handover_id`, `from_agent`, `to_agent`, `from_phase`, `to_phase`, `produced_at`, `primary_artifact`, `supplementary_artifacts`, `key_decisions`, `open_questions`, `blockers`, `context_carry`, `confidence` (high/medium/low).
- **HANDOVER-002**: consumer writes `ack-<handover_id>.json` before doing work, recording `acknowledged_by`, `questions_for_handoff`, `request_clarification`, `proceed_anyway`.
- **HANDOVER-003**: clarification loop cap — max 2 rounds. Round 2 → log `[HANDOVER-WARN]` and proceed.

The schema lives in `_shared/protocols/command-dispatch.md` "Agent-to-Agent Handover Protocol".

### 14.3 RAID-001 — single RAID log

Both P-010 (Stage 1 seeding) and P-074 (risk management) share a single RAID log at `.orchestrate/<sid>/raid-log.json` — append-only JSONL. Product-manager seeds at Phase 2 (Scope Contract); Phase 9 (Continuous Governance) appends risk-domain entries. Neither phase overwrites existing entries. Phase 5s, Phase 7 CAB, and Phase 8 post-mortems also append.

### 14.4 ENG-STD-001 — immutable Engineering Standards

The standards at `_shared/protocols/engineering-standards.md` are MANDATORY for every code-producing agent at every stage:

- §1 SOLID + Factory + DI defaults + explicit type annotations
- §2 type safety
- §3 Result-type error handling + RFC 9457 errors + resilience patterns
- §4 naming consistency; no `Impl` / `Manager` / `Helper`
- §5 no commented-out code; no unused symbols; no orphan TODO
- §6 async end-to-end + cancellation threading + bounded back-pressured channels
- §7 warnings-as-errors + shared linter config
- §8 ≤300 lines/type, ≤40 lines/function, no env-var sprawl, no direct instantiation
- §9 DI lifetime scoping; factory-then-DI wiring
- §10 typed data class for >2 args; immutable by default

Enforcement points: Stage 2 reasoning gate (TASK-CREATION-REASONING-001 sub-questions cite §N rules), Stage 3 implementation preamble, Stage 4.5 (codebase-stats + refactor-analyzer detect §5/§8/§9/§10 violations), Stage 5 (validator emits per-section ENG-STD-001 score; `overall_score < 0.9` → FAIL recommended_verdict).

User task arguments MAY ADD stricter rules; they CANNOT loosen the baseline. Contradictions log `[ENG-STD-001] task argument attempted to loosen <rule>; baseline applied.`

### 14.5 Layout (LAYOUT-GATE-001 / ORCHESTRATE-FLAT-001)

Unified `.orchestrate/` root: `.domain/`, `.audit/`, `.pipeline-state/` are subfolders of `.orchestrate/` (not siblings). Legacy roots resolve via `claude_code.lib.path_compat` for one release window. New code MUST write to the unified paths. Migration via `claude-code/scripts/migrate_to_unified_orchestrate.py` (idempotent via `.orchestrate/.migration-v1.done`).

LAYOUT-GATE-001 (Step 2.0 + Step 3.0 in `auto-orchestrate.md`) verifies the layout exists before any spawn. Missing → self-abort and re-run Step 2.0 mkdir block.

---

## 15. Token-Optimization Framework

The pipeline can be token-heavy: an `/auto-orchestrate` run spawns 20-60 subagents, each loading
protocol boilerplate, the continuity brief, and upstream artifacts. A unified, opt-in framework keeps
token cost down **without deleting any artifact (all stay byte-identical on disk) and without losing
context fidelity** — agents can always deep-read the full artifact/brief/protocol on demand.

### 15.1 Gating model — `checkpoint.optimizations.*`

Every optimization is a boolean flag in `checkpoint.optimizations` (checkpoint **schema 1.10.0**).
Convention for each flag: **slim payload primary · full payload on disk / re-derivable · consumers
tolerate both · a `needs_full_*` spawn flag re-fattens on demand · a loud `[<ID> FAIL]` fallback never
silently strips content**. Flags **default ON for fresh sessions**, **OFF on resume** (so resumed /
mixed sessions stay byte-compatible). The migration ladder adds fields with safe defaults and bumps the
schema (… 1.8.0 → 1.9.0 → **1.10.0**); see `commands/auto-orchestrate.md`. Canonical per-flag rules
live in `_shared/protocols/command-dispatch.md`; the enumerated ID index is
`_shared/references/CONSTRAINTS-REGISTRY.md`.

### 15.2 The nine optimizations

| Flag | Constraint | What it does |
|------|-----------|--------------|
| `skill_frontmatter_routing` | SKILL-FRONTMATTER-001 | Skill discovery loads YAML frontmatter only (~300 tok); body at invoke. |
| `process_injection_slim` | (INJECT) | Inject only fired process hooks per stage, not the full injection map. |
| `manifest_digest` | MANIFEST-DIGEST-001 | Non-orchestrator spawns get a ~2.6k manifest digest, not the ~19k full manifest. |
| `per_stage_templates` | TEMPLATE-EXTRACT-001 | Orchestrator spawn loads CORE + only the active stage/phase template, not the full file. |
| `stage_receipt_diet` | STAGE-RECEIPT-DIET-001 | Producers write slim v2.0.0 stage receipts; consumers read both v1/v2. |
| `handover_compress` | HANDOVER-COMPRESS-001 | Slim v2.0.0 handover receipts; `context_carry` re-derived from checkpoint. |
| `artifact_excerpt` | CONTEXT-DIET-001 | Envelope `excerpt`/`excerpt_pointers` (≤600 chars) + enriched `MANIFEST.jsonl` → digest-by-default reading; full body deep-read on demand. |
| `protocol_pack_slim` | PROTOCOL-PACK-SLIM-001 | Spawns load `_shared/protocols/spawn-core.md` (~2k) instead of the 5-doc stack (~7.5k); code agents still get full ENG-STD at Stage 3. |
| `continuity_brief_tiered` | CONTINUITY-TIER-001 | `continuity-scout` adds a `## HOT` core + `## Slice Index` over the same brief; spawns read HOT + their slice, full brief on demand. |

### 15.3 Digest-by-default (CONTEXT-DIET-001 + DOMAIN-QUERY-001)

The principle behind the newest four: **read a digest first, deep-read the body only when needed.**
Producers populate the envelope `excerpt` (§11.5); the orchestrator enriches each `MANIFEST.jsonl` line
with `artifact_type`/`status`/`excerpt`/`excerpt_pointers` so one index scan reveals what exists.
`spawn-core.md` slims the per-spawn protocol stack to the rules-by-ID + a Reference Index. The continuity
brief gains a HOT core + Slice Index (PREAMBLE-001 reads HOT + the agent's slice, and MUST full-read the
brief before declaring "no relevant item" — so PREAMBLE-002 carryover stays sound). Agents query the
domain-memory SQLite FTS index via `DomainIndexer.query(store, text, limit)` (DOMAIN-QUERY-001) instead
of scanning whole JSONL ledgers, falling back to the JSONL on any error. Nothing is deleted; every full
artifact, brief, and source protocol remains on disk and one `Read` away.

---

## 16. Where to read next

| Topic                                         | File / location                                                                                        |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Loop controller flow (Steps 0..7)             | `claude-code/commands/auto-orchestrate.md`                                                           |
| Orchestrator constraint table (MAIN-001..017) | `claude-code/agents/orchestrator.md` lines 32-50                                                     |
| Per-stage spawn templates                     | `claude-code/agents/orchestrator.md` lines ~499-1827                                                 |
| Stage-Close Protocol (MAIN-017)               | `claude-code/agents/orchestrator.md` section after the loop body (~line 489+)                        |
| Reasoning gate decision tree                  | `claude-code/commands/auto-orchestrate.md` § "Reasoning Gate Logic"                                 |
| Meta-reasoner DSVSR loop + retry rule         | `claude-code/skills/meta-reasoner/SKILL.md`                                                          |
| Human-in-the-loop gates                       | `claude-code/commands/auto-orchestrate.md` § "Human-in-the-Loop Gates"                              |
| Meeting protocol + canonical catalog          | `claude-code/_shared/protocols/meeting-enforcement.md`                                               |
| Domain phase trigger rules (ACT-001..012)     | `claude-code/_shared/protocols/agent-activation.md`                                                  |
| Handover schema                               | `claude-code/_shared/protocols/command-dispatch.md`                                                  |
| Engineering Standards (full text)             | `claude-code/_shared/protocols/engineering-standards.md`                                             |
| Output schemas (envelope)                     | `claude-code/_shared/protocols/output-schemas.md` + `claude-code/lib/artifact_envelope/schemas.py` |
| Artifact contract rules                       | `claude-code/templates/orchestrate-session/manifest.yml`                                             |
| Completeness validator                        | `claude-code/templates/orchestrate-session/check-completeness.py`                                    |
| Templates README                              | `claude-code/templates/orchestrate-session/README.md`                                                |
| CI engine (within-run + cross-run loops)      | `claude-code/lib/ci_engine/`                                                                         |
| Domain memory persistence                     | `claude-code/lib/domain_memory/` (FTS retrieval via `DomainIndexer.query`, DOMAIN-QUERY-001)         |
| Path compatibility shim                       | `claude-code/lib/path_compat.py`                                                                     |
| Shared UTC timestamp helpers                  | `claude-code/lib/_time.py`                                                                           |
| Token-optimization framework                  | this doc §15; canonical rules in `claude-code/_shared/protocols/command-dispatch.md`                 |
| Slim spawn-protocol pack (PROTOCOL-PACK-SLIM-001) | `claude-code/_shared/protocols/spawn-core.md`                                                    |
| Constraint / identifier registry (generated)  | `claude-code/_shared/references/CONSTRAINTS-REGISTRY.md`                                              |
| Process injection map                         | `claude-code/processes/process_injection_map.md`                                                     |
| Install / uninstall scripts                   | `install.sh`, `uninstall.sh`                                                                       |
| User-facing playbook                          | `PLAYBOOK.md`                                                                                        |
| Release notes                                 | `RELEASE-NOTES.md`, `CHANGELOG.md`                                                                 |
| Security audit                                | `SECURITY-AUDIT-v1.1.md`                                                                             |

---
