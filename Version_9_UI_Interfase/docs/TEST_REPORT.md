# Version 9 Final — verification report

Verification date: 7 October 2026. All data used in this run was synthetic. Source and evidence are included in the archive.

## Automated suites

| Suite | Passing tests |
|---|---:|
| Main portal (unit and WSGI route integration) | 182 |
| Preserved SITAS engine | 66 |
| Preserved SAIF engine | 13 |
| Full team SMFAA detector and new validation/Graph-boundary regressions | 44 |
| Team access-review database workflows | 4 |
| **Total** | **309** |

All five suites passed. Logs: `evidence/final9/test-results.txt`.

## End-to-end HTTP verification

Both the standard local server and Waitress passed **29 scenario groups**, each making **195 HTTP requests** against a temporary isolated database. Scenarios include onboarding, role changes, termination, approval separation, agency validation, temporary coverage, qualification expiry, reviews, notifications, API authorization, connector operations, AI privacy boundaries, MFA analysis and database integrity.

| Server | Median latency | 95th percentile | Maximum |
|---|---:|---:|---:|
| Local server | 4.39 ms | 8.38 ms | 40.43 ms |
| Waitress | 4.35 ms | 9.2 ms | 41.42 ms |

These are local sequential smoke-test timings on this environment, not a load-test capacity guarantee.

## Browser and visual verification

Chromium 134.0.6998.35: **11 checks passed**, with zero recorded JavaScript page errors. Screenshots cover dashboard, AI workspace, workforce, application access, connectors, MFA and chatbot. Responsive navigation was checked at 1024, 768 and 390 pixels, including visibility, inert background, Escape behavior and document overflow.

The browser test discovered an incorrect form action in the new team page; it was fixed and the browser and server suites were rerun. Visual inspection also prompted a navigation close-button contrast fix and improved CSV form layout.

## Upgrade and integrity

- Old v9 fixture upgraded with all 42 employee identities, names and emails preserved.
- Repeated migration succeeded without changing those records.
- SQLite integrity check passed; no foreign-key errors.
- Audit ledger verification passed after migration.
- All **545 preserved original files** matched their baseline hashes.
- Local workflow retrieval regression: **30/30** curated questions passed. These are development regressions, not a general intelligence benchmark.
- Offline SMFAA CLI produced four findings from 14 synthetic events.
- Python compilation checks passed for the active portal, team app and analyzer.

## Scope of the result

The tested local features and supplied regression scenarios passed. This does not establish that every possible input, race condition, operating system or deployment is defect-free. Live Entra/Graph permissions and mutations, external model calls, email, HRIS, rostering, SIEM and Docker execution were not validated against external infrastructure. Graph pagination/security tests use simulated responses. The separate team Flask UI and PowerShell worker require tenant configuration; their database suite passed, but their live tenant workflows were not exercised.

## Reproduce

Use the commands in `docs/OPERATING_GUIDE.md`. Current evidence is under `evidence/final9`; other retained evidence and `docs_v9_baseline` are historical. The archive contains no active demo database or API secret; a fresh database is created on launch.
