# Agent Preamble Protocol

Every spawned agent (`orchestrator`, `researcher`, `software-engineer`, `technical-writer`, all 17 team agents, the `meta-reasoner` skill, etc.) MUST execute this preamble before any other action.

## Step 1 — Read the Continuity Brief

The orchestrator writes `.orchestrate/<SESSION_ID>/continuity-brief.md` at Step -0.5 and refreshes it pre-Stage-0. Every agent's first action is:

```
READ .orchestrate/<SESSION_ID>/continuity-brief.md
```

If the file does not exist:

- During P1..P4 planning stages: HALT with `[CONTINUITY-MISSING]` — the scout did not run; escalate to orchestrator.
- During Stage 0..6: log `[CONTINUITY-WARN] no brief present; proceeding without prior-session context` and continue.

## Step 2 — Cite at Least One Item OR Declare None Relevant

Every agent's primary output (stage receipt, planning doc, code artifact, validation report, etc.) MUST include one of:

```
## Continuity Carryover
- Applied: <decision_id|pattern_id|fix_fingerprint> — <how this output uses it>.
```

or the explicit no-op declaration:

```
## Continuity Carryover
- (no relevant continuity item — task is unrelated to prior sessions)
```

Silent omission is a constraint violation flagged at the next gate.

## Step 3 — Honour User Preferences

If the brief surfaces user preferences (`## User Preferences`), the agent applies them unless they directly contradict the spec being implemented. Contradictions are escalated to a `meta-reasoner` invocation to resolve.

## Constraints (PREAMBLE)

| ID | Rule |
|---|---|
| PREAMBLE-001 | Reading the continuity brief is the first I/O operation of every agent spawn. |
| PREAMBLE-002 | Output MUST contain a `## Continuity Carryover` section. |
| PREAMBLE-003 | User preferences from the brief override default behaviours unless they conflict with the active spec. |
| PREAMBLE-004 | Conflicts between continuity items and current spec MUST invoke `meta-reasoner`. |

## Include Directive

Agent definitions reference this protocol with the directive:

```
{{include: _shared/protocols/agent-preamble.md}}
```

When the include cannot be resolved at spawn time, the orchestrator inlines the protocol body into the spawn prompt.
