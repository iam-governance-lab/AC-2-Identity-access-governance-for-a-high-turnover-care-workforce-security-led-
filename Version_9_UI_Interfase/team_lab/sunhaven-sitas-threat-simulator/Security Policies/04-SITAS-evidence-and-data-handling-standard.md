# 04 – SITAS Evidence and Data Handling Standard

## Purpose

This standard keeps SITAS evidence safe, traceable and suitable for the capstone project.

## Data Rules

SITAS uses fictional or synthetic information.

The read-only adapter may use approved Sunhaven TEST workforce and configuration files. It does not require real employee or resident data.

Do not store or submit:

- passwords;
- access or refresh tokens;
- client secrets;
- API keys;
- MFA or recovery codes;
- private keys;
- unnecessary personal information.

## Evidence Rules

Evidence should be:

- linked to a scenario, test or requirement;
- understandable without changing the result;
- repeatable where practical;
- clearly named;
- kept without hiding failures.

Useful evidence includes:

```text
scenario OFF/ON screenshots
pytest results
automatic comparison output
JSON / CSV / HTML reports
Sunhaven integration output
architecture diagrams
Git commit history
```

Older evidence such as the previous 45-test baseline may remain as development history. The current verified baseline is:

```text
66 passing tests
```

## Reporting Rules

Generated reports must:

- avoid secrets;
- use only safe project data;
- distinguish simulation from read-only observed evidence;
- avoid claiming live Entra enforcement;
- remain reproducible from the current implementation.

## Traceability

Use the chain:

```text
Requirement
→ Implementation
→ Test
→ Evidence
→ Status
```

Detailed mappings are maintained in:

```text
docs/requirements-traceability.md
```

## Repository Hygiene

Generated cache files should not be committed:

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
