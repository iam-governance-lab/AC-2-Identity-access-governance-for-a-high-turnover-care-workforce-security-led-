# SITAS Security Policy Alignment Pack

## Purpose

This folder explains how the **Sunhaven Identity Threat and Attack-Path Simulator (SITAS)** supports the wider Sunhaven Care Workforce IAM project.

SITAS is an **analysis and testing tool**. It does not replace the main project's policies or operational IAM controls.

The main project goal is to reduce identity and access risk in a high-turnover care workforce through least privilege, MFA, controlled Joiner-Mover-Leaver processes, secure shared-device use, access review and verifiable evidence.

SITAS supports that goal by modelling how identity weaknesses can create attack paths and by showing the expected effect of selected controls.

## Main Project Alignment

| Main Project Area | SITAS Contribution |
|---|---|
| Access management / least privilege | Models excessive privilege and RBAC |
| Workforce lifecycle | Models former-worker access and account disablement |
| Authentication / MFA | Models stolen credentials and MFA |
| Shared-device security | Models unattended-session misuse and session controls |
| Privileged access | Models privileged-account compromise and re-authentication |
| Risk management | Uses repeatable attack paths and a 5 × 5 risk model |
| Testing and evidence | Provides automated tests, comparisons and reports |

The current Sunhaven repository consolidates its main operational policy set into:

- **POL-01 – Access Management Policy and Procedure**
- **POL-02 – Workforce Identity Lifecycle Policy and Procedure**
- **POL-03 – Authentication and Shared Device Security Policy and Procedure**

The revised proposal also describes wider governance areas such as JML, privileged access, logging, privacy, agency access and access review. SITAS uses those themes only where they are relevant to its analysis.

## Current SITAS Baseline

```text
6 threat scenarios
6 simulated controls
BFS attack-path discovery
5 × 5 risk model
automatic OFF/ON comparison
JSON / CSV / HTML reporting
read-only Sunhaven project integration
66 passing pytest tests
```

## Project Deliverables Supported

SITAS mainly supports:

- **D4 – Security Governance Pack:** policy/control alignment evidence;
- **D5 – Risk Management Pack:** attack-path and risk analysis;
- **D11 – Test and Evaluation Pack:** automated tests and comparison results;
- **D12 – Solution Handover Package:** documentation, reports and demonstration material.

SITAS can provide supporting evidence for **D10**, but it does **not** implement the group's access-review or audit system.

## Non-Overlap Boundary

SITAS does not:

- provision or disable users;
- execute JML workflows;
- enforce live RBAC or MFA;
- run the policy-compliance engine;
- perform manager access reviews;
- provide the main portal/audit dashboard;
- make live device, network or session access decisions;
- automatically remediate findings.

This keeps the individual contribution clear and separate from the wider team implementation.

## Files

| File | Purpose |
|---|---|
| `01-SITAS-policy-alignment.md` | Maps the six scenarios to Sunhaven security goals |
| `02-SITAS-secure-development-and-testing-standard.md` | Defines safe development and testing rules |
| `03-SITAS-risk-and-control-validation-standard.md` | Defines risk scoring and control-result meaning |
| `04-SITAS-evidence-and-data-handling-standard.md` | Defines safe evidence and data handling |
| `05-SITAS-control-mapping-register.md` | Provides a short scenario-to-control map |

## Scope Statement

A result such as:

```text
MFA OFF → OPEN
MFA ON  → BLOCKED
```

means the **modelled SITAS attack path** was interrupted by the simulation rule.

It does not mean SITAS changed Microsoft Entra or proved that every real-world attack path is blocked.
