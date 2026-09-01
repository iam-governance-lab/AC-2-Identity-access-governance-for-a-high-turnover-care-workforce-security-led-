# POL-02 — Workforce Identity Lifecycle Policy

**Organisation:** Sunhaven Care
**Policy owner:** Workforce/HR Owner
**Technical owner:** IAM and Automation Lead
**Version:** 1.0
**Classification:** Internal – Student Laboratory Project
**Review frequency:** At every major project milestone and after any material lifecycle failure

## 1. Purpose

The purpose of this policy is to ensure that workforce identities and access remain aligned with approved employment status throughout the Joiner-Mover-Leaver lifecycle.

The policy reduces delayed onboarding, privilege accumulation, orphaned accounts, expired agency access and incorrect automation changes.

## 2. Scope

This policy applies to all Sunhaven workforce identity events processed through:

- The approved workforce record.
- Microsoft Entra ID.
- Microsoft Graph PowerShell automation.
- Sunhaven groups and application roles.
- The Flask care portal.
- Resident and facility assignments.

## 3. Authoritative workforce information

Lifecycle actions must be based on an approved workforce record.

The record must contain, where applicable:

- Unique employee ID.
- Worker name.
- Employment status.
- Role.
- Facility.
- Manager.
- Agency sponsor.
- Start date.
- End date.
- Required lifecycle action.

The stable employee ID must be used to identify a worker. Names alone must not be used as the automation target.

## 4. General automation requirements

Before making a change, the lifecycle process must:

1. Validate the input schema.
2. Check required fields and approved values.
3. Resolve exactly one target identity.
4. Stop if the identity is missing, duplicated or ambiguous.
5. Generate a dry-run plan.
6. Obtain approval where required.
7. Perform the approved action.
8. Read back the final state.
9. Record the result and evidence.

The process must fail closed. Invalid or uncertain input must not result in an account change.

Repeated execution must not create duplicate identities or duplicate role assignments.

## 5. Joiner requirements

When a worker joins Sunhaven, the process must:

- Confirm that the workforce record is approved and Active.
- Confirm that the employee ID is unique.
- Validate the role, facility, manager and relevant dates.
- Require a sponsor and end date for an agency worker.
- Create or safely reconcile exactly one Entra identity.
- Assign only the approved groups and application role.
- Require MFA registration.
- Create required facility and resident assignments.
- Verify that permitted access succeeds.
- Verify that prohibited access is denied.
- Record the completed onboarding evidence.

A Joiner must not receive access if required information is missing or invalid.

## 6. Mover requirements

When a worker changes role, facility or duties, the process must:

- Identify the previous and new approved access.
- Show the proposed changes in a dry-run plan.
- Remove obsolete access before adding new access.
- Assign only the new approved role and groups.
- Update facility and resident assignments.
- Require token or claim refresh where necessary.
- Test the new permitted access.
- Test that the previous access is no longer available.
- Run a policy-compliance scan for access drift.
- Record before-and-after evidence.

The Mover process must prevent a worker from accumulating old and new roles without an approved exception.

## 7. Leaver requirements

When a worker leaves Sunhaven or an agency contract expires, the process must:

- Resolve exactly one identity.
- Disable the Entra account.
- Revoke available sign-in sessions.
- Remove governed groups and application roles.
- Remove facility and resident assignments.
- Add the user to the application blocked-user control.
- Read back the final Entra and application state.
- Test that a new sign-in is denied.
- Test that the next protected request from an existing portal session is denied.
- Record the leaver result and evidence.

The account must not be deleted immediately when deletion would remove necessary investigation or audit information. Retention and deletion must follow an approved procedure.

## 8. Emergency suspension

Sunhaven may immediately suspend access when:

- An account is suspected of compromise.
- A worker presents an immediate security risk.
- Employment or contract status is disputed.
- An authorised manager requests emergency suspension.

Emergency suspension must be documented and reviewed as soon as practical.

## 9. Responsibilities

**Workforce/HR owner**

- Maintains accurate worker status, role and dates.
- Reports Joiner, Mover and Leaver events.
- Corrects inaccurate workforce information.

**Manager or sponsor**

- Approves required business access.
- Confirms role changes and contract extensions.
- Reviews exceptions.

**IAM operator**

- Reviews the dry-run plan.
- Executes only approved changes.
- Verifies final state and evidence.

**Application owner**

- Maintains roles, assignments and blocked-user status.
- Ensures application access reflects the lifecycle outcome.

**Security reviewer**

- Reviews failures, incorrect changes and unresolved access.
- Confirms that corrective actions are completed.

## 10. Exceptions and failures

A failed or partially completed lifecycle action must:

- Stop further unsafe processing.
- Record the completed and failed actions.
- Notify the responsible owner.
- Prevent unnecessary access from being granted.
- Be corrected through an approved remediation process.
- Be retested after correction.

## 11. Evidence

Lifecycle evidence must include:

- Workforce input identifier.
- Dry-run plan.
- Approval record.
- Operator.
- Target identity.
- UTC timestamp.
- Actions attempted.
- Results.
- Final-state readback.
- Relevant positive and negative tests.

## 12. Compliance

The policy is verified through Joiner, Mover and Leaver test cases, including duplicate identities, invalid agency data, role changes, expired contracts and already-open leaver sessions.
