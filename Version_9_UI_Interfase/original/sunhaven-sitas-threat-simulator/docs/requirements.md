# SITAS Requirements

## Project

**Project Title:** Sunhaven Identity Threat and Attack-Path Simulator (SITAS)  
**Unit:** COIT13236 Cyber Security Project

## 1. Purpose

This document defines the implemented requirements for SITAS. SITAS has a standalone threat-simulation mode and a read-only integration mode for the Sunhaven Care group project. Detailed links between requirements, implementation files and tests are maintained in `requirements-traceability.md`.

## 2. Functional Requirements

| ID | Requirement | Status | Verification |
|---|---|---|---|
| SITAS-FR-01 | Load a fictional Sunhaven environment from JSON. | Completed | Model-loader tests |
| SITAS-FR-02 | Validate required environment data before processing. | Completed | Invalid/missing model tests |
| SITAS-FR-03 | Represent environment objects as graph nodes. | Completed | Graph tests |
| SITAS-FR-04 | Represent relationships as directed graph edges. | Completed | Graph tests |
| SITAS-FR-05 | Allow a threat source/start node per scenario. | Completed | Scenario files/tests |
| SITAS-FR-06 | Allow a protected target per scenario. | Completed | Scenario files/tests |
| SITAS-FR-07 | Search for an attack path between start and target. | Completed | BFS tests |
| SITAS-FR-08 | Use Breadth-First Search for path discovery. | Completed | Pathfinder tests |
| SITAS-FR-09 | Prevent graph cycles causing infinite processing. | Completed | Cycle regression test |
| SITAS-FR-10 | Calculate risk using likelihood × impact. | Completed | Risk tests |
| SITAS-FR-11 | Classify Low, Medium, High or Critical severity. | Completed | Boundary tests |
| SITAS-FR-12 | Support simulated security controls. | Completed | Control tests |
| SITAS-FR-13 | Determine whether a simulated control blocks a path. | Completed | OFF/ON control tests |
| SITAS-FR-14 | Automatically compare exposure before and after a control. | Completed | Comparison-engine tests |
| SITAS-FR-15 | Display understandable path/risk/control results. | Completed | CLI runs/evidence |
| SITAS-FR-16 | Reuse the same engine across multiple scenarios. | Completed | Six scenarios |
| SITAS-FR-17 | Load risk settings from JSON. | Completed | Loader tests |
| SITAS-FR-18 | Validate likelihood and impact values. | Completed | Invalid-risk tests |
| SITAS-FR-19 | Support automated testing of major components. | Completed | 66 passing pytest tests |
| SITAS-FR-20 | Export structured JSON results. | Completed | Report tests |
| SITAS-FR-21 | Generate CSV scenario summaries. | Completed | Report tests |
| SITAS-FR-22 | Generate a static HTML threat report. | Completed | Report tests |
| SITAS-FR-23 | Locate the Sunhaven project using relative structure or an explicit root path. | Completed | Root-resolution tests |
| SITAS-FR-24 | Read and validate `data/workforce.csv` without modifying it. | Completed | Adapter tests |
| SITAS-FR-25 | Read and validate route-role, app-role and group mapping configuration. | Completed | Adapter/RBAC tests |
| SITAS-FR-26 | Generate a former-worker scenario from a Sunhaven Leaving/Inactive workforce record. | Completed | Integrated leaver tests |
| SITAS-FR-27 | Generate a role/route authorization matrix from Sunhaven configuration. | Completed | RBAC matrix tests |
| SITAS-FR-28 | Optionally ingest sanitised worker-state or leaver-result evidence in read-only mode. | Completed | Evidence parser/tests |
| SITAS-FR-29 | Generate integrated Sunhaven JSON, CSV and HTML reports. | Completed | Integration-report tests |

## 3. Security Controls

SITAS simulates six controls:

1. `CTRL-MFA` – Multi-Factor Authentication
2. `CTRL-SESSION` – Session Timeout
3. `CTRL-ACCOUNT` – Account Disablement
4. `CTRL-RBAC` – Role-Based Access Control
5. `CTRL-PRIVAUTH` – Privileged Re-authentication
6. `CTRL-DEVICE` – Trusted Device Restriction

The modelled controls do not automatically mean the corresponding control is live in the Sunhaven environment. The integration report records the boundary for each control.

## 4. Threat Scenarios

The standalone mode contains six repeatable scenarios:

1. `SITAS-S01` – Stolen Nurse Credential
2. `SITAS-S02` – Shared Workstation Session Misuse
3. `SITAS-S03` – Former Worker Identity Misuse
4. `SITAS-S04` – Excessive Privilege Abuse
5. `SITAS-S05` – Privileged Administrator Credential Compromise
6. `SITAS-S06` – Unmanaged Device Access

The integration mode additionally creates a workforce-derived scenario ID such as:

```text
SITAS-INT-LEAVER-SC1006
```

This scenario is generated from the current `workforce.csv` rather than from a hard-coded local employee record.

## 5. Risk Requirements

SITAS uses a configurable 5 × 5 model:

```text
Risk Score = Likelihood × Impact
```

Severity bands:

```text
1–4   = Low
5–9   = Medium
10–16 = High
17–25 = Critical
```

The configuration is stored in `config/risk-model.json`.

## 6. Non-Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| SITAS-NFR-01 | Scenario/resident data shall remain fictional/synthetic; group workforce records consumed by the adapter are the project's fictional TEST records. | Met |
| SITAS-NFR-02 | SITAS shall not require a live Microsoft Entra connection. | Met |
| SITAS-NFR-03 | Same inputs shall produce repeatable results. | Met |
| SITAS-NFR-04 | Risk calculations shall remain transparent and explainable. | Met |
| SITAS-NFR-05 | Source code shall remain modular. | Met |
| SITAS-NFR-06 | Invalid/missing inputs shall fail safely with understandable errors. | Met |
| SITAS-NFR-07 | No real passwords, tokens, API secrets or production credentials are required. | Met |
| SITAS-NFR-08 | Output shall be understandable for capstone demonstration. | Met |
| SITAS-NFR-09 | SITAS shall remain separate from operational JML, Flask enforcement and other team runtime components. | Met |
| SITAS-NFR-10 | Test and demonstration evidence shall be retained. | Met/ongoing |
| SITAS-NFR-11 | The same analysis engine shall be reused across scenarios. | Met |
| SITAS-NFR-12 | SITAS shall remain safe for offline demonstration and shall not perform real attacks. | Met |
| SITAS-NFR-13 | Documentation shall distinguish simulation from real enforcement. | Met |
| SITAS-NFR-14 | Sunhaven integration shall be read-only and shall not execute Graph/JML/Flask write operations. | Met |
| SITAS-NFR-15 | Integration shall use relative/explicit project paths rather than hard-coded machine-specific paths. | Met |
| SITAS-NFR-16 | Optional sanitised evidence shall be labelled as supporting snapshot evidence, not a live/current-state claim. | Met |

## 7. Individual Contribution Boundary

SITAS owns:

- threat modelling;
- attack-graph construction;
- BFS path discovery;
- risk scoring;
- control-effect simulation;
- read-only Sunhaven configuration/workforce analysis;
- automated tests;
- JSON/CSV/HTML security reporting.

SITAS does **not** own or perform:

- Joiner-Mover-Leaver changes;
- Microsoft Graph writes;
- Entra user/group/app-role changes;
- Flask authorization enforcement;
- access-review decisions/remediation;
- security monitoring/dashboard logic;
- shared-device/session enforcement;
- MFA configuration;
- device compliance enforcement.

## 8. Current Status

The current technical milestone is complete:

```text
Standalone attack-path engine               COMPLETE
Six threat scenarios                        COMPLETE
Six simulated controls                      COMPLETE
Automatic before/after comparison           COMPLETE
JSON / CSV / HTML standalone reporting      COMPLETE
Read-only Sunhaven adapter                  COMPLETE
Workforce-derived leaver analysis           COMPLETE
RBAC matrix from actual project config      COMPLETE
Optional sanitised evidence ingestion       COMPLETE
Integrated JSON / CSV / HTML reporting      COMPLETE
Automated test suite                        66 PASSING
```

Further work is evidence capture, diagram refresh and final demonstration/documentation polish rather than another core SITAS engine rewrite.

## 9. Verification Approach

Verification uses:

- automated pytest tests;
- manual standalone scenarios;
- automatic OFF/ON comparison;
- Sunhaven integration-status checks;
- workforce-derived leaver analysis;
- RBAC matrix verification;
- generated JSON/CSV/HTML reports;
- retained evidence output.
