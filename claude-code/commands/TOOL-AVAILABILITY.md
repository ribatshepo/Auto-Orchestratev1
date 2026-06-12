# Tool Availability Reference

> **Canonical source:** `_shared/references/TOOL-AVAILABILITY.md` holds the full
> tool-availability matrix, the **GAP-CRIT-001** Task-tool caveat, the file-based
> task-proposal workaround, and agent-design implications. This file covers only
> the command-vs-subagent execution-context summary below; read the canonical
> file for anything beyond it. (`agents/TOOL-AVAILABILITY.md` is a redirect to the
> same canonical source.)

## Command Execution Context (Primary Session)

Commands (`auto-orchestrate`, `auto-debug`, `auto-audit`) run in the primary Claude Code session.

| Tool | Available | Notes |
|------|-----------|-------|
| TaskCreate | YES (assumed) | Used for parent tracking task. Graceful fallback if unavailable. |
| TaskList | YES (assumed) | Used for task state queries. Falls back to checkpoint file. |
| TaskUpdate | YES (assumed) | Used for status updates. Falls back to checkpoint file. |
| TaskGet | YES (assumed) | Used for individual task queries. Falls back to checkpoint file. |
| Agent | YES | Primary spawning mechanism for subagents. |
| Read/Write/Edit/Bash/Glob/Grep | YES | Standard file and shell tools. |
| EnterPlanMode | Available but PROHIBITED | All three commands forbid plan mode. |

## Subagent Context

Agents spawned via `Agent()` have a restricted tool set.

| Tool | Available | Notes |
|------|-----------|-------|
| TaskCreate/TaskList/TaskUpdate/TaskGet | NO | Subagents use `proposed-tasks.json` and PROPOSED_ACTIONS instead. |
| Agent | YES | Subagents may spawn further subagents (e.g., orchestrator spawns researcher). |
| Read/Write/Edit/Bash/Glob/Grep | YES | Per agent definition `tools:` field. |
