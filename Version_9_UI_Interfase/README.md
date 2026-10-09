# Sunhaven Identity & Access Governance — Version 9 Final

Consolidated source release: original v9 + compatible portal features from v10–v14 + the supplied teammate lab. Release identifier: **9.0-final**. Internal migration filenames retain their original numbers to preserve upgrade compatibility.

## Run the main application

1. Extract the whole ZIP. Open the extracted `Sunhaven_v9_Final` folder in Visual Studio Code.
2. Install Python **3.12 or later**. Open a terminal in this folder.
3. Run `python run.py` (macOS/Linux: `python3 run.py`).
4. Open **http://127.0.0.1:8000**. Choose an identity and select **Enter demo workspace**.
5. For the full demonstration, select **SC1005**, the IAM operator. **SC1002** demonstrates manager permissions; **SC1001** demonstrates nurse permissions.

The local demo needs no API key, password or third-party package. It creates a fresh synthetic database with the expanded workforce profile. Keep the terminal open; Ctrl+C stops the server. Do not expose the demo identity selector to the internet.

## Included capabilities

- Workforce joiner/mover/leaver flows, agency and contractor records, site and role changes, staged termination, qualifications, temporary coverage and emergency access.
- RBAC, contextual policy checks, segregation of duties, approval workflows, application entitlements, shifts, sponsor intake, access reviews and campaigns.
- Risk and compliance dashboards, policy violations, notifications, handover notes, advanced filters, saved views, reporting and exports.
- Local connector jobs, retry handling, webhooks and integration interfaces; tenant operations remain explicitly separated from local simulations.
- AI workspace with access explanations and aggregate governance briefings; role-aware help chatbot; optional external model adapter with human decisions retained.
- **New Team services page:** full teammate MFA fatigue detector, demo/CSV analysis, persisted JSON findings and audit events.
- Full separate teammate **Entra access-review lab**: inventory, decisions, self-review guard, approval-gated plans/apply, job worker, evidence exports; plus Graph/PowerShell lifecycle, SAIF B2B and SITAS source.
- Responsive navigation, bounded static caching, compressed responses, pagination, indexed queries, session/CSRF controls, validation, health checks, audit integrity and backup tools.

## What to read

- [Operating guide](docs/OPERATING_GUIDE.md): launch, demonstration, configuration and troubleshooting.
- [Release notes and feature mapping](docs/RELEASE_NOTES.md): sources integrated and changes made.
- [Verification report](docs/TEST_REPORT.md): fresh test results and scope.
- `evidence/final9/`: current test output and screenshots.
- `team_lab/README.md`: teammate lab's own documentation.
- `docs_v9_baseline/`: historical baseline documentation; its claims and test totals do not describe this new release.

## Commands

```sh
python run.py                 # Main portal, expanded synthetic demo
python run.py smfaa           # Full offline MFA detector; runtime/smfaa outputs
python run.py sitas           # Original threat simulations
python run.py verify-original # Verify preserved original source hashes
python verify_release.py     # Verify all packaged release file hashes
python -m pip install -r requirements-test.txt
python run.py test            # Portal + SITAS + SAIF + SMFAA + review database tests
```

Optional tenant services use `python run.py lab` and `python run.py review-worker` after configuration and dependency installation described in the guide. The separate lab does not share sessions or databases with the main portal.

This is a tested demonstration and integration source release. External credentials, tenant validation, deployment infrastructure and operational acceptance remain necessary before real workforce use. No release can promise absence of every possible defect.
