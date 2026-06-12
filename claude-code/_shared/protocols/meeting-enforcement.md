# Meeting Enforcement Protocol (MEETING-GATE-001)

Canonical meetings produce mandatory minutes. When a required minute is missing, the pipeline **autonomously remediates** at the next gate (writes `gate-warn-meeting-completeness-<TS>.json` and spawns engineering-manager for a baseline check-in in the same iteration) — it does NOT halt or prompt the user, per AUTO-PACING-001.

## Mandatory (Blocking) Meetings

| Process | Meeting | When required | Handler |
|---|---|---|---|
| P-004 | Intent Review (reasoning gate) | Every session unless `--human-planning-gates` is set | Multi-Agent Sync + reasoning-gate verdict (REASONING-GATE-001) |
| P-013 | Scope Lock (reasoning gate) | Every session unless `--human-planning-gates` is set | Multi-Agent Sync + reasoning-gate verdict (REASONING-GATE-001) |
| P-019 | Dependency Acceptance (reasoning gate) | Every session unless `--human-planning-gates` is set | Multi-Agent Sync + reasoning-gate verdict (REASONING-GATE-001) |
| P-025 | Sprint Readiness (reasoning gate) | Every session unless `--human-planning-gates` is set | Multi-Agent Sync + reasoning-gate verdict (REASONING-GATE-001) |
| (Stage 1) | Per-deliverable Epic Decomposition (reasoning gate) | Once per P2 deliverable unless `--human-decomposition-gates` is set; skipped only on single-deliverable (architectural collapse) | Multi-Agent Sync + reasoning-gate verdict (DECOMP-REASONING-001) |
| (Stage 2) | Per-story Implementation-Task Spec Creation (reasoning gate) | Once per Stage 1 story unless `--human-task-creation-gates` is set | Multi-Agent Sync + reasoning-gate verdict (TASK-CREATION-REASONING-001) |
| (Stage 5) | Validation Reasoning Gate (multi-agent verdict feeding Phase 5v human gate) | Every Stage 5 unless `--sequential-stages` is set | Multi-Agent Sync + meta-reasoner-aggregated recommended_verdict (VALIDATION-REASONING-001); recommended_verdict still flows to HUMAN-GATE-001 boundary 6 for human sign-off |
| P-020 | Dependency Standup | Whenever cross-team impact flagged by P3 Dependency Charter | Multi-Agent Sync |
| P-026 | Daily Standup | Iteration boundary; L = every 5 iterations, XL = every 3 | Multi-Agent Sync |
| P-027 | Sprint Review | After Stage 6 completes | Multi-Agent Sync |
| P-028 | Sprint Retrospective | After P-027 | Multi-Agent Sync |
| P-029 | Backlog Refinement | When unrefined backlog items remain at sprint end | Async Single-Agent |
| P-076 | CAB / Change Advisory Board | When `release_flag=true` AND risk class HIGH or CRITICAL | Human-Gated |

The four reasoning-gated planning meetings (P-004, P-013, P-019, P-025) write both:
- `meetings/minutes-<gate-id>-multi-agent-sync-<TS>.json` — the meeting record produced by the facilitator agent
- `reasoning-traces/reasoning-trace-<gate-id>-<TS>.json` — the meta-reasoner's DECOMPOSE→SOLVE→VERIFY→SYNTHESIZE→REFLECT trace
- `gates/gate-approval-<gate-id>-<TS>.json` (envelope verdict `approve`) when aggregate confidence ≥ 0.8, OR `gates/gate-conditional-<gate-id>-<TS>.json` (envelope verdict `conditional`) when retries exhausted at <0.8 — the conditional path then writes `gate-pending-<gate-id>.json` and falls back to legacy human gate for that one gate only.

All other canonical meetings produce minutes (warn-only); their absence does not halt the pipeline.

## Minutes Artifact Schema

Filename: `.orchestrate/<SESSION_ID>/meetings/minutes-<process>-<type>-<YYYYMMDD-HHMMSS>.json`

Body (under unified envelope `artifact_type: meeting_minutes`):

```json
{
  "process_id": "P-020|P-026|P-027|P-028|P-029|P-076|other",
  "meeting_type": "<short-slug>",
  "facilitator_agent": "<agent-name>",
  "participants": ["<agent|user>", "..."],
  "agenda": ["..."],
  "decisions": ["..."],
  "action_items": [
    {"owner": "...", "due": "YYYY-MM-DD", "raid_link": "RAID-id-or-null"}
  ],
  "blockers": ["..."],
  "next_meeting": "ISO-8601 or null"
}
```

When no canonical meeting fires for a stage in {2, 3, 5, 6}, the orchestrator MUST spawn `engineering-manager` for a baseline stage-close check-in and write `meetings/meeting-baseline-stage-<N>-<TS>.json` from `templates/orchestrate-session/meetings/meeting-baseline-stage.json`. This is the meeting half of the MAIN-017 Stage-Close Protocol (Part 1.4) in `agents/orchestrator.md`. Sentinel `*-none-*.json` placeholders are forbidden per ARTIFACT-COMPLETENESS-001 — empty-folder protection comes from a real baseline artifact, not a stub.

## Gate Check (MEETING-GATE-001)

Insert at orchestrator Step 4.8d (between phase-receipt write and stage advance) AND again before Sprint Closure and before the Phase 7 release gate.

**Autonomous remediation (no HALT, no user pause)** per AUTO-PACING-001:

```text
expected = expected_meetings_for(stage, tshirt_size, flags)
present  = glob(".orchestrate/<sid>/meetings/minutes-{p}-*.json") for p in expected
missing  = expected - present
if missing:
    write .orchestrate/<sid>/gates/gate-warn-meeting-completeness-<TS>.json
    append entry to gates/gate-history.jsonl with verdict=warn, reason=MEETING-MISSING-AUTOREMEDIATE
    # AUTONOMOUS REMEDIATION — sub-spawn returns synchronously to this same iteration.
    Agent(subagent_type: engineering-manager,
          description: "Stage-{N} baseline check-in (auto-remediating MEETING-MISSING)",
          prompt: "Write meetings/meeting-baseline-stage-{N}-{TS}.json from "
                  "templates/orchestrate-session/meetings/meeting-baseline-stage.json. "
                  "Two-paragraph receipt: stage outcome + blockers + hand-off. NOT a placeholder.")
    # Continue iteration. Do NOT halt. Do NOT prompt user.
elif not missing and stage in {2, 3, 5, 6} and no real meeting receipt exists for stage N:
    # Baseline check-in (Part 1.4 of orchestrator Stage-Close Protocol)
    Agent(subagent_type: engineering-manager,
          description: "Stage-{N} baseline check-in",
          prompt: "Write meetings/meeting-baseline-stage-{N}-{TS}.json from "
                  "templates/orchestrate-session/meetings/meeting-baseline-stage.json. "
                  "Two-paragraph receipt: stage outcome, blockers seen, hand-off to next stage.")
```

`expected_meetings_for` rules:

- `P-026` when `iteration % cadence == 0` where cadence = 5 (L) or 3 (XL).
- `P-020` when current stage's task list shows `cross_team_impact=true`.
- `P-027`, `P-028`, `P-029` when transitioning from Stage 6 to session close.
- `P-076` when `release_flag` is set AND any RAID with severity in {HIGH, CRITICAL}.

## Multi-Agent Sync Meetings

For ad-hoc multi-agent syncs (orchestrator spawns >=2 agents in parallel for a synthesis step), produce minutes with `process_id: other` and `meeting_type` set to the synthesis topic. These are warn-only but appear in `meetings/` for the audit trail.

## Constraints

| ID | Rule |
|---|---|
| MEETING-GATE-001 | When any blocking meeting's minutes are missing, the pipeline autonomously writes `gates/gate-warn-meeting-completeness-<TS>.json` and spawns engineering-manager for a baseline check-in in the same iteration. NO halt; NO user pause (AUTO-PACING-001). |
| MEETING-GATE-002 | Every multi-agent sync writes minutes (warn-only). |
| MEETING-GATE-003 | When no canonical meeting fires for a stage in {2, 3, 5, 6}, the orchestrator MUST emit a real baseline check-in receipt (`meetings/meeting-baseline-stage-<N>-<TS>.json`) per MAIN-017 Stage-Close Protocol Part 1.4. Sentinel `*-none-*.json` placeholders are NOT acceptable (ARTIFACT-COMPLETENESS-001 supersedes the prior sentinel rule). |
| MEETING-GATE-004 | Minutes envelope MUST validate via the artifact envelope validator. |
