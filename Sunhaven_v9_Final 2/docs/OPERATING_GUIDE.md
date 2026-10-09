# Version 9 Final — operating guide

## 1. Files and launch

Extract everything before running. Open the top-level folder in VS Code using File → Open Folder. Python, HTML, CSS, JavaScript, PowerShell, tests, configuration templates and documentation are editable source files.

Run `python run.py` from that folder and visit http://127.0.0.1:8000. On systems where Python is named `python3`, use that command. `start_windows.bat` and `start_unix.sh` are convenience launchers. Python 3.12+ is required. The default local demo uses Python's standard library; internet is not required.

Choose SC1005 for the IAM operator, SC1002 for a manager, SC1001 for a nurse. These are selectable synthetic demo identities, not passwords or real authentication. The main release defaults to the expanded synthetic profile (320 workers). Directly launching `portal/run.py` uses the standard 42-worker profile unless `SUNHAVEN_DEMO_PROFILE=expanded` is set.

The main database is `portal/data/sunhaven.db` unless `SUNHAVEN_DB_PATH` is configured. Data persists after restart. Do not delete the database to solve an error; use a verified backup. Keep its audit key/checkpoint/journal files with the database. The teammate lab uses its own database; set `SUNHAVEN_LAB_DB_PATH` to relocate it.

## 2. Main workflow demonstration

1. Dashboard: explain active staff, pending work and risk indicators.
2. Employees / Onboarding: create a synthetic permanent or agency worker, enter valid role, site and dates, and complete required approvals.
3. Access requests / Application access: request an entitlement or temporary role. Sign in as a different authorized approver; approve or reject with a reason. Self-approval and privileged approval restrictions apply.
4. Employee detail: demonstrate role movement, site transfer and session revocation. Use the staged termination workflow for a leaver.
5. Qualifications / Shifts / Cover & emergencies: inspect expiry dates and time-limited assignments. Emergency access requires justification and remains auditable.
6. Quarterly reviews / Review workbench: create or inspect a campaign; record review decisions and follow-up work.
7. Roster sync / Sponsor intake: stage input, inspect validation and differences, then execute the authorized workflow.
8. Connector operations: inspect local job status and retry behavior. Read each connector's mode before assuming any external change occurred.
9. Risk insights / Policies / Compliance: examine risk explanations and policy findings. Findings are investigation aids.
10. Audit Log / Reports: inspect evidence and export relevant results. Notes & handovers stores operational context.
11. AI workspace: explain current access or generate an aggregate governance briefing. Ask the chatbot how to request access, manage roles or investigate risks.
12. Team services: run the synthetic MFA detector and download the result. It identifies prompt bursts, repeated denials and denial followed by success. No account is disabled by the analyzer.

Navigation is role filtered. Use the menu button on tablet/mobile; Escape closes navigation. The Help centre and chatbot link to the relevant workflow. A hidden page does not grant permission: the server rechecks authorization.

## 3. MFA CSV analysis

Open Team services as an IAM operator, manager or auditor. Paste a UTF-8 normalized CSV with this header:

```csv
event_id,employee_id,timestamp,event_type
sample-001,SC1001,2026-10-07T10:00:00Z,MFA_PROMPT
```

Supported event types: `MFA_PROMPT`, `MFA_DENIED`, `MFA_SUCCESS`. Supply unique event IDs, ISO 8601 timestamps and required values of 1–120 characters. Each portal run permits at most 60 KB and 2,000 events. Remove duplicates before import. Findings and supporting event IDs are stored locally and downloadable as JSON. Investigate context before taking access action.

For offline files, run `python run.py smfaa`; outputs are written under `runtime/smfaa`. The full tool's additional arguments are documented by running `python src/smfaa.py --help` inside `team_lab/services/Sunhaven MFA Fatigue Attack Analyzer`.

## 4. Separate Entra access-review lab

The full teammate lab is available in `team_lab`; it is a separate application, not an automatically connected tenant service.

1. Create a virtual environment with `python -m venv .venv`; activate it using your operating system's activation command.
2. Install `python -m pip install -r team_lab/app/requirements.txt`. These optional requirements require internet access.
3. Read `team_lab/app/README.md`, `team_lab/README.md` and the access-review documentation under `team_lab/docs`. Configure an Entra application, callback URL, authorized users/groups and the environment settings required by the supplied app. Use your own tenant identifiers; supplied configuration/evidence describes the team's historical lab.
4. Start `python run.py lab`. Its local interface is http://127.0.0.1:5000.
5. Install PowerShell and the documented Microsoft Graph modules, authorize the dedicated worker in your test tenant, and start `python run.py review-worker` in a separate activated terminal.
6. Inventory → campaign → independent decisions → remediation plan → explicit approval → apply → evidence and campaign closure. Review the baseline and privileged-role guards before allowing tenant mutations.

The lab and PowerShell operations require real permissions and may change the configured tenant when an approved apply is executed. Live tenant authentication, device-flow MFA, inventory and mutation were not exercised for this release. Use a dedicated test tenant for initial validation. Main-portal Graph mutations remain disabled until a separately tested deployment adapter is provided.

## 5. AI operation

Local guidance and aggregate insights work offline. The bundled model is a workflow retrieval model, not a newly trained general-purpose language model. The optional external provider is enabled through the `SUNHAVEN_AI_*` settings documented in `portal/agent_assistant.py`. Keep keys outside source control. User role and current account state are checked server side; high-risk access decisions stay in approval workflows. Verify provider connectivity, privacy terms and access controls before enabling it for real data.

## 6. Verification and maintenance

```sh
python -m pip install -r requirements-test.txt
python run.py test
python qa/http_final9.py
python run.py verify-original
python verify_release.py
```

HTTP tests use an isolated temporary database and port 8031. Set `SUNHAVEN_QA_SERVER=waitress` to exercise the WSGI server. Browser tests are optional: install `playwright==1.51.0`, run `python -m playwright install chromium`, then `python qa/browser_final9.py`. Browser tests use port 8044 and create screenshots in `evidence/final9`.

If editing CSS source files, rebuild `python qa/build_assets.py`. If editing help topics, run `python qa/train_assistant.py` to regenerate the retrieval model and routing evaluation. Hash verification will intentionally fail after source edits until a new release manifest is generated.

## 7. Upgrade from the old v9

Stop the old instance and take a complete backup of its database and audit companion files. Test on a copy first. Point `SUNHAVEN_DB_PATH` at that copy and run the new application; additive migrations run automatically. Do not overwrite source files in an active old installation. A fresh v9 fixture migration was tested, preserving all 42 employees and a valid audit ledger. Custom production data still needs its own migration rehearsal. Historical migration numbers remain unchanged even though the delivered product is called Version 9 Final.

## 8. Deployment and troubleshooting

For WSGI, install `portal/requirements-deploy.txt` and run `python portal/serve.py`. The supplied Docker/Compose files package the local portal and detector; Docker execution was not available in this verification run. The portal defaults to loopback. A real deployment requires HTTPS, Entra configuration, secure secrets, controlled database storage, backups with restore drills, monitoring and tenant acceptance tests. Production configuration rejects demo login and synthetic seeding. SQLite is a single-instance baseline; validate capacity and concurrency before scaling.

- Python not found: install Python 3.12+, enable its PATH option, reopen the terminal.
- Port already in use: stop the other instance or set `SUNHAVEN_PORT` and use that port in the browser.
- Request expired: refresh the form and submit once; CSRF/session checks may have expired.
- Access denied: use an active identity with the required role; do not bypass authorization.
- Database busy: wait, reload and check whether the previous action saved before retrying.
- Audit integrity failure: stop protected operations, preserve evidence, investigate and restore a verified backup if required.
- Missing optional package: install only the relevant requirements file in the active virtual environment.
- AI provider unavailable: local guidance remains available. Check provider settings without exposing keys.
