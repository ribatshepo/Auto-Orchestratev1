---
artifact_type: task_spec
schema_version: 1.0.0
session_id: {{sid}}
task_id: {{task}}
deliverable_id: {{deliverable}}
stage: 2
produced_by: spec-creator
produced_at: {{produced_at}}
dependencies: []
files_touched: []
package_versions: {}
---

# Task Spec — {{task}}

## 1. Interface contract

```python
# Replace with the canonical typed interface for this task.
# Frozen dataclasses, sealed unions, enums, etc. — no Any, no dynamic.
```

## 2. Acceptance criteria

- AC-1 — {{ac_1}} (verifiable by {{verification_method}})
- AC-2 — {{ac_2}}
- AC-3 — {{ac_3}}

## 3. Architecture constraints

- {{constraint_1}}

## 4. Test plan

- Unit: {{unit_tests}}
- Integration: {{integration_tests}}

## 5. Dependencies

| Upstream | Provides | Required by |
|----------|----------|-------------|
| {{upstream}} | {{provides}} | {{requirement}} |

## 6. Notes

{{notes}}
