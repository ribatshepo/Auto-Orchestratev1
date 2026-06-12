# Stage 5 — Validation Report

> Produced by: validator
> Session: {{sid}}
> Produced at: {{produced_at}}

## Verdict

**{{verdict}}** — aggregate confidence {{confidence}}

## Multi-agent sync

| Agent | Verdict | Confidence | Note |
|-------|---------|-----------|------|
| qa-engineer | {{v}} | {{c}} | {{n}} |
| validator | {{v}} | {{c}} | {{n}} |
| security-engineer | {{v}} | {{c}} | {{n}} |
| auditor | {{v}} | {{c}} | {{n}} |

## Sub-questions

- **S1 spec compliance** — {{score}} / {{evidence}}
- **S2 user journeys** — {{score}} / {{evidence}}
- **S3 ENG-STD-001** — {{score}} / {{evidence}}
- **S4 docker validator** — {{score}} / {{evidence}}
- **S5 security** — {{score}} / {{evidence}}
- **S6 release flag** — {{score}} / {{evidence}}

## Test summary

{{test_summary}}

## Spec compliance

{{spec_compliance_summary}}

## Security findings

{{security_findings}}
