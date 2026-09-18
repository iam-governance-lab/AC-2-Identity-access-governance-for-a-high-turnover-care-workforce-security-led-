# 04 – SITAS Evidence and Data Handling Standard

## 1. Purpose

This standard defines how SITAS test data, screenshots, generated reports and other project evidence should be handled.

The objective is to keep the project safe, reproducible and suitable for academic assessment without exposing real credentials or personal information.

---

## 2. Synthetic Data Requirement

SITAS must use only fictional or synthetic data.

Current examples include:

- fictional attackers;
- fictional workforce identities;
- fictional stolen credentials;
- fictional sessions and devices;
- fictional Sunhaven applications;
- `Fictional Resident Records`.

Real resident, patient, worker or organisation data must not be introduced into the simulator.

---

## 3. Prohibited Sensitive Content

The repository and assessment evidence must not contain:

- passwords;
- access tokens;
- client secrets;
- API keys;
- MFA codes;
- recovery codes;
- private cryptographic keys;
- unnecessary real personal information.

Before a screenshot or report is retained, it should be checked for unnecessary identifiers or secrets.

---

## 4. Evidence Requirements

Evidence should be:

- understandable;
- linked to a test, scenario or requirement;
- repeatable where practical;
- stored using clear filenames;
- retained without editing that hides failures.

Current numbered manual evidence includes:

```text
07–18  Scenario control OFF/ON evidence
19     Risk-engine pytest evidence
20     Graph/BFS pytest evidence
21     Control-engine pytest evidence
22     Model-loader pytest evidence
23     Full-suite 45-passed evidence
```

Older development screenshots may be retained as development history but should not be confused with the final numbered evidence set.

---

## 5. Generated Reporting

Future JSON, CSV and HTML reports must:

- contain only synthetic scenario information;
- avoid secrets and unnecessary identifiers;
- clearly distinguish simulation from real enforcement;
- identify the scenario, path, risk and control outcome;
- be generated reproducibly from the implemented simulator.

These features remain planned until implemented and tested.

---

## 6. Evidence Traceability

Evidence should connect to project requirements through:

```text
docs/requirements-traceability.md
```

The preferred traceability chain is:

```text
SITAS Requirement
→ Implementation
→ Test
→ Evidence
→ Status
```

Where useful for the final capstone, this can be extended to:

```text
Sunhaven Risk/Policy Area
→ SITAS Requirement
→ Implementation
→ Test
→ Evidence
```

---

## 7. Storage and Repository Hygiene

Generated caches and temporary runtime files should not be deliberately committed.

Recommended `.gitignore` entries include:

```text
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
.env
.env.*
*.log
```

Evidence that is intentionally retained for assessment may be committed when it contains only safe project information.

---

## 8. SANS Reference Alignment

This standard is informed by:

- SANS **Privacy Management Policy** – minimisation and protection of sensitive information.
- SANS **Software Development Management Policy** – controlled development and testing.
- SANS **Safeguard Validation Management Policy** – evidence that safeguards operate as intended.
