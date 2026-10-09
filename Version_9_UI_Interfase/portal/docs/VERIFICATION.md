# Verification record

Version 6: 47 passing tests (`test-results-v6.txt`). Includes reviewed agency-expiry automation, CSRF and role gates, stale preview and idempotent shutdown, control catalogue page and the version 5 ledger/MFA regression suite. The v6 DOCX was rendered and visually reviewed page by page.


Version 5: 44 passing tests (`test-results-v5.txt`). Includes ledger tamper/tail/key checks, MFA correlation, threat model, assurance page and scoped ALLOW/DENY evidence. A separate controlled demo writes example evidence under `sample-security-evidence/`. See `GROUP_PROJECT_INTEGRATION_GUIDE.md` for boundaries.


- Version 4: 38 automated tests passed. Full output: test-results-v4.txt.
- Version 4 local HTTP checks: http-smoke-v4.txt.
- Sample PDF rendered and inspected; JavaScript syntax checked.
- Coverage: lifecycle Joiner/Mover/Leaver, roles, compliance fixtures, audit
  redaction, all governance routes, CSRF missing/forged tokens, Entra/demo
  separation, expired/disabled access, resident scope, notes persistence and
  HTML escaping, approval duplication/finality/self-approval/privilege checks,
  review validation, CSV formula handling, session revocation, production
  configuration/cookies, body limit, unsupported methods and database health.
- Python compilation completed successfully.
- Local HTTP smoke test: health, login, dashboard, employees, notes, requests
  and employee CSV responded successfully using the local server.
- Deployment route adapter is covered by the automated WSGI integration tests.
- Browser visual/interaction verification was blocked by the environment's local
  address access restriction. Mobile layout and client-side pagination/filtering
  are implemented but still need browser acceptance testing on the user's PC.
- Docker was unavailable. Docker/Compose/TLS execution and real Entra/MFA sign-in
  remain unverified and require the deployment owner's environment.
- No public deployment performed; real Graph writes are disabled.

Version 3 adds tests for approved execution, one-time use, stale/expired approvals,
assignment scope, revocation, task updates, removal closure and atomic audit rollback.
