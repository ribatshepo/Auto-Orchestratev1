# Orchestrate-Session Artifact Templates

This directory is the **deterministic artifact contract** for every `auto-orchestrate` session. It guarantees that every run produces the same file tree under `.orchestrate/<session-id>/` so that downstream tools, audits, and the completeness checker can rely on a fixed shape.

## How to use

1. `manifest.yml` is the single source of truth. It lists every required path and the template that seeds it.
2. The orchestrator (and every spawned agent) **copies the matching template, fills the `{{placeholder}}` tokens, and writes to the canonical path** under `.orchestrate/<sid>/`. Templates are never executed in-place — they are scaffolds.
3. `check-completeness.py` reads `manifest.yml` and verifies the session folder against it. The orchestrate command calls this as Step 7 before closing the session.
4. Placeholders inside template files use `{{name}}` syntax. Common tokens:
   - `{{sid}}` — session id
   - `{{produced_at}}` — ISO-8601 UTC timestamp
   - `{{produced_by}}` — emitting agent
   - `{{deliverable}}` / `{{task}}` / `{{stage}}` — entity identifiers
   - `{{gate}}` / `{{verdict}}` / `{{confidence}}` — gate metadata

## Envelope

Every JSON artifact carries the envelope (`schema_version`, `artifact_type`, `session_id`, `produced_at`, `produced_by`) defined in `schemas/_envelope.schema.json`. Per-artifact schemas extend the envelope and declare type-specific fields.

## Empty-folder policy

Every folder under `.orchestrate/<sid>/` always contains at least one real artifact:
- `domain-reviews/` — orchestrator spawns at minimum one baseline review per applicable stage (qa-engineer if no activation rule fires).
- `phase-receipts/` — orchestrator emits one stage-boundary receipt per stage close.
- `stage-4/` — orchestrator always writes `stage-receipt.json` + `changes.md`; when no test-only tasks exist the receipt records that explicitly.
- `stage-6/` — technical-writer fans out to all 6 categories every run; N/A categories produce a canonical N/A doc.

## Files in this directory

```
manifest.yml                         the contract
check-completeness.py                validator
schemas/                             JSON-schema for each typed artifact
session/                             root-level template files
planning/                            P1-P4 + sprint kickoff templates
stage-0/ ... stage-6/                per-stage templates
gates/                               gate templates
handovers/                           handover templates
meetings/                            sync minutes + ceremony templates
domain-reviews/                      per-stage domain review template
phase-receipts/                      phase receipt template
reasoning-traces/                    DSVCRR trace template
```
