# SITAS Risk Analysis

## Project

**Project Title:** Sunhaven Identity Threat and Attack-Path Simulator (SITAS)  
**Unit:** COIT13236 Cyber Security Project

---

## 1. Purpose

This document records the identity-related cybersecurity risks modelled by SITAS for the fictional Sunhaven Care environment.

The purpose is to identify important assets, describe the threat or weakness represented by each scenario, assess likelihood and impact using the SITAS 5 × 5 model, and identify the simulated security control used to treat the risk.

SITAS is a simulation. The risk ratings apply to the fictional project scenarios and should not be interpreted as a formal organisational risk assessment for a real healthcare provider.

---

## 2. Sunhaven Security Context

Sunhaven Care relies on workforce identities, credentials, sessions, shared workstations, applications and privileged functions to provide access to protected fictional resident information.

Identity-related weaknesses may allow an attacker or unauthorised user to move through several connected objects before reaching a protected asset.

Examples modelled by SITAS include:

- stolen user credentials;
- unattended authenticated sessions;
- former-worker identities remaining usable;
- excessive permissions;
- compromised privileged administrator credentials;
- access from unmanaged devices.

SITAS represents these relationships as a directed graph and uses BFS to identify a reachable attack path.

---

## 3. Assets Requiring Protection

| Asset | Importance to the SITAS Model | Main Security Concern |
|---|---|---|
| Fictional Resident Records | Represents protected resident information in the Sunhaven case | Unauthorised disclosure or modification |
| Sunhaven Care Portal | Main application path used to reach protected information | Unauthorised application access |
| Workforce Identities | Determine which worker or attacker can authenticate | Identity misuse and credential compromise |
| Active User Sessions | May provide access without a new authentication event | Session reuse or hijacking |
| Shared Workstations | Used in care-work scenarios and may retain active sessions | Unattended authenticated access |
| Restricted Admin Function | Represents higher-privilege functionality | Excessive privilege |
| Restricted Admin Console | Represents privileged administrative access | Administrator account compromise |
| Device Trust State | Represents whether access originates from a trusted or unmanaged device | Untrusted-device access |

The model uses fictional assets and does not contain real resident, employee or production data.

---

## 4. Risk Assessment Method

SITAS uses a configurable 5 × 5 model.

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

The configuration is stored in:

```text
config/risk-model.json
```

The current risk engine validates likelihood and impact values before calculating the score.

---

## 5. Threat and Risk Register

| ID | Threat / Weakness | Primary Asset at Risk | Likelihood | Impact | Score | Severity | Main Control |
|---|---|---|---:|---:|---:|---|---|
| SITAS-S01 | Stolen nurse password used to access Sunhaven resources | Fictional Resident Records | 4 – Likely | 5 – Severe | 20 | Critical | Multi-Factor Authentication |
| SITAS-S02 | Unauthorised reuse of an active session on an unattended shared workstation | Fictional Resident Records | 3 – Possible | 5 – Severe | 15 | High | Session Timeout |
| SITAS-S03 | Former worker identity remains usable after employment ends | Fictional Resident Records | 3 – Possible | 4 – Major | 12 | High | Account Disablement |
| SITAS-S04 | Care worker receives excessive privilege and can reach restricted functionality | Restricted Admin Function / Resident Records | 3 – Possible | 5 – Severe | 15 | High | Role-Based Access Control |
| SITAS-S05 | Privileged administrator credential is compromised | Restricted Admin Console / Resident Records | 2 – Unlikely | 5 – Severe | 10 | High | Privileged Re-authentication |
| SITAS-S06 | Stolen care-worker credential is used from an unmanaged device | Sunhaven Care Portal / Resident Records | 3 – Possible | 4 – Major | 12 | High | Trusted Device Restriction |

---

## 6. Scenario Analysis

### SITAS-S01 – Stolen Nurse Credential

Attack path:

```text
External Attacker
→ Stolen Nurse Password
→ Nurse Identity
→ Shared Nurse Workstation
→ Sunhaven Care Portal
→ Fictional Resident Records
```

Risk:

```text
Likelihood: 4 – Likely
Impact: 5 – Severe
Score: 20/25
Severity: Critical
```

Treatment:

```text
CTRL-MFA – Multi-Factor Authentication
```

Observed simulator result:

```text
MFA OFF → OPEN
MFA ON  → BLOCKED
```

This scenario demonstrates that password compromise creates a critical modelled path when password-only authentication is sufficient.

---

### SITAS-S02 – Shared Workstation Session Misuse

Attack path:

```text
Unauthorised Person
→ Unattended Shared Workstation
→ Active Nurse Session
→ Sunhaven Care Portal
→ Fictional Resident Records
```

Risk:

```text
Likelihood: 3 – Possible
Impact: 5 – Severe
Score: 15/25
Severity: High
```

Treatment:

```text
CTRL-SESSION – Session Timeout
```

Observed simulator result:

```text
Session Timeout OFF → OPEN
Session Timeout ON  → BLOCKED
```

This scenario demonstrates that protecting credentials alone is not sufficient if an authenticated session remains available on a shared workstation.

---

### SITAS-S03 – Former Worker Identity Misuse

Attack path:

```text
Former Worker
→ Former Worker Identity
→ Sunhaven Care Portal
→ Fictional Resident Records
```

Risk:

```text
Likelihood: 3 – Possible
Impact: 4 – Major
Score: 12/25
Severity: High
```

Treatment:

```text
CTRL-ACCOUNT – Account Disablement
```

Observed simulator result:

```text
Account Disablement OFF → OPEN
Account Disablement ON  → BLOCKED
```

This scenario demonstrates the importance of promptly disabling access that is no longer required.

---

### SITAS-S04 – Excessive Privilege Abuse

Attack path:

```text
Compromised Care Worker
→ Care Worker Identity
→ Over-Privileged Role
→ Restricted Admin Function
→ Fictional Resident Records
```

Risk:

```text
Likelihood: 3 – Possible
Impact: 5 – Severe
Score: 15/25
Severity: High
```

Treatment:

```text
CTRL-RBAC – Role-Based Access Control
```

Observed simulator result:

```text
RBAC OFF → OPEN
RBAC ON  → BLOCKED
```

This scenario demonstrates the security value of least privilege and role-based permission boundaries.

---

### SITAS-S05 – Privileged Administrator Credential Compromise

Attack path:

```text
External Admin Attacker
→ Stolen Admin Credential
→ Privileged Admin Identity
→ Restricted Admin Console
→ Fictional Resident Records
```

Risk:

```text
Likelihood: 2 – Unlikely
Impact: 5 – Severe
Score: 10/25
Severity: High
```

Treatment:

```text
CTRL-PRIVAUTH – Privileged Re-authentication
```

Observed simulator result:

```text
Privileged Re-authentication OFF → OPEN
Privileged Re-authentication ON  → BLOCKED
```

The likelihood is lower than several other scenarios, but the impact remains severe because privileged access has a high potential consequence.

---

### SITAS-S06 – Unmanaged Device Access

Attack path:

```text
External Device Attacker
→ Stolen Care Worker Credential
→ Remote Care Worker Identity
→ Unmanaged Device Session
→ Sunhaven Care Portal
→ Fictional Resident Records
```

Risk:

```text
Likelihood: 3 – Possible
Impact: 4 – Major
Score: 12/25
Severity: High
```

Treatment:

```text
CTRL-DEVICE – Trusted Device Restriction
```

Observed simulator result:

```text
Trusted Device Restriction OFF → OPEN
Trusted Device Restriction ON  → BLOCKED
```

This scenario demonstrates that identity assurance can be strengthened by considering the device used to access a sensitive application.

---

## 7. Risk Treatment Summary

| Scenario | Initial Severity | Simulated Control | Control Disabled | Control Enabled |
|---|---|---|---|---|
| S01 | Critical | MFA | OPEN | BLOCKED |
| S02 | High | Session Timeout | OPEN | BLOCKED |
| S03 | High | Account Disablement | OPEN | BLOCKED |
| S04 | High | RBAC | OPEN | BLOCKED |
| S05 | High | Privileged Re-authentication | OPEN | BLOCKED |
| S06 | High | Trusted Device Restriction | OPEN | BLOCKED |

The current simulator evaluates whether the identified attack path remains reachable after the control rule is applied.

SITAS does **not** currently recalculate a separate residual likelihood, impact or residual risk score after control application. Therefore, the correct result to report at this stage is the change in modelled path status:

```text
OPEN → BLOCKED
```

rather than inventing a lower residual risk score.

---

## 8. Relationship to Sunhaven Security Policies

The risks and controls align with the project-specific policy set:

| Risk Area | Related Policy |
|---|---|
| Credential compromise | Multi-Factor Authentication Policy |
| Unattended sessions | Shared Workstation and Session Security Policy |
| Former-worker access | Account Lifecycle and Termination Policy |
| Excessive permissions | RBAC and Least Privilege Policy |
| Privileged account compromise | Privileged Access Security Policy |
| Unmanaged-device access | Trusted Device and Remote Access Policy |
| Risk scoring | Cybersecurity Risk Assessment Policy |
| Safe project testing | Secure Testing and Synthetic Data Policy |

The policies define the expected security position. SITAS demonstrates the modelled security effect of the related controls.

---

## 9. Limitations and Assumptions

The current risk analysis has the following limitations:

- all users, credentials, devices and resident records are fictional;
- SITAS uses synthetic offline scenarios rather than live threat telemetry;
- likelihood and impact values are scenario-defined project ratings;
- the ratings are not statistical predictions of real incident frequency;
- BFS identifies a shortest reachable path in the current directed graph;
- the graph does not represent every possible real-world attack technique;
- security controls are simulations rather than operational Microsoft Entra enforcement;
- a BLOCKED result means the implemented SITAS control rule blocks the modelled path;
- a BLOCKED result does not prove that all possible real-world attack paths have been eliminated;
- SITAS does not currently calculate a numerical residual-risk score after control application.

These limitations keep the project claims consistent with the implemented simulator.

---

## 10. Conclusion

The current SITAS model contains one Critical and five High initial scenario risks.

The six scenarios cover different identity-related weaknesses affecting the fictional Sunhaven environment. Each scenario is associated with a specific security control, and current manual and automated testing confirms that the implemented control simulation changes the modelled attack outcome from OPEN to BLOCKED.

This risk analysis provides the security justification for the scenario requirements, control implementation and testing performed in SITAS.
