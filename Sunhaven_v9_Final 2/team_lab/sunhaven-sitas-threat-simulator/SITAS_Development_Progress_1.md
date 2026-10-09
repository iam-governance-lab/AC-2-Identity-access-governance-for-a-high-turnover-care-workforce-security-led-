# SITAS Progress Report 1

## Project

**Project Title:** Sunhaven Identity Threat and Attack-Path Simulator (SITAS)  
**Unit:** COIT13236 Cyber Security Project  
**Individual Contribution:** Threat modelling, attack-path simulation, risk assessment and security-control evaluation

---

## 1. Progress Overview

My individual project is the **Sunhaven Identity Threat and Attack-Path Simulator (SITAS)**.

SITAS is a standalone Python-based cybersecurity simulator designed for the fictional Sunhaven Care environment. The purpose of the project is to show how identity-related weaknesses can create a path from an attacker to protected information.

At this stage, I established the project structure, documented the requirements and scope, created the initial architecture, implemented the main attack-path engine and completed the first two working security scenarios.

The project was designed to remain independent from the operational IAM work completed elsewhere in the Sunhaven project.

---

## 2. Sunhaven Problem and My Proposed Solution

Sunhaven Care depends on user identities, passwords, shared workstations, active sessions and applications to allow workers to access information.

This creates security risks if:

- a password is stolen;
- an authenticated session is left active on a shared workstation;
- an identity has more access than required;
- an old account remains usable;
- a privileged account is compromised.

A normal architecture diagram can show which systems are connected, but it does not automatically show how an attacker may move through those systems or whether a security control can stop the attack.

My solution is SITAS.

SITAS represents the fictional Sunhaven environment as a **directed graph**. Identities, credentials, devices, sessions, applications and protected assets are represented as nodes, while their relationships are represented as directed edges.

The simulator then uses **Breadth-First Search (BFS)** to find a path between a threat source and a protected target.

This gives Sunhaven a simple way to see:

- how an attack path may develop;
- which asset may be reached;
- how serious the scenario is;
- which security control is relevant;
- whether the path remains OPEN or becomes BLOCKED.

---

## 3. Work Completed

### Project Structure and Planning

I created the main project folders for:

```text
config/
docs/
evidence/
reports/
scenarios/
src/
tests/
```

I also prepared the initial:

- project plan;
- functional and non-functional requirements;
- test plan;
- architecture diagram;
- project scope and individual contribution boundary.

The scope clearly separates SITAS from live Microsoft Entra administration, Joiner-Mover-Leaver automation, access reviews, compliance checking and security-event monitoring.

### Environment and Configuration

I created JSON configuration files for the fictional Sunhaven environment and security controls.

The environment model included:

- attackers;
- stolen credentials;
- user identities;
- shared workstations;
- active sessions;
- the Sunhaven Care Portal;
- fictional resident records.

### Core Python Modules

I implemented the main Python modules:

```text
model_loader.py
graph_engine.py
pathfinder.py
risk_engine.py
control_engine.py
sitas.py
```

The main functions implemented at this stage included:

- loading JSON data;
- building the directed graph;
- mapping node IDs to readable names;
- finding attack paths with BFS;
- calculating likelihood × impact risk;
- classifying risk severity;
- checking simulated controls;
- displaying the attack path and final OPEN/BLOCKED result.

---

## 4. Scenario 1 – Stolen Nurse Credential

The first scenario models an external attacker obtaining a fictional nurse password.

The discovered path was:

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

Risk result:

```text
Likelihood: 4/5
Impact: 5/5
Risk Score: 20/25
Severity: Critical
```

The related security control is **Multi-Factor Authentication (MFA)**.

The scenario demonstrated:

```text
MFA OFF → Attack Path OPEN
MFA ON  → Attack Path BLOCKED
```

This showed that SITAS could identify an attack path, calculate its risk and demonstrate the effect of a security control.

---

## 5. Scenario 2 – Shared Workstation Session Misuse

The second scenario models an unauthorised person finding an unattended shared workstation with an active nurse session.

The path was:

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

Risk result:

```text
Likelihood: 3/5
Impact: 5/5
Risk Score: 15/25
Severity: High
```

The related control is **Session Timeout**.

The scenario demonstrated:

```text
Session Timeout OFF → Attack Path OPEN
Session Timeout ON  → Attack Path BLOCKED
```

This expanded the simulator beyond stolen passwords and showed that it can also model session-based identity risks.

---

## 6. Evidence of Individual Contribution

The work completed is supported by project files and screenshots, including:

- the VS Code project structure;
- architecture and design documentation;
- Scenario 1 OPEN and BLOCKED outputs;
- Scenario 2 OPEN and BLOCKED outputs;
- Python source modules;
- JSON configuration and scenario files;
- Git repository history.

The main evidence files for the first two scenarios are:

```text
07-scenario-01-mfa-off-open.png
08-scenario-01-mfa-on-blocked.png
09-scenario-02-session-off-open.png
10-scenario-02-session-on-blocked.png
```

---

## 7. Problems Encountered and Solutions

One issue occurred when `sitas.py` was updated to use a new `assess_control()` function while `control_engine.py` still contained the older version.

This caused an import error.

I corrected the issue by updating the control engine so both modules used the same function structure.

This helped me understand the importance of keeping dependent modules consistent when the program is being developed across several files.

---

## 8. Why This Work Is Useful to Sunhaven

The main benefit of SITAS is that it makes identity-security problems easier to understand.

Instead of only saying that a control such as MFA or Session Timeout is important, SITAS shows:

```text
Threat
↓
Attack Path
↓
Risk
↓
Security Control
↓
OPEN or BLOCKED
```

This gives the Sunhaven project a separate security-analysis capability that can explain why particular IAM controls matter.

It also provides a safe way to test ideas because all users, credentials, devices and resident records in SITAS are fictional.

---

## 9. Reflection

The main learning from this stage was understanding how separate technical components work together.

I started with the security problem and then translated it into JSON data, a directed graph, BFS pathfinding, risk scoring and control simulation.

The first two scenarios helped me confirm that the project idea was practical rather than only theoretical.

I also learned that modular code requires careful coordination. The import error between `sitas.py` and `control_engine.py` showed that a change in one module can affect another module.

At the end of this stage, I had a working prototype with two attack scenarios and two security controls. The project had a clear direction, but more scenarios, stronger risk configuration, automated testing and reporting were still needed to make it a complete capstone solution.
