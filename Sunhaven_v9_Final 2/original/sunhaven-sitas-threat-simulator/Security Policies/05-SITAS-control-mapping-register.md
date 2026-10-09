# 05 – SITAS Control Mapping Register

## Purpose

This register provides a short mapping between SITAS scenarios, controls and the main Sunhaven project goals.

| Scenario | Main Project Security Goal | SITAS Control | Main Implementation |
|---|---|---|---|
| S01 – Stolen Nurse Credential | Strong authentication | `CTRL-MFA` | `control_engine.py` |
| S02 – Shared Session | Secure shared-device sessions | `CTRL-SESSION` | `control_engine.py` |
| S03 – Former Worker | Prompt leaver access removal | `CTRL-ACCOUNT` | `control_engine.py`, `sunhaven_adapter.py` |
| S04 – Excessive Privilege | Least privilege / RBAC | `CTRL-RBAC` | `control_engine.py`, `sunhaven_adapter.py` |
| S05 – Privileged Admin Compromise | Protected privileged access | `CTRL-PRIVAUTH` | `control_engine.py` |
| S06 – Unmanaged Device | Device-aware access | `CTRL-DEVICE` | `control_engine.py` |

## Current Technical Baseline

```text
6/6 scenarios implemented
6/6 simulated controls implemented
automatic OFF/ON comparison implemented
JSON / CSV / HTML reporting implemented
read-only Sunhaven integration implemented
66 automated tests passing
```

## Interpretation

The values in `config/controls.json` are SITAS simulation states.

They do not represent the live configuration of Microsoft Entra or the wider Sunhaven runtime.

For detailed requirement IDs, tests and evidence, use:

```text
docs/requirements-traceability.md
```
