# SMFAA Project Plan

## 1. Project Title

**SMFAA – Sunhaven MFA Fatigue Attack Analyzer**

---

## 2. Project Problem

Sunhaven Care uses MFA to strengthen workforce authentication.

MFA can still be abused when a user receives many repeated prompts and eventually approves one.

One failed MFA event is not enough to identify this behaviour. The important evidence is the **timing, number and order of related MFA events**.

### Problem Statement

> **Sunhaven needs a focused way to detect suspicious MFA-fatigue behaviour without replacing its existing MFA, IAM or general security-monitoring controls.**

---

## 3. Proposed Solution

SMFAA will be a small operational detection service for the Sunhaven laboratory.

It will:

- receive MFA events;
- validate and order them;
- keep a short event history for each user;
- detect three MFA-fatigue patterns;
- create an explainable finding;
- store/export findings for review.

The three detectors are:

1. **Prompt Burst**
2. **Repeated Denial**
3. **Denial-to-Success**

SMFAA does not automatically change an account or access decision.

---

## 4. Where It Fits in the Main Project

The main Sunhaven project already manages:

- Microsoft Entra and MFA;
- RBAC;
- Joiner-Mover-Leaver processes;
- the Flask care portal;
- access review;
- broader security monitoring.

SMFAA sits after MFA authentication events are produced.

Its responsibility is only to identify MFA-fatigue patterns and produce a structured finding.

This supports the project's authentication-security and testing goals without duplicating the main IAM system.

---

## 5. Scope

### In Scope

- MFA-event ingestion;
- validation and timestamp ordering;
- grouping by user;
- rolling time windows;
- prompt-burst detection;
- repeated-denial detection;
- denial-to-success detection;
- configurable thresholds;
- finding severity and explanation;
- local finding storage;
- console, CSV and JSON output;
- automated tests.

### Out of Scope

- general security monitoring;
- dashboards;
- portal/JML/account/role anomaly monitoring;
- MFA or Conditional Access configuration;
- provisioning/de-provisioning;
- RBAC/access review;
- device/network decisions;
- shared-session monitoring;
- automatic remediation.

---

## 6. Team Boundary

### Rifat

Rifat owns core IAM, JML, compliance/access review and broader security monitoring.

SMFAA only handles the three defined MFA-fatigue patterns.

### Prothom

SMFAA does not build web or audit-presentation interfaces.

### Adnan


### SITAS

SITAS models possible attack paths.

SMFAA detects suspicious MFA behaviour from received events.

---

## 7. Operational Behaviour

SMFAA will run locally during testing and demonstration.

Initial event fields:

```text
event_id
user_id
timestamp
event_type
```

Example event types:

```text
MFA_PROMPT
MFA_DENIED
MFA_SUCCESS
```

Example finding:

```text
Finding: Denial-to-Success
User: SC1006
Severity: High
Reason: Repeated MFA denials were followed by a successful approval inside the configured time window.
```

A finding shows suspicious behaviour. It does not prove that a real attack occurred.

---

## 8. Development Plan

### Phase 1 – Event Model

- define event fields;
- define supported event types;
- define thresholds/time windows;
- prepare synthetic events.

### Phase 2 – Core Processing

- event ingestion;
- validation;
- timestamp ordering;
- per-user rolling history.

### Phase 3 – Detection

- prompt burst;
- repeated denial;
- denial-to-success;
- finding severity and explanation.

### Phase 4 – Testing

- normal cases;
- suspicious cases;
- threshold boundaries;
- invalid data;
- regression tests.

### Phase 5 – Output and Evidence

- local finding storage;
- console output;
- CSV/JSON export;
- screenshots;
- repeatable demo steps.

---

## 9. Security and Privacy

SMFAA will use fictional or sanitised authentication metadata.

It will not require or store:

- passwords;
- MFA codes;
- access/refresh tokens;
- client secrets;
- resident records;
- real employee information.

---

## 10. Success Criteria

SMFAA is complete when:

- it receives MFA events while running;
- events are validated and correlated correctly;
- normal activity stays below detection;
- all three rules work at configured thresholds;
- below-threshold cases do not trigger;
- each finding explains its rule and supporting events;
- findings can be stored/exported;
- automated tests pass;
- no IAM state is changed;
- the implementation stays separate from Rifat's broad monitoring and remediation work.

---

## 11. Current Status

Completed:

- problem definition;
- narrow scope;
- project/team boundary;
- initial requirements;
- operational service concept.

Not yet implemented:

- event ingestion;
- event schema/configuration;
- correlation engine;
- detectors;
- finding storage;
- automated tests;
- final evidence.

The next step is to define the event schema and build the first working prototype.
