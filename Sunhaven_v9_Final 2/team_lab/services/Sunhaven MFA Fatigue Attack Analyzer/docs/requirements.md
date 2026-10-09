# SMFAA Requirements

## Functional Requirements

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
| SMFAA-FR-15 | Read live Microsoft Entra sign-in records through Microsoft Graph. | Implemented |
| SMFAA-FR-16 | Map live Entra identities to Sunhaven employee identities before detection. | Implemented |
| SMFAA-FR-17 | Keep live Microsoft Graph access read-only. | Implemented by design |

## Event Model

SMFAA uses the following normalized event model:

```text
event_id
employee_id
timestamp
event_type
```

Supported MFA event types are:

```text
MFA_PROMPT
MFA_DENIED
MFA_SUCCESS
```

The same normalized model is used by the controlled demo data, exported Entra evidence and live Microsoft Graph integration.

## Detection Defaults

| Rule | Default |
|---|---|
| Prompt Burst | 5 prompts in 2 minutes |
| Repeated Denial | 3 denials in 5 minutes |
| Denial-to-Success | 3 denials followed by success within 10 minutes |

## Live Microsoft Entra Requirements

The live integration must:

- retrieve Microsoft Entra sign-in records through Microsoft Graph;
- use delegated, read-only `AuditLog.Read.All` permission;
- use the existing normalized SMFAA event model;
- map relevant Entra identities to Sunhaven employee identities;
- pass normalized events to the existing detector;
- avoid modifying users, MFA configuration, roles or sessions; and
- avoid storing access tokens, device codes or client secrets in the repository.

The live connector is implemented in:

```text
src/entra_graph_adapter.py
```

The live source is executed through:

```text
python src\smfaa.py --source live-entra --repo-root "<Sunhaven repository path>"
```

## Security Requirements

- read-only monitoring;
- no passwords, MFA codes, access tokens, refresh tokens or client secrets stored;
- no automatic blocking or remediation;
- malformed events fail clearly;
- findings explain why a rule triggered;
- findings are suspicious-pattern evidence, not proof of an attacker;
- workforce data is never modified by SMFAA;
- Microsoft Graph access is limited to the permissions required for sign-in log analysis.

## Acceptance Criteria

The SMFAA implementation is accepted when:

- the three detection rules operate at their configured boundaries using controlled test data;
- workers are kept separate during event correlation;
- findings are explainable and include supporting event information;
- console, JSON and CSV output can be generated;
- existing Sunhaven exported Entra evidence can be read;
- live Microsoft Entra sign-in records can be retrieved through Microsoft Graph;
- relevant live events can be normalized and mapped to a Sunhaven employee;
- live Repeated Denial detection can produce a finding from controlled Entra MFA activity;
- automated tests pass without modifying IAM or application state; and
- SMFAA remains a read-only detection component.

## Current Live Validation Limitation

Live Microsoft Graph testing successfully validated the retrieval and normalization of Entra sign-in events and the Repeated Denial scenario.

During testing, successful sign-in records returned `authenticationRequirement=None` and `authenticationDetails=None` in the Graph response used by the current adapter.

SMFAA intentionally does not classify every successful `errorCode 0` sign-in as `MFA_SUCCESS`, because a successful sign-in does not necessarily prove that MFA was successfully approved.

Therefore, the Denial-to-Success rule is implemented and can be validated using the controlled demo dataset, while live Denial-to-Success validation currently depends on the MFA information available from Microsoft Graph.
