# {{agent}} Domain Review — Stage {{stage}}

> Produced by: {{agent}}
> Session: {{sid}}
> Produced at: {{produced_at}}
> Stage: {{stage}}
> Activation: {{activation_rule}}  (e.g. ACT-007 fired | baseline (no rule fired))

## Scope of review

{{scope}}

## Findings

| ID | Severity | Finding | Recommendation |
|----|----------|---------|----------------|
| F-1 | {{sev}} | {{finding}} | {{recommendation}} |

## Verdict

{{verdict}}  (PASS | CONDITIONAL | BLOCKED)
Confidence: {{confidence}}

## Evidence

- Artifact: {{artifact_path}}
- Lines / sections inspected: {{lines}}

## Notes for downstream

{{downstream_notes}}

---

### Baseline-mode note (delete if rule-driven)

When this file is produced as a BASELINE review (no ACT-001..ACT-012 rule fired),
the body still records a real spot-check against the stage's primary artifact and
emits a verdict. A baseline review is never a placeholder.
