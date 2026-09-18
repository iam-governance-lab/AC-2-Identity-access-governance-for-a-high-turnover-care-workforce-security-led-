# 03 – SITAS Risk and Control Validation Standard

## 1. Purpose

This standard defines how SITAS scenario risk and simulated security-control outcomes are evaluated.

It supports consistent and explainable results across all threat scenarios.

---

## 2. Risk Model

SITAS currently uses a configurable 5 × 5 model stored in:

```text
config/risk-model.json
```

Calculation:

```text
Risk Score = Likelihood × Impact
```

Likelihood and impact use values from 1 to 5.

The risk engine must read the configured model rather than duplicate severity thresholds unnecessarily in scenario code.

---

## 3. Current Severity Terminology

The current repository uses:

```text
1–4   Low
5–9   Medium
10–16 High
17–25 Critical
```

This standard records the **current implemented repository state**.

The wider Sunhaven proposal currently uses the term `Extreme` for its 17–25 group-level risk band. If the project team decides to harmonise the terminology, the change must be made consistently across:

```text
config/risk-model.json
src/risk_engine.py if required
tests/test_risk_engine.py
README.md
docs/risk-analysis.md
docs/requirements.md
docs/test-plan.md
progress documentation
relevant diagrams
```

The tests must then be rerun before the updated terminology is treated as verified.

---

## 4. Scenario Risk Values

Current implemented scenario values are:

| Scenario | Likelihood | Impact | Score | Current Severity |
|---|---:|---:|---:|---|
| SITAS-S01 | 4 | 5 | 20 | Critical |
| SITAS-S02 | 3 | 5 | 15 | High |
| SITAS-S03 | 3 | 4 | 12 | High |
| SITAS-S04 | 3 | 5 | 15 | High |
| SITAS-S05 | 2 | 5 | 10 | High |
| SITAS-S06 | 3 | 4 | 12 | High |

The ratings are fictional project ratings used for demonstration. They are not statistical predictions of real incident frequency.

---

## 5. Control Validation

Each scenario references one relevant control:

```text
S01 → CTRL-MFA
S02 → CTRL-SESSION
S03 → CTRL-ACCOUNT
S04 → CTRL-RBAC
S05 → CTRL-PRIVAUTH
S06 → CTRL-DEVICE
```

The control engine evaluates whether the configured control rule blocks the discovered modelled path.

Current manual evidence demonstrates:

```text
Control disabled → OPEN
Control enabled  → BLOCKED
```

for all six scenarios.

---

## 6. Meaning of OPEN and BLOCKED

### OPEN

`OPEN` means the discovered modelled path remains reachable under the current SITAS control state.

### BLOCKED

`BLOCKED` means the implemented SITAS simulation rule prevents the identified modelled path from progressing under that control state.

A `BLOCKED` result does not prove:

- every possible attack path is eliminated;
- the equivalent real-world control is perfectly effective;
- the control is deployed in Microsoft Entra;
- the real organisation is compliant.

---

## 7. Residual Risk

The current SITAS implementation does **not** calculate a separate residual likelihood, impact or numerical residual-risk score after a control is applied.

Therefore, current reports should state:

```text
Before Control: OPEN
After Control:  BLOCKED
```

and should not invent a numerical residual-risk value.

A residual-risk feature may be added later only if its method is defined, justified, implemented and tested.

---

## 8. Validation Evidence

Risk and control behaviour is verified through:

- `tests/test_risk_engine.py`;
- `tests/test_control_engine.py`;
- `tests/test_graph_pathfinder.py`;
- scenario screenshots under `evidence/`;
- the full pytest suite.

Current full-suite evidence:

```text
evidence/23-pytest-full-suite-45-passed.png
```

---

## 9. SANS Reference Alignment

This standard is informed by:

- SANS **Safeguard Selection Management Policy** – selecting safeguards according to risk.
- SANS **Safeguard Validation Management Policy** – validating safeguard effectiveness.
- SANS **Access Management Policy** – least privilege and role-based access principles.
- SANS **Identity Management Policy** – identity lifecycle and strong-authentication principles.
