# Auto-Orchestrate Pipeline — Token Budget Analysis

**Analysis date:** 2026-05-21 (rev 2 — full-pipeline scope)
**Pipeline revision:** working tree on top of `dab1509` (uncommitted: PROGRESS-001/002/003 visibility + Stage 1–5 research→analysis rename + RESEARCH-BOUNDARY-001 + STAGE-0-GAP-001)
**Pricing source:** Anthropic API list price as of 2026-05-21
**Methodology constant:** `1 token ≈ 4 characters` — matches `claude-code/skills/_shared/python/layer2/token_budget.py:31` so estimates are reproducible against the codebase's own approximation.

> **What's new since rev 1 (commit `bf6b243`):** (a) The Stage 1–5 fan-out pools were reframed from "research pools" to "analysis pools" with `RESEARCH-BOUNDARY-001` (no WebSearch outside Stage 0a/0b/P1–P4) and `STAGE-0-GAP-001` (escalation token instead of inline research). Pool agents now run on shorter inputs (~15 K vs. ~22 K), shaving ~$2.15 off a medium session. (b) The headline scope was expanded to **the full pipeline including conditional phases** (5e, 5v, 5i, 5d, 7, 8, 9) — these were previously documented out-of-band; now they appear in §4 and §6. (c) `PROGRESS-001/002/003` adds ~20–30 output tokens per spawn for the new STARTING/FLEET/COMPLETED visibility — negligible (~$0.06 / session).

---

## 1. Executive Summary

A **medium session** (1 deliverable, ~10 tasks, qa + security flags fire, 1 Stage-5 retry iteration, **no** conditional phases) is estimated to consume **~2.6 M total tokens** (≈2.0 M input + 0.6 M output) at an API cost of **~$26** (band: ~$21–$33).

A **full-pipeline session** (medium scope with all conditional phases firing once: Phase 5e + 5v + 5i + 5d + Phase 7 release + Phase 8 30/60/90 + one Phase 9 sub-routine) lands at **~3.2 M tokens ≈ ~$29** — the conditional phases add ~$3.10 collectively when they all fire, but most sessions fire only one or two of them.

| Session size | Tasks | Deliverables | Total tokens (est.) | Cost band (USD) |
|---|---:|---:|---:|---:|
| **Small** | 3 | 1 | ~2.2 M | $10 – $16 |
| **Medium** ⬅ headline | 10 | 1 | ~2.6 M | $21 – $33 |
| **Full pipeline (all phases fire once)** | 10 | 1 | ~3.2 M | $25 – $35 |
| **Large** | 50 | 3 | ~13 M | $100 – $150 |

**Top 3 leaks (highest token weight):**
1. **Stage 3 implementation** — 35–40 % of session cost. `software-engineer` runs on Opus, fan-outs to `parallel_cap=5`, and reads multiple code files per task.
2. **Stage 2 spec creation** — 15–20 %. Multi-agent sync runs once per task; the spawn count grows linearly with task count.
3. **PREAMBLE-001 amplification** — the continuity-brief is reloaded by **every** agent (~25 spawns/session). At template size (~280 tokens) it's negligible; at realistic runtime size (~1.5–3 K tokens) it adds up to ~50–75 K input tokens/session of pure duplication.

**Top 3 levers (highest ROI):**
1. **Wire the token telemetry that already exists.** `checkpoint.session_token_total` and `stage-receipt.token_input/output` are declared in the schemas but **never populated**. Populating them turns this whole analysis from "estimate" into "measurement" for the price of ~50 LOC. *(Highest ROI — once measured, the structural savings from L8 below become verifiable and the L9 escalation path becomes observable.)*
2. **Cap the runtime continuity-brief.** Add a hard size limit (e.g., ≤1.5 K tokens) enforced by `continuity-scout`. Saves up to ~50 K tokens/session and stays inside MAIN-005's per-handoff intent.
3. **Audit `needs_full_manifest: true` callers.** MANIFEST-DIGEST-001 ships a ~2.6 K digest by default vs. the full 21.5 K manifest — every `true` flag is an 18.9 K-token tax per spawn. Confirm each one is justified.

---

## 2. Methodology

### Token estimation
`tokens ≈ chars / 4` — the same approximation enforced by the pipeline's existing budget tracker (`token_budget.py:31`). This is a known ±20 % rough cut; the goal here is order-of-magnitude budgeting, not exact billing.

### Per-spawn input model
Every agent spawn receives roughly:

```
input = system_prompt          (~5 K, Claude Code default harness)
      + agent_definition       (measured per file — see §3)
      + agent_preamble.md      (~555 tokens — PREAMBLE-001..004)
      + continuity_brief       (~500–1,500 tokens at runtime; 279 in template)
      + manifest_digest        (~2.6 K, MANIFEST-DIGEST-001) — or full 21.5 K if needs_full_manifest:true
      + task_prompt            (~500–2,000 tokens, stage-specific)
      + read_artifacts         (~2,000–10,000 tokens, varies by stage role)
```

A "typical" Sonnet spawn lands at ~15–25 K input tokens; a Stage-3 Opus spawn lands at ~20–30 K because it reads more code.

**Stage 1–5 analysis pools** (post 2026-05-21 rename) operate under `RESEARCH-BOUNDARY-001` — they read Stage 0 + P1–P4 + upstream-stage outputs but MUST NOT call WebSearch. Their per-spawn input is therefore lower than a research-style spawn (~15 K vs. ~22 K). Stage 0a, Stage 0b, and the P1–P4 researcher participants retain WebSearch and remain the canonical research budget. The visibility-emission overhead from `PROGRESS-001/002/003` (STARTING / FLEET / COMPLETED lines) is ~20–30 output tokens per spawn ≈ $0.06 / session — included in the per-stage rows below.

### Per-spawn output model
Output is bounded by the artifact contract (`templates/orchestrate-session/manifest.yml`) and stage receipt schema. Research stages skew long (~4–8 K tokens out); receipts and meeting minutes are short (~300–800 tokens out); code-diff stages average ~3–8 K tokens out.

### Pricing assumed (USD per 1 M tokens)
| Model | Input | Output |
|---|---:|---:|
| Sonnet 4.5 / 4.6 | $3 | $15 |
| Opus 4.5 / 4.7 | $15 | $75 |

### Scope assumption for "medium" headline
1 deliverable, ~10 tasks across 3 independence groups, `qa + security` flags fire (so phases 5q and 5s run, but not 5i or 5d), 1 fix iteration in Stage 5, full Stage-6 docs. Phases 7/8/9 are NOT counted in the headline — they fire only when `release_flag` / incident / governance schedule triggers them.

---

## 3. Base-Size Reference (measured today, from this repo)

These are the actual file sizes that drive the per-spawn input cost. Numbers are measurements (`wc -c`) — not estimates.

| Component | Chars | Tokens (≈) | Loaded by |
|---|---:|---:|---|
| `claude-code/agents/orchestrator.md` | 185,415 | **46,354** | Orchestrator only (TEMPLATE-EXTRACT-001 sends an active-stage slice, not the full file) |
| `claude-code/commands/auto-orchestrate.md` | 393,589 | **98,397** | Controller only — never reaches a subagent's context |
| `claude-code/agents/researcher.md` | 23,196 | 5,799 | Every Stage 0a / 0b / planning-research spawn |
| `claude-code/agents/software-engineer.md` | 14,011 | 3,503 | Every Stage 3 / 4 / 4.5 spawn |
| `claude-code/agents/product-manager.md` | 13,844 | 3,461 | P1, P2, Stage 1 facilitator |
| `claude-code/agents/auditor.md` | 12,158 | 3,040 | Phase 5v audit |
| `claude-code/agents/infra-engineer.md` | 11,818 | 2,955 | Phase 5i |
| `claude-code/agents/session-manager.md` | 11,207 | 2,802 | Step 0 boot |
| `claude-code/agents/security-engineer.md` | 10,642 | 2,661 | Phase 5s, P2 co-agent |
| `claude-code/agents/engineering-manager.md` | 10,481 | 2,620 | P4 lead |
| `claude-code/agents/continuity-scout.md` | 10,090 | 2,523 | Step -0.5 consolidator |
| `claude-code/agents/sre.md` | 9,605 | 2,401 | Phase 5i co-agent, Phase 8 |
| `claude-code/agents/technical-writer.md` | 9,145 | 2,286 | Stage 6 |
| `claude-code/agents/qa-engineer.md` | 8,548 | 2,137 | Phase 5q, Stage 5 facilitator |
| `claude-code/agents/technical-program-manager.md` | 7,971 | 1,993 | P3 lead |
| `claude-code/agents/ml-engineer.md` | 7,980 | 1,995 | Phase 5d |
| `claude-code/agents/staff-principal-engineer.md` | 7,717 | 1,929 | P1 co-agent, P3 co-agent |
| `claude-code/agents/data-engineer.md` | 7,711 | 1,928 | Phase 5d, P2 co-agent |
| `claude-code/agents/debugger.md` | 6,977 | 1,744 | Phase 5e |
| `claude-code/agents/scout-{jsonl,sessions,pipeline,context}.md` | ~4,000 each | ~1,000 each | Step -0.5 fan-out |
| `claude-code/_shared/protocols/agent-preamble.md` | 2,217 | 555 | **Every** agent spawn (PREAMBLE-001) |
| `claude-code/templates/orchestrate-session/session/continuity-brief.md` (template) | 1,114 | 279 | Template only — runtime brief grows to ~1–3 K |
| `claude-code/manifest.json` (full) | 86,010 | **21,503** | Sent only when `needs_full_manifest: true` |
| `manifest digest` (MANIFEST-DIGEST-001 default) | ~10,400 | ~2,600 | Default for every subagent |
| `claude-code/templates/orchestrate-session/manifest.yml` | 44,247 | 11,062 | Orchestrator reads at stage close (artifact contract) |
| `claude-code/ARCHITECTURE.md` | 84,274 | 21,069 | Reference doc — selective reads only |

---

## 4. Per-Stage Budget

Numbers assume a **medium session** (1 deliverable, 10 tasks, qa + security flags fire). Spawn counts include the fan-out floors from PLAN-FANOUT-001 / STAGE-0B-FANOUT-001 / PARALLEL-STAGE-001. Stages 1–5 reflect the post-rename **analysis pool** input cost (~15 K per pool spawn, down from ~22 K under the old "research pool" framing) — see L8 in §7.

| Stage | Lead agent | Model | Spawns | Input tokens (est.) | Output tokens (est.) | Stage cost (USD) |
|---|---|---|---:|---:|---:|---:|
| Step -0.5 (continuity scout fan-out) | continuity-scout + 4 scouts | Sonnet | 5 | 44 K | 3 K | $0.18 |
| P1 — Intent | product-manager + 4 research | Sonnet | 6 | 100 K | 24 K | $0.66 |
| P2 — Scope | product-manager + 4 research + co-agents | Sonnet | 7 | 115 K | 28 K | $0.77 |
| P3 — Dependencies | TPM + 4 research | Sonnet | 6 | 100 K | 24 K | $0.66 |
| P4 — Sprint kickoff | engineering-manager + 4 research | Sonnet | 6 | 100 K | 24 K | $0.66 |
| Stage 0a — Project research | researcher | Sonnet | 1 | 20 K | 8 K | $0.18 |
| Stage 0b — Deliverable research | 4 researchers + 1 synth | Sonnet | 5 | 100 K | 30 K | $0.75 |
| Stage 1 — Decomposition (4-analysis pool + meeting) | PM + TPM + QA + staff | Sonnet | 5 | **60 K** | 25 K | **$0.56** |
| Stage 2 — Spec creation (4-analysis pool + meeting × 10) | staff + SWE + QA + sec + spec-creator | Sonnet | 50 | **510 K** | 200 K | **$4.53** |
| **Stage 3 — Implementation (4-analysis pool + implementer × 10)** | **software-engineer + analysts** | **Opus** | 10 | **170 K** | 80 K | **$8.55** |
| Stage 4 — Tests (4-analysis pool + test-writer × 5) | software-engineer + analysts | Opus | 5 | **80 K** | 30 K | **$3.45** |
| Stage 4.5 — Metrics fan-out (4 skills) | software-engineer (host) | Opus | 1 host turn | 30 K | 8 K | $1.05 |
| Stage 5 — Validation (4-analysis pool + sync meeting) | qa-engineer + validator + docker-validator | Sonnet | 8 | **130 K** | 20 K | **$0.69** |
| Phase 5q — QA depth (conditional: qa flag) | qa-engineer | Sonnet | 1 | 30 K | 5 K | $0.17 |
| Phase 5s — Security depth (conditional: security flag) | **security-engineer** | **Opus** | 1 | 30 K | 6 K | $0.90 |
| Stage 6 — Documentation × 5 categories | technical-writer | Sonnet | 5 | 125 K | 40 K | $0.98 |
| Orchestrator overhead (cumulative across ~20 turns) | orchestrator | Sonnet | ~20 | 300 K | 40 K | $1.50 |
| **TOTAL (medium session, NO conditional phases beyond 5q/5s)** | — | — | **~141** | **~2.04 M in** | **~595 K out** | **~$26.24** |
| **— Conditional phases (each fires only when its condition hits) —** | | | | | | |
| Phase 5e — Debugger sub-loop (conditional: Stage 5 fix-loop exhausted) | debugger | Sonnet | 3 (median) – 10 (worst) | 60 K | 18 K | $0.45 median / $2.50 worst |
| Phase 5v — Compliance audit (conditional: spec-compliance < threshold) | auditor + spec-compliance | Sonnet | 2 (median) – 5 (worst) | 60 K | 18 K | $0.45 median / $1.10 worst |
| Phase 5i — Infra / SRE depth (conditional: infra flag) | infra-engineer + sre | Sonnet | 2 | 60 K | 12 K | $0.36 |
| Phase 5d — Data / ML depth (conditional: data flag) | data-engineer + ml-engineer | Sonnet | 2 | 60 K | 12 K | $0.36 |
| Phase 7 — Release readiness + CAB (conditional: release_flag) | release-notes-generator + cab-reviewer + sre | Sonnet | 4 | 100 K | 20 K | $0.60 |
| Phase 8 — Post-launch outcome 30/60/90 (conditional: post-release tracking) | okr-retrospective-tracker host | Sonnet | 3 (one per milestone) | 90 K | 15 K | $0.50 |
| Phase 9 — Continuous governance (conditional: governance schedule / risk fire) | governance sub-routine owner(s) | Sonnet | 1–2 per fire | 60 K | 10 K | $0.35 per fire |
| **TOTAL (full pipeline, all conditional phases fire once)** | — | — | **~165** | **~2.53 M in** | **~700 K out** | **~$29.31** |

> The "Spawns" column counts agent invocations, not LLM turns inside an agent — a software-engineer that runs 5 skill calls in one spawn counts as 1 spawn here.

> **Reading the table:** The first TOTAL row (~$26.30) is the medium-session headline used elsewhere in this document; it covers planning + Stages 0–6 + Phases 5q + 5s (the two flag-conditioned phases that fire on most real sessions). The second TOTAL row (~$29.77) shows what a session looks like when ALL conditional phases also fire — rare in practice (most sessions don't trigger 5e / 5i / 5d / 7 / 8 / 9).

### Per-stage cost ranking (sorted, medium session)

1. **Stage 3 — Implementation** ($8.55) — 33 % of session
2. **Stage 2 — Spec creation** ($4.53) — 17 %
3. **Stage 4 — Tests** ($3.45) — 13 %
4. **Orchestrator overhead** ($1.50) — 6 %
5. **Stage 4.5 — Metrics** ($1.05) — 4 %
6. **Stage 6 — Documentation** ($0.98) — 4 %
7. **Phase 5s — Security depth** ($0.90) — 3 %
8. **P2 — Scope** ($0.77) — 3 %
9. **Stage 0b — Deliverable research** ($0.75) — 3 %
10. **Stage 5 — Validation** ($0.69) — 3 %

Implementation + tests + specs = **63 % of session cost**. Optimizing planning stages will not move the needle as much as optimizing Stages 2–4. The analysis-pool rename (L8) trimmed ~$2 off the prior $28.49 baseline without changing what the pipeline does — that saving compounds with task count, so a large session ($110 → $105) saves more in absolute terms.

---

## 5. Per-Agent Rollup (medium session, post-rename)

| Agent | Model | Spawns | Total tokens (in+out) | Cost (USD) |
|---|---|---:|---:|---:|
| **software-engineer** | Opus | 16 | 380 K | **$12.90** |
| product-manager | Sonnet | 12 | 285 K | $1.65 |
| orchestrator | Sonnet | ~20 | 340 K | $1.50 |
| researcher | Sonnet | 21 | 425 K | $1.75 |
| qa-engineer | Sonnet | 12 | 240 K | $1.40 |
| TPM | Sonnet | 7 | 150 K | $0.85 |
| engineering-manager | Sonnet | 6 | 124 K | $0.70 |
| staff-principal-engineer | Sonnet | 6 | 115 K | $0.66 |
| **security-engineer** | Opus | 2 | 60 K | **$0.90** |
| technical-writer | Sonnet | 5 | 165 K | $0.98 |
| continuity-scout + 4 scouts | Sonnet | 5 | 47 K | $0.18 |
| spec-creator (hosted) | Sonnet | inline in Stage 2 | included above | — |
| validator + docker-validator (hosted) | Sonnet | inline in Stage 5 | included above | — |

### Conditional-phase agents (only when their phase fires)

| Agent | Model | Spawns per fire | Total tokens (in+out) | Cost (USD) per fire |
|---|---|---:|---:|---:|
| debugger (Phase 5e) | Sonnet | 3 median / 10 worst | 78 K / 260 K | $0.45 / $1.50 |
| auditor (Phase 5v) | Sonnet | 2 median / 5 worst | 78 K / 195 K | $0.45 / $1.10 |
| infra-engineer (Phase 5i) | Sonnet | 1 | 36 K | $0.20 |
| sre (Phase 5i / Phase 7 / Phase 8) | Sonnet | 1–3 | 36 K – 90 K | $0.20 – $0.50 |
| data-engineer (Phase 5d) | Sonnet | 1 | 36 K | $0.20 |
| ml-engineer (Phase 5d) | Sonnet | 1 | 36 K | $0.20 |
| release-notes-generator (skill, Phase 7) | Sonnet | inline | included in Phase 7 row | — |
| cab-reviewer (skill, Phase 7) | Sonnet | inline | included in Phase 7 row | — |
| okr-retrospective-tracker (skill, Phase 8) | Sonnet | inline | included in Phase 8 row | — |
| sprint-goal-linker / adr-publisher / raid-logger (skills, Phase 9) | Sonnet | inline | included in Phase 9 row | — |

**Opus share of cost (medium session, no conditional phases): ~$13.80 / $26.30 = 52 %** — driven by 16 software-engineer spawns and 2 security-engineer spawns.
**Sonnet share: ~$12.50 / $26.30 = 48 %** — driven by raw spawn count (~123 Sonnet spawns).

**Conditional-phase impact**: each conditional phase adds $0.20–$0.90 when it fires. The full-pipeline session (all conditionals + medium scope) is bounded around **$30** total. Phase 5e worst-case is the largest swing item (~$2.50 when debugging is genuinely hard), followed by Phase 7 release ($0.60 + ~$1 in CAB-driven re-work).

---

## 6. Sensitivity Bands (post-rename)

| Scenario | Tasks | Deliverables | Flags fired | Stage-5 retries | Conditional phases | Spawns (est.) | Tokens (in+out) | Cost (USD) |
|---|---:|---:|---|---:|---|---:|---:|---:|
| Trivial | 1 | 1 | qa only | 0 | — | ~50 | ~1.8 M | $8 |
| Small | 3 | 1 | qa, security | 0 | — | ~80 | ~2.2 M | $13 |
| **Medium** ⬅ headline (no conditional phases) | 10 | 1 | qa, security | 1 | — | ~141 | ~2.6 M | $26 |
| **Full pipeline (all conditional phases fire once)** | 10 | 1 | qa, security | 1 | 5e + 5v + 5i + 5d + 7 + 8 + 9 | ~165 | ~3.2 M | $29 |
| Large | 25 | 2 | qa, security, infra | 2 | 5e + 5v + 5i | ~280 | ~6.7 M | $68 |
| Enterprise | 50 | 3 | qa, security, infra, data | 3 | 5e + 5v + 5i + 5d | ~520 | ~13 M | $135 |
| Worst-case (large + all conditionals + Phase 7 + 3 retries) | 50 | 3 | all + release | 3 | all conditionals fire | ~700 | ~18 M | $200 |

**Linear drivers:**
- **Stage 2 scales with task count** (~$0.45 per task — 4-analysis pool + spec-creation meeting).
- **Stage 3+4 scale with tasks** (~$0.85 per task on Opus — 4-analysis pool + implementer/test-writer).
- **Planning (P1–P4) is fixed cost** (~$2.75 regardless of session size).
- **Conditional phases are step-fixed** — each fires once when its condition hits, adding $0.20–$2.50.
- **Multiple deliverables multiply Stages 0b/1** by the deliverable count (~$1.30 per extra deliverable).

**Compared to rev 1 (commit `bf6b243`):** the analysis-pool rename (L8) shaved ~7–8 % off every row by reducing Stage 1–5 pool input from ~22 K to ~15 K per spawn. The largest absolute savings are at the Large and Enterprise tiers where Stage 2 (40–60 spawns) and Stages 3/4 (~80 spawns) dominate — ~$5–$10 less per session at those scales.

---

## 7. Findings — Top Optimization Levers

### L1. Verify TEMPLATE-EXTRACT-001 actually trims orchestrator.md on every spawn
**Leak**: `orchestrator.md` is 46 K tokens. If the full file slips into a spawn (e.g., a fallback path that the recent fix commits `f67bc43` / `7e4bd01` were patching), every orchestrator spawn pays ~$0.14 in input alone instead of the ~$0.024 the digest should cost. With ~20 orchestrator turns/session that's a **$2.30 swing per session**.
**Estimated savings**: $2.00–$2.50/session when TEMPLATE-EXTRACT-001 is reliably enforced.
**Cost**: low — likely already correct, needs a guard test. Add an assertion to the orchestrator spawn path: "orchestrator system prompt size ≤ 12 K tokens."

### L2. Cap the runtime continuity-brief at ~1.5 K tokens
**Leak**: PREAMBLE-001 mandates every agent loads `.orchestrate/<sid>/continuity-brief.md`. Template is 280 tokens, but the live brief can grow with each session (it absorbs carry-over decisions, prior-session deltas, baselines). At 3 K tokens × 25 spawns × 2 (input cost) that's 150 K extra tokens/session.
**Estimated savings**: $0.45–$0.90/session (more on large sessions with deeper carry-over).
**Cost**: low — add a hard ceiling to the `continuity-scout` consolidator (CONT-007); if exceeded, summarize-then-truncate.

### L3. Audit `needs_full_manifest: true` flags
**Leak**: full manifest is 21.5 K tokens; digest is ~2.6 K. Each `true` flag costs an extra 18.9 K input tokens per spawn (~$0.057 on Sonnet, $0.28 on Opus).
**Estimated savings**: bounded by how many spawns set `true` — needs a grep to quantify. Likely $0.50–$2.00/session.
**Cost**: very low — `grep -rn 'needs_full_manifest' claude-code/` and justify each.

### L4. Confirm ARCHITECTURE.md isn't loaded wholesale anywhere
**Leak**: 21 K tokens. Loading it once into a spawn that doesn't actually need it costs ~$0.06 (Sonnet) / $0.31 (Opus).
**Estimated savings**: 0 if it's already only being read selectively; up to $1.00 if any agent prompts it via Read with no scope.
**Cost**: very low — grep for `ARCHITECTURE.md` in agent definitions and prompts.

### L5. Stage receipts and reasoning traces (MAIN-017) — quantify, don't optimize yet
**Observation**: Stage-close protocol writes 4 artifacts per stage (`phase-receipts/`, `domain-reviews/`, `reasoning-traces/`, `meetings/`). Each is ~500–1500 tokens output. Over 11 stages that's ~25–60 K tokens of output. At Sonnet rates: ~$0.50/session. **This is not a leak** — it's the audit trail that makes the pipeline replayable. But it's worth knowing it's a ~2 % budget line.

### L6. Controller separation — already correct, document it
**Observation**: `auto-orchestrate.md` is 98 K tokens (the loop controller) and `orchestrator.md` is 46 K. These are NOT both loaded into any subagent. Controller lives in the parent harness; subagents only see their own agent-definition + manifest digest. This is the single biggest reason the pipeline is affordable. Document it explicitly in `ARCHITECTURE.md` so future refactors don't accidentally merge them.

### L7. **Highest ROI**: wire the existing token telemetry
**Observation**: `claude-code/templates/orchestrate-session/session/checkpoint.json` declares `session_token_total: 0` and `claude-code/templates/orchestrate-session/schemas/stage-receipt.schema.json` declares optional `token_input` and `token_output` fields. **Neither is populated by runtime code**. The orchestrator's `REMAINING_BUDGET = 5` is a spawn counter, not a token counter — it has no idea whether a spawn cost 5 K or 50 K input tokens.
**Estimated savings**: this analysis would become observation, not estimate. Once measured, the structural saving documented in L8 becomes verifiable, and the L9 escalation path becomes observable rather than estimated.
**Cost**: ~50 LOC at the stage-close hook to capture `usage.input_tokens` / `usage.output_tokens` from the API response and write them into the receipt. Then aggregate into `checkpoint.session_token_total` on the existing close protocol.

### L8. Analysis-pool reframing already reclaimed ~$2.15 / medium session (structural; shipped this session)
**Observation**: The Stage 1–5 fan-out pools were renamed from "research pools" to "analysis pools" with `RESEARCH-BOUNDARY-001` (WebSearch/WebFetch forbidden outside Stage 0a/0b/P1–P4) and `STAGE-0-GAP-001` (escalation token instead of inline research). Pool agents are now strict read-only consumers of Stage 0 + P1–P4 + upstream-stage outputs, which dropped per-spawn input from ~22 K (research-style: broad prompt + WebSearch budget + open-ended search space) to ~15 K (focused analysis: bounded inputs, no WebSearch). Aggregate effect on a medium session: ~720 K input tokens saved ≈ ~$2.15 (Sonnet), with proportionally larger savings at higher task counts (~$5–$10 at Large / Enterprise tiers).
**Status**: shipped. Reflected in the §4 / §5 / §6 numbers above; the prior $28.49 medium headline is now ~$26.30.
**Regression guard**: assert that the spawn-template for any Stage 1–5 pool role does NOT list WebSearch/WebFetch in its allowed tools. A simple grep test against the per-stage spawn-template subsections in `claude-code/agents/orchestrator.md` is sufficient.

### L9. STAGE-0-GAP-001 escalation has a bounded but worth-monitoring cost path
**Observation**: When a Stage 1–5 analysis-pool agent emits `[STAGE-0-GAP]`, the orchestrator re-spawns the researcher in addendum mode (~30 K input + 5 K output ≈ $0.30) and then re-runs the originally-blocked pool agent (~15 K input + 3 K output ≈ $0.09 on Sonnet). Cap = 2 loops per pool agent per stage. Worst-case incremental cost per stage = ~$0.78. Across all 5 fan-out stages × multiple pool agents, the worst case is bounded around $4 / session.
**Watch-out**: if escalation fires on every pool spawn, that signals Stage 0 research is under-scoped — the symptom is `checkpoint.stage_0_gap_loops` counters hitting the cap repeatedly. Surface this in iteration history so it's observable.
**Cost to monitor**: ~20 LOC — emit a per-session aggregate `[STAGE-0-GAP-SUMMARY] N pool agents escalated; M hit cap` line at session close, plus persist the counter map in checkpoint (already specified in STAGE-0-GAP-001 row).

---

## 8. Recommended Next Steps (sorted by ROI)

1. **Implement L7** — wire `token_input` / `token_output` into stage receipts. Converts this entire analysis from estimate to measurement. (~half a day)
2. **Implement L2** — cap runtime continuity-brief size in `continuity-scout`. (~1 hour)
3. **Implement L3** — audit `needs_full_manifest: true` flags; remove unjustified ones. (~30 minutes)
4. **Add guard test for L1** — orchestrator-spawn system prompt size assertion. (~1 hour)
5. **Add guard test for L8** — assert that Stage 1–5 pool-role spawn templates do not list WebSearch/WebFetch in allowed tools. Grep-based smoke test against `claude-code/agents/orchestrator.md`. (~30 minutes)
6. **Instrument L9** — surface `checkpoint.stage_0_gap_loops` in iteration history; emit a session-close summary line `[STAGE-0-GAP-SUMMARY] N pool agents escalated; M hit cap`. Detects under-scoped Stage 0 research. (~30 minutes)
7. After 1–6 land, **re-run this analysis as a measurement** and compare actuals to the estimates here. Update the report in place.

---

## Appendix A — Key References

- Pipeline stage definitions: `claude-code/agents/orchestrator.md:932-2146`
- Stage-close protocol (MAIN-017): `claude-code/agents/orchestrator.md:3032`
- Per-handoff token cap (MAIN-005): `claude-code/agents/orchestrator.md:34`
- Token approximation constant: `claude-code/skills/_shared/python/layer2/token_budget.py:31`
- Agent preamble (PREAMBLE-001..004): `claude-code/_shared/protocols/agent-preamble.md`
- Continuity-brief template: `claude-code/templates/orchestrate-session/session/continuity-brief.md`
- Stage-receipt schema (with unpopulated token fields): `claude-code/templates/orchestrate-session/schemas/stage-receipt.schema.json`
- Artifact contract: `claude-code/templates/orchestrate-session/manifest.yml`
- **RESEARCH-BOUNDARY-001** (WebSearch researcher-only; basis for L8): `claude-code/commands/auto-orchestrate.md` constraints table (~line 517)
- **STAGE-0-GAP-001** (escalation token + max-2 addendum loops; basis for L9): `claude-code/commands/auto-orchestrate.md` constraints table (~line 519)
- **PROGRESS-001/002/003** (Spawn Visibility Protocol; basis for the ~$0.06/session visibility overhead): `claude-code/commands/CONVENTIONS.md`
- Analysis-pool sidecar paths (Stages 1–5): `stage-{1,2,3,4,5}/<id>/analysis/R{1..4}-*.json` — registered in `claude-code/templates/orchestrate-session/manifest.yml`
- Researcher `INPUT_MODE: stage-0-gap-addendum`: `claude-code/agents/researcher.md` (Stage-0 Gap-Fill Addendum Mode section)
- Recent fan-out commits: `bf6b243`, `9cb2c3c`, `7e4bd01`, `f67bc43`, `dab1509`
- Uncommitted session changes (this revision): PROGRESS-001/002/003 visibility + Stage 1–5 research→analysis rename + RESEARCH-BOUNDARY-001 + STAGE-0-GAP-001

## Appendix B — Caveats

- **All token counts are estimates** at `chars / 4`. Real tokenizer counts vary ±20 %, more for code-heavy text (which tokenizes denser).
- **Prompt caching is not modeled.** Anthropic's prompt cache (90 % discount on cached input) could cut input cost by 30–50 % if agent definitions and manifests are cached — worth measuring once L7 is wired.
- **Output-token estimates are the softest numbers** in this report. They depend heavily on how verbose individual model responses are at runtime. Bands in §6 reflect this.
- **Phases 7, 8, 9 are not in the headline cost.** They fire conditionally (release flag, incident, governance schedule) and would each add $5–$20 to a session that triggers them.
