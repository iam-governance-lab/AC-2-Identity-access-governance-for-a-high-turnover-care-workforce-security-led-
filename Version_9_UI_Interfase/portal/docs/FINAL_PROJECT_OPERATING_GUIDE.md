# Sunhaven Care IAM 6.0 — operator and technical guide

## What the finished laboratory prototype demonstrates

Sunhaven Care IAM is a coherent, offline, synthetic-data workforce governance **prototype**. It demonstrates approved Joiner/Mover/Leaver (JML), role and resident assignment checks, agency expiry, access review, policy compliance, contextual evidence through threat and MFA-sequence analysis, and a tamper-evident local ledger. It is presented as one system. It does not require a real organisation or clinical records to run.

**Demo mode:** Python 3.10+, no installation of external packages, server bound to `127.0.0.1:8000`, and 42 fictional workers, 30 fictional residents and 35 seeded workforce notes. Demo identity selection has no password and must stay on a trusted local machine. The cloud state is simulated. Entra sign-in is coded as an optional path but has not been proven in a live tenant; Graph writes are blocked by configuration. This is an industry-inspired proof of concept, not production certification.

## Start, stop and verify

1. Extract the ZIP. Keep `sunhaven_care_iam` together; do not run directly inside the ZIP.
2. In the extracted folder run `python run.py` on Windows or `python3 run.py` on Linux/macOS. You can also use `start_windows.bat` on Windows.
3. Open http://127.0.0.1:8000. Select **Ivy Chen** as IAMOperator. For a lower privilege test choose **Mia Patel**, or **Omar Rahman** for audit-only views.
4. Stop with Ctrl+C. Data stays in `data/sunhaven.db`. To refresh a lab demonstration, stop the server and run `python reset_demo.py --confirm-reset`; this deletes the current demo database and ledger evidence. Back up first if you need the evidence.
5. Run `python -m unittest discover -s tests -v` for the 47 automated tests. Run `python manage.py --help` for local administration commands.

## User roles

| Role | Portal scope | Main tasks |
|---|---|---|
| CareWorker / AgencyWorker | Assigned fictional residents, own requests and reminders | View permitted care pages, request access |
| Nurse | Same-facility resident views and clinical route | Care access and own requests |
| Manager | Workforce, compliance, review, policy and automation preview | Approve authorised requests, review access, own remediation |
| Auditor | Governance read views, audit, policy, assurance and automation preview | Verify evidence without executing changes |
| IAMOperator | Workforce administration and expiry execution | Joiner/Leaver, assignment, approved Mover, session revocation and reviewed agency shutdown |

Every restricted route checks roles on the server. Direct URLs are denied and recorded. Manager scope is currently organisation-wide; facility-scoped manager authorisation would require further work.

## Daily operator workflow

**Dashboard:** Click a statistic to open related records. Filter the live workforce chart by facility. The top search looks up permitted workers, notes, tasks and requests; press `/` to focus it. The theme toggle saves a light/dark preference in the current browser.

**Joiner:** Employees → New Joiner → complete identity, role, facility, sponsor/end date if agency → Dry run → create. Validate the generated synthetic directory state and audit event.

**Mover:** Worker profile → Mover for a dry-run preview. The worker submits an access request; a different authorised approver decides; an IAMOperator executes the approved change via Security operations or Requests. Seven-day approval, snapshot and one-use checks apply; old assignments and local sessions are removed. The direct Mover apply route is blocked.

**Leaver:** Worker profile → Process Leaver. The local workflow disables the simulated cloud state, removes role and assignments, revokes sessions and blocks further portal access.

**Access reviews and tasks:** Record Retain, Change, Remove or Temporary Exception with a reason. Track pending remediation in Security operations; close it with evidence after correcting access. Reports can export filtered aggregate PDF counts; CSV exports are available for workforce/audit/review metadata.

**Notifications and onboarding:** Pending requests, due/expired agency contracts and overdue reviews appear as role-scoped reminders. Marking read only changes the user's own inbox. Managers/operators record four onboarding steps and evidence, which does not itself grant access.

**Agency expiry automation:** Open Automation. Review expired active agency workers and upcoming dates. An IAMOperator enters a reason and runs the action. The server checks that the preview is still current, then atomically suspends each expired worker, disables simulated cloud access, removes roles/assignments, revokes sessions, blocks login and writes the audit event plus run history. A repeat run with no targets records a no-op. Other roles cannot execute.

**Security assurance:** Open the six-scenario risk/control view and verify the signed audit ledger. The controlled MFA detector has a separate command; once its findings are ingested, the latest 12 appear on this page. The device-trust, MFA policy and compromised privileged-account scenarios remain open until tested independently.

**Policy and risks:** Policies & risks displays ten mapped controls (P01–P10) and seven risks (R01–R07) with owners, evidence names, tests and residual limits. `docs/POLICY_SECURITY_PACK.md` provides practical procedures. `docs/DELIVERY_MATRIX_V6.md` maps every proposal deliverable to its current evidence and remaining work.

## Controlled evidence commands

From the project folder:

```sh
python -m security_workstream.demo --output demo-evidence
python manage.py expire-agency
python manage.py expire-agency --apply --actor-id SC1005 --reason "Daily synthetic contract expiry validated"
python manage.py backup backups/sunhaven-copy.db
```

The first command writes threat JSON/CSV/HTML, MFA finding JSON and ledger verification JSON, using six fictional sign-in events. The expiry command previews by default. `--apply` is allowed only in development/mock mode; run it as an authenticated operator in the web interface or from a trusted local operator shell. CLI actions remain visible in the audit and Automation history. Do not edit the dataset by hand to simulate a passing test; run the command.

`security_workstream.analyze_file` accepts an already sanitised JSON array of `event_id`, fictional `actor_id`, ISO 8601 `timestamp_utc`, and one of `denied`, `success`, `challenge`, `timeout` or `unknown_failure`:

```sh
python -m security_workstream.analyze_file synthetic-mfa.json --output findings.json --ingest-findings
```

Repeated denials, prompt bursts and denial-to-success patterns are evaluated in a five-minute window. A lone failure is not labelled an attack. No real MFA push, token or personal log should be placed in the synthetic demo.

## Architecture and trust boundaries

`server.py` maps HTTP routes to `lifecycle.py`, `governance.py`, `experience.py`, `automation.py` and `automation_ui.py`; all write the SQLite data model in `database.py`. `compliance.py` checks C01–C08. `security_workstream/threats.py` reads workforce state, `mfa.py` reads controlled sign-in events, and `ledger.py` mirrors committed audit evidence plus detector findings into a signed chain. `ui.py` and `static/` render accessible role-scoped pages. The local HTTP adapter and WSGI adapter share route logic.

Security decisions occur server-side. CSRF tokens protect POST forms; database queries use bound parameters; HTML and CSV exports neutralise injection; sensitive keys are excluded from shared files; the session is 15 minutes by default. Entra sign-in code binds identity by tenant and object ID in optional mode. Production configuration requires secure cookies and an HTTPS redirect, but deployment in an actual tenant remains untested.

The ledger consists of the SQLite database plus `<database>.ledger.key` and `<database>.ledger.head`. Its SHA-256/HMAC chain checks changed or missing events and the external checkpoint. The key is generated locally with restricted permissions unless `SUNHAVEN_LEDGER_KEY` is set. Back up all three consistently after stopping writers; the `manage.py backup` command copies existing sidecars. A missing key cannot be recreated to validate earlier evidence.

## Test and evidence status

Automated regression tests: **47 passing**. They cover JML, role denial, CSRF, approval constraints, governance transactions, resident scope, compliance checks, PDF output, onboarding, MFA pattern boundaries, ledger modification/tail/key loss, agency automation idempotency/stale preview/role restrictions, and WSGI routes. A local HTTP smoke run covers dashboard, policies, automation, assurance, protected resources and PDF. Sample evidence under `docs/sample-security-evidence/` is labelled synthetic; screenshots in other historical guides are references, not live cloud proof.

## Limits before any live or assessed submission claim

The approved proposal called for Flask/Jinja and Microsoft Graph PowerShell, while this runnable prototype uses a standard-library Python server and a Python Graph adapter in mock mode. The final written report should explain this architecture change. The supplied presentation cannot claim live tenant MFA enforcement, Graph write-back, device posture validation, enterprise SIEM/WORM logging, production availability, formal privacy compliance or a successful public deployment. These require real tenant access, authentic team integration where applicable, configuration review, operation tests and evidence. The original proposal itself excludes production deployment. Use `docs/PRESENTATION_RUNBOOK_V6.md` for accurate solo demonstration language.
