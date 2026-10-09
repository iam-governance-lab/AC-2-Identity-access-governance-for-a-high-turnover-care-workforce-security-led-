# SITAS Progress Report 2

## Project

**Project Title:** Sunhaven Identity Threat and Attack-Path Simulator (SITAS)  
**Unit:** COIT13236 Cyber Security Project  
**Individual Contribution:** Threat modelling, attack-path simulation, risk assessment, control evaluation and automated testing

---

## 1. Progress Overview

SITAS has progressed from an early prototype into a working multi-scenario cybersecurity simulator.

The project now uses one common Python analysis engine to load different threat scenarios, build the Sunhaven attack graph, discover an attack path using BFS, calculate risk from a configurable model and evaluate the related security control.

The simulator currently includes:

```text
6 threat scenarios
6 simulated security controls
1 common attack-graph engine
1 BFS pathfinder
1 configurable 5 × 5 risk model
45 passing automated pytest tests
```

All scenarios use the same `sitas.py` program. The Python source code does not need to be rewritten for each scenario.

---

## 2. Why SITAS Is Important for Sunhaven

Sunhaven Care has a workforce environment involving identities, passwords, sessions, shared devices, applications and protected information.

The main security problem is that one identity weakness can lead to another system and eventually create a path to sensitive information.

Examples include:

- stolen nurse credentials;
- unattended active sessions;
- former worker identities;
- excessive privileges;
- privileged administrator compromise;
- access from unmanaged devices.

SITAS helps by turning these risks into visible attack paths.

For each scenario, the simulator shows:

```text
Threat Source
↓
Attack Path
↓
Protected Asset
↓
Likelihood and Impact
↓
Risk Score
↓
Relevant Security Control
↓
OPEN or BLOCKED
```

This is useful to Sunhaven because it demonstrates not only that a security control should exist, but **why the control is useful and what attack path it prevents**.

SITAS remains a simulation and does not make changes to live Microsoft Entra accounts or production systems.

---

## 3. Risk Model Improvement

The risk component was improved from simple hard-coded scoring into a configurable risk model stored in:

```text
config/risk-model.json
```

The model uses:

```text
Risk Score = Likelihood × Impact
```

Likelihood and impact are rated from 1 to 5.

The risk bands are:

```text
1–4   = Low
5–9   = Medium
10–16 = High
17–25 = Critical
```

The simulator also displays readable labels such as:

```text
Likelihood: 4/5 (Likely)
Impact: 5/5 (Severe)
```

The `risk_engine.py` module now validates ratings and reads the severity bands from the JSON risk model instead of relying only on hard-coded values.

---

## 4. Six Implemented Threat Scenarios

### Scenario 1 – Stolen Nurse Credential

```text
External Attacker
↓
Stolen Nurse Password
↓
Nurse Identity
↓
Shared Nurse Workstation
↓
Sunhaven Care Portal
↓
Fictional Resident Records
```

```text
Control: MFA
Risk: 20/25 – Critical
MFA OFF → OPEN
MFA ON  → BLOCKED
```

Evidence:

```text
07-scenario-01-mfa-off-open.png
08-scenario-01-mfa-on-blocked.png
```

### Scenario 2 – Shared Workstation Session Misuse

```text
Unauthorised Person
↓
Unattended Shared Workstation
↓
Active Nurse Session
↓
Sunhaven Care Portal
↓
Fictional Resident Records
```

```text
Control: Session Timeout
Risk: 15/25 – High
Control OFF → OPEN
Control ON  → BLOCKED
```

Evidence:

```text
09-scenario-02-session-off-open.png
10-scenario-02-session-on-blocked.png
```

### Scenario 3 – Former Worker Identity Misuse

```text
Former Worker
↓
Former Worker Identity
↓
Sunhaven Care Portal
↓
Fictional Resident Records
```

```text
Control: Account Disablement
Risk: 12/25 – High
Control OFF → OPEN
Control ON  → BLOCKED
```

Evidence:

```text
11-scenario-03-account-off-open.png
12-scenario-03-account-on-blocked.png
```

### Scenario 4 – Excessive Privilege Abuse

```text
Compromised Care Worker
↓
Care Worker Identity
↓
Over-Privileged Role
↓
Restricted Admin Function
↓
Fictional Resident Records
```

```text
Control: Role-Based Access Control
Risk: 15/25 – High
Control OFF → OPEN
Control ON  → BLOCKED
```

Evidence:

```text
13-scenario-04-rbac-off-open.png
14-scenario-04-rbac-on-blocked.png
```

### Scenario 5 – Privileged Administrator Credential Compromise

```text
External Admin Attacker
↓
Stolen Admin Credential
↓
Privileged Admin Identity
↓
Restricted Admin Console
↓
Fictional Resident Records
```

```text
Control: Privileged Re-authentication
Risk: 10/25 – High
Control OFF → OPEN
Control ON  → BLOCKED
```

Evidence:

```text
15-scenario-05-privauth-off-open.png
16-scenario-05-privauth-on-blocked.png
```

### Scenario 6 – Unmanaged Device Access

```text
External Device Attacker
↓
Stolen Care Worker Credential
↓
Remote Care Worker Identity
↓
Unmanaged Device Session
↓
Sunhaven Care Portal
↓
Fictional Resident Records
```

```text
Control: Trusted Device Restriction
Risk: 12/25 – High
Control OFF → OPEN
Control ON  → BLOCKED
```

Evidence:

```text
17-scenario-06-device-off-open.png
18-scenario-06-device-on-blocked.png
```

---

## 5. Design and Architecture Work

The design documentation was expanded beyond the initial architecture diagram.

The project now includes diagrams covering:

- high-level SITAS architecture;
- attack path and control evaluation;
- module and data dependencies;
- security boundary and independence from operational IAM;
- threat scenario processing workflow.

These diagrams help explain how the JSON configuration, Python modules, graph engine, BFS pathfinder, risk engine and control engine work together.

They also show that SITAS remains separate from live operational IAM administration.

---

## 6. Automated Testing

A major improvement in this progress stage was the implementation of automated testing with `pytest`.

The project now has four main test areas.

### Risk Engine Tests

```text
14 passed
```

These test:

- scenario risk calculations;
- severity boundaries;
- invalid likelihood values;
- invalid impact values;
- non-integer ratings.

### Graph and BFS Tests

```text
9 passed
```

These test:

- graph node creation;
- directed relationships;
- readable node names;
- successful attack-path discovery;
- shortest-path behaviour;
- unreachable targets;
- graph cycles;
- start equals target;
- the real Scenario 6 attack path.

### Control Engine Tests

```text
13 passed
```

These test all six security controls in enabled and disabled states, plus unknown-control handling.

### Model Loader and Configuration Tests

```text
9 passed
```

These test:

- valid environment JSON;
- missing nodes;
- missing relationships;
- invalid JSON;
- missing files;
- the real environment file;
- the real controls file;
- the real risk model;
- all six scenario files.

The complete test suite was then executed together:

```text
45 passed
```

Evidence:

```text
19-pytest-risk-engine.png
20-pytest-graph-bfs.png
21-pytest-control-engine.png
22-pytest-model-loader.png
23-pytest-full-suite-45-passed.png
```

This gives stronger evidence that SITAS behaves consistently and is not only working in manual demonstrations.

---

## 7. Problems Encountered and How They Were Solved

### Scenario 6 Path Collision

During Scenario 6, BFS initially returned the wrong path.

The new unmanaged-device scenario reused the same `care_worker_identity` node as the excessive-privilege scenario. This gave the graph two possible routes to the target, and BFS selected the other valid route.

I corrected this by creating a separate:

```text
Remote Care Worker Identity
```

for the unmanaged-device scenario.

After the change, Scenario 6 produced the intended path through:

```text
Remote Care Worker Identity
→ Unmanaged Device Session
→ Sunhaven Care Portal
```

A pytest case was also added for the real Scenario 6 path so that this problem can be detected automatically if the graph is changed later.

### Pytest Import and Circular Import Problems

While setting up automated tests, pytest initially could not import the modules from the `src` folder.

I added:

```text
pytest.ini
```

with the Python source path configured.

A second issue occurred when `risk_engine.py` accidentally contained an import from itself, causing a circular import.

I corrected the risk-engine file and reran the full test suite successfully.

These problems improved my understanding of Python module paths, test configuration and dependency errors.

---

## 8. Measurable Progress

The project has moved well beyond the first prototype.

Current measurable progress includes:

```text
6/6 planned scenarios implemented
6/6 planned control simulations implemented
12 before/after scenario outcomes demonstrated
45 automated tests passing
5 main architecture/design diagrams
configurable JSON risk model
scenario selection through one common Python program
```

This is a clear improvement from the earlier two-scenario prototype.

---

## 9. Current Value to Sunhaven

SITAS now demonstrates several different identity-related risks instead of focusing on only one type of attack.

It can show the effect of:

- MFA against stolen passwords;
- Session Timeout against unattended sessions;
- Account Disablement against former-worker access;
- RBAC against excessive privilege;
- Privileged Re-authentication against administrator compromise;
- Trusted Device Restriction against unmanaged-device access.

This gives the fictional Sunhaven environment a reusable security-analysis tool for explaining attack paths and the value of identity controls.

The project is also safe for demonstration because it uses synthetic data and does not require production access.

---

## 10. Remaining Work and Future Plan

The main attack-path, risk, control and automated-testing components are now working.

The remaining work will focus on improving presentation, reporting and final project usability.

### Automatic Before/After Comparison

Add a comparison mode so a scenario can automatically display both:

```text
Control OFF → OPEN
Control ON  → BLOCKED
```

without manually changing `controls.json`.

This will make the final demonstration cleaner.

### JSON Result Export

Generate a structured JSON result containing:

- scenario information;
- attack path;
- risk;
- control;
- final status.

### CSV Summary

Generate a CSV file that compares all six scenarios in one table.

### HTML Security Report

Generate a static HTML report that presents:

- scenario name;
- attack path;
- risk score;
- severity;
- security control;
- before/after result;
- security finding.

The HTML component will be a generated report, not a separate web application.

### Documentation and Evidence

Remaining documentation work includes:

- updating the README;
- updating the test plan to match the implemented 45-test suite;
- updating requirements where needed;
- cleaning evidence filenames;
- keeping editable Draw.io sources;
- preparing final Git commits and GitHub evidence;
- preparing the final demonstration and explanation.

---

## 11. Reflection

The biggest improvement in this stage was moving from a basic prototype into a more complete and testable system.

Building six different scenarios helped me understand that attack-path modelling needs careful graph design. The Scenario 6 path collision was useful because it showed that a graph may contain more than one valid route and that node reuse can change BFS results.

Automated testing was also an important improvement. Earlier I was checking each scenario manually. The pytest suite now gives me a repeatable way to check the risk engine, graph, BFS algorithm, controls and configuration files after changes.

I also improved the risk model by moving the scale and severity bands into JSON. This made the design easier to explain and separated the risk policy from the Python processing logic.

The project now demonstrates the main technical idea successfully: SITAS can model an identity threat, discover a path to a protected asset, calculate the risk and show how a security control changes the outcome.

The remaining work is mainly focused on automatic comparison, report generation, final documentation and presentation preparation rather than rebuilding the core simulator.
