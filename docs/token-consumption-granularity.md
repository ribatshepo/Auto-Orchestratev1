# Auto-Orchestrate Pipeline — Token Consumption by Granularity

**Date:** 2026-06-13
**Methodology constant:** `1 token ≈ 4 characters` — matches `claude-code/skills/_shared/python/layer2/token_budget.py:31` (`CHARS_PER_TOKEN = 4`), so estimates here are reproducible against the codebase's own approximation.
**Related:** see [`token-budget-analysis.md`](./token-budget-analysis.md) for the full cost-band derivations and pricing source. This document is the *granularity* companion: it answers **at what levels tokens are tracked, which levels are actually measured vs. only estimated, and how a session breaks down per stage.**

---

## 1. How tokens are counted

Token usage is **character-estimated**, not measured from the API:

```
tokens ≈ len(text) / 4
```

The estimator lives in `claude-code/skills/_shared/python/layer2/token_budget.py`:

```python
CHARS_PER_TOKEN: int = 4
def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN
```

**Per-spawn estimation** (documented in `claude-code/commands/auto-orchestrate.md`, Step 4.6 "Record iteration history + token counts"):

```
input_estimate  = (chars_spawn_prompt + chars_agent_md + sum(chars_skill_mds_loaded)) / 4
output_estimate = chars_returned_text / 4
```

Accuracy is a **±20% rough cut** (more for code-heavy text), per `token-budget-analysis.md`.

---

## 2. Granularity levels

The pipeline defines five levels of token accounting. Critically, **only the per-stage level is wired to emit live values** — the finer per-spawn and per-session counters exist in the checkpoint schema but are not populated by runtime code.

| Level | Field / source | Source file | Status |
|---|---|---|---|
| **Per-spawn** (agent + stage + phase) | `iteration_history[].token_counts_by_spawn` | `commands/auto-orchestrate.md` (~L4336) | ⚠️ **Declared, NOT populated** |
| **Per-session total** | `checkpoint.session_token_total {input, output}` | `commands/auto-orchestrate.md` (~L3754) | ⚠️ **Declared, NOT populated** |
| **Per-stage** | `token_input` / `token_output` | `lib/ci_engine/stage_metrics_collector.py` | ✅ **Actively recorded** |
| **Per-stage in run report** | `TokenCount {input, output}` | `lib/ci_engine/run_summary.py` | ✅ Optional, schema-backed |
| **Prometheus / OTel** | `pipeline_stage_token_{input,output}_total` (labeled by stage) | `lib/ci_engine/prometheus_exporter.py` | ✅ Exported when enabled |

**Per-spawn schema shape** (when wired):

```json
{
  "spawn_id": "<uuid-or-counter>",
  "agent": "orchestrator",
  "stage": 3,
  "phase": null,
  "input_estimate": 41200,
  "output_estimate": 6800,
  "skills_loaded": ["production-code-workflow"],
  "optimizations_active": ["manifest_digest", "skill_frontmatter_routing"]
}
```

The per-stage collector emits a `stage_end` JSONL event carrying `token_input`/`token_output`, which `prometheus_exporter.py` replays into counters on the `/metrics` endpoint.

---

## 3. Per-stage breakdown

Estimates for a **medium session**: 1 deliverable, ~10 tasks, qa + security flags fire, 1 Stage-5 retry, no conditional phases beyond 5q/5s.

| Stage | Model | Spawns | Input | Output | Cost |
|---|---|---:|---:|---:|---:|
| Continuity scout (Step -0.5) | Sonnet | 5 | 44K | 3K | $0.18 |
| P1 — Intent | Sonnet | 6 | 100K | 24K | $0.66 |
| P2 — Scope | Sonnet | 7 | 115K | 28K | $0.77 |
| P3 — Dependencies | Sonnet | 6 | 100K | 24K | $0.66 |
| P4 — Sprint kickoff | Sonnet | 6 | 100K | 24K | $0.66 |
| Stage 0a — Project research | Sonnet | 1 | 20K | 8K | $0.18 |
| Stage 0b — Deliverable research | Sonnet | 5 | 100K | 30K | $0.75 |
| Stage 1 — Decomposition | Sonnet | 5 | 60K | 25K | $0.56 |
| **Stage 2 — Spec creation** | Sonnet | 50 | **510K** | 200K | $4.53 |
| **Stage 3 — Implementation** | **Opus** | 10 | 170K | 80K | **$8.55** |
| Stage 4 — Tests | Opus | 5 | 80K | 30K | $3.45 |
| Stage 4.5 — Metrics fan-out | Opus | 1 | 30K | 8K | $1.05 |
| Stage 5 — Validation | Sonnet | 8 | 130K | 20K | $0.69 |
| Phase 5q — QA depth | Sonnet | 1 | 30K | 5K | $0.17 |
| Phase 5s — Security depth | Opus | 1 | 30K | 6K | $0.90 |
| Stage 6 — Documentation | Sonnet | 5 | 125K | 40K | $0.98 |
| Orchestrator overhead (~20 turns) | Sonnet | ~20 | 300K | 40K | $1.50 |
| **TOTAL** | — | **~141** | **~2.04M** | **~595K** | **~$26.24** |

**Hot spots:** Stage 3 (implementation, Opus) ≈ **35%** of cost; Stage 2 (spec creation, 50 spawns) ≈ **17%** of cost.

---

## 4. By session size

| Scenario | Tasks | Total tokens (in+out) | Cost |
|---|---:|---:|---:|
| Trivial | 1 | ~1.8M | $8 |
| Small | 3 | ~2.2M | $13 |
| **Medium** (headline) | 10 | ~2.6M | $26 |
| Full pipeline (all conditionals fire once) | 10 | ~3.2M | $29 |
| Large | 25 | ~6.7M | $68 |
| Enterprise | 50 | ~13M | $135 |

---

## 5. Conditional phases (fire on demand)

These fire only when their trigger condition is met; costs are **per fire**.

| Phase | Trigger | Spawns | Input | Output | Cost |
|---|---|---|---:|---:|---:|
| 5e — Debugger sub-loop | Stage 5 fix-loop exhausted | 3 median / 10 worst | 60K / 260K | 18K | $0.45 / $2.50 |
| 5v — Compliance audit | spec-compliance < threshold | 2 median / 5 worst | 60K | 18K | $0.45 / $1.10 |
| 5i — Infra / SRE depth | infra flag fires | 2 | 60K | 12K | $0.36 |
| 5d — Data / ML depth | data flag fires | 2 | 60K | 12K | $0.36 |
| 7 — Release readiness + CAB | release flag fires | 4 | 100K | 20K | $0.60 |
| 8 — Post-launch 30/60/90 | post-release tracking | 3 | 90K | 15K | $0.50 |
| 9 — Continuous governance | governance schedule / risk | 1–2 per fire | 60K | 10K | $0.35 |

Most sessions fire only one or two of these; all-fire-once adds ~$3.10 collectively.

---

## 6. Optimization-suite savings

The 6-phase token-budget optimization suite cuts a typical session from **~2.0M → ~1.1M input tokens (~45%)**. Each phase is gated by a `checkpoint.optimizations.<flag>` boolean (default `true` on fresh installs).

| Phase | Constraint ID | Saved / session | Mechanism |
|---|---|---:|---|
| 3 — Manifest digest | `MANIFEST-DIGEST-001` | **~416K** | Subagents get a ~2.6K digest instead of the ~19K full manifest (~86% compression) |
| 4 — Orchestrator template extract | `TEMPLATE-EXTRACT-001` | **~302K** | Orchestrator spawn gets CORE (~8K) + active stage/phase template instead of full ~33K `orchestrator.md` (~75% compression) |
| 1 — Skill frontmatter routing | `SKILL-FRONTMATTER-001` | ~76K | Skill discovery loads only YAML frontmatter (~300 tok/skill); body loads at invocation |
| 2 — Process injection slim | — | ~50K | Spawn builder injects only fired process hooks, not the full injection map |
| 5 — Stage receipt diet | `STAGE-RECEIPT-DIET-001` | ~40K | Slim v2.0.0 stage-receipt schema; tolerant readers |
| 6 — Handover compress | `HANDOVER-COMPRESS-001` | ~20K | Slim v2.0.0 handover schema; `context_carry` re-derived from checkpoint |

Three further context-diet optimizations are documented in `ARCHITECTURE.md §15.2`: `CONTEXT-DIET-001` (envelope excerpts/pointers), `PROTOCOL-PACK-SLIM-001` (`spawn-core.md` ~2K vs. 5-doc ~7.5K stack), and `CONTINUITY-TIER-001` (HOT core + slice-index over the continuity brief).

---

## 7. Status & caveat

**The numbers above the per-stage level are estimates, not live measurements.** Specifically:

- Per-spawn (`token_counts_by_spawn`) and per-session (`session_token_total`) counters are **declared in the checkpoint schema but not populated by runtime code**.
- Only the **per-stage** counters in `lib/ci_engine/stage_metrics_collector.py` emit real values (to JSONL telemetry, OTel, and Prometheus).
- The all-up session/stage figures in §3–§5 are derived from `token-budget-analysis.md` using the char/4 estimator (±20%).

**Highest-ROI gap:** wiring the Phase-0 instrumentation that populates `session_token_total` and `token_counts_by_spawn` (~50 LOC) would turn the per-spawn and per-session estimates into measurements — the prerequisite for measuring every other optimization phase accurately.
