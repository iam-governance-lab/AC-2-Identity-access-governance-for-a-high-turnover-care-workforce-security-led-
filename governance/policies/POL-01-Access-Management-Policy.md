# POL-01 Access Management Policy and Procedure

| Document field | Detail |
| --- | --- |
| Organisation | Sunhaven Care |
| Reference number | POL-01 |
| Document owner | Sunhaven Service Owner |
| Administrator | IAM and Security Lead |
| Approval authority | Sunhaven Service Owner |
| Version | 2.0 Draft |
| Classification | Internal - Student Laboratory Project |

A printed copy is uncontrolled. Refer to the version-controlled private project repository for the current version.

## 1 Purpose

1.1 This policy and procedure ensures that Sunhaven Care workers receive only the system access needed for their approved duties and keep that access only while it remains necessary.

1.2 It supports least privilege, protection of resident information, individual accountability, timely access removal and reliable audit evidence.

## 2 Scope

2.1 This policy and procedure applies to permanent employees, casual workers, nurses, care workers, managers, agency and third-party workers, auditors, IAM operators and administrators represented in the Sunhaven Care laboratory.

2.2 It covers Microsoft Entra ID identities, security groups, application roles, the Sunhaven Care Portal, resident and facility assignments, access-review records, and the PowerShell processes used to administer access.

2.3 The current implementation is a student proof of concept. It uses fictional identities and synthetic resident data and is not approved for production healthcare use.

## 3 Policy statement

3.1 Sunhaven Care will grant access only when an approved business need exists and an authorised manager or agency sponsor has confirmed the request.

3.2 Every worker must use an individual identity. Shared workforce accounts are prohibited.

3.3 Access must follow least privilege and must be based on the worker's current role, employment status, facility and resident assignments.

3.4 Authentication does not automatically authorise access to protected information. The care portal must perform server-side authorisation checks for every protected function.

3.5 Privileged access must remain separate from normal care duties and must use a named administrator identity with only the permissions needed for the approved task.

3.6 Access must be reviewed, changed or removed when the worker's duties, facility, contract or employment status changes.

3.7 Access decisions and changes must create evidence that can be reviewed without exposing passwords, tokens, client secrets or unnecessary personal information.

## 4 Procedure

### 4.1 Access request and approval

4.1.1 A manager or agency sponsor must submit or approve the workforce record before access is granted.

4.1.2 The approved record must identify, where applicable:

- the worker's unique employee ID and name
- employment status
- required job and application role
- facility and resident assignments
- manager or agency sponsor
- start date, and
- contract end date for agency or time-limited access.

4.1.3 An incomplete, duplicated or ambiguous request must be rejected and returned for correction. The IAM operator must not guess the intended identity or access.

### 4.2 Account and access provision

4.2.1 The IAM operator must use the approved employee ID to create or identify exactly one Microsoft Entra ID account.

4.2.2 The operator must review the proposed change before execution. Where automation is used, a dry-run plan must show the intended account, group and application-role changes.

4.2.3 The worker must receive only the approved groups, application role, facility access and resident assignments.

4.2.4 The completed change must be read back from Entra ID and the application where applicable. Provisioning is not complete until the final state has been verified.

### 4.3 Least privilege and role-based access

4.3.1 The approved application roles are CareWorker, Nurse, Manager, AgencyWorker, Auditor and IAMOperator.

4.3.2 A worker must hold only one normal care-application role unless a documented, time-limited exception has been approved.

4.3.3 CareWorker and AgencyWorker access must be limited to active resident assignments. Nurse and Manager access must follow the approved application design and business responsibilities.

4.3.4 The care portal must deny requests that do not satisfy the required role or assignment check, including direct requests that bypass visible navigation links.

### 4.4 Agency and third-party access

4.4.1 Every agency worker must have a named sponsor, an approved role, a start date and a mandatory end date.

4.4.2 Agency access must be limited to the assigned duties, facility and residents.

4.4.3 The sponsor must review an extension before the current end date. If an approved extension is not recorded, the access must be treated as expired and removed.

### 4.5 Privileged access

4.5.1 Administrative tasks must use a separately authorised administrator identity.

4.5.2 A CareWorker, Nurse, Manager or AgencyWorker role must not provide directory-administration authority.

4.5.3 Microsoft Graph permissions must be limited to the scopes required for the approved lifecycle task.

4.5.4 Shared administrator accounts are prohibited. Privileged actions must be attributable to a named operator and included in the audit evidence.

### 4.6 Access review

4.6.1 Managers must review workforce access at least quarterly in an operational deployment and at each formal assurance milestone in the student laboratory.

4.6.2 The review must confirm whether each access assignment should be retained, modified, removed or accepted temporarily as an approved exception.

4.6.3 The review record must identify the reviewer, review date, decision, reason, affected identity and required remediation.

4.6.4 A denied or overdue decision must be assigned to an owner and tracked until remediation is verified.

### 4.7 Access removal

4.7.1 Access must be removed when employment ends, an agency contract expires, a role is no longer required, a manager denies continued access, or an unacceptable security risk is identified.

4.7.2 Removal must address the Entra account status, governed groups, application roles, facility and resident assignments, active sessions and the application's blocked-user control where relevant.

4.7.3 The operator must verify the final state and test that unauthorised access is denied.

### 4.8 Exceptions

4.8.1 An exception must be documented before access is granted or retained outside the normal rules.

4.8.2 The exception record must contain the business reason, affected identity and access, risk, compensating controls, approver, responsible owner and expiry date.

4.8.3 Permanent or undocumented exceptions are prohibited. An expired exception must be removed or formally reassessed.

### 4.9 Logging and evidence

4.9.1 Access creation, modification, review and removal must produce sufficient evidence to reconstruct the decision and result.

4.9.2 Evidence should include the approver, operator, target identity, action, UTC timestamp, result, correlation identifier and final-state verification.

4.9.3 Passwords, MFA codes, access tokens, refresh tokens, client secrets and unnecessary identity or resident information must not be included.

## 5 Responsibilities

### 5.1 Role responsibilities

| Role | Responsibility |
| --- | --- |
| Sunhaven Service Owner | Approves this document, accepts residual business risk and resolves material access disputes. |
| Manager or agency sponsor | Confirms the business need, approves the role and assignments, supplies accurate dates and completes access reviews. |
| IAM operator | Performs only approved changes, uses least-privilege administration and verifies the final state. |
| Application owner | Maintains portal roles, route protections, assignments and blocked-user controls. |
| Security or audit reviewer | Reviews privileged access, exceptions, access-review results and evidence; reports unresolved non-compliance. |
| Worker | Uses only their own account, protects authentication information and reports incorrect or unnecessary access. |

### 5.2 Compliance monitoring and review

5.2.1 Compliance must be assessed through configuration review, positive and negative access tests, access-review exports, audit records and exception reporting.

5.2.2 The planned policy-compliance checker may automate selected read-only checks. Until that feature is implemented and tested, the project must describe those checks as planned and use the existing manual reports and test evidence.

5.2.3 This policy must be reviewed after a material access incident, major role-model change or significant change to Entra ID, Microsoft Graph or the care portal.

### 5.3 Reporting

5.3.1 High-risk access errors, active leaver accounts, unexpected privileged access and unresolved review denials must be reported promptly to the Service Owner and Security Reviewer.

5.3.2 The report must state the affected identity, issue, immediate containment, owner and required follow-up without disclosing credentials or unnecessary personal information.

### 5.4 Records management

5.4.1 Access approvals, dry-run plans, execution results, readbacks, reviews, exceptions and test evidence must be stored in the approved private project location.

5.4.2 Records must use the project's evidence naming and indexing rules and be retained for the period defined by the approved evidence plan.

5.4.3 Disposal must be authorised and must not remove evidence that is still required for assessment, investigation or an open exception.

## 6 Definitions

| Term | Definition |
| --- | --- |
| Access review | A recorded decision about whether existing access should be retained, changed or removed. |
| Application role | A role issued through Entra ID and used by the care portal to make authorisation decisions. |
| Authorisation | The decision about what an authenticated user is permitted to access or perform. |
| Least privilege | Giving a person only the access needed for current approved duties. |
| Privileged access | Access that can administer identities, permissions, applications or security settings. |
| Synthetic data | Fictional information created for testing and not taken from real residents or workers. |

## 7 Related documents and guidance

- Sunhaven Care Workforce IAM Solution Design
- Sunhaven Workforce Identity Lifecycle Policy and Procedure POL-02
- Sunhaven Authentication and Shared Device Security Policy and Procedure POL-03
- Sunhaven workforce input schema, route-role map, test plan and evidence index
- CQUniversity Australia, *Privacy Policy and Procedure*, reference 3124, effective 12 March 2024. Structural reference only: https://delivery-cqucontenthub.stylelabs.cloud/api/public/content/privacy-policy-and-procedure.pdf
- SANS Institute, *Access Management Policy*: https://www.sans.org/information-security-policy/access-management-policy
- SANS Institute, *Privileged Account Management Policy*: https://www.sans.org/information-security-policy/privileged-account-management-policy

## 8 Feedback

8.1 Feedback or proposed amendments must be sent to the document owner through the project's documented change-control process.

8.2 Proposed changes must identify the affected requirement, reason, security effect and any required update to controls, tests or evidence.

## 9 Approval and review details

| Approval and review field | Detail |
| --- | --- |
| Approval authority | Sunhaven Service Owner |
| Required consultation | Workforce or HR Owner, IAM and Security Lead, Application Owner and Security or Audit Reviewer |
| Administrator | IAM and Security Lead |
| Approval status | Draft for capstone review; not yet approved for operational use |
| Next review | 12 months after approval, or earlier following a material incident or system change |

### Approval and amendment history

| Version | Date | Details | Authority |
| --- | --- | --- | --- |
| 1.0 | September 2026 | Initial student-project policy draft | Project team |
| 2.0 Draft | 9 September 2026 | Restructured as a policy and procedure; added monitoring, reporting, records management, definitions, approval details and implementation status | Pending Sunhaven Service Owner approval |

## Appendix A Implementation status

| Requirement or control | Current project position | Status |
| --- | --- | --- |
| Named Entra identities, security groups and application roles | Configured and used in the laboratory | Implemented |
| Server-side Flask role and resident-assignment checks | Present in the care portal | Implemented |
| JML removal of governed groups and application roles | Present in the PowerShell lifecycle scripts | Implemented |
| Access-review export and approved remediation | Export and limited denied-assignment remediation scripts are present | Implemented with defined laboratory scope |
| Manager or sponsor approval and exception records | Performed as a documented project process | Manual process |
| Automated policy-compliance checker and findings | Designed as a remaining capstone extension; not present in the current code package | Planned |

