# SITAS Requirements Traceability Matrix

## Project

**Project Title:** Sunhaven Identity Threat and Attack-Path Simulator (SITAS)  
**Unit:** COIT13236 Cyber Security Project

---

## 1. Purpose

This document links SITAS requirements to their implementation, verification method and supporting evidence.

The purpose of the matrix is to show that project requirements are not only documented but can be traced to working code, configuration, tests and evidence.

The traceability flow is:

```text
Requirement
→ Implementation
→ Verification
→ Evidence
→ Status
```

---

## 2. Functional Requirements Traceability

| Requirement | Main Implementation | Verification | Supporting Evidence | Status |
|---|---|---|---|---|
| SITAS-FR-01 Load fictional environment from JSON | `src/model_loader.py`, `config/environment.json` | `test_valid_environment_loads`, `test_real_environment_file_loads` | `evidence/22-pytest-model-loader.png` | PASS |
| SITAS-FR-02 Validate required environment data | `src/model_loader.py` | `test_environment_missing_nodes_is_rejected`, `test_environment_missing_relationships_is_rejected` | `evidence/22-pytest-model-loader.png` | PASS |
| SITAS-FR-03 Represent environment objects as graph nodes | `src/graph_engine.py` | `test_graph_creates_all_nodes` | `evidence/20-pytest-graph-bfs.png` | PASS |
| SITAS-FR-04 Represent relationships as directed graph edges | `src/graph_engine.py` | `test_graph_creates_directed_relationships` | `evidence/20-pytest-graph-bfs.png` | PASS |
| SITAS-FR-05 Define a threat source/start node per scenario | `scenarios/*.json`, `src/sitas.py` | Six scenario files load successfully | `evidence/22-pytest-model-loader.png` | PASS |
| SITAS-FR-06 Define a protected target per scenario | `scenarios/*.json`, `src/sitas.py` | Six scenario files load successfully | `evidence/22-pytest-model-loader.png` | PASS |
| SITAS-FR-07 Search for an attack path | `src/pathfinder.py` | `test_bfs_finds_attack_path` | `evidence/20-pytest-graph-bfs.png` | PASS |
| SITAS-FR-08 Use BFS for path discovery | `src/pathfinder.py` | BFS path and shortest-path tests | `evidence/20-pytest-graph-bfs.png` | PASS |
| SITAS-FR-09 Prevent cycles causing infinite processing | `src/pathfinder.py` visited-node logic | `test_bfs_handles_graph_cycle` | `evidence/20-pytest-graph-bfs.png` | PASS |
| SITAS-FR-10 Calculate likelihood × impact risk | `src/risk_engine.py` | Scenario risk tests | `evidence/19-pytest-risk-engine.png` | PASS |
| SITAS-FR-11 Classify Low, Medium, High or Critical severity | `src/risk_engine.py`, `config/risk-model.json` | Risk severity boundary tests | `evidence/19-pytest-risk-engine.png` | PASS |
| SITAS-FR-12 Support simulated security controls | `src/control_engine.py`, `config/controls.json` | Control-engine test suite | `evidence/21-pytest-control-engine.png` | PASS |
| SITAS-FR-13 Determine whether control blocks attack path | `src/control_engine.py`, `src/sitas.py` | Six enabled/disabled control pairs | `evidence/21-pytest-control-engine.png`, evidence 07–18 | PASS |
| SITAS-FR-14 Compare attack exposure before and after controls | `src/comparison_engine.py`, `src/analysis_engine.py` | `test_compare_scenario_shows_open_then_blocked` plus scenario report generation | Existing OFF/ON screenshots and generated reports | PASS |
| SITAS-FR-15 Display understandable attack-path results | `src/sitas.py`, node names from `src/graph_engine.py` | Manual scenario execution | Scenario evidence 07–18 | PASS |
| SITAS-FR-16 Support multiple scenarios through the same engine | `src/sitas.py`, `scenarios/*.json` | `test_all_six_scenario_files_load` plus manual runs | `evidence/22-pytest-model-loader.png`, scenario evidence | PASS |
| SITAS-FR-17 Load risk settings from JSON | `config/risk-model.json`, `src/model_loader.py` | `test_real_risk_model_loads` | `evidence/22-pytest-model-loader.png` | PASS |
| SITAS-FR-18 Validate likelihood and impact values | `src/risk_engine.py` | invalid likelihood, invalid impact and non-integer tests | `evidence/19-pytest-risk-engine.png` | PASS |
| SITAS-FR-19 Support automated testing | `tests/`, `pytest.ini` | Full pytest execution | Existing test evidence; current verified run 66 passed | PASS |
| SITAS-FR-20 Export structured JSON results | `src/report_generator.py` | `test_json_report_generated` | `reports/sitas-analysis.json` | PASS |
| SITAS-FR-21 Generate CSV scenario summary | `src/report_generator.py` | `test_csv_summary_generated` | `reports/sitas-summary.csv` | PASS |
| SITAS-FR-22 Generate static HTML security report | `src/report_generator.py` | `test_html_report_generated` | `reports/sitas-threat-report.html` | PASS |

---

## 3. Non-Functional Requirements Traceability

| Requirement | Implementation / Design Evidence | Verification | Status |
|---|---|---|---|
| SITAS-NFR-01 Fictional/synthetic data only | `config/environment.json`, scenario files, fictional resident target | Documentation and configuration review | PASS |
| SITAS-NFR-02 No live Microsoft Entra dependency | Standalone Python and JSON architecture | Source/design review | PASS |
| SITAS-NFR-03 Repeatable results for same input | Deterministic graph, BFS, risk and control logic | Automated test suite | PASS |
| SITAS-NFR-04 Explainable risk calculations | `risk-model.json`, `risk_engine.py` | Risk tests and documentation | PASS |
| SITAS-NFR-05 Modular Python source | Separate loader, graph, pathfinder, risk and control modules | Architecture/source review | PASS |
| SITAS-NFR-06 Safe handling of current invalid JSON/risk input | `model_loader.py`, `risk_engine.py` | Model-loader and invalid-risk tests | PASS |
| SITAS-NFR-07 No real passwords/tokens/secrets required | Offline synthetic design | Project/source review | PASS |
| SITAS-NFR-08 Understandable for capstone demonstration | Modular output, diagrams, README and evidence | Demonstration preparation / mentor demo | ONGOING |
| SITAS-NFR-09 Independent from other team runtime components | Standalone SITAS repository and offline model | Architecture/design review | PASS |
| SITAS-NFR-10 Retain testing evidence | `evidence/`, test files, screenshots | Evidence review | PASS / ONGOING |
| SITAS-NFR-11 Reuse same engine across scenarios | Shared `sitas.py` and modules | Six scenario executions | PASS |
| SITAS-NFR-12 Safe offline demonstration | No real attack or production dependency | Design/source review | PASS |
| SITAS-NFR-13 Distinguish simulation from real enforcement | README, policies, requirements and risk-analysis wording | Documentation review | PASS / ONGOING |

---

## 4. Scenario-to-Control Traceability

| Scenario | Security Problem | Related Control | Manual Evidence | Automated Verification |
|---|---|---|---|---|
| SITAS-S01 | Stolen nurse credential | CTRL-MFA | 07 / 08 | MFA OFF/ON control tests |
| SITAS-S02 | Shared active session | CTRL-SESSION | 09 / 10 | Session OFF/ON control tests |
| SITAS-S03 | Former-worker identity | CTRL-ACCOUNT | 11 / 12 | Account OFF/ON control tests |
| SITAS-S04 | Excessive privilege | CTRL-RBAC | 13 / 14 | RBAC OFF/ON control tests |
| SITAS-S05 | Privileged admin compromise | CTRL-PRIVAUTH | 15 / 16 | Privileged re-auth OFF/ON tests |
| SITAS-S06 | Unmanaged-device access | CTRL-DEVICE | 17 / 18 | Device OFF/ON tests and Scenario 6 BFS regression test |

---

---

## 5. Sunhaven Integration Requirements Traceability

| Requirement | Main Implementation | Verification | Status |
|---|---|---|---|
| SITAS-FR-23 Locate Sunhaven project root | `src/sunhaven_adapter.py` | `test_resolve_sunhaven_root_detects_parent_of_sitas`, root validation tests | PASS |
| SITAS-FR-24 Read/validate workforce data | `load_workforce()` | workforce and duplicate-ID tests | PASS |
| SITAS-FR-25 Read/validate route-role/app-role/group maps | `build_sunhaven_snapshot()` | adapter and RBAC tests | PASS |
| SITAS-FR-26 Generate Sunhaven-derived former-worker scenario | `build_integrated_leaver_comparison()` | integrated leaver test | PASS |
| SITAS-FR-27 Generate role/route matrix | `build_rbac_matrix()` | CareWorker/Nurse route tests | PASS |
| SITAS-FR-28 Ingest optional sanitised state/evidence | `load_worker_state_csv()`, `load_leaver_result_json()` | parser/evidence tests | PASS |
| SITAS-FR-29 Generate integrated JSON/CSV/HTML reports | `src/sunhaven_report_generator.py` | integration report test | PASS |

## 6. Group-Project Alignment and Ownership Boundary

| SITAS Area | Sunhaven Project Relationship | Boundary |
|---|---|---|
| S01 Stolen credential / MFA | Supports strong-authentication threat analysis | SITAS models expected effect; it does not configure MFA |
| S02 Shared session | Supports shared-device/session threat modelling | SITAS does not manage sessions/devices |
| S03 Former worker | Reads `workforce.csv`; maps to leaver/account-disablement objective | SITAS does not execute JML or disable accounts |
| S04 Excessive privilege | Reads route-role/app-role/group configuration | SITAS does not enforce Flask/Entra RBAC |
| S05 Privileged compromise | Security extension analysis | No live privileged re-auth enforcement is claimed |
| S06 Unmanaged device | Future-production control analysis | No MDM/device-compliance implementation is claimed |

## 7. Current Coverage Summary

All current functional requirements SITAS-FR-01 through SITAS-FR-29 are implemented and covered by source/configuration review, automated tests or generated reports.

Current verified automated result:

```text
66 passed
```

The next work is evidence capture, diagram refresh and final demonstration/documentation polish rather than another core implementation phase.

## 8. Traceability Maintenance

Update this matrix whenever requirements, source contracts, tests, evidence filenames or group integration interfaces change.
