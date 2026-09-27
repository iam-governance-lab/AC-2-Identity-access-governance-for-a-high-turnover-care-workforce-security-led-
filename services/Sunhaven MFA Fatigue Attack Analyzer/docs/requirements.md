# SMFAA Requirements

## Functional requirements

| ID | Requirement | Status |
|---|---|---|
| SMFAA-FR-01 | Receive controlled or exported Entra-style MFA events. | Implemented |
| SMFAA-FR-02 | Validate `event_id`, `employee_id`, `timestamp`, `event_type`. | Implemented |
| SMFAA-FR-03 | Support `MFA_PROMPT`, `MFA_DENIED`, `MFA_SUCCESS`. | Implemented |
| SMFAA-FR-04 | Parse and order timestamps before correlation. | Implemented |
| SMFAA-FR-05 | Keep separate event windows per employee. | Implemented |
| SMFAA-FR-06 | Detect Prompt Burst. | Implemented |
| SMFAA-FR-07 | Detect Repeated Denial. | Implemented |
| SMFAA-FR-08 | Detect Denial-to-Success. | Implemented |
| SMFAA-FR-09 | Avoid findings for normal/below-threshold activity. | Implemented |
| SMFAA-FR-10 | Produce explainable findings with supporting event IDs. | Implemented |
| SMFAA-FR-11 | Export console, JSON and CSV evidence. | Implemented |
| SMFAA-FR-12 | Read Sunhaven workforce context in read-only mode. | Implemented |
| SMFAA-FR-13 | Run separately from Flask and not become an access dependency. | Implemented by design |
| SMFAA-FR-14 | Read the existing sanitised Entra export from the repository. | Implemented |
| SMFAA-FR-15 | Read live Entra sign-in events. | Later manual integration |

## Event model

```text
event_id
employee_id
timestamp
event_type
```

## Detection defaults

| Rule | Default |
|---|---|
| Prompt Burst | 5 prompts in 2 minutes |
| Repeated Denial | 3 denials in 5 minutes |
| Denial-to-Success | 3 denials followed by success within 10 minutes |

## Security requirements

- read-only monitoring;
- no passwords, MFA codes, access tokens, refresh tokens or client secrets stored;
- no automatic blocking or remediation;
- malformed events fail clearly;
- findings explain why a rule triggered;
- findings are suspicious-pattern evidence, not proof of an attacker;
- workforce data is never modified by SMFAA.

## Acceptance criteria

The local/exported-event implementation is accepted when all three rules work at their configured boundaries, workers are kept separate, findings are explainable, output is generated, existing Sunhaven evidence can be read, and automated tests pass without modifying IAM/application state.
