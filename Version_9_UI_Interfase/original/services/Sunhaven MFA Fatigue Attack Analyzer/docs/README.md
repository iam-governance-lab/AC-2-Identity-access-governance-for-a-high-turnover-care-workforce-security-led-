# SMFAA — Sunhaven MFA Fatigue Attack Analyzer

## Project Summary

**SMFAA** is a small operational MFA-fatigue detection service for the fictional **Sunhaven Care Workforce IAM** project.

The Sunhaven core system already provides Microsoft Entra ID authentication, MFA, Joiner-Mover-Leaver (JML) automation, RBAC and the Flask care portal. SMFAA does not replace those controls.

SMFAA has one narrow job:

> **Receive Sunhaven MFA authentication events, detect suspicious MFA-fatigue patterns and create explainable findings for review.**

SMFAA is designed to run **alongside** the Sunhaven Flask portal as a separate service inside the same project repository.

---

## 1. Problem

MFA improves account security, but repeated MFA prompts can still be abused through MFA fatigue or push bombing.

For example:

```text
10:00 MFA_DENIED
10:01 MFA_DENIED
10:02 MFA_DENIED
10:03 MFA_SUCCESS
```

A sequence of repeated denials followed by a success can be more suspicious than one isolated denial.

The project problem is:

> **How can Sunhaven detect suspicious MFA-fatigue behaviour from the timing and order of MFA authentication events without changing the existing IAM controls?**

---

## 2. Where SMFAA Fits in Sunhaven

SMFAA sits beside the core Flask application and consumes MFA/sign-in events from the authentication layer.



The important boundary is:

- **Entra ID** authenticates users and performs MFA.
- **Flask** enforces application access after authentication.
- **SMFAA** observes MFA-event sequences and creates findings.

SMFAA is not placed in the login path, so the core application can continue working even if SMFAA is stopped.


---

## 3. SMFAA Solution

SMFAA will:

1. receive controlled Entra-style MFA events;
2. validate the required event fields;
3. order events by timestamp;
4. group events by Sunhaven worker;
5. maintain a short rolling event window;
6. run three MFA-fatigue detectors;
7. create an explainable finding when a detector matches;
8. export findings to console, JSON and CSV.

The three detectors are:

1. **Prompt Burst**
2. **Repeated Denial**
3. **Denial-to-Success**

SMFAA findings are for review and evidence only. They do not automatically disable users or change IAM state.

---

## 4. Simple Sunhaven Event Model

Initial events use only the fields needed for detection:

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

Supported MVP event types:

```text
MFA_PROMPT
MFA_DENIED
MFA_SUCCESS
```

Development and demonstration events are synthetic or sanitised.

---

## 5. Sunhaven Worker Context

SMFAA may read the existing Sunhaven workforce source **read-only**:

```text
../../data/workforce.csv
```

A small Sunhaven adapter can use `employee_id` to confirm that an event belongs to a fictional Sunhaven worker and, where useful, add safe context such as role or facility to a finding.

SMFAA must not modify `workforce.csv`, Entra ID, Flask state or JML data.

---

## 6. Detection Rules

Initial configurable defaults for the MVP are:

| Rule | Initial default |
|---|---|
| Prompt Burst | 5 or more `MFA_PROMPT` events within 2 minutes |
| Repeated Denial | 3 or more `MFA_DENIED` events within 5 minutes |
| Denial-to-Success | 3 or more `MFA_DENIED` events followed by `MFA_SUCCESS` within 10 minutes |

These values will live in configuration so they can be tested and changed without rewriting detector logic.

---

## 7. Scope

### In Scope

- MFA-event ingestion;
- event validation;
- timestamp ordering;
- grouping by Sunhaven employee ID;
- rolling time-window correlation;
- prompt-burst detection;
- repeated-denial detection;
- denial-to-success detection;
- configurable thresholds;
- finding severity and explanation;
- read-only Sunhaven workforce lookup;
- local finding storage;
- console, JSON and CSV output;
- automated testing;
- side-by-side testing with the Sunhaven Flask application.

### Out of Scope

- configuring MFA or Conditional Access;
- user provisioning or de-provisioning;
- JML execution;
- RBAC or access-review decisions;
- disabling users;
- revoking sessions;
- changing Flask access decisions;
- general Sunhaven log monitoring;
- broad security dashboards;
- device or network trust decisions;
- automatic remediation.


---

## 8. Initial Scenarios

| ID | Scenario | Expected result |
|---|---|---|
| SMFAA-S01 | Normal MFA success | No finding |
| SMFAA-S02 | One or two isolated denials | No finding |
| SMFAA-S03 | Repeated denials in a short window | Repeated-denial finding |
| SMFAA-S04 | Repeated denials followed by success | Denial-to-success finding |
| SMFAA-S05 | Rapid repeated prompts | Prompt-burst finding |
| SMFAA-S06 | Below/exact threshold | Correct boundary behaviour |
| SMFAA-S07 | Invalid event data | Validation failure |
| SMFAA-S08 | Events for two workers | Each worker analysed separately |
| SMFAA-S09 | Out-of-order timestamps | Events ordered before detection |
| SMFAA-S10 | Unknown Sunhaven employee ID | Clear integration warning or rejection based on test mode |

---

## 9. Current Status

Completed:

- problem definition;
- project scope;
- team boundary;
- initial requirements;
- Sunhaven placement decision (`services/smfaa/`);
- whole-project architecture;
- individual solution design;
- operational workflow;
- initial development plan.

Next implementation stage:

- create the final folder structure;
- define `detection-rules.json`;
- implement event loading and validation;
- implement processing and the three detectors;
- add findings and output;
- add the read-only Sunhaven adapter;
- run unit and integrated tests with the core Sunhaven system.
