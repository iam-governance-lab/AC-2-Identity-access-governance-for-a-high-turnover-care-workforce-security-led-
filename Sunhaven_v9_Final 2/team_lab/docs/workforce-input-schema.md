# Sunhaven Workforce Input Schema

## Purpose

The workforce.csv file represents approved fictional HR input for the
Sunhaven Care IAM lab.

The file contains desired workforce state. It must pass local
validation and dry-run review before any Microsoft Graph write is
permitted.

## Required columns

| Column | Required | Purpose |
|---|---|---|
| employeeId | Yes | Stable identity reconciliation key |
| displayName | Yes | Fictional TEST display name |
| mailAlias | Yes | Source for the planned lab UPN |
| jobRole | Yes | Desired Sunhaven RBAC role |
| facility | Yes | Desired facility or department |
| status | Yes | Active, Leaving or Inactive |
| startDate | No | Workforce start date in YYYY-MM-DD |
| endDate | Conditional | Required for AgencyWorker and Leaving |

## Allowed job roles

- CareWorker
- Nurse
- Manager
- AgencyWorker
- Auditor

Privileged tenant administrator roles are not assigned through the
ordinary workforce feed.

## Allowed lifecycle statuses

- Active
- Leaving
- Inactive

## Validation rules

1. employeeId, displayName, mailAlias, jobRole, facility and status
   cannot be blank.
2. Every displayName must contain TEST.
3. employeeId values must be unique within the file.
4. The planned UPN generated from mailAlias must be unique.
5. jobRole must be present in the allowed-role list.
6. status must be Active, Leaving or Inactive.
7. AgencyWorker records must contain endDate.
8. Leaving records must contain endDate.
9. Dates must use the YYYY-MM-DD format.
10. endDate cannot be earlier than startDate.
11. The entire file must be validated before any Graph write.
12. Validation failures must be written to a separate evidence file.
13. Passwords, access tokens and client secrets must never be stored
    in the CSV or workflow log.

## Reconciliation safety

The automation will match Microsoft Entra users by employeeId.

Zero unexpected matches or multiple matches will stop the affected
workflow for human review. Display name alone will never be used as the
identity match key.

## Lab-data classification

All identities and workforce records are fictional TEST records. No
real worker, resident, diagnosis or clinical information is used.
