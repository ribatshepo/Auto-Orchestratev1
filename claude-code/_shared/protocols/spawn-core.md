# Spawn Core Protocol (slim pack — PROTOCOL-PACK-SLIM-001)

This is the tight "must-know-up-front" pack injected into every subagent spawn when
`checkpoint.optimizations.protocol_pack_slim == true`. It states **every constraint by ID with its
normative rule**; the long-form prose, pseudocode, schema bodies, and examples stay in the five source
docs on disk and are read **on demand** via the Reference Index at the bottom. Nothing is deleted —
this pack is assembled *from* those docs, not instead of them. Code-producing agents at Stage 3 also
receive the full `engineering-standards.md`.

---

## 0. Preamble — MANDATORY FIRST ACTION (PREAMBLE-001..004)

Before any other action, read the continuity brief and apply prior context.

| ID | Rule |
|---|---|
| PREAMBLE-001 | Reading `.orchestrate/<SESSION_ID>/continuity-brief.md` is the first I/O of every spawn. (Tiered read under CONTINUITY-TIER-001 — see `agent-preamble.md`.) Missing brief: HALT `[CONTINUITY-MISSING]` during P1-P4; `[CONTINUITY-WARN]` and proceed during Stage 0-6. |
| PREAMBLE-002 | Your primary output MUST contain a `## Continuity Carryover` section citing ≥1 applied item, or the explicit `(no relevant continuity item — task is unrelated to prior sessions)`. Silent omission is a violation flagged at the next gate. |
| PREAMBLE-003 | User preferences from the brief override default behaviours unless they conflict with the active spec. |
| PREAMBLE-004 | Conflicts between a continuity item and the current spec MUST invoke `meta-reasoner`. |

## 1. Output Requirements (OUT-001..005, RFC 2119 MUST)

| ID | Rule |
|---|---|
| OUT-001 | MUST write findings to `{{OUTPUT_DIR}}/{{DATE}}_{{SLUG}}.md` (naming per NAME-001). |
| OUT-002 | MUST append ONE line to the session `MANIFEST.jsonl` (per MANIFEST-SESSION). |
| OUT-003 | MUST return ONLY a short summary message (e.g. "Research complete. See MANIFEST.jsonl."). |
| OUT-004 | MUST NOT return full content in the response (it would bloat the orchestrator context). |
| OUT-005 | MUST write `stage-receipt.json` to `{{OUTPUT_DIR}}/` on completion (per RECEIPT-001). |

## 2. Cross-command consistency (from output-standard.md §7)

| ID | Rule |
|---|---|
| NAME-001 | ALL output files use `YYYY-MM-DD_<slug>.<ext>`. |
| MANIFEST-SESSION | Each session has ONE `MANIFEST.jsonl` at session root. |
| RECEIPT-001 | Every stage/cycle writes a `stage-receipt.json`. |
| CHECKPOINT-001 | Atomic write: tmp → rename. |
| STRUCTURE-001 | All commands use subdirectories for phases/stages. |
| DOMAIN-BRIDGE | Stage receipts are the standard input for domain-memory hooks. |
| CONTEXT-DIET-001 | Read `MANIFEST.jsonl` + envelope `excerpt` first; deep-read a full body only when the task needs detail (see §6). |

## 3. Large-file & manifest reading (READ-001..005, MAN-001/002)

| ID | Rule |
|---|---|
| READ-001 | Size-before-read: `Read` with `limit:50` to check line count; >500 lines → chunked/targeted. |
| READ-002 | Chunked reading: >500-line files in 300-line chunks via `offset`/`limit`; process each before the next. |
| READ-003 | Targeted reading: `Grep` for line numbers first, then `Read` ±30 lines around the match. |
| READ-004 | Consolidation: build a running summary per chunk; do not hold all chunks in context. |
| READ-005 | Multi-file budget: if combined >1,500 lines, prioritise by relevance and apply READ-003 to the rest. |
| MAN-001 | Read only the **last 50** manifest entries (`offset`); log `[MAN-001]` if >200 entries. |
| MAN-002 | Orchestrator rotates a >200-entry manifest at boot (archive + fresh active manifest). |

## 4. Early exit under turn/context pressure (EARLY-001..003)

| ID | Rule |
|---|---|
| EARLY-001 | Write partial results to the output file after each major phase so work survives termination. |
| EARLY-002 | Near the turn limit: write partials, set manifest status `"partial"`, return `"PARTIAL: completed X, remaining: Y"`. |
| EARLY-003 | Priority order when budget is tight: (1) core deliverable, (2) self-review, (3) security audit, (4) quality pipeline — skip lower items and note them as skipped. |

## 5. Engineering standards digest (ENG-STD-001 — IMMUTABLE baseline)

Task arguments MAY add stricter rules; they CANNOT loosen the baseline (log
`[ENG-STD-001] task argument attempted to loosen <rule>; baseline applied.`). **Code-producing agents
read the full `engineering-standards.md` at their Stage-3 preamble** (injected automatically when
`protocol_pack_slim` is on). Digest:

| § | Rule (one-line) |
|---|---|
| §1 | SOLID is governing; Factory is the default creational pattern; DI is the default structural pattern; explicit type annotations are imperative. |
| §2 | Strictest type-checking; no `any`/untyped structured data; >2 args → a single typed data class; validate external input at the boundary. |
| §3 | Result types for expected failures (no exceptions for control flow); no silent/empty handlers; resilience (retry/timeout/circuit-breaker) on network calls; structured error envelopes. |
| §4 | Follow language naming exactly; no meaningless `Impl`/`Manager`/`Helper`; async distinguishable; `Factory` suffix; one public type per file. |
| §5 | No commented-out/dead code; no unused imports/params; no `TODO`/`FIXME` without a linked issue. |
| §6 | I/O async end-to-end; thread cancellation/context; typed bounded streams/channels with back-pressure. |
| §7 | Warnings-as-errors in CI; shared linter/formatter config; format+lint as a CI gate. |
| §8 | **No type >~300 lines, no function >~40 lines**; no feature-flag sprawl; no tech debt by default; no env-var sprawl; no security violations; no direct dependency instantiation; no untyped signatures. |
| §9 | All services via DI/explicit injection; narrowest lifetime; tier behaviour wired at startup; factories encapsulate complex construction. |
| §10 | >2 params → a dedicated immutable data class; every field typed; boundary data classes validate; purposeful names (no `Params`/`Args`). |

Enforcement: Stage 2 reasoning sub-questions cite §N; Stage 3 preamble (full read); Stage 4.5 detectors (§5/§8/§9/§10); Stage 5 validator per-section score (`overall_score < 0.9` fails the verdict).

## 6. Digest-by-default context intake (CONTEXT-DIET-001 / DOMAIN-QUERY-001)

- **Artifacts**: read `.orchestrate/<sid>/MANIFEST.jsonl` once (the discovery index), filter by
  `artifact_type`/`status`/stage, read each candidate's `excerpt`, and `Read` a full body ONLY when the
  task needs detail (target via `excerpt_pointers`; log `[CONTEXT-DIET-001] deep-read <path>`).
- **Domain memory**: query `DomainIndexer.query(store, text, limit)` for ranked rows instead of reading
  whole `.orchestrate/domain/*.jsonl` ledgers; fall back to the JSONL on any error.

## Completion checklist (before returning)

- [ ] Output file written to `{{OUTPUT_DIR}}/` (OUT-001) · [ ] Manifest line appended (OUT-002)
- [ ] `## Continuity Carryover` present (PREAMBLE-002) · [ ] `stage-receipt.json` written (OUT-005)
- [ ] Response is ONLY the summary (OUT-003/004) · [ ] Status returned: complete | partial | blocked

---

## Reference Index — read these on demand (full detail stays on disk)

| When you need… | Read |
|---|---|
| Output-file template, manifest field definitions, key-findings guidance | `_shared/protocols/subagent-protocol-base.md` (Output File Format / Manifest Entry Format) |
| Chunked/targeted large-file read recipe (pseudocode) | `subagent-protocol-base.md` "Large File Reading Protocol" (READ-001..005) |
| Manifest rotation / read-last-50 recipe (pseudocode) | `subagent-protocol-base.md` "Manifest Size Management" (MAN-001/002) |
| Partial-result output format + implementation-specific partials | `subagent-protocol-base.md` "Early Exit Protocol" |
| Task lifecycle / token reference / error-handling long form | `subagent-protocol-base.md` (Task Lifecycle / Token Reference / Error Handling) |
| Exact stage-receipt v1/v2 schema + tolerant reader | `_shared/protocols/output-standard.md` §4 |
| Full `.orchestrate/` directory layout | `output-standard.md` §2 |
| Gap-report schema | `output-standard.md` §6 |
| CONTEXT-DIET-001 full rule | `output-standard.md` §8 |
| Skill-script JSON output shapes | `_shared/protocols/output-schemas.md` (whole file — only for spawns running those scripts) |
| Full ENG-STD-001 §N normative prose | `_shared/protocols/engineering-standards.md` (code agents read in full at Stage 3) |
| Full preamble protocol (tiered-read recipe) | `_shared/protocols/agent-preamble.md` |
