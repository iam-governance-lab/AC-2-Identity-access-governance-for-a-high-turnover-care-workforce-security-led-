# Sunhaven Care - final release 9.0

A tested local workforce identity and access governance application for a high-turnover care workforce. Uses fictional workers/residents and a mock directory. The original uploaded project is preserved unchanged in `original/`.

## Start here

1. Install **Python 3.12 or later** and extract the entire ZIP.
2. Open a terminal in this folder and run `python qa/preflight.py` (Windows: `py -3.12 qa/preflight.py` also works).
3. Run `python run.py`, or double-click `start_windows.bat`.
4. Open **http://127.0.0.1:8000**. Choose Ivy Chen for IAM operations, Daniel Lee for manager approvals, Sarah Khan for nurse scenarios, or Mia Patel for restricted worker access.
5. Read **Sunhaven_v9_Operator_Handbook.pdf** for the complete demo and operating procedure.

The first start creates `portal/data/sunhaven.db`: 42 fictional workers, 30 fictional residents, 35 notes and 46 qualification records. No dependencies are needed for this local demo. Keep the terminal open. Ctrl+C stops it; saved data remains.

**Do not put the password-free demo on a public network.** Production configuration requires Entra authentication and external infrastructure. Live Graph writes are deliberately disabled. This is a verified demonstration release, not a production certification or a guarantee of zero defects.

## Final documents

- `Sunhaven_v9_Final_Report.pdf`: complete inventory, baseline comparison, new/improved features, security, architecture, database, tests and limitations.
- `Sunhaven_v9_Operator_Handbook.pdf`: operating instructions, roles, scenario inputs, deployment settings and troubleshooting.
- Editable text versions are in `docs/`.
- Earlier guides and evidence are historical. **The v9 report and handbook take precedence.**

## What is new in v9

- Qualification register with independent verification and enforced care/clinical eligibility.
- Manager-then-operator approval for temporary site coverage.
- Time-limited named-resident emergency access, notification and independent closure.
- Explainable risk and dormancy signals; allowlisted plain-language reporting.
- Versioned operational policies; site/team hierarchy and scoped qualification delegates.
- Idempotent daily agency expiry/session cleanup/qualification reminders and durable in-app outbox.
- Authenticated read-only API and explicitly limited SCIM-shaped user representation.
- Session digests, rate limiting, stricter script CSP, request IDs and query-redacted logs.
- UTC date consistency, roster approval expiry, last-operator protection and self-review denial.
- Full-history audit search and consistent no-overwrite audit export.

## Verify

```text
python -m pip install -r requirements-test.txt
python run.py test
python qa/preflight.py
python qa/http_final.py
python qa/backup_check.py
python run.py verify-original
```

Recorded results: **88 portal + 66 SITAS + 13 SAIF = 167 passing automated tests**. Fifteen acceptance scenario groups passed over 103 real HTTP requests on each of the local and Waitress servers. See `evidence/` for raw results. The acceptance harness uses an isolated temporary database and port 8031.

## Optional Waitress deployment test

```text
python -m pip install -r portal/requirements-deploy.txt
cd portal
python serve.py
```

`compose.yaml` and the Dockerfile are supplied. The Docker build, public deployment, live tenant/MFA, real provisioning, load test and browser accessibility audit were not executed here.

## Visual evidence

The remote browser could not access localhost. `evidence/rendered-pages/` contains sanitized HTML captured from the running application; `evidence/page-renders/` contains clearly labelled offline document renderings. **These are not browser screenshots and do not prove JavaScript or responsive behavior.** The handbook explains the remaining local-browser checks.

## Boundaries

SQLite and the local ledger target one application process on one host. There is no distributed queue, multi-tenant isolation, remote immutable ledger, live email delivery or full SCIM provisioning server. `connectors.py` supplies typed extension points that fail closed when unconfigured. See the final report before using real workforce information.
