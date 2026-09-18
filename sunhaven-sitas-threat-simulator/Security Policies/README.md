# SITAS Security Policy Alignment Pack

## Purpose

This folder explains how the **Sunhaven Identity Threat and Attack-Path Simulator (SITAS)** aligns with the wider Sunhaven Care security-policy framework and with recognised cybersecurity policy guidance.

These files are **not a second set of organisational Sunhaven policies**. The wider Sunhaven Care project policy set remains the source of organisational policy requirements.

The purpose of this folder is to show how SITAS:

- models risks that are relevant to the Sunhaven policy framework;
- simulates selected security controls;
- tests whether those controls block modelled attack paths;
- uses synthetic data and safe offline testing;
- records repeatable evidence for the capstone project.

---

## Current SITAS Implementation Verified

The current repository contains:

```text
6 threat scenarios
6 simulated security controls
directed graph modelling
Breadth-First Search attack-path discovery
configurable 5 × 5 risk model
66 passing automated pytest tests
manual OPEN/BLOCKED evidence for all six scenarios
```

SITAS supports standalone simulation plus a read-only adapter for approved Sunhaven project files. It does not configure Microsoft Entra, call Microsoft Graph for writes, execute JML actions, modify accounts, enforce device compliance, or use real resident information.

---

## Files in This Folder

| File | Purpose |
|---|---|
| `01-SITAS-policy-alignment.md` | Maps SITAS scenarios and controls to the Sunhaven policy areas and relevant SANS guidance |
| `02-SITAS-secure-development-and-testing-standard.md` | Defines secure development and testing expectations for SITAS |
| `03-SITAS-risk-and-control-validation-standard.md` | Defines how scenario risk and simulated-control outcomes are assessed |
| `04-SITAS-evidence-and-data-handling-standard.md` | Defines synthetic-data, secret-handling and evidence requirements |
| `05-SITAS-control-mapping-register.md` | Provides a concise traceable mapping from scenario to control, requirement, implementation and evidence |

---

## Relationship to the Wider Sunhaven Policy Set

The formal Sunhaven Care policy set currently covers these major areas:

- **POL-01 – Access Management**
- **POL-02 – Workforce Identity Lifecycle**
- **POL-03 – Authentication and Shared Device Security**

SITAS does not replace these policies. It provides an analytical simulator that demonstrates why related controls matter.

Example:

```text
Sunhaven Policy Requirement
        ↓
Identity Security Control
        ↓
SITAS Threat Scenario
        ↓
Attack Path
        ↓
Risk Assessment
        ↓
Control Simulation
        ↓
OPEN or BLOCKED
        ↓
Evidence
```

---

## SANS Reference Basis

The structure and security principles in this alignment pack are informed by the SANS/Cybersecurity Risk Foundation policy library. Relevant references include:

- SANS Cybersecurity / Information Security Policies and Standards  
  https://www.sans.org/information-security-policy
- SANS Access Management Policy  
  https://www.sans.org/information-security-policy/access-management-policy
- SANS Identity Management Policy  
  https://www.sans.org/information-security-policy/identity-management-policy
- SANS Privileged Account Management Policy  
  https://www.sans.org/information-security-policy/privileged-account-management-policy
- SANS Privacy Management Policy  
  https://www.sans.org/information-security-policy/privacy-management-policy
- SANS Software Development Management Policy  
  https://www.sans.org/information-security-policy/software-development-management-policy
- SANS Safeguard Validation Management Policy  
  https://www.sans.org/information-security-policy/safeguard-validation-management-policy
- SANS Internal Network Access Management Policy  
  https://www.sans.org/information-security-policy/internal-network-access-management-policy

These files are project-specific adaptations written for the fictional Sunhaven Care capstone environment. They are not copies of SANS templates.

---

## Important Scope Statement

SITAS demonstrates the **modelled effect** of security controls.

A result such as:

```text
MFA OFF → OPEN
MFA ON  → BLOCKED
```

means the implemented SITAS rule blocks that modelled attack path.

It does **not** mean that SITAS has enabled MFA in Microsoft Entra or proven that every possible real-world attack path has been eliminated.

This distinction must be maintained in project documentation, evidence and demonstrations.
