# SMFAA Requirements

## 1. Purpose

These requirements define the r the **Sunhaven MFA Fatigue Attack Analyzer (SMFAA)**.

SMFAA is an operational detection service in the Sunhaven laboratory. It runs alongside the core IAM and Flask application but does not modify IAM state.

---

## 2. Functional Requirements

| ID | Requirement |
|---|---|
| SMFAA-FR-01 | Receive controlled Entra-style MFA authentication events. |
| SMFAA-FR-02 | Validate the required event fields: `event_id`, `employee_id`, `timestamp` and `event_type`. |
| SMFAA-FR-03 | Accept only the supported MVP event types: `MFA_PROMPT`, `MFA_DENIED` and `MFA_SUCCESS`. |
| SMFAA-FR-04 | Parse, validate and order event timestamps before correlation. |
| SMFAA-FR-05 | Group events by fictional Sunhaven `employee_id`. |
| SMFAA-FR-06 | Maintain a rolling event window for each employee. |
| SMFAA-FR-07 | Detect a prompt burst when the configured prompt threshold is reached inside its time window. |
| SMFAA-FR-08 | Detect repeated MFA denials when the configured denial threshold is reached inside its time window. |
| SMFAA-FR-09 | Detect repeated denials followed by an MFA success inside the configured time window. |
| SMFAA-FR-10 | Keep normal and below-threshold activity from creating an MFA-fatigue finding. |
| SMFAA-FR-11 | Create an explainable finding containing the matched rule, time window, severity, reason and supporting event references. |
| SMFAA-FR-12 | Export findings through console, JSON and CSV output. |
| SMFAA-FR-13 | Read the Sunhaven workforce source in read-only mode to validate or enrich fictional employee context. |
| SMFAA-FR-14 | Run independently alongside the Sunhaven Flask application without being required for portal access. |
| SMFAA-FR-15 | Process events for multiple Sunhaven workers without mixing their rolling windows. |

---

## 3. Initial Event Schema

```text
event_id
employee_id
timestamp
event_type
```

Example:

```json
{
  "event_id": "MFA-0001",
  "employee_id": "SC1001",
  "timestamp": "2026-09-21T10:01:00Z",
  "event_type": "MFA_DENIED"
}
```

Supported event types:

```text
MFA_PROMPT
MFA_DENIED
MFA_SUCCESS
```

---

## 4. Initial Detection Configuration

The MVP will use configurable defaults rather than hard-coding thresholds in detector logic.

| Rule | Initial default |
|---|---|
| Prompt Burst | 5 prompts in 2 minutes |
| Repeated Denial | 3 denials in 5 minutes |
| Denial-to-Success | 3 denials followed by success within 10 minutes |

The final values may be adjusted during testing, but the detector interface must remain configurable.

---

## 5. Security Requirements

| ID | Requirement |
|---|---|
| SMFAA-SR-01 | SMFAA shall not change users, MFA, roles, sessions, JML state or Flask access decisions. |
| SMFAA-SR-02 | Development and demonstration data shall use fictional or sanitised authentication metadata. |
| SMFAA-SR-03 | Passwords, MFA codes, access tokens, refresh tokens and client secrets shall not be stored. |
| SMFAA-SR-04 | Invalid or malformed event data shall fail clearly and shall not silently create a finding. |
| SMFAA-SR-05 | Findings shall explain why a rule triggered. |
| SMFAA-SR-06 | Findings shall not automatically block, revoke or remediate access. |
| SMFAA-SR-07 | A finding shall be described as suspicious MFA behaviour, not proof of a real attacker. |
| SMFAA-SR-08 | Sunhaven workforce data shall be read-only from SMFAA. |
| SMFAA-SR-09 | SMFAA shall remain outside the core authentication decision path so its failure does not prevent normal portal operation. |

---

## 6. Non-Functional Requirements

| ID | Requirement |
|---|---|
| SMFAA-NFR-01 | The same event set and configuration shall produce the same result. |
| SMFAA-NFR-02 | Thresholds and time windows shall be configurable. |
| SMFAA-NFR-03 | Event loading, validation, processing, detection and reporting shall remain modular. |
| SMFAA-NFR-04 | Core behaviour shall be covered by automated tests. |
| SMFAA-NFR-05 | Rules and findings shall be easy to explain during demonstration. |
| SMFAA-NFR-06 | SMFAA shall remain separate from the team's general monitoring and IAM controls. |
| SMFAA-NFR-07 | SMFAA shall be able to run locally at the same time as the Sunhaven Flask application. |
| SMFAA-NFR-08 | Repository structure and documentation shall clearly identify SMFAA as an individual component of the Sunhaven project. |

---

## 7. Acceptance Criteria

The MVP is complete when:

- Entra-style MFA events can be loaded or received and validated;
- event timestamps are ordered correctly;
- events are grouped by `employee_id`;
- separate workers do not share detection windows;
- all three detectors work at their configured thresholds;
- normal and below-threshold behaviour does not create an unnecessary finding;
- findings explain the matched rule and supporting events;
- findings can be exported to console, JSON and CSV;
- the Sunhaven workforce source can be read safely in read-only mode;
- SMFAA can run at the same time as the core Flask application;
- automated tests pass;
- no IAM or application state is changed.

---

## 8. Explicit Exclusions

The MVP does not include:

```text
general security monitoring
security dashboard or live alert dashboard
portal access-denied detection
blocked-user detection
expired-account detection
JML failure detection
role/admin-assignment monitoring
MFA configuration
Conditional Access configuration
RBAC or access review
device/network trust decisions
shared-session monitoring
agency federation or B2B onboarding
automatic remediation
```
