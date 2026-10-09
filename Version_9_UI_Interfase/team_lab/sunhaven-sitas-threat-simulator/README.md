# Sunhaven Identity Threat and Attack-Path Simulator (SITAS)

## Overview

SITAS is a Python cybersecurity threat-analysis component developed for the fictional **Sunhaven Care** environment. It supports both standalone simulation and read-only integration with the main Sunhaven group project.

The project models identity-related security weaknesses as attack paths. It shows how an attacker could move from an initial compromise, such as a stolen credential or active session, toward a protected Sunhaven resource.

SITAS then calculates the risk of the scenario and simulates whether a relevant security control would leave the attack path **OPEN** or make it **BLOCKED**.

The project uses fictional/test project data only. Its Sunhaven adapter reads approved project files and optional sanitised evidence, but it does not connect to or modify a live Microsoft Entra environment.

---

## Why SITAS Is Needed

Sunhaven Care depends on user identities, passwords, shared workstations, sessions, applications and privileged access.

This creates possible security problems such as:

- stolen user credentials;
- unattended workstations with active sessions;
- former worker accounts remaining usable;
- users having more access than required;
- compromised privileged administrator credentials;
- access from unmanaged or untrusted devices.

A normal architecture diagram can show which systems exist, but it does not automatically show:

- how an attacker could move through the environment;
- whether a protected asset is reachable;
- how serious the scenario is;
- which security control is relevant;
- whether the control changes the attack outcome.

SITAS was created to provide this additional security-analysis capability.

---

## How SITAS Helps Sunhaven

SITAS turns identity-security risks into visible and repeatable attack scenarios.

For example:

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

The same scenario can then be tested with a security control disabled and enabled:

```text
MFA OFF → Attack Path OPEN
MFA ON  → Attack Path BLOCKED
```

This helps demonstrate:

- where attack paths exist;
- which fictional Sunhaven assets may be exposed;
- the likelihood and impact of the threat;
- the overall risk level;
- which control can reduce the exposure;
- the difference between weak and protected configurations.

SITAS is therefore a **threat-modelling, integration-assurance and security decision-support component**, not an operational identity-management system.

---

## Main Features

The current SITAS implementation includes:

- JSON-based environment modelling;
- directed attack-graph construction;
- Breadth-First Search (BFS) attack-path discovery;
- configurable 5 × 5 risk model;
- likelihood and impact validation;
- Low, Medium, High and Critical severity classification;
- six repeatable threat scenarios;
- six simulated security controls;
- command-line scenario selection;
- OPEN/BLOCKED control evaluation;
- modular Python design;
- automated testing with pytest;
- automatic control OFF/ON comparison;
- JSON, CSV and static HTML reporting;
- read-only Sunhaven workforce/configuration adapter;
- workforce-derived leaver analysis;
- RBAC matrix generation from the group project configuration;
- optional sanitised worker-state/leaver evidence ingestion;
- screenshot and evidence collection.

The current automated test suite contains **66 passing tests** covering the risk engine, graph/BFS logic, control engine, JSON/model loading, automatic before/after comparison, standalone reporting and Sunhaven integration.

---

## Implemented Scenarios

| ID | Scenario | Security Control | Risk |
|---|---|---|---|
| SITAS-S01 | Stolen Nurse Credential | Multi-Factor Authentication | 20/25 – Critical |
| SITAS-S02 | Shared Workstation Session Misuse | Session Timeout | 15/25 – High |
| SITAS-S03 | Former Worker Identity Misuse | Account Disablement | 12/25 – High |
| SITAS-S04 | Excessive Privilege Abuse | Role-Based Access Control | 15/25 – High |
| SITAS-S05 | Privileged Administrator Credential Compromise | Privileged Re-authentication | 10/25 – High |
| SITAS-S06 | Unmanaged Device Access | Trusted Device Restriction | 12/25 – High |

Each scenario can be demonstrated with its related control disabled and enabled.

---

## Security Controls

SITAS currently simulates the following controls:

### CTRL-MFA – Multi-Factor Authentication

Used to test whether MFA blocks a password-only identity compromise.

### CTRL-SESSION – Session Timeout

Used to test whether an old active session on an unattended workstation remains usable.

### CTRL-ACCOUNT – Account Disablement

Used to test whether a former worker identity can still authenticate.

### CTRL-RBAC – Role-Based Access Control

Used to test whether excessive privileges allow access to restricted functionality.

### CTRL-PRIVAUTH – Privileged Re-authentication

Used to test whether additional authentication prevents a compromised privileged identity from reaching an administrative console.

### CTRL-DEVICE – Trusted Device Restriction

Used to test whether access from an unmanaged device session is blocked.

These controls are simulations only. SITAS does not change real security policies.

---

## How SITAS Works

```text
Scenario JSON
     ↓
Load Environment and Configuration
     ↓
Build Directed Attack Graph
     ↓
Run BFS Attack-Path Search
     ↓
Calculate Likelihood × Impact
     ↓
Classify Risk Severity
     ↓
Evaluate Related Security Control
     ↓
OPEN or BLOCKED Result
```

The same analysis engine is reused for every scenario. Separate Python programs are not required for each attack.

---

## Risk Model

SITAS uses a 5 × 5 risk model.

```text
Risk Score = Likelihood × Impact
```

### Likelihood

| Value | Rating |
|---:|---|
| 1 | Rare |
| 2 | Unlikely |
| 3 | Possible |
| 4 | Likely |
| 5 | Almost Certain |

### Impact

| Value | Rating |
|---:|---|
| 1 | Insignificant |
| 2 | Minor |
| 3 | Moderate |
| 4 | Major |
| 5 | Severe |

### Severity

| Score | Severity |
|---:|---|
| 1–4 | Low |
| 5–9 | Medium |
| 10–16 | High |
| 17–25 | Critical |

The risk configuration is stored in:

```text
config/risk-model.json
```

---

## Project Structure

```text
sunhaven-sitas-threat-simulator/
├── config/
│   ├── controls.json
│   ├── environment.json
│   └── risk-model.json
├── docs/
│   ├── diagrams/
│   ├── requirements.md
│   ├── requirements-traceability.md
│   ├── SITAS_Project_Plan.md
│   ├── Sunhaven_Integration.md
│   └── test-plan.md
├── evidence/
├── reports/
├── scenarios/
├── src/
│   ├── analysis_engine.py
│   ├── comparison_engine.py
│   ├── control_engine.py
│   ├── graph_engine.py
│   ├── model_loader.py
│   ├── pathfinder.py
│   ├── report_generator.py
│   ├── risk_engine.py
│   ├── sitas.py
│   ├── sunhaven_adapter.py
│   └── sunhaven_report_generator.py
├── tests/
│   ├── test_comparison_engine.py
│   ├── test_control_engine.py
│   ├── test_graph_pathfinder.py
│   ├── test_model_loader.py
│   ├── test_report_generator.py
│   ├── test_risk_engine.py
│   └── test_sunhaven_adapter.py
├── pytest.ini
└── README.md
```

---


## Main Python Modules

### `model_loader.py`

Loads the environment, controls, risk model and scenario JSON files.

### `graph_engine.py`

Converts the environment relationships into a directed adjacency-list graph and provides readable node names.

### `pathfinder.py`

Uses Breadth-First Search to discover a reachable attack path between a threat source and protected target.

### `risk_engine.py`

Validates likelihood and impact values, calculates the risk score and applies the configured severity bands.

### `control_engine.py`

Contains the simulation rules for the six implemented security controls.

### `sunhaven_adapter.py`

Read-only integration layer that validates and consumes `workforce.csv`, route-role mappings, app-role/group mappings and optional sanitised worker-state/leaver evidence. It never performs Microsoft Graph or JML write operations.

### `sunhaven_report_generator.py`

Generates integrated JSON, RBAC CSV and HTML security-analysis outputs.

### `sitas.py`

Main command-line program for standalone scenarios, automatic comparison/reporting and the Sunhaven integration commands.

---

## Running SITAS

Open PowerShell or the VS Code terminal in the project root.

### Scenario 1

```powershell
python src/sitas.py scenarios/scenario-01-stolen-nurse-credential.json
```

### Scenario 2

```powershell
python src/sitas.py scenarios/scenario-02-shared-session.json
```

### Scenario 3

```powershell
python src/sitas.py scenarios/scenario-03-former-worker.json
```

### Scenario 4

```powershell
python src/sitas.py scenarios/scenario-04-excessive-privilege.json
```

### Scenario 5

```powershell
python src/sitas.py scenarios/scenario-05-privileged-admin.json
```

### Scenario 6

```powershell
python src/sitas.py scenarios/scenario-06-unmanaged-device.json
```

If no scenario is supplied, SITAS uses Scenario 1 by default:

```powershell
python src/sitas.py
```

---

## Sunhaven Integrated Mode

When this SITAS folder is placed directly inside the main Sunhaven repository, it automatically detects the parent project and reads the required inputs without any hard-coded `C:\...` path.

Check the group-project inputs:

```powershell
python src/sitas.py sunhaven-status
```

Run the workforce-derived former-worker comparison:

```powershell
python src/sitas.py sunhaven-leaver
```

Generate integrated reports:

```powershell
python src/sitas.py sunhaven-report
```

Generated files:

```text
reports/sunhaven-integration-analysis.json
reports/sunhaven-rbac-matrix.csv
reports/sunhaven-integration-report.html
```

For a standalone SITAS checkout, supply the main-project root explicitly:

```powershell
python src/sitas.py sunhaven-status --root "C:\Sunhaven\core-downloaded"
```

The adapter is read-only. It does not run JML scripts, modify Flask, change Entra users/roles, configure MFA or enforce device/session policy. Optional sanitised evidence can be supplied with `--worker-state` or `--leaver-result` and is labelled as snapshot evidence rather than a live-state claim. See `docs/Sunhaven_Integration.md`.

---

## Enabling and Disabling Controls

Control states are stored in:

```text
config/controls.json
```

Example:

```json
{
  "id": "CTRL-MFA",
  "name": "Multi-Factor Authentication",
  "enabled": false
}
```

Changing:

```json
"enabled": false
```

to:

```json
"enabled": true
```

allows the same scenario to be compared before and after the simulated control is enabled.

No Python source code needs to be changed to switch a control on or off.

---

## Automatic Comparison and Reporting

Run one automatic control OFF/ON comparison:

```powershell
python src/sitas.py compare scenarios/scenario-03-former-worker.json
```

Compare all six scenarios:

```powershell
python src/sitas.py compare-all
```

Generate the structured JSON, CSV summary and static HTML report:

```powershell
python src/sitas.py report-all
```

Generated files are written to `reports/`:

- `sitas-analysis.json`
- `sitas-summary.csv`
- `sitas-threat-report.html`

The comparison engine changes control state only in memory. It does not modify `config/controls.json` and does not make changes to Microsoft Entra ID or the Sunhaven portal.

---

## Automated Testing

SITAS uses `pytest`.

Install pytest if required:

```powershell
python -m pip install pytest
```

Run the complete test suite:

```powershell
python -m pytest -v
```

Current verified result:

```text
66 passed
```

The tests cover:

- risk calculations;
- risk severity boundaries;
- invalid risk values;
- directed graph construction;
- BFS attack-path discovery;
- shortest-path behaviour;
- unreachable targets;
- graph-cycle handling;
- all six security controls in enabled and disabled states;
- invalid and missing JSON files;
- real environment and configuration loading;
- all six scenario files;
- automatic comparison and standalone reporting;
- Sunhaven root/source validation;
- workforce-derived leaver analysis;
- RBAC matrix generation;
- optional sanitised evidence parsing;
- integrated JSON/CSV/HTML reporting.

---

## Current Development Status

### Completed

- standalone graph/BFS/risk/control engine;
- six scenarios and six simulated controls;
- automatic OFF/ON comparison;
- standalone JSON/CSV/HTML reporting;
- read-only Sunhaven adapter;
- workforce-derived former-worker analysis;
- RBAC matrix generated from the real project configuration;
- optional sanitised worker-state/leaver evidence ingestion;
- integrated JSON/CSV/HTML reporting;
- 66 passing automated tests.

### Remaining

- refresh final architecture diagrams to show the implemented adapter;
- capture final evidence screenshots/text outputs;
- final README/report polish and demonstration rehearsal.

---

## Individual Project Boundary

SITAS is an independent technical component within the wider Sunhaven Care Workforce IAM project.

SITAS does **not**:

- create or modify Microsoft Entra users;
- execute Joiner-Mover-Leaver automation;
- conduct manager access reviews or remediation;
- implement the team's compliance/monitoring dashboard;
- modify Flask authorization decisions;
- configure MFA, sessions or device compliance;
- automatically remediate access;
- use production credentials or real resident data.

The wider Sunhaven project provides the business and IAM context. SITAS now reads the project's fictional TEST workforce/configuration artefacts through a read-only adapter, while remaining the separate threat-modelling, attack-path, risk and control-analysis component.

---

## Security and Privacy

Standalone SITAS scenarios use fictional identities, credentials, sessions, applications and resident records. Integrated mode reads the fictional TEST workforce/configuration records already used by the Sunhaven capstone project. Optional evidence inputs must be sanitised.

The simulator is designed for local/offline analysis and does not perform real attacks, execute JML changes, or modify production systems.

---

## Project Value

The key value of SITAS is that it makes identity-security risks easier to understand.

Instead of only documenting that a control such as MFA, RBAC or Session Timeout should exist, SITAS demonstrates a modelled attack path and shows how the outcome changes when that control is applied.

This provides Sunhaven with a repeatable way to:

- visualise identity-related attack paths;
- understand the risk of different threat scenarios;
- demonstrate the purpose of security controls;
- compare weak and protected configurations;
- communicate technical cybersecurity findings more clearly.

---

## Limitations

SITAS remains an analysis/simulation component. Standalone results depend on the graph, scenario definitions and control rules. Integrated results additionally depend on the Sunhaven project files or sanitised evidence supplied at the time of analysis; they are not live-state guarantees.

It is not a replacement for:

- penetration testing;
- Microsoft Entra security configuration;
- SIEM monitoring;
- production threat detection;
- identity governance;
- real-world risk assessment.

Its purpose is to demonstrate attack-path analysis and the effect of identity-security controls within the Sunhaven capstone environment.
