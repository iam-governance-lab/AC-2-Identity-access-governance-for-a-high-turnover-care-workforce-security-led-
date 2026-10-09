# Version 9 release and second audit

Current operating instructions and inventory are in the v9 handbook and final report (PDF at project root; editable Markdown in this directory).

## Audit scope

All Python source modules were indexed and parsed, database schemas and route/mixin architecture inspected, and critical authentication, authorization, lifecycle, approval, expiry, evidence, integration and operational paths reviewed. The original code remains unchanged; external tenant execution is outside the available environment. Static analysis is not a formal security certification.

## Main fixes

- Fail-closed missing agency end date and future-start checks at session and service boundaries.
- One UTC business date across contract, qualification, review and job logic.
- Hashed session storage, CSRF retention, script CSP tightening, rate limits and safe request logs.
- Lifecycle authorization, self/last-operator protection and self-attestation denial.
- Roster approval lifetime, detailed previews, approver safety and remediation tasks.
- Consistent locked audit-export snapshot and atomic no-overwrite destination.
- Full-campaign pending totals and transactional team synchronization.
- Proper SQLite connection closure and fewer repeated compliance/risk queries.

## Added functional modules

`assurance.py`, `assurance_ui.py`, `connectors.py`, `clock.py`, `static/final.css`, 22 new tests and reproducible QA commands.

## Evidence

167 automated tests passed. Both HTTP transports passed 15 scenario groups / 103 requests each. Fresh-seed schema/FK checks, original manifest and backup restore rehearsal passed. Browser screenshot capture was blocked; offline HTML renderings are labelled. No live-tenant, Docker-image, independent-penetration or enterprise-load validation is claimed.
