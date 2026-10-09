# 03 – SITAS Risk and Control Validation Standard

## Purpose

This standard keeps SITAS risk and control results consistent and easy to explain.

## Risk Model

SITAS uses:

```text
Risk Score = Likelihood × Impact
```

with values from 1 to 5.

Severity bands:

```text
1–4   Low
5–9   Medium
10–16 High
17–25 Critical
```

The model is stored in:

```text
config/risk-model.json
```

Current scenario ratings are:

| Scenario | Score | Severity |
|---|---:|---|
| S01 – Stolen Nurse Credential | 20 | Critical |
| S02 – Shared Session | 15 | High |
| S03 – Former Worker | 12 | High |
| S04 – Excessive Privilege | 15 | High |
| S05 – Privileged Admin Compromise | 10 | High |
| S06 – Unmanaged Device | 12 | High |

These are deterministic project ratings for demonstration, not predictions of real incident probability.

## Control Validation

Each scenario has one main simulated control:

```text
S01 → CTRL-MFA
S02 → CTRL-SESSION
S03 → CTRL-ACCOUNT
S04 → CTRL-RBAC
S05 → CTRL-PRIVAUTH
S06 → CTRL-DEVICE
```

Automatic comparison evaluates the model with the related control OFF and ON.

```text
OPEN    = the identified modelled path remains reachable
BLOCKED = the SITAS rule interrupts that identified path
```

A BLOCKED result does not prove that all possible attacks are removed or that the equivalent control is live in Microsoft Entra.

SITAS does not currently calculate a separate numerical residual-risk score after a control is applied, so reports should not invent one.
