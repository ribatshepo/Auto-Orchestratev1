# Auto-Orchestrate Integration Guide

**Last Updated**: 2026-05-18
**Scope**: how to install, configure, run, extend, and troubleshoot the Auto-Orchestrate pipeline. Companion to `ARCHITECTURE.md` (which documents the pipeline's internals); this file documents the boundaries — installation, configuration, surrounding tools, extension points, troubleshooting.

---

## 1. Overview

Auto-Orchestrate ships as a tree of Claude Code components (agents, skills, commands, shared protocols, libraries, templates) plus an install script. Installation deploys everything under `~/.claude/`; the user then invokes `/auto-orchestrate "<task>"` inside any project directory. The pipeline writes a per-session folder under `<project>/.orchestrate/<sid>/` and validates it against a deterministic artifact contract at session close.

This guide covers:

- Prerequisites and quick install
- Full and selective install procedures
- Where every component ends up
- Verification (sanity tests + drift detection)
- Configuration (settings.json, CLAUDE.md, hooks, flags)
- Integration with Git, Docker, CI/CD, IDEs
- How to invoke the pipeline + read its outputs from outside
- Cross-pipeline shared state (`.orchestrate/pipeline-state/`)
- How to extend the pipeline (add an agent / skill / artifact / template)
- Migration + upgrade procedures
- Uninstallation
- Troubleshooting reference (every named error code)

For pipeline internals (stages, gates, the artifact contract, agent inventory), read `ARCHITECTURE.md`.

---

## 2. Prerequisites

| Requirement                                | Why                                                                                     | Verify                           |
| ------------------------------------------ | --------------------------------------------------------------------------------------- | -------------------------------- |
| **Claude Code CLI** authenticated    | The runtime that loads agents/skills/commands                                           | `claude --version`             |
| **`~/.claude/` directory** present | Install target (created automatically by Claude Code)                                   | `ls ~/.claude/`                |
| **Python 3.10+**                     | `check-completeness.py` validator + skill scripts                                     | `python3 --version`            |
| **`bash`** (4.x or 5.x)            | `install.sh` / `uninstall.sh` runtime                                               | `bash --version`               |
| **`git`**                          | Pipeline integrates with git for diff/log/status (read-only by default — see MAIN-014) | `git --version`                |
| **`jq`** (optional)                | JSON validation; convenience for inspecting `.orchestrate/<sid>/` artifacts           | `jq --version`                 |
| **`docker`** (conditional)         | Required only if Stage 5 needs `docker-validator` skill (HTTP endpoint smoke tests)   | `docker --version`             |
| **Network access**                   | Researcher agent uses WebSearch + WebFetch at Stage 0                                   | `curl https://example.com -sI` |

The pipeline does not require any external service accounts (Slack, Linear, etc.) by default. Integrations with those systems are opt-in via skill configuration (see §8.5).

---

## 3. Installation

### 3.1 Quick install (recommended)

From the repository root:

```bash
./install.sh
```

The installer:

1. Validates `claude-code/` source directory
2. Backs up any existing `~/.claude/` config to `~/.claude/backup-<TS>/`
3. Runs an orchestrator-integrity SHA check
4. Copies skills, agents, commands, `_shared/`, `lib/`, `scripts/`, `processes/`, `templates/`, `manifest.json`, `settings.json`, `PERMISSION-MODES.md`
5. `chmod +x ~/.claude/templates/orchestrate-session/check-completeness.py`
6. Installs Python dependencies (best-effort via `pip3 install --user --quiet` against `claude-code/requirements.txt` if present)
7. Runs `check-completeness.py --lint` as a post-install sanity probe
8. Prints a final ratio: `Agents: 22/22`, `Skills: 49/49`, `Templates: N/N`, etc.

Add `--check` for **drift detection without writing**: it compares source vs `~/.claude/` and reports any missing or mismatched components without modifying anything. Use this to verify a previous install or to dry-run an upgrade.

```bash
./install.sh --check
```

### 3.2 Full manual install

Equivalent to the quick install but step-by-step (useful for understanding, scripting, or installing on a constrained environment):

```bash
# 1. Create target directories
mkdir -p ~/.claude/{skills,agents,commands,_shared,lib,scripts,processes,templates}

# 2. Copy components
cp -r claude-code/skills/*    ~/.claude/skills/
cp -r claude-code/agents/*    ~/.claude/agents/
cp -r claude-code/commands/*  ~/.claude/commands/
cp -r claude-code/_shared     ~/.claude/_shared
cp -r claude-code/lib         ~/.claude/lib
cp -r claude-code/scripts     ~/.claude/scripts
cp -r claude-code/processes   ~/.claude/processes
cp -r claude-code/templates/* ~/.claude/templates/

# 3. The deterministic artifact contract (ARTIFACT-CONTRACT-001)
chmod +x ~/.claude/templates/orchestrate-session/check-completeness.py

# 4. The routing registry (MANIFEST-001)
cp claude-code/manifest.json ~/.claude/manifest.json

# 5. Settings (permissions allow/deny lists)
cp claude-code/settings.json ~/.claude/settings.json

# 6. (optional) Permission modes reference
cp claude-code/PERMISSION-MODES.md ~/.claude/PERMISSION-MODES.md

# 7. Sanity probe
python3 ~/.claude/templates/orchestrate-session/check-completeness.py --lint
# Expected: [LINT] manifest OK: 100 rules
```

### 3.3 Selective install

Install only specific categories when you don't need the full pipeline. Examples:

**Docs-only**:

```bash
cp -r claude-code/skills/docs-lookup    ~/.claude/skills/
cp -r claude-code/skills/docs-write     ~/.claude/skills/
cp -r claude-code/skills/docs-review    ~/.claude/skills/
cp claude-code/agents/technical-writer.md ~/.claude/agents/
```

**Research + analysis**:

```bash
cp -r claude-code/skills/researcher           ~/.claude/skills/
cp -r claude-code/skills/codebase-stats       ~/.claude/skills/
cp -r claude-code/skills/dependency-analyzer  ~/.claude/skills/
cp -r claude-code/skills/refactor-analyzer    ~/.claude/skills/
cp claude-code/agents/researcher.md           ~/.claude/agents/
```

**Workflow commands only** (no autonomous pipeline):

```bash
cp -r claude-code/skills/workflow-* ~/.claude/skills/
cp claude-code/agents/session-manager.md ~/.claude/agents/
```

Selective installs work, but `/auto-orchestrate` itself requires the **PIPELINE-CRITICAL subset** (11 agents + 11 skills enumerated in PREFLIGHT-001 — see ARCHITECTURE.md §9.2). The orchestrator will halt at pre-flight with a clear missing-component error if any critical agent or skill is absent.

### 3.4 Development mode (symlinks)

When iterating on the pipeline itself, symlink the source files so edits take effect immediately:

```bash
# Repo root
REPO="$(pwd)/claude-code"

# Symlink skills (per directory, since each skill is a folder)
for d in "$REPO"/skills/*/; do
  ln -sfn "$d" ~/.claude/skills/"$(basename "$d")"
done

# Symlink agents (flat .md files)
for f in "$REPO"/agents/*.md; do
  ln -sfn "$f" ~/.claude/agents/"$(basename "$f")"
done

# Symlink commands directory
ln -sfn "$REPO/commands" ~/.claude/commands

# Symlink shared resources
ln -sfn "$REPO/_shared"  ~/.claude/_shared
ln -sfn "$REPO/lib"      ~/.claude/lib
ln -sfn "$REPO/templates" ~/.claude/templates
ln -sfn "$REPO/manifest.json" ~/.claude/manifest.json
```

Caveats: `install.sh --check` will report drift (the symlink target's mtime won't match a fresh copy). That's expected in dev mode.

### 3.5 What gets installed where

After `./install.sh` succeeds, `~/.claude/` looks like this:

```
~/.claude/
├── manifest.json                  ← MANIFEST-001 routing registry
├── settings.json                  ← permissions allow/deny + env vars
├── PERMISSION-MODES.md            ← user-facing reference
├── backup-<YYYYMMDD>-<HHMMSS>/    ← created by installer if existing config was present
├── agents/                        ← 22 agent .md files (flat)
│   ├── orchestrator.md
│   ├── researcher.md
│   └── …
├── skills/                        ← 49 skill directories (each with SKILL.md + scripts)
│   ├── _shared/                   ← shared Python lib for skill scripts
│   ├── meta-reasoner/
│   ├── validator/
│   └── …
├── commands/
│   └── auto-orchestrate.md        ← the one user-facing command
├── _shared/                       ← 13 protocols + templates + style guides
│   ├── protocols/
│   │   ├── agent-activation.md
│   │   ├── agent-preamble.md
│   │   ├── command-dispatch.md
│   │   ├── cross-pipeline-state.md
│   │   ├── engineering-standards.md
│   │   ├── meeting-enforcement.md
│   │   ├── output-schemas.md
│   │   ├── output-standard.md
│   │   ├── skill-chain-contracts.md
│   │   ├── skill-chaining-patterns.md
│   │   ├── spawn-core.md            (slim per-spawn protocol pack, PROTOCOL-PACK-SLIM-001)
│   │   ├── subagent-protocol-base.md
│   │   └── task-system-integration.md
│   ├── references/                  (… + CONSTRAINTS-REGISTRY.md, TOOL-AVAILABILITY.md)
│   └── …
├── lib/                           ← 3 Python packages + 2 single-file modules
│   ├── artifact_envelope/          (envelope schemas + validator; optional excerpt digest)
│   ├── ci_engine/                  (within-run OODA + cross-run PDCA loops)
│   ├── domain_memory/              (persistence + DomainIndexer FTS query, DOMAIN-QUERY-001)
│   ├── _time.py                    (shared UTC timestamp helpers)
│   └── path_compat.py              (legacy-root resolver during migration)
├── scripts/                       ← migration + helper scripts
├── processes/                     ← P-001 .. P-093 catalog + injection map
└── templates/                     ← session artifact contract + validator
    └── orchestrate-session/
        ├── manifest.yml            (100 rules)
        ├── check-completeness.py   (the validator)
        ├── README.md
        ├── schemas/                (18 JSON schemas)
        ├── session/
        ├── planning/
        ├── stage-0/ … stage-6/
        ├── stage-4_5/
        ├── gates/
        ├── meetings/
        ├── handovers/
        ├── domain-reviews/
        ├── phase-receipts/
        └── reasoning-traces/
```

---

## 4. Verification

After install, run these checks (or `./install.sh --check` does most of them automatically).

### 4.1 Component counts

```bash
ls ~/.claude/agents/*.md   | wc -l   # 18
ls -d ~/.claude/skills/*/  | wc -l   # 49 (+ _shared)
ls ~/.claude/commands/*.md | wc -l   # 1 (auto-orchestrate.md)
ls ~/.claude/_shared/protocols/*.md | wc -l   # 12
```

### 4.2 Manifest registry valid

```bash
python3 -c "import json; m=json.load(open('$HOME/.claude/manifest.json')); print('agents:', len(m['agents']), 'skills:', len(m['skills']))"
# Expected: agents: 18 skills: 49
```

### 4.3 Artifact contract lint

```bash
python3 ~/.claude/templates/orchestrate-session/check-completeness.py --lint
# Expected: [LINT] manifest OK: 100 rules
```

### 4.4 Quick smoke test

Open Claude Code in any project, then try:

```
/workflow-start
```

Expected: a task-overview message with no errors. If you get `[MANIFEST-001] manifest.json not found`, the install missed the registry — re-run §3.

```
/workflow-dash
```

Expected: a project-task-dashboard summary.

```
/auto-orchestrate "trivial test: print hello"
```

Expected: the loop controller initializes, runs Step 2.0 (mkdir), and begins pre-flight with `[AUTO-ORC] Pre-flight: 15/15 pipeline-critical agents present, 11/11 pipeline-critical skills present (manifest totals: 22 agents, 49 skills, 13 protocols, 3 lib_libraries).` Abort with Ctrl-C if you don't actually want to run the full pipeline.

### 4.5 Artifact contract templates

```bash
ls ~/.claude/templates/orchestrate-session/manifest.yml   # exists
file ~/.claude/templates/orchestrate-session/check-completeness.py
# expected: ... ELF or shebang executable

# Drift check via installer
./install.sh --check
# expected (if everything in sync): [OK] templates: N/N + [OK] templates: manifest.yml --lint passes
```

### 4.6 Domain memory + cross-pipeline state

```bash
# Created lazily on first session — these directories may not exist until then.
ls .orchestrate/domain/ 2>/dev/null            # JSONL stores; empty until first session writes
ls .orchestrate/pipeline-state/ 2>/dev/null    # research-cache, fix-registry, codebase-analysis, etc.
```

---

## 5. Configuration

### 5.1 `~/.claude/settings.json`

The default `settings.json` installed by `install.sh` ships with conservative permissions: read+write inside `~/.claude/**`, `/tmp/**`, and `./**` (project working dir); WebFetch + WebSearch enabled (required by researcher); and an explicit deny list covering credentials (`~/.ssh/**`, `~/.gnupg/**`, `~/.aws/**`), system paths (`/etc/**`, `/bin/**`, `/sbin/**`, `/usr/**`, `/boot/**`, etc.), and destructive shell commands (`rm -rf`, `dd`, `mkfs*`, `fdisk *`, `wipefs *`, etc.).

To customise permissions, edit `~/.claude/settings.json` or use the `/update-config` skill (preferred — it writes the right schema). Common edits:

- Add a project-specific allow (e.g. `Bash(npm test*)`)
- Tighten the project-write scope from `Write(./**)` to a narrower glob
- Add an `env:` block for `DEBUG`, `CLAUDE_LOG_LEVEL`, etc.

### 5.2 Per-project `CLAUDE.md`

The pipeline reads `CLAUDE.md` from the project root as part of every agent's preamble (PREAMBLE-001..004). Put project-specific context here: tech stack, coding conventions, what tests to run, what NOT to touch. Example skeleton:

```markdown
# Project: <name>

## Tech stack
- Python 3.12 + uv
- pytest + ruff + mypy --strict

## Run tests
`uv run pytest -x`

## Do NOT touch
- src/legacy/  (deprecated; will be deleted in v3.0)
- migrations/  (run only via `alembic upgrade head`)
```

CLAUDE.md is referenced once per agent spawn — keep it concise (under 200 lines).

### 5.3 Hooks (settings.json)

Automated behaviors triggered by harness events ("from now on when X", "before/after Y") live in `~/.claude/settings.json` under `hooks:`. Use the `/update-config` skill to add them. Memory and preferences cannot fulfill harness-level automation — only hooks can. Examples: auto-format-on-save, auto-rerun-tests-after-edit, slack-notify-on-error.

### 5.4 Flag reference for `/auto-orchestrate`

| Flag                            | Purpose                                                                                                                                                                                             |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--skip-planning`             | Bypass P1–P4 (only way besides `planning_skipped: true` in a resume checkpoint). Triage complexity no longer auto-skips planning.                                                                |
| `--human-planning-gates`      | Restore legacy human-gated planning at all four planning gates (overrides REASONING-GATE-001).                                                                                                      |
| `--human-decomposition-gates` | Downgrade DECOMP-REASONING-001 → HUMAN-GATE-001 for Stage 1 (legacy single-agent product-manager spawn).                                                                                           |
| `--human-task-creation-gates` | Downgrade TASK-CREATION-REASONING-001 → HUMAN-GATE-001 for Stage 2 (legacy inline spec-creator).                                                                                                   |
| `--sequential-stages`         | Disable parallel spawning at Stages 4/4.5/5/6 and domain phases; revert to one-at-a-time.                                                                                                           |
| `--respect-pacing-directives` | Honor pacing directives ("one unit per response", "wait for my approval", etc.) instead of stripping them at Step 1a (AUTO-PACING-001). The autonomous-pipeline default is to ignore pacing pauses. |
| `--fast`                      | Fast-path mode for trivial single-stage tasks (requires `--skip-planning`).                                                                                                                       |

Engineering Standards (ENG-STD-001) are immutable — flags cannot loosen them. Task arguments MAY ADD stricter rules but cannot weaken the baseline.

---

## 6. Pipeline integration points

### 6.1 Invoking the pipeline

Inside any project's working directory:

```
/auto-orchestrate "<task description>"
```

The loop controller:

1. Enhances the prompt (Step 1) — strips pacing directives, preserves quality directives under `## Engineering Standards (HONORED)`.
2. Creates the session infrastructure (Step 2) — mkdir's `.orchestrate/{domain,audit,knowledge_store,pipeline-state/*,<sid>/{planning,stage-0..6,gates,meetings,handovers,domain-reviews,phase-receipts,reasoning-traces}}`.
3. Spawns the orchestrator agent (Step 3) — which then drives P1 → P4 → PRE-RESEARCH-GATE → Stage 0 → ... → Stage 6.
4. Runs Step 4.8d.5 (meeting completeness) at every stage transition.
5. Runs Step 7 (ARTIFACT-CHECK-001) before writing `terminal_state`.
6. On successful close, runs Sprint Closure (P-027 → P-028 → P-029) and optionally Phase 7/8/9.

### 6.2 The session directory contract

Every session creates `<project>/.orchestrate/<sid>/` where `<sid>` is `auto-orc-<YYYYMMDD>-<project-slug>`. The full canonical layout is documented in `ARCHITECTURE.md` §12. Key files external tools read:

| Path                                                     | Purpose                                                   | Read by                                                     |
| -------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------- |
| `<sid>/checkpoint.json`                                | Current iteration, status, terminal_state, phase counters | Resume logic; external dashboards                           |
| `<sid>/proposed-tasks.json`                            | Merged task list (after Stage 1)                          | workflow-* commands; external monitoring                    |
| `<sid>/continuity-brief.md`                            | Pre-P1 context (written by continuity-scout)              | All spawned agents (preamble)                               |
| `<sid>/raid-log.json`                                  | Single RAID log per session (RAID-001)                    | RAID-related skills; PM dashboards                          |
| `<sid>/gates/gate-pending-*.json`                      | Human-gate prompts awaiting approval                      | The user (via Claude Code UI)                               |
| `<sid>/gates/gate-completeness-<TS>.json`              | Latest completeness verdict                               | `auto-orchestrate` Step 7 decision logic                  |
| `.orchestrate/pipeline-state/workflow/task-board.json` | Single source of truth for task state (WORKFLOW-SYNC-001) | `/workflow-dash`, `/workflow-next`, `/workflow-focus` |

### 6.3 Reading session state from outside

While `/auto-orchestrate` is active, four read-only workflow commands let you observe state without interfering:

| Command             | Returns                                                             |
| ------------------- | ------------------------------------------------------------------- |
| `/workflow-dash`  | Project-task dashboard with all in-progress/pending/completed tasks |
| `/workflow-next`  | Suggested next task (dependency-aware)                              |
| `/workflow-focus` | Current focused task (single-task-discipline)                       |
| `/workflow-start` | Status overview at session boundary                                 |

Per WORKFLOW-SYNC-002, these commands operate **read-only** when `pipeline-context.json#active_command` shows a Big Three command (auto-orchestrate / auto-audit / auto-debug) with `last_updated` within 5 minutes. Read-write resumes when no Big Three session is active.

### 6.4 Resuming a session

`/auto-orchestrate` automatically detects a prior session checkpoint (`<sid>/checkpoint.json`) and resumes from the last completed stage. To force a fresh session, archive the prior `.orchestrate/<sid>/` directory before re-invoking. To bypass planning on resume (the prior session already approved P1–P4), the resume logic sets `planning_skipped: true` in the new checkpoint automatically when prior planning artifacts are detected.

### 6.5 Approving / rejecting human gates

When the loop controller writes `gates/gate-pending-<gate_id>.json`, the user approves by writing `gates/gate-approval-<gate_id>.json` (or rejects via `gate-rejected-<gate_id>.json`). The polling interval is 30s by default (`gate_poll_interval_seconds`) up to a 24h timeout (`gate_timeout_seconds`). On timeout: `terminal_state: "gate_timeout"`.

The Claude Code UI surfaces pending gates automatically; you typically click "approve" rather than writing the JSON by hand. The four boundaries currently human-gated by default: Phase 5e Debug Entry, Phase 5v Compliance Verdict, CAB Review (conditional per CAB-GATE-001), Phase 7 Release Readiness.

### 6.6 Token optimization

The pipeline's per-spawn and per-artifact token cost is governed by nine `checkpoint.optimizations.*`
flags (checkpoint schema 1.10.0), default-on for fresh sessions and off on resume. They never delete
artifacts or lose context — full bodies, briefs, and protocol docs stay on disk and are deep-read on
demand. The full catalogue (flags, constraints, slim spawn pack, digest-by-default reading, tiered
continuity brief, FTS retrieval, gating + migration ladder) is documented in **ARCHITECTURE.md §15**;
the canonical per-flag rules are in `_shared/protocols/command-dispatch.md`.

---

## 7. Cross-pipeline shared state

`<project>/.orchestrate/pipeline-state/` is shared across all autonomous commands (`auto-orchestrate`, plus the legacy `auto-audit` / `auto-debug` invocations now subsumed as Phase 5v/5e). Per the `cross-pipeline-state.md` protocol (SHARED-001..004):

| File                             | Purpose                                                                                                                                                                                                              | Lifecycle                   |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| `research-cache.jsonl`         | Research findings reusable across pipelines. Researcher agent checks this BEFORE running new web queries (SHARED-003). Entries past `ttl_hours` are hints, not facts.                                              | Append-only                 |
| `fix-registry.jsonl`           | Error → fix mappings from auto-debug / Phase 5e. Before diagnosing a new error, the debugger MUST check for an existing verified fix (`verification_result: "pass"`) for the same error fingerprint (SHARED-004). | Append-only, never modified |
| `codebase-analysis.jsonl`      | Cached codebase insights from any pipeline (Stage 4.5 outputs especially).                                                                                                                                           | Append-only                 |
| `escalation-log.jsonl`         | Cross-pipeline escalation history (SHARED-002 — handoffs go here, not into session-local dirs).                                                                                                                     | Append-only                 |
| `pipeline-context.json`        | Current pipeline state summary; overwritten by every Big Three invocation. Drives WORKFLOW-SYNC-002 read-only mode.                                                                                                  | Overwritten                 |
| `command-receipts/`            | Per-command receipts (STATE-001) timestamped `<command>-<YYYYMMDD>-<HHMMSS>.json`.                                                                                                                                 | Append-only                 |
| `process-log/`                 | Per-process execution history (STATE-003) as `P-004.jsonl` ... `P-093.jsonl`.                                                                                                                                    | Append-only                 |
| `workflow/active-session.json` | Currently-active session ID + pid                                                                                                                                                                                    | Overwritten                 |
| `workflow/task-board.json`     | **Single source of truth for task state** (WORKFLOW-SYNC-001). Updated atomically at every iteration (write `.tmp`, rename).                                                                                 | Overwritten                 |
| `workflow/focus-stack.json`    | Currently-focused task ID + stack (read by `/workflow-focus`).                                                                                                                                                     | Overwritten                 |

This shared layer enables knowledge transfer across sessions and across pipelines without violating session isolation (each session still owns its own `<sid>/` subdir).

---

## 8. Integration with surrounding tools

### 8.1 Git

By MAIN-014, **no agent may run `git commit` or `git push`** or any git write operation. Agents collect commit messages in their stage receipts (`Git-Commit-Message:` block in DONE markers) and surface them at session end; the user reviews and commits.

Read-only git operations are allowed and used liberally: `git log`, `git status`, `git diff`, `git show <hash>`, `git log --oneline -p -- <path>`. The orchestrator typically reads recent commits to derive change history when injecting context.

If you want a git-write-enabled workflow, use the `dev-workflow` skill — it's the only sanctioned wrapper that knows how to write atomic conventional commits. Invoke it explicitly via `/dev-workflow commit "<message>"`; it will NOT fire from autonomous flow.

### 8.2 Docker

- **`docker-validator` skill** runs at Stage 5 when Docker is available. It captures pre-test container state, runs `docker compose build` + `docker compose up`, hits HTTP endpoints (authenticated + unauthenticated), detects 4xx/5xx, and restores Docker state to baseline. Its findings feed VALIDATION-REASONING-001's six sub-questions (specifically: docker-validator no blocking errors).
- **`docker-workflow` skill** is invocation-on-demand. Use it for ad-hoc Dockerfile authoring, container debugging, or image-security checklists.

If Docker isn't installed, the orchestrator detects this at Stage 5 and skips the docker-validator sub-spawn (logged `[STAGE-5] docker-validator skipped — docker not available`); the validation gate still runs.

### 8.3 CI / CD

- **`cicd-workflow` skill** generates GitHub Actions / GitLab CI configs and debugs failing pipelines. Invoked when triage flags include `ci` or when Phase 5i (infra/SRE) requires release-pipeline review.
- **The pipeline itself can be embedded in CI**. `check-completeness.py --session-root .orchestrate/<sid>` exits 0/1/2 and writes a single JSON, making it scriptable. Example CI pattern:

  ```yaml
  # .github/workflows/orchestrate-verify.yml
  - name: Verify orchestrate session artifacts
    run: |
      python3 ~/.claude/templates/orchestrate-session/check-completeness.py \
        --session-root .orchestrate/$(ls -1 .orchestrate/ | grep '^auto-orc-' | tail -1)
  ```

  Non-zero exit → CI fails. JSON output is in `.orchestrate/<sid>/gates/gate-completeness-<TS>.json`.
- **CI feedback hooks** in orchestrator.md (around the "CI Feedback Hooks: research_completeness_score Blocking Gate" section) define a hard blocking gate: if `research_completeness_score` from Stage 0 is < 70, Stage 1 cannot begin. This protects against shallow research.

### 8.4 IDE integrations

Claude Code runs as a CLI in the terminal AND as IDE extensions for VS Code and JetBrains. The same `~/.claude/` install serves both. Symlink mode (§3.4) is particularly convenient for IDE workflows because file edits in the source repo immediately update the IDE's loaded skill set.

### 8.5 External services (Slack, Linear, Jira, GitHub PRs)

The pipeline does not ship with direct integrations to external services. Patterns to wire them in:

- **Slack / GitHub PR / Linear posting**: write a small skill (use `skill-creator`) that wraps the relevant CLI (`gh`, `slack-cli`, `linear-cli`) and invoke it from a phase hook. Phase 8 (Post-Launch) and Phase 9 (Governance) are the natural call sites for retro / OKR posting.
- **MCP servers**: any MCP server you've configured (e.g. Google Drive, GitHub, Slack) is automatically available to agents that have permission for it. Permissions live in `~/.claude/settings.json` under `permissions.allow`.
- **Reading from external systems**: agents have WebSearch + WebFetch. For structured-data reads (Jira tickets, Linear issues), write a researcher-spawned skill that targets the API.

The `references/` field in skill memory (see `/remember`) is the canonical way to record "where X is tracked" (e.g. "pipeline bugs are in Linear project INGEST"), so future sessions know where to look.

---

## 9. Extending the pipeline

### 9.1 Add a new agent

1. Create `claude-code/agents/<name>.md` with frontmatter:

   ```yaml
   ---
   name: <name>
   description: |
     One- to three-line purpose statement. The orchestrator reads
     this to decide when to dispatch.
   tools:
     - Read
     - Write
     - Edit
     - Bash
     - Glob
     - Grep
     - Task   # only if the agent itself spawns subagents
   model: sonnet  # or opus / haiku
   triggers:       # optional — lets the orchestrator pre-match
     - "<keyword phrase>"
   ---
   ```
2. Add a body section describing inputs, outputs (envelope type + path pattern), constraints, and the agent's place in the pipeline.
3. Register the agent in `claude-code/manifest.json` under `"agents": [...]`:

   ```json
   {
     "name": "<name>",
     "file": "agents/<name>.md",
     "purpose": "<one-line>",
     "tools": ["Read", "Bash", "..."]
   }
   ```
4. If the agent should fire on stage-close domain activation, add an `activation_rules:` entry under `manifest.agents[<name>]` (see `_shared/protocols/agent-activation.md` for ACT-001..012 format).
5. Re-run `./install.sh` to deploy.

### 9.2 Add a new skill

Use the `skill-creator` skill:

```
/skill-creator "I want a skill that <does X>"
```

It scaffolds `claude-code/skills/<name>/SKILL.md` with the right frontmatter, optional `scripts/` directory for Python helpers, and updates `manifest.json`. Manual structure:

```
claude-code/skills/<name>/
├── SKILL.md                  ← frontmatter + body
├── scripts/                  ← optional Python helpers
│   └── *.py
└── references/               ← optional reference docs the skill embeds
```

SKILL.md frontmatter:

```yaml
---
name: <name>
description: |
  When to use this skill. Triggers: "<trigger phrase>",
  "<trigger phrase>", etc.
---
```

### 9.3 Add a new artifact rule

Artifacts the pipeline produces are governed by `templates/orchestrate-session/manifest.yml`. To add a new required artifact:

1. Append a new rule under `rules:`:

   ```yaml
     - id: ART-<area>-<NNN>
       path: <session>/<area>/<filename-pattern>
       template: <area>/<template-filename>
       schema: schemas/<schema-name>.schema.json
       owner: <agent-or-skill-name>
       cardinality: one | one-per-deliverable | one-per-task | one-per-stage | one-or-more
       required: true
   ```
2. Create the seed template at `templates/orchestrate-session/<area>/<template-filename>` (use existing templates as reference). Use `{{placeholder}}` tokens where the producing agent will substitute values.
3. If the new artifact has a JSON schema, add it under `schemas/`.
4. If the artifact needs a cross-cardinality consistency check, add a `CONS-NNN` entry under `consistency_checks:` in `manifest.yml` AND a matching block in `check-completeness.py#run_consistency_checks()`.
5. Lint: `python3 templates/orchestrate-session/check-completeness.py --lint` — should still pass.
6. Re-run `./install.sh` to deploy.

### 9.4 Add a new template

For non-required templates (orchestrator references them in spawn prompts but completeness checker doesn't enforce):

1. Create the file under the appropriate `templates/orchestrate-session/<area>/`.
2. Reference it from `claude-code/agents/<agent>.md` or `claude-code/commands/auto-orchestrate.md` via path: `templates/orchestrate-session/<area>/<file>`.
3. Re-run `./install.sh`.

### 9.5 Modify or add a constraint (MAIN-*, PHASE-*, AGENT-ACTIVATE-*)

1. Edit the constraint table at the top of `claude-code/agents/orchestrator.md` (MAIN-*) or in `claude-code/commands/auto-orchestrate.md` (gate / layout / artifact constraints).
2. If the constraint requires concrete code, add an implementation section in the same file (the way MAIN-017's "Stage-Close Protocol" section sits after the loop body).
3. Update any cross-references in `_shared/protocols/*.md`.
4. Update `ARCHITECTURE.md` §10 (constraints reference) and §11 (artifact contract) as needed.

---

## 10. Migration & upgrade

### 10.1 Unified `.orchestrate/` migration

If you have a legacy install with `.domain/`, `.audit/`, `.pipeline-state/` as siblings (rather than subfolders of `.orchestrate/`), run:

```bash
python3 ~/.claude/scripts/migrate_to_unified_orchestrate.py
```

The script is **idempotent** via a marker file (`.orchestrate/.migration-v1.done`); safe to re-run. Per ORCHESTRATE-FLAT-001, new code MUST write to the unified paths.

`claude-code/lib/path_compat.py` provides a shim that resolves legacy paths to unified paths for one release window — old code continues to work during the transition. The shim will be removed in a future release.

### 10.2 Upgrade procedure (installed version)

```bash
cd <repo>
git pull
./install.sh --check    # see what would change
./install.sh            # apply (backs up existing config to ~/.claude/backup-<TS>/)
```

The installer's orchestrator-integrity check compares orchestrator.md SHA before/after; mismatches are reported but installation proceeds.

### 10.3 Schema version upgrades

`checkpoint.json` carries a `schema_version` field (currently `1.10.0`). When the schema bumps, the `schema-migrator` skill upgrades existing session checkpoints in place:

```
/schema-migrator "bump checkpoint to 2.0.0 in .orchestrate/<sid>/"
```

The skill validates the new structure against `templates/orchestrate-session/schemas/checkpoint.schema.json` before writing.

### 10.4 Drift detection (post-upgrade)

```bash
./install.sh --check
```

Reports any mismatch between `claude-code/` source and `~/.claude/` installed tree. Look for `[DRIFT]` lines.

---

## 11. Uninstallation

```bash
./uninstall.sh             # interactive confirmation
./uninstall.sh --dry-run   # show what would be removed without removing
./uninstall.sh --yes       # non-interactive; remove without prompting
```

Components removed (the `COMPONENTS` list in `uninstall.sh`): `~/.claude/{skills, agents, commands, _shared, lib, scripts, processes, templates, manifest.json, settings.json, PERMISSION-MODES.md}`.

Project-level `.orchestrate/<sid>/` session directories are **not** touched — those are project state, not install state. Remove them manually if desired:

```bash
rm -rf .orchestrate   # ONE specific project; do not run repo-wide
```

---

## 12. Troubleshooting

### 12.1 Common error codes

| Code                                                 | Meaning                                                                                                                                                        | Fix                                                                                                                                                                                   |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[MANIFEST-001]`                                   | `manifest.json` missing or malformed at `~/.claude/manifest.json`                                                                                          | Re-run `./install.sh`                                                                                                                                                               |
| `[LAYOUT-GATE-001]`                                | Required deterministic-layout directory missing from `.orchestrate/`                                                                                         | Re-run Step 2.0 mkdir block; if seen at session start, this means Step 2.0 didn't fire — check for upstream loop-controller errors                                                   |
| `[LAYOUT-GATE-001-VIOLATION]`                      | Session directory found at repo root (`./<sid>/`) instead of `.orchestrate/<sid>/`                                                                         | Step 3.0a self-heals via `mv ./<sid> .orchestrate/<sid>` automatically; check the `[LAYOUT-GATE-001-ERROR]` variant if both paths exist (requires manual reconciliation)          |
| `[ARTIFACT-MISSING]`                               | An empty folder was detected at session close that should have contained a real artifact                                                                       | Read `audit/findings-ledger.jsonl` and the failing `gates/gate-completeness-<TS>.json#consistency_failures` for the specific path; spawn the rule-owner from the remediation hint |
| `[ARTIFACT-CHECK-001-MISSING]`                     | Loop controller tried to set `terminal_state = "completed"` without a current passing `gate-completeness-<TS>.json`                                        | Rewind to Step 7.1 and run `check-completeness.py`; if it FAILs, follow the 3-cycle remediation loop                                                                                |
| `[ENVELOPE-INVALID]`                               | A JSON artifact failed envelope validation                                                                                                                     | Check `claude-code/lib/artifact_envelope/schemas.py` for the expected envelope shape; fix the producing agent's template                                                            |
| `[MEETING-MISSING]`                                | gate-meeting-completeness check found a mandatory meeting's minutes absent                                                                                     | Spawn the missing meeting's facilitator with the right `meetings/minutes-<process>-*.json` template                                                                                 |
| `[PLAN-GATE-001..004]`                             | One of P1–P4 planning gates incomplete; Stage 0 cannot begin                                                                                                  | Run the missing planning gate; or pass `--skip-planning` (consequences: no Intent Brief, Scope Contract, etc.); or resume a session whose `planning_skipped: true` is already set |
| `[TASK-ARG-001]`                                   | Loop controller attempted worker behaviour (read project files, identified components, etc.) — self-aborts and restarts at Step 0                             | Usually transient; check the task argument doesn't trick the loop controller into acting like a worker                                                                                |
| `[CAB-SKIP]`                                       | CAB Review gate skipped because risk classification is LOW/MEDIUM                                                                                              | Informational; not an error                                                                                                                                                           |
| `[GATE-TIMEOUT]`                                   | A human gate didn't receive `gate-approval-*.json` within `gate_timeout_seconds` (default 24h); session terminated with `terminal_state: "gate_timeout"` | Resume the session manually and approve the gate, OR adjust `gate_timeout_seconds` in checkpoint                                                                                    |
| `[ENG-STD-001]`                                    | Task argument attempted to loosen an Engineering Standards baseline rule                                                                                       | Baseline applied automatically; informational                                                                                                                                         |
| `[CONS-004 missing: domain-reviews/*-stage-N*.md]` | Stage N closed without writing any real domain review                                                                                                          | The MAIN-017 Part 1.2 baseline qa-engineer review should have fired; check that the orchestrator's Stage-Close Protocol block actually ran                                            |
| `[CONS-005 missing: meetings/*.json]`              | No real meeting receipt for the session (sentinels excluded)                                                                                                   | MAIN-017 Part 1.4 baseline check-in didn't fire; check meeting-enforcement.md Step 4.8d.5 wiring                                                                                      |
| `[CONS-007 layout]`                                | Session is outside `.orchestrate/` (LAYOUT-GATE-001 violation)                                                                                               | Use Step 3.0a self-heal or `mv <sid> .orchestrate/<sid>` manually; for forensic runs only, pass `--allow-unrooted` to `check-completeness.py`                                   |

### 12.2 Validator FAIL is non-fatal during diagnosis

`check-completeness.py` always writes `gates/gate-completeness-<TS>.json` — even when verdict is FAIL. Read that file to see exactly which rules are missing, which consistency checks failed, and the auto-generated remediation list (each entry maps to the responsible MAIN-017 Stage-Close Protocol part or per-rule owner spawn).

### 12.3 Diagnosing an empty `phase-receipts/` / `domain-reviews/` / `meetings/` / `reasoning-traces/`

If you see a session where one of these directories is empty:

1. Check `<sid>/checkpoint.json#terminal_state`. If `"completed"`, the Step 7 contract was broken — the loop controller wrote `completed` without a passing completeness check. Look for missing `gate-completeness-*.json` in `<sid>/gates/`.
2. If `terminal_state == "INCOMPLETE_ARTIFACTS"`, the gate fired and the orchestrator exhausted 3 remediation cycles. Read the most recent `gate-completeness-*.json#rules_missing` and follow the remediation list manually.
3. If neither, the session crashed before terminal-state. Resume it; the loop controller will re-run from the last successful stage and re-fire the Stage-Close Protocol.

### 12.4 Reset everything

```bash
./uninstall.sh --yes
rm -rf ~/.claude/backup-*    # if you don't want the backups either
./install.sh
```

### 12.5 Debug mode

Set `CLAUDE_LOG_LEVEL=DEBUG` in the environment (or in `~/.claude/settings.json#env`) for verbose orchestrator logging. Per-stage spawn prompts, gate-evaluation traces, and remediation dispatch calls all log to stderr.

### 12.6 Where the support breadcrumbs are

| Need                       | File                                    |
| -------------------------- | --------------------------------------- |
| User-facing playbook       | `PLAYBOOK.md`                         |
| Security audit             | `SECURITY-AUDIT-v1.1.md`              |
| Engineering team structure | `Engineering_Team_Structure_Guide.md` |
| Release notes              | `RELEASE-NOTES.md`, `CHANGELOG.md`  |
| Permission modes reference | `claude-code/PERMISSION-MODES.md`     |
| Contributing guide         | `CONTRIBUTING.md`                     |
| Pipeline internals         | `ARCHITECTURE.md`                     |

---

## 13. Where to read next

| Topic                                          | File / location                                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Full pipeline architecture                     | `ARCHITECTURE.md`                                                                                    |
| Loop controller flow (Steps 0..7)              | `claude-code/commands/auto-orchestrate.md`                                                           |
| Orchestrator constraints (MAIN-001..017)       | `claude-code/agents/orchestrator.md` lines 32-50                                                     |
| Stage-Close Protocol (MAIN-017 Parts 1.1–1.4) | `claude-code/agents/orchestrator.md` section after loop body                                         |
| Reasoning gate logic (P1–P4 autonomous)       | `claude-code/commands/auto-orchestrate.md` § "Reasoning Gate Logic"                                 |
| Meta-reasoner (DSVSR loop)                     | `claude-code/skills/meta-reasoner/SKILL.md`                                                          |
| Meeting completeness                           | `claude-code/_shared/protocols/meeting-enforcement.md`                                               |
| Domain phase activation rules                  | `claude-code/_shared/protocols/agent-activation.md`                                                  |
| Handover schema                                | `claude-code/_shared/protocols/command-dispatch.md`                                                  |
| Cross-pipeline state                           | `claude-code/_shared/protocols/cross-pipeline-state.md`                                              |
| Engineering Standards (full text)              | `claude-code/_shared/protocols/engineering-standards.md`                                             |
| Output schemas / envelope                      | `claude-code/_shared/protocols/output-schemas.md` + `claude-code/lib/artifact_envelope/schemas.py` |
| Artifact contract (100 rules)                  | `claude-code/templates/orchestrate-session/manifest.yml`                                             |
| Completeness validator                         | `claude-code/templates/orchestrate-session/check-completeness.py`                                    |
| Templates README                               | `claude-code/templates/orchestrate-session/README.md`                                                |
| Install script                                 | `install.sh`                                                                                         |
| Uninstall script                               | `uninstall.sh`                                                                                       |
| Process catalog (P-001..P-093)                 | `claude-code/processes/process_injection_map.md`                                                     |
| Migration script                               | `claude-code/scripts/migrate_to_unified_orchestrate.py`                                              |

---
