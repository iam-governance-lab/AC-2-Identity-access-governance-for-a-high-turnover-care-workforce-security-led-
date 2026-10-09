> Historical project reference. For version 3 operating steps, including mandatory approved Mover execution, use the Operating and Technical Guide.

# Sunhaven Care IAM — Final Demo Runbook

Target: **under 10 minutes**.

## 1. Problem — 30 seconds

“Sunhaven Care has permanent, casual and agency workers, shared devices and sensitive resident information. The project makes sure each worker receives only the access they need, keeps that access only while approved, and loses it promptly when their role or employment changes.”

## 2. Dashboard — 30 seconds

- Login as **Ivy Chen — IAMOperator**.
- Show active workers, agency workers, leavers and current compliance findings.
- Point out the seeded expired agency finding.

## 3. Joiner — 1.5 minutes

- Employees → New Joiner.
- Create a fictional Nurse such as `SC1010`.
- First press **Dry run only**.
- Explain that validation occurs before changes.
- Return and apply the Joiner.
- Open the employee detail and show approved/current role plus audit correlation ID.

## 4. Mover — 1.5 minutes

- Open the same employee → Mover for a dry run.
- Submit an access request as the worker, have another manager/operator approve it, then execute the approved request as an operator through Security operations.
- Show that only the new role remains and old resident assignments were cleared.

## 5. RBAC / 403 — 1 minute

- Sign in as a lower-privilege worker such as CareWorker.
- Open permitted resident/care-notes page.
- Attempt a Manager/Auditor/IAM route directly.
- Show HTTP 403 and the resulting audit evidence.

## 6. Leaver — 2 minutes

- Login again as IAMOperator.
- Open the demonstration employee.
- Process Leaver.
- Show:
  - status = Leaver
  - cloud enabled = No
  - no active role
  - no assignments
  - portal blocked = Yes
- Explain that local mode simulates the directory disable. Real Graph writes are blocked pending tenant integration.

## 7. Access Review — 45 seconds

- Open Access Reviews.
- Record Retain / Change / Remove / Temporary Exception for one worker.
- Show reviewer, date, reason and status.

## 8. Compliance — 45 seconds

- Open Compliance.
- Explain C01–C08.
- Run & store scan.
- Show the seeded expired-agency violation.

## 9. Audit & conclusion — 45 seconds

- Open Audit Log.
- Point out actor, target, action, UTC time, result and correlation ID.
- State that passwords/tokens/secrets are deliberately excluded.
- Conclude: right worker, minimum access, prompt removal, reviewable evidence.

## Optional version 5 assurance demo

As an operator, open Security assurance to compare the six scenarios and verify the audit ledger. Open a permitted protected page and a denied page under a restricted worker, then inspect correlated ALLOW/DENY in Audit and the ledger. Run `python -m security_workstream.demo --output demo-evidence` to show controlled MFA findings and JSON/CSV/HTML threat evidence. Identify modelled outcomes as simulation and keep this within the allotted time.
