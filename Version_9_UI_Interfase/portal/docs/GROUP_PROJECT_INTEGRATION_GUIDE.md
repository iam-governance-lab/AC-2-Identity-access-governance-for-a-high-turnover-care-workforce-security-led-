> Historical version 5 comparison. For the current solo version 6 prototype, start with `FINAL_PROJECT_OPERATING_GUIDE.md`.

# Sunhaven Care — integrated lab project and honest handover

## What this package is

Version 5 is one runnable synthetic-data **laboratory demonstration** of workforce identity governance, with the version 4 portal, security policy checker, JML workflows, approval and review evidence, threat-control analysis, an MFA sequence detector and a tamper-evident local audit ledger. It can run offline on Python 3.10+ with no third-party packages in demo mode.

This implementation was assembled from the supplied prototype and the two planning documents. It is not the same source repository as the separate team members' SITAS (45 tests reported in the plan), SMFAA or SALI. The source code for those components was not supplied. The new modules are an independently implemented *lab integration demonstration* with 44 local tests; do not attribute these modules or their tests to a teammate without their review. Do not submit the package as proof of a live Microsoft tenant, MFA policy, Graph mutation, device posture, or final faculty acceptance.

## Quick start

1. Unzip the package. From `sunhaven_care_iam`, run `python run.py` (Windows) or `python3 run.py` (macOS/Linux).
2. Open http://127.0.0.1:8000. Local demo mode has fictional people and password-free selection. Use Ivy Chen (operator), Daniel Lee (manager), Omar Rahman (auditor), or Mia Patel (care worker). Keep the demo bound to localhost.
3. Open **Security assurance** in the left menu as Ivy, Daniel or Omar. The page shows the six modelled threats, current local snapshot, control outcomes and ledger verification. It does not alter accounts.
4. Open a protected resource as Ivy (`/protected/iam-admin`) to generate a real portal ALLOW event. Sign in as Mia and request the same path to generate a real DENY event. Reopen Security assurance as Ivy to check the ledger. The audit page shows the same correlation IDs.
5. In a terminal, run `python -m security_workstream.demo --output demo-evidence`. This initialises the current demo DB, compares controls, detects three patterns from six controlled MFA events, ingests findings and writes threat JSON, CSV, HTML, MFA JSON and a ledger verification JSON. Files in `docs/sample-security-evidence/` show one independent synthetic example. Use a fresh output folder for each run.
6. Run `python -m unittest discover -s tests -v`. It checks the existing governance flows and new ledger, detector, page permissions and tampering behaviours.

## System map and ownership

| Layer | Current working code | Evidence and boundary |
|---|---|---|
| Approved source and JML | `database.py`, `lifecycle.py`, `governance.py`, `graph_service.py` | Synthetic workforce, dry runs, approvals, audited local changes. Graph is forced into mock mode. Original proposal called for Graph PowerShell; this is a Python implementation difference requiring explicit justification in a final report. |
| Identity and care portal | `auth.py`, `server.py`, `features.py`, `operations_ui.py`, `experience.py` | Optional Entra OIDC sign-in code exists, but has no live tenant test. Role and resident assignment decisions run on the server. Demo login is local. |
| Policy compliance | `compliance.py` | C01–C08 compare approved local records with simulated cloud/app fields. They do not query live Entra state. |
| SITAS-like threat analysis | `security_workstream/threats.py` | Six static scenario/control comparisons. Three read local workforce/assignment conditions. MFA, device and session outcomes remain open. These results are modelled, not live attack telemetry. |
| SMFAA-like sequence analysis | `security_workstream/mfa.py`, `security_workstream/analyze_file.py` | Five supported outcome classes; per-identity rolling 5-minute window; repeated denial, prompt burst and denial-to-success rules. Synthetic example included. No live sign-in API or Entra export mapped automatically. |
| SALI-like evidence integrity | `security_workstream/ledger.py` | Mirrors committed portal audit rows, signs a hash chain with HMAC and stores an external signed head file. Correlated MFA findings can also be appended. The verifier catches changes to ledger entries or mirrored audit rows and a missing ledger tail. It is local tamper-evident evidence, not an immutable central service. |
| Interface | `ui.py`, `static/` | Dashboard, access workflows, reports and a scoped Security assurance page. The proposal specified Flask/Jinja; this standalone version uses Python's standard-library server plus WSGI adapter. Integrate the real Flask repository separately if it exists. |

## MFA input contract

Prepare an already sanitised JSON array with `event_id`, `actor_id`, `timestamp_utc` (ISO 8601 with UTC offset), and `outcome` set to `denied`, `success`, `challenge`, `timeout`, or `unknown_failure`:

```json
[
  {"event_id":"MFA-1","actor_id":"SC1005","timestamp_utc":"2026-09-24T00:00:00Z","outcome":"denied"},
  {"event_id":"MFA-2","actor_id":"SC1005","timestamp_utc":"2026-09-24T00:00:30Z","outcome":"challenge"}
]
```

Run `python -m security_workstream.analyze_file input.json --output findings.json`. Add `--ingest-findings` to append its findings into the local ledger. The tool ignores duplicate event IDs, sorts out-of-order timestamps, rejects missing fields, limits input to 2 MB/10,000 events, and distinguishes unknown failures and timeouts from explicit user denial. Thresholds can be changed through the Python API; the CLI uses 3 denials and 5 prompts in 5 minutes. Treat identity IDs as fictional lab IDs; remove tokens, IP addresses and real-person data before import.

## Integrity design and recovery

Portal writes first commit to `audit_events`, then `ledger.sync()` mirrors them with their correlation IDs into `security_ledger` and saves the head checkpoint outside SQLite. A ledger event includes schema, source, source ID, UTC time, actor, target, action, result, correlation and sanitised metadata. Each event has a sequence, previous SHA-256 hash, SHA-256 event hash and HMAC-SHA256 tag. The verifier recomputes these and compares the original audit row and signed external checkpoint. A failed integrity check should be investigated; never regenerate the signing key to make an old chain appear valid.

Three files form one evidence set: the SQLite database, `<database>.ledger.key` and `<database>.ledger.head`. A random 32-byte key is created with restricted local permissions in demo mode, or supply `SUNHAVEN_LEDGER_KEY` (32+ characters) through a secure environment for repeatable deployments. Stop the app before making a consistent backup. `python manage.py backup backups/my-copy.db` copies the DB and, when present, both ledger sidecars. Restore all three using matching names. Keep keys out of source control and ZIP deliveries. Local filesystem/HMAC cannot stop a privileged attacker who can replace both the database and its signing key; remote durable checkpoints would be needed for stronger assurance. A process crash between DB commit and head update can require operator investigation.

## Real group integration still required

1. Obtain the actual repositories from Rifat, Prothom, Adnan and Loojaw with commit history. Compare their module contracts before replacing any contribution. No repository or implementation of their SITAS/SMFAA/SALI was attached here.
2. Reconcile Flask/Jinja and Python server choices, the original Graph PowerShell plan and this Python Graph adapter. Preserve individual contribution ownership and record approved architecture changes.
3. Set up a dedicated student/lab Entra tenant, app registration, app roles, test users, MFA and screenshots. Bind by stable immutable object ID. Test real sign-in under role boundaries. The application blocks real Graph mutations by design because live partial failure and recovery have not been validated.
4. Connect approved source events and permitted Graph writes, then demonstrate Joiner/Mover/Leaver readback, failure handling and delayed token/session denial in the controlled tenant. Never assume the synthetic `cloud_enabled` field proves the directory state.
5. Bring actual SITAS attack graph, MFA mapping to Entra sign-in export, and teammate audit-integrity code into the agreed interface. Add interface and correlation tests; this package only supplies a compatible demonstration, not their unprovided source.
6. Complete project governance deliverables: security policies, risk registers, requirements/risk/control/test matrix, genuine team commit evidence and labelled screenshots of the real integrated system. Produce a short demo video and final report with known limitations.

## Scope and evidence rules

The original proposal explicitly places production deployment, clinical data, enterprise SIEM, MDM and production certification out of scope. A complete capstone submission is an integrated **lab proof of concept plus genuine evidence and report**, not an industry production claim. The attached team plan still described much of SMFAA and all of SALI as unfinished at the time it was written; do not relabel planned work as completed without running their code.
