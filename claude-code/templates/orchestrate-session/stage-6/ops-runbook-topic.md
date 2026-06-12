# {{topic_title}} — Ops Runbook

> Produced by: technical-writer
> Session: {{sid}}
> Produced at: {{produced_at}}
> Category: ops-runbook

> NOTE: If this subsystem has no operational surface (purely internal library),
> the orchestrator MUST still produce a document in this folder. Name it
> `no-ops-impact.md` and explain why no runbook applies (e.g. "library only;
> hosted in caller process; no daemon, queue, or external surface").

## Service overview

{{service_overview}}

## Alerts

| Alert | SLO it protects | First responder | Runbook step |
|-------|----------------|-----------------|--------------|
| {{alert}} | {{slo}} | {{role}} | §{{section}} |

## Troubleshooting

### Symptom — {{symptom}}

- Likely cause: {{cause}}
- Diagnostic command: `{{cmd}}`
- Resolution: {{resolution}}

## Escalation

{{escalation_chain}}
