# Extending the Auto-Orchestrate Workflow

**Date:** 2026-06-13
**Scope:** how to extend the pipeline by (1) adding **skills**, (2) **aligning skills to agents** in the manifest, and (3) adding **agents**.
**Related:** `CONTRIBUTING.md` §3/§4, `claude-code/INTEGRATION.md` §9, and `claude-code/skills/skill-creator/SKILL.md`. This document unifies that scattered guidance into one checklist-driven reference and calls out the verification steps and current gaps.

---

## 1. The extension model

The workflow is a **registry-driven** system. Three things must agree for an extension to work:

1. **On-disk file** — a `skills/<name>/SKILL.md` directory or an `agents/<name>.md` file.
2. **`manifest.json` entry** — `claude-code/manifest.json` (schema `1.0.0`) is the authoritative registry. Top-level arrays: `agents[]`, `skills[]`, `commands[]`, `processes[]`, plus `shared{}` and `stats{}`.
3. **Install** — `./install.sh` copies the dev tree into `~/.claude/`; `./install.sh --check` SHA256-verifies the installed copy against source (drift detection, read-only).

### Routing is digest-driven

Most subagents never see the full ~19K manifest. `claude-code/skills/_shared/python/layer1/manifest_digest.py` builds a ~2.6K digest containing **only `name` + `dispatch_triggers`** for every agent and skill (`MANIFEST-DIGEST-001`). That makes those two fields **load-bearing for routing** — everything else (`description`, `model`, `tools`, `capabilities`, `chaining`, `path`) is metadata used elsewhere.

Exceptions get the full manifest (`needs_full_manifest()`, `manifest_digest.py:108`):

```python
if agent_name in ("orchestrator", "session-manager"):
    return True
if task and task.get("needs_full_manifest") is True:
    return True
```

> **Implication:** if a new agent needs to read `chaining`, `capabilities`, or other agents' full entries at runtime, either add it to that allowlist or set `needs_full_manifest: true` on its task. Otherwise the slim digest is enough.

---

## 2. Adding a new skill

**On-disk layout** (`claude-code/skills/<name>/`):

```
skills/<name>/
├── SKILL.md          # required: YAML frontmatter + body
├── scripts/          # optional: *.py invoked by the skill
└── references/       # optional: docs loaded on demand
```

**Steps:**

1. **Scaffold** — `python3 skills/skill-creator/scripts/init_skill.py <name> --path skills/` (or copy `_shared/templates/skill-boilerplate.md`).
2. **Write `SKILL.md` frontmatter.** Put *what it does AND when to use it* in `description` — under `SKILL-FRONTMATTER-001`, discovery loads only the frontmatter (~300 tok), so trigger context must live there:

   ```yaml
   ---
   name: my-skill
   description: >
     One-paragraph statement of what the skill does and when to use it.
     Use when the user says "...", "...".
   triggers:
     - trigger phrase 1
     - trigger phrase 2
   ---
   ```

3. **Register in `manifest.json`** under `skills[]` (note `dispatch_triggers`, not `triggers`, is the manifest field name):

   ```json
   {
     "name": "my-skill",
     "description": "One-sentence description.",
     "dispatch_triggers": ["trigger phrase 1", "trigger phrase 2"],
     "has_scripts": false,
     "has_references": false,
     "path": "skills/my-skill/SKILL.md",
     "chaining": {
       "produces": ["my-artifact"],
       "consumes_from": ["upstream-skill"],
       "chains_to": ["downstream-skill"],
       "chains_from": ["upstream-skill"],
       "patterns": ["producer", "sequential-pipeline"]
     }
   }
   ```

   `chaining` is optional but recommended for any skill that participates in a pipeline.

4. **Bump `stats.total_skills`** by one.
5. **Validate** — `python3 skills/skill-creator/scripts/quick_validate.py skills/my-skill/` and `python3 skills/_shared/python/validate_manifest.py manifest.json`.
6. **Install** — `./install.sh`, then `./install.sh --check` to confirm no drift.

Representative skills to copy from: `skills/spec-compliance/` (scripts + references + chaining), `skills/accessibility-check/` (SKILL.md only).

---

## 3. Aligning skills to agents (in the manifest)

The skill→agent link is a **field on the agent**, `skills_orchestrated[]` — unidirectional (the agent declares which skills it may invoke; the skill needs no back-reference). To wire a skill to an agent:

1. **Add the skill `name`** to the agent's `skills_orchestrated` array in `manifest.json`:

   ```json
   {
     "name": "auditor",
     "...": "...",
     "skills_orchestrated": ["spec-compliance"]
   }
   ```

   The string must match a skill's `name` exactly.

2. **Mirror it in the agent body.** Agent `.md` files carry a **"Mandatory Skills"** table that documents the invocation. Keep this table and `skills_orchestrated` in sync — the manifest field is what tooling reads; the table is what the agent reads at spawn.

3. **Use `chaining` for ordering.** If skill A's output feeds skill B, set A's `chains_to` and B's `chains_from`/`consumes_from`. This expresses pipeline order independent of which agent invokes them.

**Worked example — `auditor` ↔ `spec-compliance`:** the `auditor` agent declares `skills_orchestrated: ["spec-compliance"]`; the `spec-compliance` skill declares `chaining.chains_to: ["validator", "orchestrator"]` so its `gap-report` flows downstream. A skill is **never** marked exclusive to one agent — multiple agents may list the same skill.

---

## 4. Adding a new agent

Agents are **flat Markdown files** in `claude-code/agents/<name>.md` (no per-agent directory). There is currently **no scaffolder** (see §6) — copy an existing agent such as `agents/auditor.md` or `agents/software-engineer.md`.

**Steps:**

1. **Create `agents/<name>.md`** with frontmatter + body:

   ```yaml
   ---
   name: my-agent
   description: One- to three-line purpose statement.
   tools: Read, Write, Edit, Bash, Glob, Grep
   model: sonnet   # one of: sonnet | opus | haiku
   triggers:
     - keyword phrase
   ---
   ```

   Body must include, in order: the **preamble** (PREAMBLE-001..004 — read `continuity-brief.md` first), an **IMMUTABLE constraints** table (e.g. `MY-001`, `MY-002`), an optional **Mandatory Skills** table, the **workflow** steps, **process ownership**, and the **artifact emission contract** (what it produces and where).

2. **Register in `manifest.json`** under `agents[]`:

   ```json
   {
     "name": "my-agent",
     "description": "What the agent does and when it is spawned.",
     "model": "sonnet",
     "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
     "dispatch_triggers": ["keyword phrase", "another trigger"],
     "skills_orchestrated": ["some-skill"],
     "capabilities": { "produces": ["my-output.json"], "phases": ["3"] },
     "path": "agents/my-agent.md"
   }
   ```

   `model` is validated against `sonnet|opus|haiku`. `skills_orchestrated`, `activation_rules`, and `capabilities` are optional.

3. **Bump `stats.total_agents`** by one.
4. **Decide manifest eligibility** — if the agent only routes/executes work, the slim digest is sufficient; if it must read other entries' full metadata at runtime, add it to the `needs_full_manifest()` allowlist (`manifest_digest.py:108`) or set `needs_full_manifest: true` on its tasks.
5. **Document it** — if it's a *critical* agent (required for `/auto-orchestrate` to run), add it to `ARCHITECTURE.md` §9.2 component inventory.
6. **Validate & install** — `validate_manifest.py manifest.json`, then `./install.sh` and `./install.sh --check`.

---

## 5. Validation & verification checklist

| Step | Command | Checks |
|---|---|---|
| Skill folder | `quick_validate.py skills/<name>/` | frontmatter, naming, structure, description quality |
| Manifest schema | `validate_manifest.py manifest.json` | required fields, types, `model` enum, date/version patterns |
| Deploy | `./install.sh` | copies dev tree → `~/.claude/` |
| Drift | `./install.sh --check` | SHA256 installed vs. source (read-only) |

**Manual cross-reference checklist** (the schema validator does *not* yet enforce these — see §6):

- [ ] Every name in any agent's `skills_orchestrated` exists in `skills[]`.
- [ ] Every `path` resolves to a real file on disk (`agents/<name>.md`, `skills/<name>/SKILL.md`).
- [ ] New `dispatch_triggers` don't collide with existing triggers (collisions cause misrouting).
- [ ] `stats.total_skills` / `stats.total_agents` match the actual array lengths.
- [ ] Every `chaining.chains_to` / `chains_from` / `consumes_from` names a real skill.
- [ ] Frontmatter `triggers` and the manifest `dispatch_triggers` for the same component agree.

---

## 6. Known gaps & hardening recommendations

The mechanism above makes extension *possible*; these are the gaps that keep it from being *safe* by default. Each is a recommended follow-up, not implemented here:

1. **No cross-referential integrity in `validate_manifest.py`.** It checks schema/types/enums only. It will happily accept an agent that orchestrates a non-existent skill, a `path` to a missing file, duplicate `dispatch_triggers`, or `stats` counts that drift from reality. **Recommendation:** extend `skills/_shared/python/validate_manifest.py` with a cross-reference pass (the six manual checks in §5), so a single `validate_manifest.py` run fails fast on a broken extension.

2. **Frontmatter `triggers` vs. manifest `dispatch_triggers` drift.** The two sources of truth are maintained by hand and can diverge; the digest builder silently falls back between them, masking the drift. **Recommendation:** add a validator check that the on-disk frontmatter and the manifest entry for each component agree on name and triggers.

3. **No agent scaffolder.** Skills have `init_skill.py`; agents are hand-written, which invites missing preamble/constraint sections and manifest entries. **Recommendation:** add an `init_agent.py` (mirroring `skills/skill-creator/scripts/init_skill.py`) that generates `agents/<name>.md` from a template *and* appends a stub `agents[]` manifest entry with `stats` bumped — making "add an agent" as turnkey as "add a skill."

Implementing #1 first yields the most leverage: it turns every future skill/agent addition into a self-checking operation.
