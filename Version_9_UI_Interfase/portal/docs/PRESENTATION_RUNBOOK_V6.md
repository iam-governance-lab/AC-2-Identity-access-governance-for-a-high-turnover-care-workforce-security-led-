# Solo presentation runbook — eight to ten minutes

## Preparation (before the session)

Use a fresh extracted copy. Run `python -m unittest discover -s tests -q` and record the passing test count. Back up your database if you have saved work. Start `python run.py`; keep a terminal open beside the browser. The demo login must be local to your computer. Use fictional identities only. Open `docs/sample-security-evidence/` as a backup if the terminal display is unavailable.

## Live sequence and spoken explanation

| Time | Action | Explain in plain language |
|---|---|---|
| 0:00–0:45 | Log in as Ivy; show dashboard and role/facility chart. | “The approved workforce record drives access decisions. The dashboard is a live local view of 42 fictional workers.” |
| 0:45–1:45 | Employees → New Joiner → Dry run (do not create if time is short). | “Validation checks role, facility, identity, and agency sponsor/end date before a change.” |
| 1:45–2:45 | Requests → existing request history; show Security operations and approval execution path. | “A worker requests a change; another authorised person decides; an operator executes a current approval. Old access and sessions are removed.” |
| 2:45–3:45 | Show permitted care access as Ivy or Mia, then direct `/protected/iam-admin` as Mia for 403. | “The server checks role and assignment on every request. A denied route creates an audit event.” |
| 3:45–5:00 | Reopen as Ivy. Automation → review the expired agency row → run with reason. | “The operator reviews the exact target list, then one transaction suspends local access and records evidence. Running again is safe.” |
| 5:00–6:00 | Compliance C01–C08; Access Reviews; Policies & risks. | “Deterministic checks identify exceptions. Each control links a risk, owner, evidence and test.” |
| 6:00–7:15 | Run `python -m security_workstream.demo --output demo-evidence`, then refresh Security assurance. | “Six threat scenarios compare control states. Fictional MFA sequences produce explainable findings; the portal displays their correlation IDs.” |
| 7:15–8:15 | Security assurance ledger PASS; audit log ALLOW/DENY; mention tamper test. | “The ledger detects changed records or a missing tail through hashes, HMAC and a separate signed checkpoint. Our automated tests include controlled tampering.” |
| 8:15–9:00 | Reports → filtered PDF; show help/guide. | “A manager/auditor can export aggregate counts without exposing note text or resident records.” |

## Questions and truthful answers

**Is this production ready?** “It is a runnable, tested laboratory prototype with industry-inspired controls. The original project excludes production deployment. A real tenant, end-to-end Entra/Graph tests, device management and operational review would be needed before live care data.”

**Does it enforce real Microsoft MFA or disable a real Entra user?** “The offline demonstration does neither. Optional Entra sign-in code exists, but real directory writes are intentionally blocked. MFA patterns are analysed using controlled synthetic events.”

**Why does the proposal say Flask and Graph PowerShell?** “This implemented lab uses a standard-library Python server and Python Graph adapter. The final report records that design change and its unverified tenant boundary. Features are shown through their actual test evidence.”

**What was automated?** “The agency-expiry action is executable against local simulated state after operator review; the CLI can be scheduled by a trusted OS task. It is not a live cloud scheduler. Approval and recertification still require human decisions.”

**How do you know audit records were not edited?** “The verifier checks the source audit row, ordered chain, HMAC and separately stored signed head; the tamper tests demonstrate FAIL. A privileged attacker controlling the key and host is outside the strength of this lab control.”

Use your real contribution statement and any AI-use declaration required by your course. Show the running code and evidence; do not claim to have run a tenant or a test you did not run.
