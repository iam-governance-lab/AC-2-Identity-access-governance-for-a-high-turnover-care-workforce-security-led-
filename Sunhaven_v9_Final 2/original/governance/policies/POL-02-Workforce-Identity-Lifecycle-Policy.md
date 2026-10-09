# POL-02 Workforce Identity Lifecycle Policy and Procedure

| Document field | Detail |
| --- | --- |
| Organisation | Sunhaven Care |
| Reference number | POL-02 |
| Document owner | Workforce or HR Owner |
| Administrator | IAM and Automation Lead |
| Approval authority | Sunhaven Service Owner |
| Version | 2.0 Draft |
| Classification | Internal - Student Laboratory Project |

A printed copy is uncontrolled. Refer to the version-controlled private project repository for the current version.

## 1 Purpose

1.1 This policy and procedure ensures that Sunhaven workforce identities and access remain aligned with approved employment information throughout the Joiner, Mover and Leaver lifecycle.

1.2 It is intended to reduce delayed onboarding, privilege accumulation, orphaned accounts, expired agency access and incorrect automation changes.

## 2 Scope

2.1 This policy and procedure applies to Sunhaven workforce identity events processed through the approved workforce record, Microsoft Entra ID, Microsoft Graph PowerShell automation, security groups, application roles, the Flask care portal, resident and facility assignments, and lifecycle evidence.

2.2 It applies to permanent, casual, agency and third-party workers represented in the Sunhaven laboratory.

2.3 The current implementation is a student proof of concept using fictional identities and synthetic resident data. It does not connect to a production HR system or production healthcare environment.

## 3 Policy statement

3.1 The approved workforce record is the authoritative source for a worker's identity, status, role, facility, sponsor and relevant dates.

3.2 A stable employee ID must identify the worker throughout the lifecycle. A name alone must not be used as the automation target.

3.3 Lifecycle automation must validate its input, identify exactly one target, show the proposed change, make only approved changes and verify the final state.

3.4 Invalid, missing, duplicated or ambiguous information must stop the workflow without changing an account.

3.5 Repeated execution must be safe and must not create duplicate identities, memberships or application-role assignments.

3.6 Obsolete access must be removed promptly when a worker changes duties, leaves Sunhaven or reaches an agency contract end date.

3.7 Every lifecycle event must produce evidence of the request, approval, action, result and final-state verification.

## 4 Procedure

### 4.1 Workforce record preparation and approval

4.1.1 The Workforce or HR Owner must prepare or approve the lifecycle record before the IAM operator makes a change.

4.1.2 The record must contain, where applicable:

- unique employee ID
- worker name and user principal name
- employment status
- job and application role
- facility
- manager or agency sponsor
- start date
- end date, and
- requested lifecycle action.

4.1.3 An agency record without a sponsor or end date must be rejected until the missing information is supplied and approved.

### 4.2 Validation and dry run

4.2.1 The operator must run the workforce-input validation before any cloud change.

4.2.2 Validation must check the required schema, approved values, dates, duplicate employee IDs and duplicate user principal names.

4.2.3 The automation must resolve exactly one intended identity. It must stop if the target is missing, duplicated or ambiguous.

4.2.4 A dry-run plan must show whether the action will create, update, disable, remove or make no change. The operator or approver must review the plan before execution.

### 4.3 Joiner procedure

4.3.1 Before creating access, the process must confirm that the worker is approved and active and that required role, facility, manager and date information is valid.

4.3.2 For an approved Joiner, the process must:

1. create or safely reconcile exactly one Entra identity
2. assign only the approved governed group and application role
3. require the worker to complete the applicable MFA registration
4. create the approved facility and resident assignments
5. read back the Entra and application state
6. test permitted access and at least one prohibited action, and
7. record the result and evidence.

4.3.3 A Joiner must not receive access when required information is missing or invalid.

### 4.4 Mover procedure

4.4.1 The process must compare the worker's previous access with the new approved role, facility and assignments.

4.4.2 For an approved Mover, the process must:

1. show the proposed removal and addition in the dry-run plan
2. remove obsolete access before adding the new access
3. update the worker's approved identity attributes
4. add only the new governed group and application role
5. update facility and resident assignments
6. revoke sessions or require a fresh sign-in when claims must change
7. verify that the new access works and the previous access no longer works, and
8. record before-and-after evidence.

4.4.3 The Mover process must prevent a worker from keeping old and new normal care roles unless a documented exception has been approved.

### 4.5 Leaver and expired-agency procedure

4.5.1 A worker must be processed as a Leaver when employment ends, an authorised departure is recorded or an agency contract expires without an approved extension.

4.5.2 For an approved Leaver, the process must:

1. resolve exactly one identity
2. disable the Entra account
3. revoke available sign-in sessions
4. remove Sunhaven-governed groups and care-application roles
5. remove facility and resident assignments
6. add the identity to the care portal's blocked-user control
7. read back the final Entra and application state
8. test that a new sign-in is denied
9. test that the next protected request from an existing portal session is denied, and
10. record the action and evidence.

4.5.3 The account must not be deleted immediately when deletion would remove evidence required for investigation, assessment or audit. Retention and disposal must follow the approved evidence plan.

### 4.6 Emergency suspension

4.6.1 Sunhaven may suspend access immediately when an account is suspected of compromise, a worker presents an immediate security risk, employment status is disputed or an authorised manager requests emergency suspension.

4.6.2 The operator must document the requester, reason, affected identity, time, actions and result. The Service Owner or Security Reviewer must review the suspension as soon as practical.

### 4.7 Failure and remediation

4.7.1 A failed or partially completed lifecycle action must stop further unsafe processing and record which actions succeeded or failed.

4.7.2 The responsible owner must be notified. The account must remain in, or be moved to, the safer state while the problem is investigated.

4.7.3 Correction must use an approved remediation process. The final state must be read back and the relevant tests repeated before closure.

### 4.8 Verification and evidence

4.8.1 Lifecycle evidence must include the workforce input identifier, dry-run plan, approval record, operator, target identity, UTC timestamp, actions attempted, results, final-state readback and relevant positive and negative tests.

4.8.2 Evidence must not contain passwords, tokens, client secrets or unnecessary personal or resident information.

### 4.9 Compliance checking

4.9.1 The existing project must use its validation scripts, state exports, access-review reports, application logs and test evidence to identify lifecycle errors.

4.9.2 The proposed policy-compliance checker will add read-only checks for enabled leavers, expired agency identities, role mismatches and other access drift. It must be described as planned until its rules, script, outputs and tests exist in the repository.

4.9.3 Remediation must remain a separate, approved workflow. A compliance finding must not automatically make a directory change.

## 5 Responsibilities

### 5.1 Role responsibilities

| Role | Responsibility |
| --- | --- |
| Workforce or HR Owner | Maintains accurate workforce status, role, facility, sponsor and dates; initiates lifecycle events and corrects invalid records. |
| Manager or agency sponsor | Approves required access, confirms role and contract changes and reviews exceptions. |
| IAM operator | Reviews validation and dry-run results, executes only approved changes and verifies final state and evidence. |
| Application owner | Maintains application roles, resident assignments and blocked-user status so that application access reflects the lifecycle outcome. |
| Security reviewer | Reviews failures, unexpected access, emergency suspensions and unresolved remediation. |
| Sunhaven Service Owner | Approves this document and accepts any residual risk that cannot be removed within the approved project scope. |

### 5.2 Compliance monitoring and review

5.2.1 Compliance must be assessed through the Joiner, Mover and Leaver test cases, including duplicate identities, invalid agency data, role changes, expired contracts, repeated execution and already-open leaver sessions.

5.2.2 The IAM and Automation Lead must review lifecycle failures and incomplete remediation at each project assurance milestone.

5.2.3 This document must be reviewed after a material lifecycle failure or a major change to the workforce schema, Entra configuration, Graph permissions, lifecycle scripts or application access model.

### 5.3 Reporting

5.3.1 A lifecycle failure that leaves excessive or active leaver access must be reported promptly to the Workforce or HR Owner, Service Owner and Security Reviewer.

5.3.2 The report must identify the worker, intended state, actual state, completed actions, failed actions, temporary protection, owner and planned retest.

### 5.4 Records management

5.4.1 Workforce inputs, dry-run plans, approvals, execution results, readbacks, failure records, remediation evidence and tests must be stored in the approved private project location.

5.4.2 Evidence must follow the project's naming, indexing, access and retention rules.

5.4.3 Credentials and unnecessary identity or resident information must be removed before evidence is stored or submitted.

## 6 Definitions

| Term | Definition |
| --- | --- |
| Authoritative workforce record | The approved record that states the identity and access Sunhaven intends a worker to have. |
| Desired state | The approved account, role, group, facility, assignment and status that should exist after processing. |
| Dry run | A preview of intended actions that makes no cloud or application change. |
| Fail closed | Stopping without granting or changing access when required information or certainty is missing. |
| Idempotent | Safe to run repeatedly without creating duplicate or unintended results. |
| Joiner | A person receiving a workforce identity and approved access. |
| Leaver | A person whose employment, contract or approved access has ended. |
| Mover | A person whose role, facility or duties have changed. |
| Readback | Retrieving the post-change state to verify that the intended result exists. |
| Reconciliation | Comparing approved desired state with actual state and correcting approved differences. |

## 7 Related documents and guidance

- Sunhaven Care Workforce IAM Solution Design
- Sunhaven Access Management Policy and Procedure POL-01
- Sunhaven Authentication and Shared Device Security Policy and Procedure POL-03
- Sunhaven workforce input schema, JML scripts, test plan and evidence index
- CQUniversity Australia, *Privacy Policy and Procedure*, reference 3124, effective 12 March 2024. Structural reference only: https://delivery-cqucontenthub.stylelabs.cloud/api/public/content/privacy-policy-and-procedure.pdf
- Microsoft Graph PowerShell documentation: https://learn.microsoft.com/en-us/powershell/microsoftgraph/overview

## 8 Feedback

8.1 Feedback or proposed amendments must be sent to the document owner through the project's documented change-control process.

8.2 A proposed change must identify any effect on the workforce schema, lifecycle scripts, permissions, application controls, tests and evidence.

## 9 Approval and review details

| Approval and review field | Detail |
| --- | --- |
| Approval authority | Sunhaven Service Owner |
| Required consultation | Workforce or HR Owner, IAM and Automation Lead, Application Owner and Security Reviewer |
| Administrator | IAM and Automation Lead |
| Approval status | Draft for capstone review; not yet approved for operational use |
| Next review | 12 months after approval, or earlier following a material lifecycle failure or system change |

### Approval and amendment history

| Version | Date | Details | Authority |
| --- | --- | --- | --- |
| 1.0 | September 2026 | Initial student-project policy draft | Project team |
| 2.0 Draft | 9 September 2026 | Restructured as a policy and procedure; clarified lifecycle steps, monitoring, reporting, records, definitions and implementation status | Pending Sunhaven Service Owner approval |

## Appendix A Implementation status

| Requirement or control | Current project position | Status |
| --- | --- | --- |
| Workforce schema validation and duplicate checks | Present in the PowerShell input-validation workflow | Implemented |
| Dry-run lifecycle planning | Present in the project automation workflow | Implemented |
| Joiner, Mover and Leaver automation with readback | Present in the PowerShell lifecycle scripts | Implemented |
| Local care-portal block for leavers | Present in the Flask and SQLite implementation | Implemented |
| Access-review export and limited denied-assignment remediation | Present within the approved laboratory scope | Implemented with defined laboratory scope |
| Live HR system integration | The laboratory uses an approved CSV workforce source | Outside current scope |
| Automated policy-compliance checker and rescan closure | Designed as a remaining capstone extension; not present in the current code package | Planned |

