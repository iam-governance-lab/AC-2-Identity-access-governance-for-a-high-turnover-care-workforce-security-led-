# SITAS Project Plan

## Project Title

**Sunhaven Identity Threat and Attack-Path Simulator (SITAS)**

---

## 1. Project Background

Sunhaven Care is a fictional care organisation used for the cybersecurity capstone project.

The organisation has different types of workers, user identities, passwords, shared workstations, active sessions, applications and protected fictional resident information.

Because access depends on identity, one weakness can create a path through several systems. Examples include stolen passwords, unattended sessions, old accounts, excessive permissions, compromised administrator identities and access from unmanaged devices.

SITAS is being developed to make these identity-related security risks visible and easier to explain.

---

## 2. Problem

A normal architecture diagram can show which systems and users exist, but it does not automatically show:

- how an attacker may move through the environment;
- whether the attacker can reach a protected asset;
- which identity weakness created the path;
- how serious the scenario is;
- which security control is relevant;
- whether that control changes the result.

This is the main problem SITAS is designed to solve.

---

## 3. Proposed Solution

SITAS is a standalone Python cybersecurity simulator.

The system creates a fictional model of the Sunhaven environment and represents it as a directed graph.

The model includes things such as:

- attackers;
- credentials;
- user identities;
- sessions;
- workstations;
- applications;
- privileged functions;
- protected fictional information.

SITAS then uses Breadth-First Search (BFS) to find a path from a threat source to a protected target.

It also calculates the risk of the scenario and evaluates a related security control.

Example:

```text
External Attacker
→ Stolen Nurse Password
→ Nurse Identity
→ Shared Nurse Workstation
→ Sunhaven Care Portal
→ Fictional Resident Records
```

The same scenario can then be evaluated with MFA disabled and enabled.

```text
MFA OFF → OPEN
MFA ON  → BLOCKED
```

---

## 4. Main Objective

> To build a standalone cybersecurity simulator that finds identity-related attack paths in a fictional Sunhaven environment, calculates their risk and demonstrates how security controls can reduce or block those paths.

---

## 5. How SITAS Helps Sunhaven

SITAS gives the Sunhaven project a separate security-analysis capability.

Instead of only stating that a control is important, SITAS demonstrates:

```text
Threat
↓
Attack Path
↓
Protected Asset
↓
Risk
↓
Security Control
↓
OPEN or BLOCKED
```

This helps Sunhaven understand:

- where identity-related attack paths exist;
- which fictional assets may be exposed;
- how serious each scenario is;
- which control is relevant;
- how the outcome changes when the control is enabled.

Because SITAS uses synthetic data and operates offline, it is safe to demonstrate and does not require production access.

---

## 6. Individual Contribution

SITAS is my individual technical contribution within the wider Sunhaven Care Workforce IAM project.

My contribution focuses on:

- threat modelling;
- attack-graph design;
- BFS attack-path discovery;
- risk scoring;
- security-control simulation;
- scenario development;
- automated testing;
- security reporting.

SITAS does not perform operational IAM administration.

It does not:

- create Microsoft Entra users;
- modify Microsoft Entra users;
- delete Microsoft Entra users;
- perform Joiner-Mover-Leaver automation;
- conduct access reviews;
- monitor live security events;
- automatically remediate access;
- use real employee or resident information.

---

## 7. Current System Design

The main processing flow is:

```text
Fictional Sunhaven Data
        ↓
JSON Configuration
        ↓
Model Loader
        ↓
Directed Attack Graph
        ↓
BFS Attack-Path Discovery
        ↓
Risk Engine
        ↓
Security-Control Evaluation
        ↓
OPEN / BLOCKED Result
        ↓
Security Finding
```

The same Python analysis engine is reused for all six scenarios.

---

## 8. Attack Graph

SITAS represents Sunhaven as a directed graph.

```text
Nodes = objects in the environment
Edges = directed relationships between objects
```

Example nodes include:

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

This allows the system to model how an attacker may move from an initial compromise toward protected information.

---

## 9. Why BFS Is Used

SITAS uses Breadth-First Search because it is:

- suitable for the current graph model;
- easy to understand;
- able to find a short reachable path;
- easy to test;
- explainable during the capstone demonstration.

A visited-node set prevents graph cycles from causing endless processing.

---

## 10. Risk Assessment

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

The risk configuration is stored in:

```text
config/risk-model.json
```

The Python risk engine reads this model and validates the input values before calculating the result.

---

## 11. Implemented Threat Scenarios

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

---

## 12. Implemented Security Controls

SITAS currently simulates:

1. Multi-Factor Authentication
2. Session Timeout
3. Account Disablement
4. Role-Based Access Control
5. Privileged Re-authentication
6. Trusted Device Restriction

The controls are simulations only and do not change live Microsoft Entra configuration.

---

## 13. Automated Testing

Automated testing is implemented using `pytest`.

The current suite includes:

```text
Risk Engine Tests              14
Graph + BFS Tests               9
Control Engine Tests           13
Model Loader Tests              9
Automatic Comparison Tests      2
Standalone Reporting Tests      3
Sunhaven Integration Tests     16
---------------------------------
Total                          66
```

Current verified result:

```text
66 passed
```

The automated tests cover:

- JSON loading;
- invalid JSON;
- missing files;
- graph creation;
- directed relationships;
- BFS attack paths;
- shortest path behaviour;
- unreachable targets;
- graph cycles;
- real Scenario 6 path validation;
- risk calculations;
- severity boundaries;
- invalid likelihood and impact values;
- all six security controls;
- all six scenario files.

This provides repeatable evidence that the core simulator behaves correctly.

---

## 14. Architecture and Design Documentation

The project includes design diagrams covering:

- high-level system architecture;
- attack path and control evaluation;
- module and data dependencies;
- security boundary and independence from operational IAM;
- threat-scenario processing workflow.

These diagrams support both technical documentation and presentation.

---

## 15. Current Technologies

```text
Python 3
JSON
pytest
Visual Studio Code
Git
GitHub
Draw.io
```

Reporting and integration output also uses:

```text
CSV
HTML/CSS
```

---

## 16. Current Project Status

### Completed

- project scope and planning;
- requirements;
- environment modelling;
- modular Python implementation;
- directed graph;
- BFS pathfinding;
- configurable risk model;
- six threat scenarios;
- six security-control simulations;
- before/after manual evidence;
- architecture/design diagrams;
- 66 passing automated tests;
- automatic before/after comparison;
- JSON/CSV/HTML standalone reporting;
- read-only Sunhaven project adapter;
- workforce-derived leaver analysis;
- RBAC matrix from project configuration;
- integrated JSON/CSV/HTML reporting;
- improved README.

### Remaining

- final integration evidence capture;
- diagram refresh to show the implemented Sunhaven adapter;
- final documentation cleanup;
- final Git/GitHub evidence;
- presentation/demo preparation.

---

## 17. Future Development Plan

### Stage 1 – Automatic Comparison

Add a mode that automatically evaluates:

```text
Control OFF → OPEN
Control ON  → BLOCKED
```

without manually changing the controls file.

### Stage 2 – JSON Result Export

Generate structured scenario results for machine-readable evidence.

### Stage 3 – CSV Summary

Generate one summary file comparing all six scenarios.

### Stage 4 – HTML Security Report

Generate a readable static report containing:

- scenario name;
- attack path;
- risk score;
- severity;
- security control;
- before/after result;
- security finding.

### Stage 5 – Finalisation

Complete:

- requirements and test traceability;
- final diagram review;
- evidence cleanup;
- Git commits;
- GitHub update;
- README final check;
- final presentation/demo preparation.

---

## 18. Evidence

Evidence includes:

- scenario screenshots;
- control OFF/ON results;
- pytest outputs;
- architecture/design diagrams;
- JSON configuration;
- Python source code;
- Git commits;
- GitHub repository history.

The automated full-suite result provides evidence that the main analysis components work together successfully.

---

## 19. Expected Final Result

The completed system should provide the following flow:

```text
Load Scenario
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
Generate Security Finding
↓
Export Reports and Evidence
```

---

## 20. Success Criteria

SITAS will be considered successful when it can:

1. load the fictional Sunhaven environment;
2. build the directed attack graph;
3. discover attack paths using BFS;
4. calculate and classify risk;
5. simulate multiple identity-related controls;
6. show OPEN and BLOCKED results;
7. support several independent attack scenarios;
8. pass automated testing;
9. automatically compare before/after control states;
10. generate understandable reports;
11. remain independent from live Microsoft Entra systems;
12. provide clear evidence of individual contribution.

The first eight criteria are already substantially completed. The remaining work is mainly automatic comparison, reporting and finalisation.
