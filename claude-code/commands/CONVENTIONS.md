# Command Conventions

## PROGRESS-001 — Standard Progress Output Format

All commands use this format for progress output:

```
[<COMMAND>] [<STEP>] <message>
```

When the message concerns a specific agent or skill invocation, include the agent's badge from the **Agent Badge Palette** (below) and one of the spawn-lifecycle keywords from the **Spawn Visibility Protocol**:

```
[<COMMAND>] [<STEP>] <badge> <STARTING|COMPLETED|FAILED> — <message>
```

Examples:

- `[AUTO-ORC] [STEP 3] Spawning orchestrator — iteration 5 of 100`
- `[AUTO-ORC] [STEP 3] ⚙️ **orchestrator** STARTING — iteration 5 of 100`
- `[AUTO-ORC] [STAGE 3] 🛠️ **software-engineer** STARTING — task #4 "implement auth middleware"`
- `[AUTO-ORC] [STAGE 3] 🛠️ **software-engineer** ✦ production-code-workflow — reading skill`
- `[AUTO-ORC] [STAGE 3] 🛠️ **software-engineer** COMPLETED — task #4 — 12 files written`
- `[AUTO-DBG] [STEP 3] 🐛 **debugger** STARTING — cycle 3 of 50`
- `[AUTO-AUD] [STEP 3] 🛡️ **auditor** STARTING — cycle 2 of 5`

Prefix codes:

| Command | Prefix |
|---------|--------|
| auto-orchestrate | `AUTO-ORC` |
| auto-debug | `AUTO-DBG` |
| auto-audit | `AUTO-AUD` |

All three commands share the same palette and protocol below.

Commands should reference this file in their PROGRESS-001 rule: "See `commands/CONVENTIONS.md` for format, palette, and spawn-visibility protocol."

---

## PROGRESS-002 — Agent Badge Palette

Every emission about a specific agent or skill carries a stable visual badge so the running agent is identifiable at a glance. Badges are fixed for the life of the project — users build muscle memory.

| Agent / Component | Badge | Use sites |
|---|---|---|
| orchestrator | ⚙️ **orchestrator** | Every iteration of auto-orchestrate Step 3 |
| researcher | 🔬 **researcher** | Stage 0a, Stage 0b R1–R4, every planning P1–P4 R1–R4 |
| continuity-scout (consolidator) | 🧭 **continuity-scout** | Step -0.5 finalizer |
| scout-jsonl | 🟢 **scout-jsonl** | Step -0.5 fan-out (4 parallel) |
| scout-sessions | 🟡 **scout-sessions** | Step -0.5 fan-out (4 parallel) |
| scout-pipeline | 🟠 **scout-pipeline** | Step -0.5 fan-out (4 parallel) |
| scout-context | 🟣 **scout-context** | Step -0.5 fan-out (4 parallel) |
| product-manager | 📋 **product-manager** | Stage 1, planning P1, P2 |
| technical-program-manager | 🤝 **technical-program-manager** | Planning P3, dependency-matrix work |
| engineering-manager | 👥 **engineering-manager** | Planning P4 |
| staff-principal-engineer | ⭐ **staff-principal-engineer** | Stage 1/2/3 analysis pools when architectural concerns flagged |
| software-engineer | 🛠️ **software-engineer** | Stage 2 (spec-creator host), Stage 3, Stage 4 (test-writer host) |
| qa-engineer | 🧪 **qa-engineer** | Stage 4 fan-out, Stage 5 (validator + spec-compliance host) |
| security-engineer | 🔒 **security-engineer** | Stage 2/3/4/5 analysis pools when security in scope |
| sre | 🚀 **sre** | Stage 3/4/5 analysis pools when `release_flag` |
| infra-engineer | 🏗️ **infra-engineer** | Stage 3 IaC tasks |
| data-engineer | 🧬 **data-engineer** | Stage 3 pipeline/dbt tasks |
| ml-engineer | 🧠 **ml-engineer** | Stage 3 ML tasks |
| technical-writer | 📝 **technical-writer** | Stage 6 |
| auditor | 🛡️ **auditor** | Stage 4.5, Stage 5 |
| debugger | 🐛 **debugger** | Phase 5e |
| Skill (run inside a host agent) | ✦ `<skill>` | Append after the host agent's badge, e.g. `🛠️ **software-engineer** ✦ spec-creator — building spec for task-3` |
| Loop controller (no specific agent) | *(no badge)* | Pre-flight, mkdir, file I/O between spawns |

**Why emoji and not ANSI:** Claude Code renders assistant text as Markdown. ANSI escape codes in assistant text are not reliably rendered across surfaces (terminal CLI, desktop, web, IDE). Emoji glyphs render in all surfaces, so they are the canonical visual channel. Wrapper scripts that write directly to a TTY (e.g. `install.sh` smoke-tests) MAY additionally emit matching ANSI 256-color codes — but inside `/auto-orchestrate`, `/auto-debug`, `/auto-audit`, the badge IS the color.

---

## PROGRESS-003 — Spawn Visibility Protocol

Three required emissions per spawn, plus a heartbeat rule and a gate keepalive rule. This protocol applies at **every** `Agent(...)` spawn site in `commands/auto-orchestrate.md`, `commands/auto-debug.md`, `commands/auto-audit.md`, and `agents/orchestrator.md`.

### Required emissions

| Phase | Format | When |
|---|---|---|
| **STARTING** | `[<CMD>] [<STEP>] <badge> STARTING — <one-line task summary>` | Immediately before any `Agent(...)` call |
| **FLEET** | `[<CMD>] [<STEP>] FLEET: <badge1> + <badge2> + <badge3> + <badge4> — <fan-out reason>` | When ≥2 agents are spawned in a single parallel batch (replaces N separate STARTING lines; each agent still emits its own COMPLETED line as it returns) |
| **COMPLETED** | `[<CMD>] [<STEP>] <badge> COMPLETED — <verdict / artifact count / status>` | Immediately after the spawn returns, before processing its return text |
| **FAILED** | `[<CMD>] [<STEP>] <badge> FAILED — <error class>` | When a spawn returns an error or the agent self-reports failure. Use instead of COMPLETED. |

### Between-spawn heartbeat

If more than ~10 seconds of controller-side processing happens between a COMPLETED line and the next STARTING (or between Step 4 sub-steps, or while building a complex spawn prompt), emit:

```
[<CMD>] [<STEP X.Y>] processing — <activity>
```

at every sub-step boundary so the stream never goes silent for >10 s. The activity field names what's happening: `reading proposed-tasks.json`, `validating blockedBy chains`, `building Stage 3 spawn prompt`, `writing checkpoint`, etc. This is what stops the gap-between-iterations from looking like a request-for-input.

### Human-gate keepalive

While the loop controller is in HUMAN-GATE-001 polling (the existing `gate_poll_interval_seconds`, default 30 s), emit **one line per poll tick**:

```
[<CMD>] [HUMAN-GATE] ⏳ waiting for gate-approval-<id>.json — <elapsed>s elapsed of <timeout>s
```

The hourglass and the explicit "waiting for a file" wording matter: they tell the user the pipeline is alive AND that the wait is for a file write, not for them to type into the prompt.

### Between-iteration banner

Immediately before returning to Step 3 for the next iteration of the auto-orchestrate loop, emit:

```
[AUTO-ORC] [STEP 5] iteration N complete — beginning iteration N+1
```

This closes the most common silent gap in the loop.

### FLEET-line examples

```
[AUTO-ORC] [STEP -0.5] FLEET: 🟢 **scout-jsonl** + 🟡 **scout-sessions** + 🟠 **scout-pipeline** + 🟣 **scout-context** — continuity-brief parallel fan-out (CONT-007 / SCOUT-FANOUT-001)
[AUTO-ORC] [STAGE 0b] FLEET: 🔬 **researcher** ×4 — deliverable D2 4-research-pool (STAGE-0B-FANOUT-001)
[AUTO-ORC] [STAGE 1] FLEET: 📋 + 🤝 + 🧪 + ⭐ — deliverable D1 decomposition analysis pool (DECOMP-FANOUT-001)
[AUTO-ORC] [STAGE 3] FLEET: 🛠️ + 🧪 + 🚀 + 🔒 — task #4 implementation analysis pool (STAGE-3-FANOUT-001)
[AUTO-ORC] [STAGE 3] FLEET: 🛠️ **software-engineer** ×3 — parallel implementers for tasks #4, #6, #7 (STAGE-3-FANOUT-001)
[AUTO-ORC] [STAGE 4.5] FLEET: ✦ codebase-stats + ✦ refactor-analyzer + ✦ dependency-analyzer + ✦ security-auditor — 4-skill fan-out (STAGE-4-5-FANOUT-001)
```

**Naming convention**: FLEET lines for Stage 0a, Stage 0b, and P1–P4 use "research pool" (actual research, 🔬 researcher participates). FLEET lines for Stages 1, 2, 3, 4, 5 use "analysis pool" (specialist analysis only — no research, no WebSearch; see RESEARCH-BOUNDARY-001 in `commands/auto-orchestrate.md`).

When the same agent type fan-outs ×N, use `<badge> ×N` instead of repeating the badge N times.

---

## PROGRESS rule cross-reference

| Constraint | Owner doc | Summary |
|---|---|---|
| PROGRESS-001 | this file | The `[<CMD>] [<STEP>] <message>` line format |
| PROGRESS-002 | this file | The Agent Badge Palette |
| PROGRESS-003 | this file | The Spawn Visibility Protocol (STARTING / FLEET / COMPLETED / FAILED + heartbeat + gate keepalive + between-iteration banner) |

Commands and agents MUST link to these IDs rather than copy the format inline, so a single edit to this file changes the behavior everywhere.
