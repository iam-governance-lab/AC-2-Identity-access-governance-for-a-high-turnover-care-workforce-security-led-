# Version 6.0

Adds reviewed mock-directory agency expiry automation, a versioned policy/risk catalogue, visible MFA findings and a complete operating/presentation/security pack. 47 tests pass. Real tenant actions remain outside verified scope.

# Version 5.0

Adds integrated synthetic security assurance (threat comparison, MFA pattern detection and HMAC/hash-chained ledger), scoped UI, demo evidence exporter, fifteen-minute sessions and 44 tested cases. The proposal and teammate source boundaries are documented in `GROUP_PROJECT_INTEGRATION_GUIDE.md`; live tenant and teammate repository integration are pending.

# Version 4.0

Facility-filtered charts, clickable statistics, light/dark themes, scoped workspace search, personal notification reads, approval timelines, onboarding evidence checklists and filtered PDF reports. See V4_FEATURE_GUIDE.md.

# Version 3.0

Adds controlled approved Mover execution, seven-day expiry, approval snapshot validation,
single-use execution and local transaction rollback on audit failure. The old direct web
Mover application is blocked; the dry-run preview remains available.

Adds Security operations: resident assignments, local session inventory/revocation,
remediation tasks with owner/priority/evidence, and pending review closure. Remove-review
closure verifies local access has been removed. Governance roles retain organisation-wide
scope. Audit log and access updates commit atomically for the new governance operations.

Existing data is preserved using additive tables. Old approvals without snapshots cannot
execute and must be resubmitted. No real Graph writes are enabled. See the complete guide
for the limits of each workflow. The older PDF guides are historical references.
