# Constraint & Identifier Registry

> **Generated index — not a source of truth.** This file enumerates every stable
> `PREFIX-NNN` identifier family used across the plugin (constraints, gates, reasoning
> gates, artifact contracts, per-agent rules) and the file where each family is
> *primarily* documented. The authoritative definition of any ID always lives in its
> defining file — edit there, then regenerate this index. Grouped by primary file;
> within a group, families are listed by descending occurrence count.

**Coverage:** 142 identifier families · 435 distinct IDs · plus the 93-entry `P-NNN` process catalog (see below).

## Process catalog (`P-001`–`P-093`)

The `P-NNN` family is the organizational process catalog. It is documented in full in
`processes/00_process_handbook_overview.md` (master table) and the 18 numbered process
specs (`processes/01_*`–`processes/18_*`); the cross-reference index is
`processes/18_cross_reference_index.md`. Not re-listed here.

## Constraint / gate / artifact families (by primary file)

### `agents/orchestrator.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `MAIN-NNN` | 17 | 001–017 | 153 |
| `HANDOVER-NNN` | 3 | 001–003 | 41 |
| `MANIFEST-NNN` | 1 | 001 | 36 |
| `IMPL-NNN` | 16 | 001–016 | 34 |
| `CONS-NNN` | 7 | 001–007 | 28 |
| `AGENT-ACTIVATE-NNN` | 5 | 001–005 | 23 |
| `ART-S4-NNN` | 3 | 001–003 | 9 |
| `PLAN-ROUTE-NNN` | 5 | 001–005 | 6 |
| `SKILL-FRONTMATTER-NNN` | 1 | 001 | 5 |
| `SFI-NNN` | 1 | 001 | 3 |
| `TAXONOMY-NNN` | 1 | 001 | 2 |

### `commands/auto-orchestrate.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `CONT-NNN` | 9 | 001–009 | 94 |
| `PARALLEL-NNN` | 3 | 001–003 | 64 |
| `FANOUT-NNN` | 1 | 001 | 62 |
| `HUMAN-GATE-NNN` | 1 | 001 | 54 |
| `PROGRESS-NNN` | 3 | 001–003 | 40 |
| `REASONING-GATE-NNN` | 1 | 001 | 39 |
| `AUTO-PACING-NNN` | 1 | 001 | 35 |
| `AUTO-NNN` | 9 | 001–009 | 31 |
| `LAYOUT-GATE-NNN` | 1 | 001 | 25 |
| `GAP-NNN` | 1 | 001 | 24 |
| `PARALLEL-STAGE-NNN` | 1 | 001 | 23 |
| `TASK-CREATION-REASONING-NNN` | 1 | 001 | 22 |
| `WORKFLOW-SYNC-NNN` | 2 | 001–002 | 21 |
| `ART-S0-NNN` | 4 | 001–004 | 19 |
| `RESEARCH-BOUNDARY-NNN` | 1 | 001 | 19 |
| `DECOMP-REASONING-NNN` | 1 | 001 | 18 |
| `MEETING-NNN` | 2 | 001–002 | 17 |
| `VALIDATION-REASONING-NNN` | 1 | 001 | 17 |
| `ARTIFACT-CONTRACT-NNN` | 1 | 001 | 16 |
| `ARTIFACT-COMPLETENESS-NNN` | 1 | 001 | 15 |
| `PHASE-LOOP-NNN` | 4 | 001–004 | 15 |
| `AUTONOMY-NNN` | 1 | 001 | 14 |
| `SCOUT-FANOUT-NNN` | 1 | 001 | 14 |
| `ART-S45-NNN` | 4 | 001–004 | 13 |
| `RESEARCH-DEPTH-NNN` | 1 | 001 | 13 |
| `SHARED-NNN` | 4 | 001–004 | 13 |
| `AUTO-EVAL-NNN` | 1 | 001 | 12 |
| `CAB-GATE-NNN` | 1 | 001 | 12 |
| `DECOMP-FANOUT-NNN` | 1 | 001 | 12 |
| `ART-PLAN-NNN` | 8 | 001, 005–007, 009–011, 013 | 11 |
| `PLAN-FANOUT-NNN` | 1 | 001 | 11 |
| `PLAN-GATE-NNN` | 4 | 001–004 | 11 |
| `TASK-CREATION-FANOUT-NNN` | 1 | 001 | 11 |
| `TASK-ARG-NNN` | 1 | 001 | 10 |
| `PER-STORY-RESEARCH-NNN` | 1 | 001 | 9 |
| `REGRESS-NNN` | 3 | 001–003 | 9 |
| `ART-S5-NNN` | 4 | 001–004 | 8 |
| `ART-S2-NNN` | 3 | 002–004 | 7 |
| `MANIFEST-DIGEST-NNN` | 1 | 001 | 7 |
| `PLAN-REV-NNN` | 4 | 001–004 | 7 |
| `PREFLIGHT-NNN` | 1 | 001 | 7 |
| `ART-S1-NNN` | 3 | 003–005 | 6 |
| `ART-S6-NNN` | 3 | 001, 007–008 | 5 |
| `CROSS-NNN` | 4 | 001–003, 006 | 5 |
| `FAST-NNN` | 1 | 001 | 5 |
| `OUTPUT-NNN` | 5 | 001–005 | 5 |
| `RESUME-RECONCILE-NNN` | 1 | 001 | 5 |
| `SCOPE-NNN` | 2 | 001–002 | 5 |
| `BACKTRACK-NNN` | 3 | 001–003 | 3 |
| `DISPLAY-NNN` | 1 | 001 | 3 |
| `AO-INEFF-NNN` | 1 | 001 | 2 |
| `COST-CEIL-NNN` | 1 | 001 | 2 |
| `DIMINISH-NNN` | 1 | 001 | 2 |
| `SHA-NNN` | 1 | 256 | 2 |
| `THRASH-NNN` | 1 | 001 | 2 |
| `AO-GAP-NNN` | 1 | 002 | 1 |
| `ART-MTG-NNN` | 1 | 007 | 1 |
| `ART-RT-NNN` | 1 | 007 | 1 |
| `CEILING-NNN` | 1 | 001 | 1 |
| `HINT-NNN` | 1 | 001 | 1 |
| `INPROG-NNN` | 1 | 001 | 1 |
| `REASONING-NNN` | 1 | 001 | 1 |
| `SKILL-REUSE-NNN` | 1 | 003 | 1 |
| `SPEC-COMPLIANCE-NNN` | 1 | 001 | 1 |
| `TRIAGE-NNN` | 1 | 001 | 1 |

### `_shared/protocols/agent-activation.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `ACT-NNN` | 12 | 001–012 | 31 |
| `DISPATCH-GUARD-NNN` | 1 | 001 | 2 |
| `TRIG-NNN` | 2 | 001, 013 | 2 |

### `_shared/protocols/agent-preamble.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `PREAMBLE-NNN` | 4 | 001–004 | 29 |

### `_shared/protocols/command-dispatch.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `HANDOVER-COMPRESS-NNN` | 1 | 001 | 4 |
| `TRIGGER-TIE-NNN` | 1 | 001 | 1 |

### `_shared/protocols/cross-pipeline-state.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `STATE-NNN` | 3 | 001–003 | 21 |
| `AD-GAP-NNN` | 1 | 002 | 1 |

### `_shared/protocols/engineering-standards.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `ENG-STD-NNN` | 1 | 001 | 49 |

### `_shared/protocols/meeting-enforcement.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `MEETING-GATE-NNN` | 4 | 001–004 | 12 |

### `_shared/protocols/output-schemas.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `REQ-NNN` | 3 | 001–002, 012 | 5 |

### `_shared/protocols/output-standard.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `STAGE-RECEIPT-DIET-NNN` | 1 | 001 | 4 |
| `CHECKPOINT-NNN` | 1 | 001 | 1 |
| `STRUCTURE-NNN` | 1 | 001 | 1 |

### `_shared/protocols/skill-chain-contracts.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `CHAIN-NNN` | 11 | 001–011 | 26 |

### `_shared/protocols/subagent-protocol-base.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `READ-NNN` | 5 | 001–005 | 20 |
| `OUT-NNN` | 5 | 001–005 | 13 |
| `MAN-NNN` | 2 | 001–002 | 10 |
| `EARLY-NNN` | 3 | 001–003 | 9 |
| `NAME-NNN` | 1 | 001 | 2 |

### `_shared/protocols/task-system-integration.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `LIMIT-NNN` | 4 | 001–004 | 14 |
| `GUARD-NNN` | 3 | 001–003 | 5 |
| `PERSIST-NNN` | 3 | 001–003 | 5 |

### `agents/README.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `TEMPLATE-EXTRACT-NNN` | 1 | 001 | 3 |

### `agents/auditor.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `AUD-NNN` | 8 | 001–008 | 15 |

### `agents/data-engineer.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `DE-NNN` | 7 | 001–007 | 9 |

### `agents/infra-engineer.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `IE-NNN` | 11 | 001–011 | 11 |

### `agents/ml-engineer.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `ML-NNN` | 8 | 001–008 | 12 |

### `agents/qa-engineer.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `QA-NNN` | 6 | 001–006 | 9 |

### `agents/researcher.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `RES-NNN` | 14 | 001–014 | 94 |
| `RECEIPT-NNN` | 1 | 001 | 5 |

### `agents/security-engineer.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `SEC-NNN` | 8 | 001–008 | 8 |

### `agents/software-engineer.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `SE-NNN` | 9 | 001–009 | 17 |

### `agents/sre.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `SRE-NNN` | 7 | 001–007 | 7 |

### `agents/staff-principal-engineer.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `SPE-NNN` | 7 | 001–007 | 7 |

### `agents/technical-program-manager.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `TPM-NNN` | 6 | 001–006 | 10 |
| `D-NNN` | 2 | 001, 012 | 2 |

### `agents/technical-writer.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `TW-NNN` | 7 | 001–007 | 7 |

### `processes/04_sprint_delivery_execution.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `EM-NNN` | 7 | 001–007 | 18 |
| `PM-NNN` | 7 | 001–007 | 15 |
| `PROJ-NNN` | 1 | 123 | 1 |

### `processes/13_risk_change_management.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `A-NNN` | 1 | 003 | 1 |
| `I-NNN` | 1 | 007 | 1 |

### `processes/UNIFIED_END_TO_END_PROCESS.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `DEP-NNN` | 1 | 001 | 2 |
| `RC-NNN` | 1 | 001 | 1 |

### `processes/pipeline_chains_spec.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `R-NNN` | 2 | 001, 007 | 5 |
| `T-NNN` | 3 | 005, 016–017 | 3 |

### `processes/process_injection_map.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `PROCESS-SCOPE-NNN` | 1 | 001 | 9 |
| `ENFORCE-UPGRADE-NNN` | 1 | 001 | 7 |
| `DISPATCH-NNN` | 1 | 001 | 4 |
| `PROCESS-DELEGATE-NNN` | 1 | 001 | 1 |

### `processes/tests/gate_state_tests.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `GSP-NNN` | 10 | 001–010 | 12 |

### `processes/tests/handoff_test_scenarios.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `GAP-PIPE-NNN` | 3 | 001, 004–005 | 9 |
| `HS-NNN` | 5 | 001–005 | 5 |
| `GAP-NEW-NNN` | 1 | 002 | 2 |

### `ARCHITECTURE.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `RAID-NNN` | 1 | 001 | 16 |
| `ART-S3-NNN` | 4 | 001–004 | 12 |
| `ARTIFACT-CHECK-NNN` | 1 | 001 | 12 |
| `ART-ROOT-NNN` | 5 | 001–005 | 9 |
| `REASONER-NNN` | 2 | 001–002 | 9 |
| `ORCHESTRATE-FLAT-NNN` | 1 | 001 | 7 |
| `OUTPUT-TRIPLET-NNN` | 1 | 001 | 4 |
| `ARTIFACT-ENVELOPE-NNN` | 1 | 001 | 3 |

### `PERMISSION-MODES.md`

| Family | Distinct IDs | ID numbers | Occurrences |
|--------|-------------:|------------|------------:|
| `GAP-CRIT-NNN` | 1 | 001 | 13 |
| `DBG-NNN` | 2 | 002, 004 | 6 |
| `GAP-MED-NNN` | 1 | 002 | 3 |

