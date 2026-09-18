# 02 – SITAS Secure Development and Testing Standard

## 1. Purpose

This standard defines the minimum secure-development and testing practices for the SITAS repository.

It applies to:

- Python source code;
- JSON configuration;
- threat-scenario files;
- automated tests;
- evidence;
- generated reports;
- project documentation.

It is informed by secure-development and safeguard-validation principles from the SANS policy library.

---

## 2. Development Requirements

### 2.1 Modular Design

SITAS source code should remain separated by responsibility.

Current modules include:

```text
src/model_loader.py
src/graph_engine.py
src/pathfinder.py
src/risk_engine.py
src/control_engine.py
src/sitas.py
```

A new feature should be placed in the appropriate module rather than unnecessarily duplicating existing logic.

### 2.2 Configuration Before Hard-Coding

Where practical, scenario and policy-like values should be stored in version-controlled JSON configuration rather than duplicated across Python files.

Current examples include:

```text
config/environment.json
config/controls.json
config/risk-model.json
scenarios/*.json
```

### 2.3 Safe Failure

Invalid JSON, missing required environment data and invalid risk ratings should be handled without uncontrolled failure.

Tests must verify error-handling behaviour where it is part of the implemented feature.

### 2.4 No Real Secrets

The repository must not contain:

- real passwords;
- access tokens;
- API keys;
- client secrets;
- MFA codes;
- private production credentials.

If future development introduces configuration requiring a secret, it must not be committed to the repository.

### 2.5 Synthetic Test Data

SITAS must continue to use fictional identities, credentials, sessions, applications and resident data.

Real Sunhaven Care data does not exist for this student project and must not be substituted with real healthcare information.

---

## 3. Testing Requirements

### 3.1 Automated Testing

The current project uses `pytest`.

Current verified baseline:

```text
45 tests passed
```

The suite covers:

- risk calculations and severity boundaries;
- graph construction;
- BFS path discovery;
- graph cycles;
- the Scenario 6 regression path;
- all six simulated security controls;
- JSON/model loading;
- all six scenario files.

### 3.2 Regression Testing

When a defect is discovered and corrected, a regression test should be added where practical.

Example:

```text
Scenario 6 originally reused a shared identity node.
BFS selected an unintended valid path.
A separate Remote Care Worker Identity was introduced.
A regression test now verifies the intended Scenario 6 route.
```

### 3.3 Test New Features Before Claiming Completion

A feature must not be marked `Completed` in `docs/requirements.md` until:

- the implementation exists;
- expected behaviour has been checked;
- appropriate automated or manual verification exists;
- evidence is retained where required.

### 3.4 Planned Features

At the current repository stage, these remain incomplete:

```text
SITAS-FR-14 automatic before/after comparison
SITAS-FR-20 JSON result export
SITAS-FR-21 CSV scenario summary
SITAS-FR-22 static HTML security report
```

They must remain marked as partial/planned until implemented and tested.

---

## 4. Change and Documentation Control

When code changes affect behaviour, the corresponding documentation should be reviewed.

Relevant documents include:

```text
README.md
docs/requirements.md
docs/risk-analysis.md
docs/test-plan.md
docs/requirements-traceability.md
docs/SITAS_Project_Plan.md
```

Architecture diagrams should also be updated when the implemented design materially changes.

---

## 5. SANS Reference Alignment

This standard is informed by:

- SANS **Software Development Management Policy** – security integration, testing and change-management principles.
- SANS **Safeguard Validation Management Policy** – verifying that security safeguards operate effectively.
- SANS **Configuration Management Policy** – consistent baselines and controlled change.
- SANS **Privacy Management Policy** – responsible handling of sensitive information.

SITAS applies these principles at student-project scale.
