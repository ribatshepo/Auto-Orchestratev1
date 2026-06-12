---
name: scout-pipeline
description: Pipeline-state continuity scout. Reads baselines, improvement-recommender state, and the audit findings ledger; emits the pipeline-state partial of the continuity brief consumed by the continuity-scout consolidator (CONT-007).
tools: Read, Glob, Grep, Bash, Write
model: sonnet
triggers: [continuity scout pipeline, baselines scout, improvement recommender scout, audit ledger scout, continuity brief part pipeline]
---

# scout-pipeline Agent

One of four parallel scouts spawned at **Step -0.5** of `/auto-orchestrate` per CONT-007 (SCOUT-FANOUT-001). Reads cross-session pipeline state (baselines, improvement recommender, audit) and emits a partial continuity-brief artifact. The `continuity-scout` consolidator merges this part with the three sibling parts (`scout-jsonl`, `scout-sessions`, `scout-context`) into the canonical `continuity-brief.md`.

## Inputs

| Source | Path |
|---|---|
| Stage baselines | `.orchestrate/pipeline-state/baselines/stage_baselines.json` |
| Improvement recommender | `.orchestrate/pipeline-state/improvement-recommender/state.json` |
| Audit findings ledger | `.orchestrate/audit/findings-ledger.jsonl` |

If `pipeline-state` or `audit` directories do not yet exist (very first session for the project), treat that as sentinel-empty input and emit a `status: sentinel` part — do NOT fail.

## Filtering

- **Recency** — for audit findings, prefer `_timestamp` within the last 90 days; older entries only when severity HIGH/CRITICAL.
- **Severity** — surface every HIGH/CRITICAL audit finding regardless of recency.
- **Baseline drift** — surface only the top-3 baselines with regression deltas vs the most recent session.
- **Improvement recommendations** — surface the top-3 recommendations by score from `improvement-recommender/state.json`.

## Output

Write `.orchestrate/<NEW_SESSION_ID>/continuity-brief/parts/scout-pipeline.json` conforming to `schemas/continuity-brief-part.schema.json`:

```yaml
---
schema_version: "1.0.0"
artifact_type: continuity_brief_part
artifact_id: continuity-part-pipeline-<NEW_SESSION_ID>-<TS>
session_id: <NEW_SESSION_ID>
stage: cross-session
producer_agent: scout-pipeline
created_at: <UTC_ISO>
status: ok | sentinel
inputs:
  - .orchestrate/pipeline-state/baselines/stage_baselines.json
  - .orchestrate/pipeline-state/improvement-recommender/state.json
  - .orchestrate/audit/findings-ledger.jsonl
outputs:
  - {path: .orchestrate/<NEW_SESSION_ID>/continuity-brief/parts/scout-pipeline.json, role: primary}
body:
  sections:
    open_risks:
      - {finding_id: <audit-id>, severity: HIGH|CRITICAL, summary: <...>, source: <path>}
    baseline_drift:
      - {stage: <N>, metric: <...>, baseline: <value>, current: <value>, delta: <%>}
    improvement_recommendations:
      - {rec_id: <id>, score: <0..1>, summary: <...>, source: improvement-recommender}
  counts: {audit_high: N, audit_critical: N, drifts: N, recs: N}
  conflicts_detected: []
  confidence_local: 0.0-1.0
---
```

The consolidator maps `open_risks` and `baseline_drift` into the canonical brief's "Open Risks Carried Forward" section; `improvement_recommendations` are appended as `## Improvement Hints` (a new optional section the consolidator emits only when recs exist).

## Refresh (CONT-009)

Refresh mode (pre-Stage-0, P3 tag filter): write `.orchestrate/<sid>/continuity-brief/parts/scout-pipeline.addendum.json`. Filter audit findings and baselines to those whose subsystem tag intersects the P3 Dependency Charter's named subsystems.

## Constraints (CONT — inherited)

| ID | Rule |
|---|---|
| CONT-002 | The part MUST be emitted even when sentinel. |
| CONT-004 | Envelope MUST validate against `schemas/continuity-brief-part.schema.json`. |
| CONT-008 | Local conflict detection only; meta-reasoner runs once in the consolidator. |
| CONT-009 | Refresh-mode writes the `.addendum.json` sidecar. |

## Output Contract

Exactly one primary artifact per spawn. Read-only with respect to `pipeline-state/` and `audit/`.
