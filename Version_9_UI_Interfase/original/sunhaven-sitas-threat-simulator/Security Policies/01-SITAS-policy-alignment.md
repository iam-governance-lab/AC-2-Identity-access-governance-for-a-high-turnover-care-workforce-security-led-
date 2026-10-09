# 01 – SITAS Policy Alignment

## Purpose

This document maps the six SITAS scenarios to the security goals of the Sunhaven Care Workforce IAM project.

SITAS supports the project through **simulation and analysis**, not operational enforcement.

## Scenario Alignment

| Scenario | Simulated Control | Main Sunhaven Alignment |
|---|---|---|
| S01 – Stolen Nurse Credential | `CTRL-MFA` | POL-03: MFA and authentication protection |
| S02 – Shared Workstation Session Misuse | `CTRL-SESSION` | POL-03: shared-device and session security |
| S03 – Former Worker Identity Misuse | `CTRL-ACCOUNT` | POL-02 + POL-01: timely leaver access removal |
| S04 – Excessive Privilege Abuse | `CTRL-RBAC` | POL-01: least privilege and role-based access |
| S05 – Privileged Administrator Compromise | `CTRL-PRIVAUTH` | POL-01 + POL-03: protected privileged access |
| S06 – Unmanaged Device Access | `CTRL-DEVICE` | Future device-control security principle |

## Important Boundary

The wider project treats enterprise device compliance, MDM and kiosk controls as future/production controls. Therefore, Scenario 6 is a **simulation only** and must not be described as currently enforced by the Sunhaven laboratory.

SITAS also follows the wider project's principles for:

- fictional/synthetic data;
- no secrets in evidence;
- repeatable testing;
- clear traceability;
- honest separation between simulated and live controls.

Detailed requirement-to-code-to-test mapping remains in:

```text
docs/requirements-traceability.md
```
