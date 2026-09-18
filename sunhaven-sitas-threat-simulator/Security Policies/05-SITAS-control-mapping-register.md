# 05 – SITAS Control Mapping Register

## Purpose

This register provides a concise mapping between the current SITAS threat scenarios, controls, subsystem requirements, implementation and evidence.

It is intended to support assessment traceability and policy alignment.

---

| Scenario | Related Security Problem | Control | Key SITAS Requirements | Main Implementation | Evidence |
|---|---|---|---|---|---|
| SITAS-S01 – Stolen Nurse Credential | Password compromise | `CTRL-MFA` | SITAS-FR-12, 13, 14 | `control_engine.py` MFA rule | `07`, `08`, `21`, `23` |
| SITAS-S02 – Shared Workstation Session Misuse | Active session reuse | `CTRL-SESSION` | SITAS-FR-12, 13, 14 | `control_engine.py` session rule | `09`, `10`, `21`, `23` |
| SITAS-S03 – Former Worker Identity Misuse | Stale former-worker access | `CTRL-ACCOUNT` | SITAS-FR-12, 13, 14 | `control_engine.py` account rule | `11`, `12`, `21`, `23` |
| SITAS-S04 – Excessive Privilege Abuse | Excessive permissions | `CTRL-RBAC` | SITAS-FR-12, 13, 14 | `control_engine.py` RBAC rule | `13`, `14`, `21`, `23` |
| SITAS-S05 – Privileged Administrator Credential Compromise | Privileged account compromise | `CTRL-PRIVAUTH` | SITAS-FR-12, 13, 14 | `control_engine.py` privileged re-auth rule | `15`, `16`, `21`, `23` |
| SITAS-S06 – Unmanaged Device Access | Untrusted-device access | `CTRL-DEVICE` | SITAS-FR-12, 13, 14 | `control_engine.py` trusted-device rule | `17`, `18`, `20`, `21`, `23` |

---

## Supporting Cross-Cutting Requirements

| Requirement | Policy/Assurance Purpose |
|---|---|
| SITAS-FR-07 / 08 / 09 | Discover paths safely using BFS and handle cycles |
| SITAS-FR-10 / 11 | Provide explainable risk scoring |
| SITAS-FR-17 / 18 | Keep risk configuration explicit and validate ratings |
| SITAS-FR-19 | Provide automated verification |
| SITAS-NFR-01 | Use synthetic data |
| SITAS-NFR-02 | Remain independent of live Entra |
| SITAS-NFR-07 | Avoid real secrets |
| SITAS-NFR-09 | Remain separate from operational IAM runtime |
| SITAS-NFR-10 | Retain assessment evidence |
| SITAS-NFR-12 | Remain safe for offline demonstration |
| SITAS-NFR-13 | Avoid claiming simulation is real enforcement |

---

## Control Status Interpretation

The values in `config/controls.json` represent the current simulation configuration.

They do not represent the real operational status of controls in Microsoft Entra or the wider Sunhaven IAM laboratory.

The purpose of the simulator is to evaluate the modelled security effect of changing those states.

---

## Current Verification Baseline

At the time this register was prepared:

```text
6/6 threat scenarios implemented
6/6 control simulation rules implemented
12 manual OFF/ON scenario outcomes evidenced
45 automated tests passing
```

This register should be updated if scenarios, control IDs, evidence filenames or requirements change.
