# 02 – SITAS Secure Development and Testing Standard

## Purpose

This standard defines the minimum development and testing rules for SITAS.

## Development Rules

SITAS should:

- keep Python modules separated by responsibility;
- keep scenario, control and risk settings in version-controlled configuration where practical;
- reject invalid or missing input with understandable errors;
- avoid hard-coded machine-specific paths;
- keep Sunhaven integration read-only;
- use fictional or approved synthetic project data;
- never store real passwords, tokens, API keys, client secrets or MFA codes.

Main modules include:

```text
model_loader.py
graph_engine.py
pathfinder.py
risk_engine.py
control_engine.py
comparison_engine.py
report_generator.py
sunhaven_adapter.py
sunhaven_report_generator.py
sitas.py
```

## Testing Rules

Automated testing uses `pytest`.

Current verified result:

```text
66 passed
```

The suite covers:

- graph and BFS behaviour;
- risk calculation;
- six control simulations;
- model loading and validation;
- automatic OFF/ON comparison;
- JSON/CSV/HTML reporting;
- read-only Sunhaven integration.

After a behaviour-changing code update:

```powershell
python -m pytest -q
```

must pass before the change is treated as verified.

A feature should only be marked complete when the implementation, verification and documentation agree.

## Current Status

Automatic comparison, reporting and Sunhaven read-only integration are implemented and tested. Remaining work is final evidence, diagrams, repository cleanup and demonstration preparation.
