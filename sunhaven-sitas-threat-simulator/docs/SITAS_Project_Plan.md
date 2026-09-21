# SITAS Project Plan

## Project Title

**Sunhaven Identity Threat and Attack-Path Simulator (SITAS)**

---

## 1. Project Background

Sunhaven Care is a care organisation used in the cybersecurity capstone project.

The environment includes different worker roles, user identities, shared workstations, sessions, applications and fictional resident information. Because access depends heavily on identity, weaknesses such as stolen credentials, unattended sessions, old accounts or excessive permissions can create attack paths to protected information.

SITAS was developed to make these identity-related risks easier to identify, test and explain.

---

## 2. Problem

A normal system architecture shows users, applications and controls, but it does not clearly show:

- how an attacker may move through the environment;
- whether a protected asset can be reached;
- which identity weakness creates the attack path;
- how serious the scenario is;
- which security control is relevant;
- whether that control changes the result.

SITAS addresses this problem by modelling identity threats as attack paths.

---

## 3. Solution

SITAS is a Python-based cybersecurity simulator.

It represents a fictional Sunhaven environment as a directed graph containing objects such as:

- attackers;
- credentials;
- identities;
- sessions;
- workstations;
- applications;
- privileged functions;
- protected assets.

Breadth-First Search (BFS) is used to find a reachable path from a threat source to a protected target.

SITAS then:

1. finds the attack path;
2. calculates the scenario risk;
3. identifies the related control;
4. compares the control OFF and ON states;
5. reports whether the path remains OPEN or becomes BLOCKED.

Example:

```text
External Attacker
→ Stolen Nurse Password
→ Nurse Identity
→ Shared Nurse Workstation
→ Sunhaven Care Portal
→ Fictional Resident Records
```

```text
MFA OFF → OPEN
MFA ON  → BLOCKED
```

---

## 4. Main Objective

> Build a cybersecurity simulator that identifies identity-related attack paths in the fictional Sunhaven environment, calculates their risk and demonstrates how relevant security controls can reduce or block those paths.

---

## 5. Individual Contribution

SITAS is my individual technical contribution to the wider Sunhaven Care Workforce IAM project.

My work focuses on:

- threat modelling;
- attack-graph design;
- BFS path discovery;
- risk scoring;
- security-control simulation;
- automated before/after comparison;
- Sunhaven read-only integration;
- automated testing;
- JSON, CSV and HTML reporting.

SITAS is an analysis tool and does not perform operational IAM administration.

It does not:

- create, modify or delete Microsoft Entra users;
- execute Joiner-Mover-Leaver processes;
- enforce RBAC;
- configure MFA;
- perform manager access reviews;
- monitor general live security events;
- make device, network or session access decisions;
- automatically remediate access;
- use real employee or resident information.

This keeps SITAS separate from the operational IAM responsibilities of the wider team.

---

## 6. Operating Modes

SITAS currently supports two main modes.

### Mode 1 – Standalone Simulation

Standalone mode uses fictional JSON configuration and scenario files.

```text
Scenario + Environment
        ↓
Model Loader
        ↓
Directed Graph
        ↓
BFS Attack Path
        ↓
Risk Analysis
        ↓
Control Simulation
        ↓
Before / After Comparison
        ↓
JSON / CSV / HTML Reports
```

This mode is used for the six repeatable SITAS threat scenarios.

### Mode 2 – Sunhaven-Integrated Read-Only Analysis

The integration mode reads approved Sunhaven project files without changing the main system.

```text
Sunhaven Project Files
        ↓
Read-Only SITAS Adapter
        ↓
Normalised SITAS Model
        ↓
Attack Path + Risk Analysis
        ↓
Control Comparison
        ↓
JSON / CSV / HTML Reports
```

The adapter can read items such as:

- workforce records;
- route-role mappings;
- application-role configuration;
- governed-group configuration;
- optional sanitised worker-state evidence.

The adapter does not make live Microsoft Graph changes or execute JML actions.

---

## 7. Attack Graph and BFS

SITAS represents the environment as a directed graph.

```text
Nodes = objects in the environment
Edges = directed relationships between objects
```

Example node types include:

```text
Attacker
Credential
Identity
Session
Workstation
Application
Admin Function
Protected Asset
```

BFS is used because it is simple, deterministic, easy to test and suitable for finding a short reachable path in the current graph model.

A visited-node set prevents graph cycles from causing endless processing.

---

## 8. Risk Assessment

Each scenario contains likelihood and impact values from 1 to 5.

```text
Risk Score = Likelihood × Impact
```

Severity bands are:

```text
1–4   = Low
5–9   = Medium
10–16 = High
17–25 = Critical
```

The risk model is stored in:

```text
config/risk-model.json
```

The risk engine validates the values before calculating the final risk result.

---

## 9. Implemented Threat Scenarios

### Scenario 1 – Stolen Nurse Credential

```text
External Attacker
→ Stolen Nurse Password
→ Nurse Identity
→ Shared Nurse Workstation
→ Sunhaven Care Portal
→ Fictional Resident Records
```

```text
Control: MFA
Risk: 20/25 – Critical
OFF → OPEN
ON  → BLOCKED
```

### Scenario 2 – Shared Workstation Session Misuse

```text
Unauthorised Person
→ Unattended Shared Workstation
→ Active Nurse Session
→ Sunhaven Care Portal
→ Fictional Resident Records
```

```text
Control: Session Timeout
Risk: 15/25 – High
OFF → OPEN
ON  → BLOCKED
```

### Scenario 3 – Former Worker Identity Misuse

```text
Former Worker
→ Former Worker Identity
→ Sunhaven Care Portal
→ Fictional Resident Records
```

```text
Control: Account Disablement
Risk: 12/25 – High
OFF → OPEN
ON  → BLOCKED
```

### Scenario 4 – Excessive Privilege Abuse

```text
Compromised Care Worker
→ Care Worker Identity
→ Over-Privileged Role
→ Restricted Admin Function
→ Fictional Resident Records
```

```text
Control: RBAC
Risk: 15/25 – High
OFF → OPEN
ON  → BLOCKED
```

### Scenario 5 – Privileged Administrator Credential Compromise

```text
External Admin Attacker
→ Stolen Admin Credential
→ Privileged Admin Identity
→ Restricted Admin Console
→ Fictional Resident Records
```

```text
Control: Privileged Re-authentication
Risk: 10/25 – High
OFF → OPEN
ON  → BLOCKED
```

### Scenario 6 – Unmanaged Device Access

```text
External Device Attacker
→ Stolen Care Worker Credential
→ Remote Care Worker Identity
→ Unmanaged Device Session
→ Sunhaven Care Portal
→ Fictional Resident Records
```

```text
Control: Trusted Device Restriction
Risk: 12/25 – High
OFF → OPEN
ON  → BLOCKED
```

The device-control scenario remains a simulated security scenario. SITAS does not claim that live device-compliance enforcement is implemented in the Sunhaven MVP.

---

## 10. Implemented Security Controls

SITAS currently simulates six controls:

1. Multi-Factor Authentication;
2. Session Timeout;
3. Account Disablement;
4. Role-Based Access Control;
5. Privileged Re-authentication;
6. Trusted Device Restriction.

These controls are simulations used to analyse security effects. They do not modify live Microsoft Entra configuration.

---

## 11. Automatic Control Comparison

SITAS automatically compares a scenario with its related control disabled and enabled.

```text
Control OFF
→ analyse attack path
→ OPEN

Control ON
→ analyse attack path again
→ BLOCKED
```

This avoids manually changing the control configuration for each comparison.

The result also records whether the control successfully interrupts the attack path.

---

## 12. Sunhaven Integration

The Sunhaven adapter provides a read-only connection between the SITAS analysis model and the wider group project.

The adapter can analyse project configuration such as:

```text
data/workforce.csv
config/route-role-map.csv
config/app-role-ids.json
config/group-object-ids.json
```

The strongest integrated scenario currently uses a worker marked as leaving in the workforce data.

SITAS builds a threat model such as:

```text
Former Worker
→ Existing Identity
→ Sunhaven Care Portal
→ Fictional Resident Records
```

The baseline models the exposure if the identity remains usable.

The protected version models the expected effect of account disablement.

Any operational evidence supplied to SITAS is treated as read-only supporting evidence. SITAS does not claim that this is a live Entra query.

---

## 13. Reporting

SITAS can generate standalone and Sunhaven-integrated reports.

Current output formats are:

```text
JSON
CSV
HTML
```

Examples include:

```text
reports/sitas-analysis.json
reports/sitas-summary.csv
reports/sitas-threat-report.html

reports/sunhaven-integration-analysis.json
reports/sunhaven-rbac-matrix.csv
reports/sunhaven-integration-report.html
```

The reports provide structured evidence of:

- attack paths;
- risk scores;
- severity;
- related controls;
- baseline and protected results;
- control effectiveness;
- Sunhaven integration information.

---

## 14. Automated Testing

Automated testing is implemented using `pytest`.

Current test coverage includes:

```text
Risk Engine Tests               14
Graph + BFS Tests                9
Control Engine Tests            13
Model Loader Tests               9
Automatic Comparison Tests       2
Standalone Reporting Tests       3
Sunhaven Integration Tests      16
----------------------------------
Total                           66
```

Current verified result:

```text
66 passed
```

Testing covers:

- configuration loading;
- invalid and missing input;
- graph creation;
- directed relationships;
- BFS attack paths;
- unreachable targets;
- graph cycles;
- risk calculation;
- severity boundaries;
- six security controls;
- six scenario files;
- automatic OFF/ON comparison;
- report generation;
- Sunhaven project integration;
- integrated leaver analysis.

The full passing suite provides repeatable evidence that the main SITAS components work together correctly.

---

## 15. Technologies

SITAS currently uses:

```text
Python 3
JSON
CSV
HTML/CSS
pytest
Visual Studio Code
Git
GitHub
Draw.io
```

---

## 16. Current Project Status

### Completed

- project scope and requirements;
- directed attack-graph model;
- BFS pathfinding;
- configurable 5 × 5 risk model;
- six threat scenarios;
- six simulated security controls;
- automatic OFF/ON control comparison;
- JSON reporting;
- CSV summary reporting;
- HTML security reporting;
- read-only Sunhaven adapter;
- workforce-derived leaver analysis;
- RBAC matrix generation;
- Sunhaven integration reports;
- requirements traceability;
- automated testing;
- 66 passing tests.

### Remaining Finalisation

The remaining work is mainly presentation and evidence preparation:

- update the final architecture diagram;
- clean final documentation;
- capture final screenshots/evidence;
- clean repository cache files;
- complete final Git/GitHub evidence;
- prepare the capstone demonstration.

No major change to the working SITAS analysis engine is currently required.

---

## 17. Final Architecture

The final high-level integrated architecture is:

```text
Sunhaven Project Files
        ↓
SITAS Read-Only Adapter
        ↓
SITAS Analysis Engine
Attack Paths + Risk + Controls
        ↓
Before / After Comparison
        ↓
JSON / CSV / HTML Reports
```

The standalone JSON scenario mode continues to use the same core analysis engine.

---

## 18. Evidence

SITAS evidence includes:

- scenario execution screenshots;
- control OFF/ON comparisons;
- full pytest results;
- architecture diagrams;
- JSON configuration;
- generated JSON/CSV/HTML reports;
- integrated Sunhaven analysis;
- Python source code;
- Git commits;
- GitHub repository history.

The automated test result and generated reports provide repeatable evidence of the current implementation.

---

## 19. Final System Flow

The completed SITAS workflow is:

```text
Load Scenario or Sunhaven Snapshot
        ↓
Build Directed Graph
        ↓
Find Attack Path
        ↓
Calculate Risk
        ↓
Evaluate Security Control
        ↓
Compare Before and After
        ↓
Generate Analysis Result
        ↓
Export Reports and Evidence
```

---

## 20. Success Criteria

SITAS is successful when it can:

1. model the fictional Sunhaven environment;
2. build a directed attack graph;
3. discover attack paths using BFS;
4. calculate and classify risk;
5. simulate identity-related security controls;
6. show OPEN and BLOCKED outcomes;
7. support multiple independent scenarios;
8. automatically compare control OFF and ON states;
9. generate understandable JSON, CSV and HTML reports;
10. analyse selected Sunhaven project information in read-only mode;
11. remain independent from live Microsoft Entra administration;
12. pass automated testing;
13. provide clear evidence of my individual technical contribution.
