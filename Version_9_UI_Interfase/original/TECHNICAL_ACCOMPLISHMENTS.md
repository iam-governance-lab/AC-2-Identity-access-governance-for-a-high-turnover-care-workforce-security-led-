# Sunhaven Care Workforce IAM — Technical Accomplishments

Use the concise bullets for a resume and the expanded bullets for a portfolio, LinkedIn project entry or interview discussion. The wording accurately describes a student-controlled laboratory using fictional data.

## Resume-ready bullets

- Built an end-to-end workforce Identity and Access Management lab using **Microsoft Entra ID, Microsoft Graph, PowerShell, Python, Flask, OIDC and SQLite**, covering Joiner, Mover and Leaver lifecycles.
- Engineered **safe, idempotent JML automation** with local input validation, read-only dry runs, exact approval phrases, explicit tenant guards, immutable object-ID targeting and final-state readback verification.
- Implemented **least-privilege RBAC** using Entra security groups and application roles, plus assignment-scoped resident access and server-side HTTP `403` enforcement for unauthorized clinical and manager routes.
- Designed a fail-closed **Leaver workflow** that disables accounts, revokes sessions, removes governed groups and app roles, blocks active local sessions and verifies the resulting state.
- Measured the lab Leaver workflow at **7.57 seconds** and observed application denial **16.76 seconds** after workflow start, demonstrating rapid revocation across cloud and application controls.
- Developed sanitized **security audit and UTC event-correlation evidence**, combining Entra sign-in/audit data with application authorization and lifecycle events.
- Built and executed a **14-test security and lifecycle suite**, validating positive access, negative authorization, idempotency, invalid-input rejection, expiry, leaver enforcement, secret safety and wrong-tenant protection; achieved **14/14 PASS**.
- Performed an evidence-backed **access review and remediation**, removing denied access, preserving approved assignments and validating the post-review least-privilege state.
- Established repository security controls that exclude `.env`, credentials, raw exports and private evidence, and completed **secret adjudication plus active Git-history sanitization** before a tagged private release.
- Produced a versioned **risk register, lessons-learned assessment, future roadmap, cleanup plan and final handover package** for a controlled IAM laboratory release.

## Portfolio and interview bullets

### Identity lifecycle automation

- Created PowerShell workflows for Joiner, Mover and Leaver events, integrating workforce CSV records with Microsoft Graph directory operations.
- Implemented a validation pipeline that detects unsupported roles, duplicate employee IDs, duplicate UPNs, missing employment dates and invalid lifecycle states before any Graph connection or write occurs.
- Separated planning from execution: read-only Graph discovery generates `CREATE`, `UPDATE`, `DISABLE`, `NO CHANGE` or `ERROR` plans with zero directory writes.
- Added explicit human-in-the-loop approval through employee-specific phrases such as `CREATE <EmployeeId>` and `LEAVE <EmployeeId>`; mismatches fail before mutation.
- Designed idempotent reruns so an already compliant identity returns `NO CHANGE` and performs zero writes, preventing duplicate accounts, memberships or role assignments.
- Used immutable Entra object IDs and configuration maps to resolve groups, service principals and application roles safely rather than relying only on mutable display names.
- Added compensating rollback behavior for partial Joiner failures and final-state verification for account attributes, group memberships and app-role assignments.

### Authentication and authorization

- Integrated Flask with Microsoft identity/OIDC authentication while ensuring tokens and client secrets are never displayed or written to audit evidence.
- Implemented reusable Python decorators for active-session enforcement and server-side role authorization.
- Enforced a 15-minute fixed local application session lifetime with `HttpOnly` and `SameSite=Lax` cookie protections and no per-request lifetime refresh.
- Combined RBAC with relationship-based access: CareWorker and AgencyWorker users see only residents connected through active, non-expired assignment records.
- Built route-level authorization for CareWorker, AgencyWorker, Nurse, Manager and Auditor roles and recorded sanitized allow/deny audit events.
- Added immediate local leaver blocking on every protected request, closing the gap between cloud-session revocation and application-side denial for an already signed-in user.

### Leaver and session-revocation controls

- Ordered Leaver actions to reduce exposure quickly: disable the account first, revoke sessions, remove governed groups, remove care-app roles, apply the local block and verify the final state.
- Correlated Graph results, local application block status, sign-in failures and application audit events to prove both new-login denial and active-session denial.
- Verified account-disabled error evidence, zero remaining governed groups, zero remaining care-app roles and an active local block after offboarding.
- Demonstrated stale-session handling after a role change by revoking sessions and validating the new role only in a fresh authentication context.

### Audit, governance and security assurance

- Created sanitized audit exports that retain timestamps, object identifiers, activities and outcomes while removing network source, device, browser, session, token and credential data.
- Normalized identity, lifecycle and application events into UTC timelines and validated timestamp parsing, completeness, chronological ordering and expected outcomes.
- Implemented a documented access-review workflow with reviewer/operator separation, dry-run remediation, explicit approval, one-assignment removal and post-review validation.
- Built a repository safety scanner and adjudication process to distinguish real risks from template placeholders and runtime-generated credential expressions without printing candidate secret values.
- Detected a credential-like historical transcript entry, preserved a private recovery bundle, sanitized the active repository and rewrote/validated Git history so all reachable versions contained the redaction marker.
- Added a wrong-tenant negative test proving tenant validation occurs before the first write-capable Graph command and executes zero writes when the authenticated tenant differs.

### Testing and engineering practice

- Designed a requirements-to-test crosswalk covering 14 core scenarios across authentication, RBAC, Joiner, Mover, Leaver, review, privacy and automation safety requirements.
- Tested positive and negative authorization paths, including assigned-resident access, CareWorker clinical denial, Nurse clinical access and post-review application denial.
- Validated fail-closed behavior for invalid roles and duplicate employee IDs and confirmed rejected records created no Entra identities.
- Captured reproducible, sanitized evidence for dry runs, apply results, idempotent reruns, state exports, application audits, sign-in outcomes and access reviews.
- Used Git commits and annotated release tags to identify the tested release while excluding local configuration, credentials, raw evidence and private recovery material.

## Short portfolio summary

Built a security-focused workforce IAM laboratory for a fictional care organisation using Microsoft Entra ID, Microsoft Graph, PowerShell, Python, Flask, OIDC and SQLite. The solution automates validated and approval-gated Joiner–Mover–Leaver workflows, enforces group- and application-role-based access, scopes frontline staff to assigned residents, revokes stale sessions and immediately blocks leavers at the application layer. I also designed a 14-test security suite, UTC audit-correlation process, access-review workflow, repository secret/history controls and a complete risk, roadmap and handover package. All 14 core tests passed on the tagged private release.

## Suggested technology keywords

`Microsoft Entra ID` · `Microsoft Graph` · `Identity and Access Management` · `Joiner-Mover-Leaver` · `RBAC` · `OIDC` · `PowerShell` · `Python` · `Flask` · `SQLite` · `Security Automation` · `Identity Governance` · `Session Revocation` · `Audit Correlation` · `Least Privilege` · `Secure SDLC` · `Git`

