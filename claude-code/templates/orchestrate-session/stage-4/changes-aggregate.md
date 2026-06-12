# Stage 4 — Aggregate Test Changes

> Produced by: orchestrator
> Session: {{sid}}
> Produced at: {{produced_at}}

This file is ALWAYS produced, even when zero test-only tasks were decomposed. In that case the body documents that explicitly.

## Test-only tasks executed

{{test_only_task_table}}

If empty: "No test-only tasks decomposed in Stage 1 (see `.orchestrate/{{sid}}/proposed-tasks.json`). Unit-test coverage is provided by Stage-3 per-task receipts (`test_files_created` field). Integration / e2e / coverage-only suites were not in scope this session."

## Test files added

| Path | Tests | Owner task |
|------|------|-----------|
| {{path}} | {{n}} | {{task}} |

## Coverage delta

- Before: {{coverage_before}}
- After: {{coverage_after}}
