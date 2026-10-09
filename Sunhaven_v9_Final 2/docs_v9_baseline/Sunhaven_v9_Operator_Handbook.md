# Operator handbook
Start, demonstrate, operate, troubleshoot and extend Sunhaven
Release 9.0 - 25 September 2026

## Contents

1. Quick start and presentation preparation

2. Accounts, roles and navigation

3. Onboarding and qualification checks

4. Role changes, transfers and ordinary access packages

5. Temporary site cover and emergency access

6. Roster imports, reviews and termination

7. Automation, notifications and risk insights

8. Policies, delegated administration and integration boundaries

9. Audit, reports, backup and recovery

10. Technical operation, API and deployment configuration

11. Troubleshooting and final demonstration checklist


## 1. Quick start

1. Install Python 3.12 or later. In a terminal run python --version, or on Windows py -3.12 --version.

2. Extract the whole ZIP, not only run.py. Open the sunhaven_final_v9 folder in a terminal.

3. Run python qa/preflight.py. It checks a temporary database and does not change your saved portal data. Expect status PASS.

4. Run python run.py. Alternatively double-click start_windows.bat. Keep the terminal open.

5. Open http://127.0.0.1:8000 in your normal browser. Choose Ivy Chen - IAMOperator and select Enter demo workspace.

6. When finished, use Sign out; press Ctrl+C in the terminal to stop the server. Your database remains on disk.

The local demo needs no third-party Python packages. Tests require pytest; the deployment server requires Waitress. All workforce and resident data are fictional. The password-free identity chooser is for local demonstration only.


## If port 8000 is already in use

Windows PowerShell:
$env:SUNHAVEN_PORT="8010"
python run.py
Then open http://127.0.0.1:8010. On macOS/Linux run SUNHAVEN_PORT=8010 python3 run.py.


## Make the presentation repeatable

Use a separate fresh extraction for your demonstration, or set SUNHAVEN_DB_PATH to a new filename. Do not reset the only copy of your evidence database. Practice the exact sequence below before presenting. The report figures are offline HTML renderings; capture genuine browser screenshots on your computer with Windows+Shift+S if your assessor needs screenshot evidence.


## 2. Demo identities and roles

| Identity | ID / role | Use |
|---|---|---|
| Ivy Chen | SC1005 / IAMOperator | Joiners, execute approved changes, leavers, jobs, policies and delegated administration. |
| Daniel Lee | SC1002 / Manager | Approve business requests, first site-cover stage, qualifications and independent review. |
| Sarah Khan | SC1001 / Nurse | Request qualified site cover, activate narrow emergency access and view permitted residents. |
| Mia Patel | SC1003 / CareWorker | Demonstrate assignment-limited residents and denial of governance pages. |
| Omar Rahman | SC1004 / Auditor | Inspect reports, audit and assurance; cannot change qualifications or run operator jobs. |
| Ali Noor | SC1006 / expired agency | Intentional expired-account fixture. Sign-in is denied; daily job disables remaining mock access. |
| Grace Wilson | SC1007 / Leaver | Demonstrates blocked former-worker access. |
| SiteDelegate | Create an appropriate new worker | Requires an operator-issued, unexpired site delegation before qualification administration works. |
To change identity, use Sign out and select the next person. Use separate normal browser profiles if demonstrating two concurrent roles. A new login replaces that person's previous local session. Sessions expire after 15 minutes by default; expired pages must be reloaded before submitting a form.


## Navigation at a glance

| Pages | Purpose |
|---|---|
| Dashboard / Employees / Notes | Workforce state, individual profiles and handover evidence. |
| Access requests / Catalogue / Coverage | Ordinary changes, temporary packages, two-stage cover and emergency access. |
| Qualifications / Reviews / Campaigns | Care eligibility and manager recertification. |
| Compliance / Insights / Audit / Assurance | Find violations, understand risk and investigate decisions. |
| Roster sync / Control centre / Automation | Reconcile roster changes, run daily jobs and preview agency expiry. |
| Notifications / Reports / Guide | Your reminders, exports and help. |
| Unified governance | Original SITAS/SAIF adapters, services, incidents and policy simulator. |

## 3. Onboard a worker

1. Sign in as Ivy. Open Employees and New Joiner.

2. Use a unique employee ID such as DEMO3001, name Avery Demo, email avery.demo@sunhaven.test, Permanent, CareWorker, Ashford Main, status Active, sponsor SC1002 and today's UTC start date.

3. Select Dry run to inspect the plan. Return to the form, re-enter values if needed, then apply the Joiner.

4. Open the employee profile and confirm role, facility and mock identity. Add a workforce handover note without secrets or clinical information.

5. Open Onboarding. Choose the worker, tick only the steps verified and save supporting evidence. This checklist records work; it does not grant extra permissions.

6. Sign out. As Daniel, open Qualifications and verify Safeguarding for the new worker with a future date and an evidence reference of at least 10 characters.

Agency example: use a different unique ID/email, worker type Agency, role AgencyWorker, a named sponsor and a future end date. The end date cannot precede the start date. Missing or expired agency dates deny login. Future starters cannot sign in until their start date. All business-day boundaries in the portal use UTC.


## Qualification rules

| Worker / resource | Required current evidence |
|---|---|
| CareWorker or AgencyWorker / residents and care routes | Safeguarding; assignment also required for resident access. |
| Nurse / residents and clinical view | Safeguarding and Professional registration. |
| Manager / permitted care view | Safeguarding; managerial scope remains limited to own facility residents. |
| Medication competency / Moving and handling | Tracked and reminded, but not mapped to a medication or manual-handling task engine. |
To renew, choose the same worker and qualification, enter the new valid-through date and independent evidence, then save. Self-verification is forbidden. Expired evidence remains visible until renewed. The system is not a professional-registration authority; an authorised person must check the real source outside this demo.


## 4. Change a role or transfer a site

1. Sign in as the affected worker and open Access requests. Select the new role and facility, then provide the business reason.

2. Sign out and sign in as Daniel. Review the request and record Approved or Rejected with evidence. A manager cannot approve an IAMOperator privilege request.

3. Sign in as Ivy. Use Execute approved change on the request workflow / Security operations, selecting the approved request.

4. Confirm the profile now has the new role/site. Old resident assignments and sessions are removed. The affected worker must sign in again.

5. Use Security operations to assign permitted residents for the new role and facility. An assignment must be active and within the appropriate site.

An approval older than seven days or based on a changed role/site is rejected. Create a new request rather than forcing a stale change. The Mover profile page provides a dry-run preview; direct unapproved execution is intentionally blocked. Qualification requirements still apply after an approved move.


## Use access packages

1. Open Access catalogue as an eligible worker. Request Care learning, Quality review or Temporary incident responder, giving a business reason.

2. A different Manager or IAMOperator decides the request. Open the resource only after approval.

3. Care learning lasts up to 1,440 minutes, Quality review up to 240, and Incident responder up to 60. The quality and incident packages conflict; revoke the existing conflicting package first.

4. For incidents, acquire the incident package, then create an incident and move it through Open, Investigating, Contained and Resolved with evidence.

Packages grant only the local resources described in the catalogue. They do not give Microsoft 365 or external clinical-system access. Worker state and expiry are rechecked when a resource is opened.


## 5. Temporary site cover

Figure: Handbook figure A. Actual server response after the manager stage, rendered offline. It is not a browser screenshot.

1. Sign in as Sarah. Confirm current Safeguarding and Professional registration. Open Cover & emergencies.

2. Request North Wing for 60 minutes and give a reason such as Cover the North Wing clinical shift. The policy maximum defaults to 240 minutes.

3. Sign in as Daniel. Select the pending request, choose Approve and record evidence. The status becomes Pending operator.

4. Sign in as Ivy. Select that request and Approve independently. The grant becomes Active; its countdown begins at final approval.

5. Return as Sarah and open Residents. North Wing records now appear alongside normal facility access.

6. Revoke the grant when no longer needed. Otherwise the resource gate denies it at expiry even if the daily job has not run.

The manager and final operator must be different people, and neither can be the requester. A pending request expires after 24 hours. Changed worker state or expired qualifications prevents approval. The cover grant never changes the worker's permanent home site or creates an IAM role.


## Emergency access

Figure: Handbook figure C. Manager view of emergency access, rendered offline from the tested HTTP response.

1. As Sarah, open Cover & emergencies. For the fictional demonstration enter resident R005, incident reference INC-DEMO-001 and a clear urgent-care reason.

2. Select Activate limited access. A default 15-minute grant is created only for that resident. Managers/operators receive an in-app message.

3. Open Residents and confirm R005 is available, while an unrelated resident at that site is not automatically granted.

4. As Daniel, review the emergency event with investigation evidence and close it. This ends any remaining grant time. Review is expected within 24 hours; a daily job can notify overdue cases.

Do not use emergency access as a routine staffing workaround. It cannot bypass an inactive identity, expired agency contract or missing professional qualifications. It grants no admin permissions and sends no real clinical-system command.


## 6. Reconcile a roster

1. As Ivy or Daniel, open Roster sync. Paste CSV with exactly these columns: employee_id,email,role,facility,status,end_date. Maximum 100 workers and 32 KB.

2. Use existing immutable worker IDs and matching emails. Status must be Active or Leaver. An active agency record requires an end date.

3. Select Check & stage import. Inspect every preview action and any old/new date values.

4. A different Manager or IAMOperator approves the staged import with evidence.

5. An IAMOperator other than that approver applies the checked changes within 24 hours. State changes invalidate the preview and require a new import.

Role/site changes and unknown identities are review findings rather than silent bulk provisioning. Known role/site conflicts create remediation tasks; unknown IDs remain audit findings. A leaver action disables local access. An import cannot remove its approver or executing operator, or remove the last active operator.


## Review and attest access

1. As Ivy, open Quarterly reviews and create/open the current quarter. Repeating this does not duplicate the campaign.

2. As Daniel, review another worker. Retain or Remove with evidence. You cannot review yourself.

3. Remove revokes temporary access packages and opens a core-role remediation task. It does not by itself delete the workforce record or permanently remove every core role.

4. Complete the task using the approved lifecycle/operations workflow and retain closure evidence. The history count covers the whole campaign; the page lists the latest 100 decision items.


## Terminate a worker

As Ivy, open the correct worker profile and Process Leaver, checking the confirmation. The system disables the mock identity, removes local roles and assignments, deletes sessions and blocks future access. Verify the final profile and audit event. If you select yourself or the last active operator, the action is denied. There is no one-click rehire/reactivation flow; review a returner separately.


## 7. Daily operation and risk review

Figure: Handbook figure B. Control-centre response after the tested daily job. This is an offline HTML rendering.

1. As Ivy, open Control centre and review the current policy. Automatic agency expiry is enabled by default in the synthetic workspace.

2. Select Run daily job now. It enforces expired/incomplete agency access, cleans expired sessions, expires temporary cover and writes renewal or overdue-review messages.

3. Inspect the job row and result. Running again on the same UTC day returns the existing committed result. A failed transaction can be retried.

4. Open Notifications as Daniel to see messages. Mark read changes personal read status; it does not resolve the underlying issue. Email is not sent.

5. Open Risk insights. Review the explanation for high scores. Try dormant accounts, expired qualifications, agency risks or show high risk workers.

A high score is not an automatic disciplinary or access decision. Confirm workforce facts with the manager. Portal inactivity does not prove inactivity in external applications. A newly disabled expired agency worker may still have an overdue review finding; each control addresses a different issue.


## Schedule the command

From the portal folder run:
python scheduler.py
This previews current governance work. To apply local daily work and create/open the quarterly campaign:
python scheduler.py --apply --actor SC1005
Use Windows Task Scheduler or cron with the correct working directory and SUNHAVEN_DB_PATH. It must target the same data file as the running portal. The application does not install a schedule for you.


## 8. Policies and delegated administration

| Setting | Range / default | Meaning |
|---|---|---|
| Dormancy window | 30-180 / 90 days | Review workers without a locally observed recent sign-in. |
| Renewal reminder | 7-90 / 30 days | Notify before recorded qualification expiry. |
| Emergency lifetime | 5-30 / 15 minutes | Maximum single-resident emergency grant duration. |
| Cover lifetime | 30-480 / 240 minutes | Maximum requested/final temporary site coverage. |
| Automatic agency expiry | 0 or 1 / 1 | Whether the daily local job disables expired or incomplete agency access. |
As Ivy, edit the values in Control centre and supply a reason. A concurrent edit causes a version conflict: reload and review the newer policy before trying again. Turning off the daily disable does not allow expired agency sign-in; the request-time eligibility gate still denies it.


## Delegate a site

1. Create a worker with primary role SiteDelegate using the normal operator Joiner process.

2. Open Control centre as Ivy. Grant the delegate a known site and expiry within 90 days.

3. Sign in as that delegate. Qualifications and Risk insights are available only for that site; global employee and audit pages remain denied.

4. Allow the delegation to expire when no longer needed, or apply the appropriate lifecycle removal. Full organisation-wide delegation across legacy governance pages is future work.


## Integration screens

Unified governance exposes original SITAS and SAIF read-only adapters. SITAS analyzes a synthetic portal workforce snapshot. SAIF validates a synthetic agency record and previews an invitation; nothing is sent. Services records a Service/Agent owner, permitted local scopes and expiry, then evaluates or disables that record. Policy lab uses declared inputs and is explicitly a simulation. These screens do not establish a live external connection.


## 9. Investigate and export

1. Open Audit as a Manager, Auditor or IAMOperator. Search an actor ID, target ID, action or correlation ID. The search covers full history with 50 rows per page.

2. Expand Inspect evidence to read the recorded reason and relevant identifiers. Do not enter secrets in notes or evidence.

3. Open Security assurance to verify the HMAC ledger and view threat/MFA findings. FAIL means investigate or restore original evidence; do not discard or regenerate keys to hide it.

4. Use Reports for a filtered aggregate PDF or the CSV export links on employee, audit and review pages. CSV formula-like values are neutralized.

5. For a verified NDJSON audit handover, from portal run: python audit_export.py ../audit-export.ndjson --actor SC1004. Choose a new destination filename; retain the printed checksum.


## Backup and restore safely

1. Stop portal and scheduler writers. Preserve the original data and ledger files before any upgrade.

2. From portal run: python manage.py backup ../backups/sunhaven-backup.db. Use a new path. This creates a SQLite backup and copies available .ledger.key and .ledger.head sidecars.

3. Keep the backup and signing material access restricted, encrypted and away from the main host as appropriate for your organisation.

4. To rehearse restore, copy the backup plus sidecars to a separate directory and set SUNHAVEN_DB_PATH to that database path before starting. Never overwrite the only working database.

5. Open profiles, run database integrity/foreign-key checks and verify Security assurance. The supplied qa/backup_check.py performs an isolated offline rehearsal and passed.

Changing or losing the signing key/checkpoint can make legitimate evidence unverifiable. Backups taken while separate writers are modifying ledger state are not an approved restore point. Real production retention, encryption and off-site storage remain organisation responsibilities.


## 10. Technical operation

| Command / file | Purpose |
|---|---|
| python run.py | Start the dependency-free local demo. |
| python qa/preflight.py | Fresh temporary DB, seed, FK/integrity and original-file checks. |
| python -m pip install -r requirements-test.txt | Install pytest needed by original-module tests. |
| python run.py test | Run portal unittest and both original pytest suites. |
| python qa/http_final.py | Run the isolated real-HTTP acceptance sequence; writes evidence; does not touch portal/data. |
| python qa/backup_check.py | Run the isolated backup/restore rehearsal. |
| python run.py verify-original | Check all 545 preserved uploaded files. |
| python run.py sitas | Run original scenario comparisons. |
| portal/requirements-deploy.txt | Optional Waitress and MSAL deployment dependencies. |
| portal/serve.py | Start the Waitress WSGI deployment server after dependencies are installed. |
Windows example for Waitress:
python -m pip install -r portal/requirements-deploy.txt
cd portal
python serve.py
The demo remains on localhost unless configuration is changed. Docker files are supplied, but a Docker image build was not executed here. The Python/Waitress server itself passed the acceptance sequence.


## API usage

After authenticating in the same browser, open /api/v1/docs. Read-only resources are employees, risks, qualifications, health and scim/Users. Example: /api/v1/employees?page=1&page_size=25. Page size is 1-100. A governance role is required; SiteDelegate results are filtered to current delegation. Health details require Operator or Auditor. Anonymous requests receive 401, insufficient roles 403, bad pagination 400 and exhausted rate limit 429.

The API uses the portal session cookie, not a personal API key. There are no API writes or full SCIM filter/bulk/provisioning operations. Do not connect a production IdP expecting a complete SCIM service. Integration developers should implement the connectors.py contract with authentication, retries, idempotency and reconciliation, then add live tests.


## Environment and deployment

| Variable | Purpose / boundary |
|---|---|
| SUNHAVEN_HOST / SUNHAVEN_PORT | Default 127.0.0.1 / 8000. Keep password-free demo loopback-only. |
| SUNHAVEN_DB_PATH | Persistent SQLite file. Its parent must be writable; keep the ledger sidecars beside it. |
| SUNHAVEN_ENV | development or production. Production activates strict configuration checks and Secure cookies. |
| SUNHAVEN_AUTH_MODE | local demo or entra. Production requires entra. |
| SUNHAVEN_SEED_DEMO | 1 in development by default; must be 0 in production. |
| SUNHAVEN_SECRET_KEY | Random secret of at least 32 characters for production. Never put it in the report or source ZIP. |
| SUNHAVEN_TENANT_ID / CLIENT_ID / CLIENT_SECRET | Entra application settings supplied securely by the organisation. |
| SUNHAVEN_REDIRECT_URI | Registered HTTPS callback required in production. |
| SUNHAVEN_SESSION_MINUTES | 1-480; default 15. Longer demo sessions increase unattended-session risk. |
| SUNHAVEN_GRAPH_MODE | mock only in this release. real intentionally fails configuration validation. |
| SUNHAVEN_LEDGER_KEY | Optional external signing key; otherwise protected local sidecar generated. Preserve its identity across backups. |
For an empty non-demo Entra deployment, use the documented offline bootstrap command in portal/manage.py with the immutable object ID. Do not expose a local demo to the Internet to avoid configuring authentication. Production still needs tenant testing, HTTPS/reverse-proxy hardening, external monitoring, retention, secret management and independent assessment.


## 11. Troubleshooting and presentation checklist

| Symptom | What to do |
|---|---|
| Python syntax error at startup | Use Python 3.12 or later and extract the entire ZIP. |
| Address already in use | Stop the previous server or set another SUNHAVEN_PORT and use that port in the URL. |
| Request expired / HTTP 403 on a form | Reload the page and sign in again if necessary. CSRF and absolute session expiry are intentional. |
| Agency or future starter cannot log in | Check active/enabled state, start date, sponsor/end date and blocked status. Expired seed Ali is deliberately denied. |
| Clinical or resident access absent | Check required qualifications, role, facility, assignment and any current approved cover. |
| Cannot approve cover | Use Manager for stage one and a different IAMOperator for stage two; requester cannot approve. |
| Old roster request will not apply | Approval may be older than 24 hours or workforce state changed. Stage a new reviewed preview. |
| Daily run changes nothing | A successful run already exists for this UTC day, or no policy targets are due. Request-time access expiry still applies. |
| Ledger FAIL | Stop and preserve evidence; check key/checkpoint/database consistency. Restore the original matched set. |
| No email or Microsoft account change | These are not connected in this release. In-app outbox and mock-directory state are the implemented behavior. |
| Rate limited / HTTP 429 | Wait for the next minute window. Do not disable limits for a public deployment. |
1. Run preflight and the supplied tests on the presentation computer. Confirm the home page and key forms open in your real browser.

2. Use a new demo database. Keep a backup and a second clean extraction. Avoid reusing example IDs from a rehearsal.

3. Confirm Ivy, Daniel, Sarah and Mia can sign in; remember Ali and Grace should be denied.

4. Practice manager/operator switching, cover approval, emergency review and leaver confirmation.

5. Capture actual browser screenshots on your computer if required. Test keyboard navigation, mobile layout and dark mode there because those were not verified in the remote browser.

6. State the boundary accurately: a tested local governance prototype with integration-ready architecture, not a live tenant or regulatory certification.
