---
name: meta-reasoner
description: Universal meta-cognitive reasoning skill invoked at flagged complex decision points. Produces a DECOMPOSE -> SOLVE -> VERIFY -> SYNTHESIZE -> REFLECT trace with confidence scores and retries when aggregate confidence < 0.8. Skipped for simple questions.
triggers:
  - meta-reasoner
  - meta-cognitive
  - decompose problem
  - confidence reasoning
  - reasoning trace
  - reflect on answer
---

# Meta-Reasoner Skill

Universal reasoning aid for agents facing complex decisions. Implements a five-phase loop (DECOMPOSE, SOLVE, VERIFY, SYNTHESIZE, REFLECT) with explicit confidence floats per sub-problem, weighted aggregation, and a retry-on-low-confidence loop. Output triplet: Answer / Confidence / Key Caveats.

The skill is **never always-on**. For simple questions it returns ``{"skipped": true, "reason": ...}`` and the caller emits a direct answer without producing a reasoning trace.

---

## Pipeline Hook Sites

The skill fires from these specific orchestrator/agent hooks:

| Hook | Triggering condition |
|---|---|
| Stage 0 plan synthesis | More than 3 candidate plans produced by researcher |
| Stage 1 decomposition | ``proposed-tasks.json`` has > 10 nodes OR a dependency cycle |
| Stage 2 spec authoring | ``spec-analyzer`` flagged ambiguity |
| Gate dispute | Same gate rejected >= 2 times |
| Stage 5 validation | Validator returned >= 2 conflicting findings |
| Cross-team cycle | ``dependency-matrix-generator`` reported a cycle |

## Skip Heuristic

Skip when **all** of the following hold:

- ``inputs.length <= 1``
- No alternative approaches listed
- No validator warnings on the current draft
- Not in a gate dispute
- Self-reported draft confidence >= 0.7

The skill enforces this in ``scripts/reasoner.py::should_skip`` and returns a JSON document the caller stores instead of a trace::

    {"skipped": true, "reason": "single-input lookup; no alternatives"}

## Five-Phase Loop

1. **DECOMPOSE** — Break the problem into sub-problems S1..Sn with explicit dependencies.
2. **SOLVE** — For each Si, produce an answer and a confidence float in ``[0.0, 1.0]`` with cited evidence.
3. **VERIFY** — Cross-check each Si against the verification rule (missing logic, facts, completeness, bias). Adjust each Si's confidence downward when verification fails.
4. **SYNTHESIZE** — Combine sub-answers using weighted aggregation. ``aggregate_confidence = sum(weight_i * adj_confidence_i)`` with weights summing to 1.0.
5. **REFLECT** — If ``aggregate_confidence < 0.8``, identify the weakest sub-problem and re-run SOLVE+VERIFY for it. Maximum 3 retries. Persist each attempt under ``reflect.retry_history``.

The final ``output_triplet`` is::

    {"answer": ..., "confidence": <aggregate>, "key_caveats": [...]}

## Invocation Contract

Callers invoke via::

    python claude-code/skills/meta-reasoner/scripts/reasoner.py \
        --trigger '<TRIGGER_JSON>' \
        --inputs '<INPUTS_JSON>' \
        --session-id <SID> \
        --stage <STAGE> \
        --producer-agent <AGENT> \
        --output .orchestrate/<SID>/reasoning-traces/reasoning-trace-<TS>.json

``TRIGGER_JSON`` carries ``{agent, stage, complexity_signals: []}``.
``INPUTS_JSON`` is the array of candidate options or sub-problems.

The script writes an envelope-wrapped ``reasoning_trace`` artifact. The caller's own artifact then sets::

    "confidence": {
      "value": <aggregate>,
      "reasoning_trace": "<output path>",
      "caveats": [...]
    }

## Output Schema

```json
{
  "trigger": {"agent": "...", "stage": "...", "complexity_signals": [...]},
  "decompose": [{"sub_id": "S1", "problem": "...", "dependencies": []}],
  "solve":     [{"sub_id": "S1", "answer": "...", "confidence": 0.0, "evidence": []}],
  "verify":    [{"sub_id": "S1", "cross_check": "...", "passed": true, "adj_confidence": 0.0}],
  "synthesize":{"weights": {"S1": 0.4}, "aggregate_confidence": 0.0, "answer": "..."},
  "reflect":   {"meets_threshold": true, "threshold": 0.8, "retries": 0, "retry_history": []},
  "output_triplet": {"answer": "...", "confidence": 0.0, "key_caveats": []}
}
```

This body sits under the unified envelope's ``body`` field with ``artifact_type: reasoning_trace``.

## Constraints

- **REASONER-001**: Aggregate confidence threshold is 0.8 (hard-coded; tune via flag if needed).
- **REASONER-002**: Maximum retries is 3 per invocation. If still below threshold after retries, return the final triplet with ``reflect.meets_threshold = false`` and add a caveat naming the weakest sub-problem.
- **REASONER-003**: Skip-on-simple is mandatory; never produce a trace for trivial single-input lookups.
- **REASONER-004**: All confidence values must be in ``[0.0, 1.0]``. Weights must sum to 1.0 +/- 1e-6.
