# SITAS Test Plan

## Project

**Project Title:** Sunhaven Identity Threat and Attack-Path Simulator (SITAS)  
**Unit:** COIT13236 Cyber Security Project

## 1. Purpose

The test plan verifies both SITAS operating modes:

- standalone attack-path simulation; and
- read-only integration with the Sunhaven Care project files.

Automated testing uses `pytest` and is supported by generated reports and command-line evidence.

## 2. Test Scope

The current suite covers:

- JSON/model loading and validation;
- graph construction and node-name mapping;
- BFS attack-path discovery, shortest paths and cycle handling;
- risk calculation and severity boundaries;
- all six security-control simulations;
- all six standalone scenario files;
- automatic before/after comparison;
- standalone JSON/CSV/HTML reporting;
- Sunhaven root discovery and source validation;
- workforce CSV loading/validation;
- duplicate employee-ID rejection;
- route-role/app-role/group-map integration;
- deterministic RBAC matrix generation;
- workforce-derived former-worker scenario generation;
- optional sanitised worker-state parsing;
- optional sanitised leaver-result parsing;
- integrated JSON/CSV/HTML reporting.

## 3. Test Environment

Run from the SITAS root:

```powershell
python -m pytest -v
```

No live Microsoft Entra connection is required for the automated suite.

## 4. Current Automated Test Summary

| Test Area | Passing Tests |
|---|---:|
| Risk engine | 14 |
| Graph and BFS | 9 |
| Control engine | 13 |
| Model loader/configuration | 9 |
| Automatic comparison | 2 |
| Standalone reporting | 3 |
| Sunhaven integration adapter/reporting | 16 |
| **Total** | **66** |

Current verified result:

```text
66 passed
```

## 5. Standalone Acceptance Checks

Standalone tests verify:

- expected attack paths are found;
- unreachable paths return no result;
- graph cycles do not cause endless processing;
- risk values match the configured 5 × 5 model;
- each control produces the expected OFF/ON behaviour;
- all six scenario files are valid;
- comparison results are deterministic;
- JSON/CSV/HTML reports are generated.

## 6. Sunhaven Integration Acceptance Checks

The integration stage is accepted when:

- a valid main-project root is detected or accepted through `--root`;
- missing required Sunhaven files are rejected with a clear error;
- `workforce.csv` is parsed without modification;
- duplicate workforce IDs are rejected;
- a Leaving/Inactive worker can drive an integrated former-worker scenario;
- the integrated leaver comparison produces `OPEN` with account control OFF and `BLOCKED` with it ON;
- `route-role-map.csv` and app roles produce the expected role/route matrix;
- CareWorker is denied `/clinical` under the current project configuration;
- Nurse is allowed `/clinical` under the current project configuration;
- optional worker-state evidence parses `AccountEnabled` safely;
- optional leaver-result evidence is only treated as supporting evidence;
- integrated JSON/CSV/HTML reports are generated;
- the adapter never executes JML or live Microsoft Graph write operations.

## 7. Manual Integrated Verification

When SITAS is located directly inside the downloaded main Sunhaven project:

```powershell
python src/sitas.py sunhaven-status
python src/sitas.py sunhaven-leaver
python src/sitas.py sunhaven-report
```

Expected current-project result includes:

```text
Workforce records: 4
Leaving records:   1
SC1006 | CareWorker | Leaving

Baseline (control OFF): OPEN
Protected (control ON): BLOCKED
Path interrupted:       YES
```

The RBAC integration should also identify five configured application roles and five configured application routes from the current repository snapshot.

## 8. Regression Requirement

After any adapter, report or documentation change:

```powershell
python -m pytest -q
```

must still complete with all tests passing before the changed SITAS folder is copied/uploaded to the main group repository.
