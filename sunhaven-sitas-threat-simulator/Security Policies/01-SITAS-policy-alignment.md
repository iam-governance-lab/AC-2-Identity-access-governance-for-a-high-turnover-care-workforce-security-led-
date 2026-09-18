# 01 – SITAS Policy Alignment

## 1. Purpose

This document maps SITAS threat scenarios and simulated controls to the relevant areas of the wider Sunhaven Care security-policy framework.

SITAS is an analytical and educational simulator. It does not replace the formal Sunhaven Care policy and procedure set and does not operationally enforce those policies.

---

## 2. Alignment Principles

SITAS follows these policy-alignment principles:

1. **Least privilege** – access should be restricted to approved duties.
2. **Strong authentication** – a stolen password should not automatically provide sensitive access.
3. **Identity lifecycle control** – access should be removed when a worker leaves.
4. **Session protection** – authenticated sessions on shared devices should not remain unnecessarily usable.
5. **Privileged-access protection** – administrative access requires stronger safeguards.
6. **Device-aware access** – higher-risk access may require a trusted device or equivalent control.
7. **Synthetic data** – testing must not use real resident or employee data.
8. **Evidence and validation** – security-control behaviour should be repeatable and testable.

---

## 3. Scenario-to-Policy Alignment

| SITAS Scenario | Security Problem | Simulated Control | Sunhaven Policy Area | Alignment Status |
|---|---|---|---|---|
| SITAS-S01 – Stolen Nurse Credential | Password compromise | `CTRL-MFA` Multi-Factor Authentication | POL-03 Authentication and Shared Device Security | Direct alignment |
| SITAS-S02 – Shared Workstation Session Misuse | Reuse of an unattended authenticated session | `CTRL-SESSION` Session Timeout | POL-03 Authentication and Shared Device Security | Direct alignment |
| SITAS-S03 – Former Worker Identity Misuse | Access remains available after departure | `CTRL-ACCOUNT` Account Disablement | POL-02 Workforce Identity Lifecycle + POL-01 Access Management | Direct alignment |
| SITAS-S04 – Excessive Privilege Abuse | User has access beyond approved duties | `CTRL-RBAC` Role-Based Access Control | POL-01 Access Management | Direct alignment |
| SITAS-S05 – Privileged Administrator Credential Compromise | Compromised privileged identity | `CTRL-PRIVAUTH` Privileged Re-authentication | POL-01 Access Management + POL-03 Authentication | Direct alignment |
| SITAS-S06 – Unmanaged Device Access | Credential used from an untrusted device | `CTRL-DEVICE` Trusted Device Restriction | POL-03 device/shared-device security principles | Future-control simulation |

---

## 4. Important Note for Scenario 6

The current wider Sunhaven project treats enterprise device-compliance controls such as MDM, kiosk enforcement and compliant-device requirements as future or out-of-MVP controls.

Therefore, SITAS-S06 must be described as:

> a simulation of the security benefit that a trusted-device restriction could provide.

It must **not** be described as a control currently enforced in the Sunhaven Entra laboratory.

---

## 5. Relevant SANS Guidance

The alignment is consistent with themes found in the SANS policy library:

- **Access Management Policy** – identity verification, least privilege, RBAC and periodic review.
- **Identity Management Policy** – identity lifecycle, MFA and role-based access principles.
- **Privileged Account Management Policy** – stronger controls for privileged accounts, least privilege and MFA.
- **Internal Network Access Management Policy** – identity-based access, device awareness and role-based controls.
- **Privacy Management Policy** – protection and minimisation of sensitive information.
- **Safeguard Validation Management Policy** – verification that security safeguards operate as intended.

SITAS uses these concepts as design guidance only.

---

## 6. Relationship to SITAS Requirements

Relevant SITAS requirements include:

```text
SITAS-FR-10  Calculate scenario risk
SITAS-FR-11  Classify risk severity
SITAS-FR-12  Support simulated security controls
SITAS-FR-13  Determine whether a control blocks an attack path
SITAS-FR-14  Compare exposure before and after a control
SITAS-FR-19  Support automated testing

SITAS-NFR-01 Use fictional/synthetic data
SITAS-NFR-02 Operate without live Entra
SITAS-NFR-07 Require no real secrets
SITAS-NFR-09 Remain independent from operational IAM
SITAS-NFR-12 Remain safe for offline demonstration
SITAS-NFR-13 Distinguish simulation from real enforcement
```

Detailed requirement-to-code-to-test evidence is maintained in:

```text
docs/requirements-traceability.md
```

---

## 7. Alignment Conclusion

SITAS is aligned with the Sunhaven policy areas that are relevant to identity threats, authentication, lifecycle management, least privilege, privileged access and shared-device security.

The alignment is demonstrated through **simulated attack paths and control outcomes**, not through operational policy enforcement.
