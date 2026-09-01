# POL-01 — Access Management Policy

**Organisation:** Sunhaven Care
**Policy owner:** Sunhaven Service Owner
**Technical owner:** IAM and Security Lead
**Version:** 1.0
**Classification:** Internal – Student Laboratory Project
**Review frequency:** At every major project milestone and at least annually if adopted operationally

## 1. Purpose

The purpose of this policy is to ensure that Sunhaven Care workers receive only the access required for their approved duties and retain that access only while it remains necessary.

This policy supports least privilege, protection of resident information, clear accountability and timely removal of unnecessary access.

## 2. Scope

This policy applies to:

- Permanent employees.
- Casual workers.
- Nurses and care workers.
- Managers.
- Agency and third-party workers.
- Auditors.
- IAM administrators.
- Microsoft Entra ID accounts.
- The Sunhaven care portal.
- Resident, facility and assignment information used by the project.

The current implementation is a student laboratory proof of concept using fictional identities and synthetic resident data.

## 3. Policy requirements

### 3.1 Individual accounts

Every Sunhaven worker must use an individual, named account.

Shared workforce accounts are prohibited because they prevent Sunhaven from determining who performed an action.

### 3.2 Access approval

Access must not be granted without an approved workforce record and an identified manager or agency sponsor.

The approval must identify:

- Worker identity.
- Employment status.
- Required role.
- Facility.
- Manager or sponsor.
- Start date.
- Contract end date where applicable.

### 3.3 Least privilege

Workers must receive only the minimum access necessary for their current duties.

Access must be determined using:

- Approved application role.
- Facility.
- Resident assignment.
- Employment status.
- Agency contract end date.

A worker must have only one normal care-application role unless a documented exception has been approved.

### 3.4 Role-based access

The Sunhaven care portal must enforce access on the server.

Authentication alone must not provide access to protected information.

The approved roles are:

- CareWorker.
- Nurse.
- Manager.
- AgencyWorker.
- Auditor.
- IAMOperator.

Unauthorised requests must be denied, including direct requests that bypass the user interface.

### 3.5 Privileged access

Administrative duties must use a separate authorised administrator identity.

Care-worker roles must not provide Entra ID or IAM administration privileges.

Microsoft Graph permissions must be limited to those necessary for the approved lifecycle operation.

### 3.6 Agency access

Every agency worker must have:

- A named sponsor.
- An approved role.
- A contract start date.
- A mandatory contract end date.
- Access limited to assigned duties and residents.

Agency access must be disabled or reviewed when the contract end date is reached.

### 3.7 Access reviews

Managers must periodically review workforce access.

The review must confirm whether access should be:

- Retained.
- Modified.
- Removed.
- Temporarily accepted as an exception.

Review decisions must record the reviewer, date, decision and required remediation.

### 3.8 Access removal

Access must be removed when:

- Employment ends.
- An agency contract expires.
- A role is no longer required.
- A manager denies continued access.
- The account presents an unacceptable security risk.

Removal must include relevant Entra roles, groups, application roles and resident assignments.

### 3.9 Logging and evidence

Access creation, modification, review and removal must produce sufficient evidence.

Evidence should include:

- Approver.
- Operator.
- Target identity.
- Action.
- UTC timestamp.
- Result.
- Correlation identifier.
- Final-state verification.

Passwords, tokens, client secrets and unnecessary personal information must not appear in evidence.

## 4. Roles and responsibilities

**Service owner**

- Approves the policy.
- Accepts residual business risk.
- Resolves major access disputes.

**Manager or agency sponsor**

- Confirms the worker’s business need.
- Approves role and facility access.
- Completes access reviews.

**IAM operator**

- Performs approved account and access changes.
- Uses least-privilege administration.
- Verifies the final result.

**Security or audit reviewer**

- Reviews privileged access, exceptions and audit evidence.
- Reports policy violations.

**Workers**

- Use only their individual accounts.
- Protect authentication information.
- Report incorrect or unnecessary access.

## 5. Exceptions

An exception must record:

- Business justification.
- Affected identity and access.
- Risk created by the exception.
- Compensating controls.
- Approver.
- Responsible owner.
- Expiry date.

Permanent or undocumented exceptions are prohibited.

## 6. Compliance

Non-compliance may result in access removal, investigation, corrective action or risk escalation.

For the laboratory project, compliance is evaluated through test cases, configuration reviews, audit records and the policy-compliance checker.

## 7. References

- SANS Institute, _Access Management Policy_: https://www.sans.org/information-security-policy/access-management-policy
- SANS Institute, _Privileged Account Management Policy_: https://www.sans.org/information-security-policy/privileged-account-management-policy
