# Sunhaven Care IAM — version 1.0 lab governance pack

**Status:** prototype policies for fictional Sunhaven Care. Effective for controlled lab demonstrations; the organisation would need an authorised policy owner, legal review, training and periodic review before real use. Control IDs P01–P10 and risk IDs R01–R07 match the application's Policies & risks page.

## P01: Workforce identity lifecycle

HR/approved sponsor supplies a unique employee ID, status, role, facility and dates. Agency access requires a named sponsor and expiry. Operators check a dry run before creating or changing identities and verify final state afterwards. Unclear, duplicate or invalid records fail closed. Keep a correlation ID for each change. No real person may be represented by synthetic records.

## P02: Change approval and segregation

The requester cannot approve their own Mover request. An authorised manager/operator reviews the reason and requested role; high privilege requires an operator. Approved requests are valid for seven days, tied to the worker's role and facility snapshot, and usable once. A separate execution step applies the change. Any stale approval requires a new decision.

## P03: Least privilege and resident access

Grant one approved normal care role where possible; only active same-facility resident assignments provide CareWorker/AgencyWorker visibility. Nurse and Manager views follow their defined scope. Route handling checks authorisation even when reached through a direct URL. Review organisation-wide Manager scope before real data use.

## P04: Third-party and agency access

The sponsor owns the contract end date. The operator previews daily expiry and due-soon reminders. For an expired contract, a reviewed local automation run suspends simulated access, removes roles and assignments, destroys sessions and blocks login, with a recorded reason. Never present the mock directory flag as actual Entra disablement.

## P05: Leaver and session management

On departure, remove application roles and resident assignments, revoke sessions and set a portal block. The demo default session expires after 15 minutes. Shared devices need an actual managed sign-out and unattended session standard beyond this application. The operator tests a denied request after a Leaver event.

## P06: Access recertification and exceptions

The manager reviews each active worker at least every 90 days and records Retain, Change, Remove or a time-limited exception with reason. Pending Change/Remove decisions remain open until a documented correction and review closure. Exceptions have an expiry. An auditor verifies evidence independently.

## P07: Evidence and integrity

Security events record UTC time, actor, target, action, outcome and correlation ID. Audit details are sanitised. The local ledger rechecks the original audit row and signs an ordered hash chain and external head. An integrity failure is an incident requiring investigation; never silently rebuild a broken chain. The DB, key and checkpoint share a controlled backup/restore process. This is tamper-evident lab evidence, not immutable enterprise storage.

## P08: Authentication and MFA

Production access requires approved Entra OIDC sign-in and tenant MFA policy evidence. The local identity picker has no password and exists only for an offline demo. Never expose it publicly. Controlled MFA sign-in telemetry may be analysed for a correlated pattern; a single unknown failure is not by itself a finding. Device-trust checks are future integration work.

## P09: Secret, privacy and retention

Do not commit credentials, signing keys, tokens, resident real names or production log exports. Restrict SQLite file and backup permissions; redact sensitive details in the audit. Use only fictional identities and residents in demos. Assign retention and deletion periods before handling real data. Access to exports should follow job duties.

## P10: Remediation and incident response

Scan policy checks C01–C08, prioritise Critical/High before routine review, assign an owner and record corrective evidence. A suspected MFA fatigue pattern requires a human investigator, review of sign-in context and session revocation if justified. For a ledger FAIL result, preserve original DB/key/checkpoint copies, suspend untrusted automation, identify the first mismatch and investigate. The tool must not autonomously promote/disable a worker on an MFA finding alone.

## Risk register and demonstration evidence

| Risk | Current treatment | Residual issue |
|---|---|---|
| R01 departed worker retains access | Layered local Leaver block, role removal and session revocation | No verified cloud disablement |
| R02 expired agency worker retains access | Daily preview, operator-run atomic local suspension | No live directory timer or job scheduler |
| R03 privilege accumulation | Approved one-use Mover, role replacement and assignment reset | Organisation-wide Manager permissions |
| R04 shared workstation reuse | Absolute session expiry and operator revoke | No managed endpoint signal or idle lock |
| R05 audit alteration | HMAC chain plus external signed checkpoint | Same-host key control and crash window |
| R06 MFA prompt fatigue | Five-minute pattern detector and correlated finding | No connected real Entra event feed |
| R07 overdue review | Ninety-day finding and reminder | Human review and evidence still required |

The risk scores and policy decisions are illustrative. A real operator would need sign-off, calibration to local threat context and periodic review.
