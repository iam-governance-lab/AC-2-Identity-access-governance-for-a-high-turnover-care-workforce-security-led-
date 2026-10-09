# SMFAA Scope Boundary

## 1. Locked Scope

> **SMFAA is a small operational Sunhaven service that receives MFA authentication events and detects only three MFA-fatigue patterns: prompt bursts, repeated denials and denial-to-success.**

It creates explainable findings but does not change IAM or application state.

---

## 2. Position in the Sunhaven Project

SMFAA is part of the Sunhaven solution but remains a separate service from the Flask portal.

Recommended location:

```text
Sunhaven-main/
├── app/                  # Core Flask portal
├── automation/           # Core JML / Graph automation
├── config/
├── data/
└── services/
    └── smfaa/            # Operational MFA-fatigue detector
```

The runtime relationship is:

```text
Microsoft Entra ID + MFA
        |                 \
        | OIDC             \ MFA / sign-in events
        v                   v
Sunhaven Flask Portal      SMFAA
                            |
                            v
                      MFA finding
```

SMFAA is not placed between Entra and Flask and must not become a dependency for normal portal access.

---

## 3. SMFAA Owns

- MFA-event ingestion;
- event validation;
- timestamp ordering;
- grouping by Sunhaven `employee_id`;
- rolling time-window correlation;
- prompt-burst detection;
- repeated-denial detection;
- denial-to-success detection;
- threshold and boundary behaviour;
- finding severity and explanation;
- read-only Sunhaven workforce lookup;
- local finding storage;
- console/JSON/CSV output;
- automated tests;
- side-by-side integrated demonstration with the core system.



---

## 4. Data Boundary

The MVP only needs simple MFA event metadata:

```text
event_id
employee_id
timestamp
event_type
```

SMFAA may also read safe fictional Sunhaven worker context from the existing `data/workforce.csv` file.

Development and demonstration data is fictional or sanitised.

SMFAA does not require:

- passwords;
- MFA codes;
- access/refresh tokens;
- client secrets;
- resident records;
- real employee information.

---

## 5. Output Boundary

A finding may contain:

```text
finding_id
employee_id
rule_id
finding_type
window_start
window_end
event_count
supporting_event_ids
severity
reason
```

Optional safe Sunhaven context may include:

```text
job_role
facility
```

The finding is for review/evidence only.

SMFAA does not automatically:

- disable a user;
- revoke a session;
- change MFA;
- change roles;
- execute JML;
- modify Flask access;
- perform remediation.

---

## 6. Scope Check

A feature belongs in SMFAA only if it directly supports:

- MFA-event handling;
- one of the three MFA-fatigue detectors;
- Sunhaven worker correlation;
- validation;
- automated testing;
- finding explanation or export.

Anything broader stays outside SMFAA unless the team formally changes the project scope.
