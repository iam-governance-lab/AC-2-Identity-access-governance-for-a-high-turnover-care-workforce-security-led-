# POL-03 Authentication and Shared Device Security Policy and Procedure

| Document field | Detail |
| --- | --- |
| Organisation | Sunhaven Care |
| Reference number | POL-03 |
| Document owner | Security Owner |
| Administrators | IAM Lead and Application Security Lead |
| Approval authority | Sunhaven Service Owner |
| Version | 2.0 Draft |
| Classification | Internal - Student Laboratory Project |

A printed copy is uncontrolled. Refer to the version-controlled private project repository for the current version.

## 1 Purpose

1.1 This policy and procedure protects Sunhaven workforce accounts, credentials and application sessions, particularly when workers use shared or reused workplace devices.

1.2 It establishes requirements for individual authentication, multi-factor authentication, credential protection, secure sessions, sign-out, blocked-user checks and privileged authentication.

## 2 Scope

2.1 This policy and procedure applies to all Sunhaven workforce and administrator identities, Microsoft Entra ID authentication, the Flask care portal, shared or reused browsers and devices, application cookies and sessions, authentication configuration, and related evidence.

2.2 The current implementation is a student proof of concept. It uses fictional identities, synthetic resident data and local laboratory devices and is not approved for production healthcare use.

## 3 Policy statement

3.1 Every worker and administrator must use an individual identity. Account, password and active-session sharing are prohibited.

3.2 Workforce access must use multi-factor authentication where supported by the laboratory tenant and required by the approved configuration.

3.3 Passwords, MFA codes, tokens, client secrets and recovery information must be protected from unauthorised access and must not be committed to the source repository or included in evidence.

3.4 Shared-device use must include screen locking, explicit sign-out, browser-state control and a short application session.

3.5 The care portal must authenticate through Microsoft Entra ID and must independently check roles, assignments, session age and blocked-user status on the server.

3.6 Privileged accounts must be separate, named, protected by MFA and used only for authorised administration.

3.7 Suspected credential or session compromise must result in prompt containment, review and documented corrective action.

## 4 Procedure

### 4.1 Named accounts

4.1.1 Each worker must sign in with their assigned individual identity.

4.1.2 Workers and administrators must not share accounts, passwords, MFA methods or active sessions, allow another person to work under their identity, or sign in using another worker's identity.

4.1.3 Administrative actions must be attributable to a separately authorised named administrator.

### 4.2 Multi-factor authentication

4.2.1 The IAM operator must enable or require MFA using the controls available in the approved Entra laboratory configuration.

4.2.2 A new worker must complete the required MFA registration before normal access testing is accepted as complete.

4.2.3 Workers must not approve an unexpected authentication request. A suspected MFA compromise must be reported and the account reviewed or temporarily suspended.

4.2.4 Production Conditional Access controls are outside the current laboratory scope and must not be reported as implemented unless they are separately licensed, configured and tested.

### 4.3 Password, token and secret protection

4.3.1 Passwords must not be shared, stored in source code, committed to GitHub, shown in screenshots or reports, reused as evidence, or sent through an unapproved channel.

4.3.2 Access tokens, refresh tokens, MFA codes, client secrets and recovery information must be treated as sensitive authentication information.

4.3.3 The laboratory application's client secret must be supplied through an environment variable and excluded from the repository.

4.3.4 A suspected secret exposure must result in removal from evidence or source history where possible, rotation of the affected credential, review of relevant logs and documentation of the response.

4.3.5 A production implementation should use an approved managed identity, certificate or secrets vault instead of relying on a locally managed client secret.

### 4.4 Shared-device use

4.4.1 A worker using a shared device must:

- use their own identity
- prevent the browser from saving credentials
- lock the screen when leaving the device
- explicitly sign out when work is complete
- close the browser session after signing out, and
- report a device that remains signed in as another user.

4.4.2 Shared workforce accounts are prohibited.

4.4.3 During a project demonstration, each test persona must use a separate private-browser session. Browser state must be cleared between tests where continued state could affect the result.

4.4.4 Managed-device, kiosk and mobile-device-management controls are production recommendations and are not part of the current laboratory implementation.

### 4.5 Application session protection

4.5.1 The care portal must use a limited local session lifetime. The current laboratory target is 15 minutes.

4.5.2 Session cookies must use HttpOnly and SameSite protection. A production deployment must also use HTTPS and the Secure cookie flag.

4.5.3 The application must avoid unnecessary persistent authentication information, perform authorisation checks on the server and return an access-denied response when the user is not authorised.

4.5.4 The portal must validate the local session timestamp and must not silently extend the fixed session beyond the approved lifetime.

### 4.6 Leaver and blocked-user sessions

4.6.1 Disabling an Entra account may not immediately end a session already held by the care portal. The portal must therefore check the local blocked-user status on every protected request.

4.6.2 When a signed-in user becomes a Leaver, the authorised process must disable the Entra account, revoke available Entra sessions, remove application access, add the user to the local blocked-user control and deny the next protected portal request.

4.6.3 The operator must verify the block and retain evidence of the allowed-before and denied-after results.

### 4.7 Privileged authentication

4.7.1 Administrative work must use a separately authorised administrator identity protected by MFA.

4.7.2 Privileged accounts must not be shared, must be used only for administration, must receive only the required permissions and must have their activity logged and reviewed.

4.7.3 Normal CareWorker, Nurse, Manager or AgencyWorker access must not automatically grant Entra ID, Microsoft Graph or IAM administration authority.

### 4.8 Authentication or session incident

4.8.1 A suspected account, credential or session compromise must result in:

1. account review or temporary suspension
2. session revocation where available
3. application-side blocking when necessary
4. credential or secret rotation where appropriate
5. review of sign-in, automation and application logs, and
6. documentation of findings, decisions and corrective actions.

4.8.2 The response must be assigned to an owner and remain open until containment and required verification are complete.

### 4.9 Exceptions

4.9.1 An exception must be documented, risk-assessed, approved and time-limited.

4.9.2 MFA, individual-account and secret-protection requirements must not be bypassed for convenience.

4.9.3 An expired exception must be removed or formally reassessed by the Security Owner.

### 4.10 Monitoring and evidence

4.10.1 Authentication and session evidence should include the test identity, sign-in result, MFA result, application-role claim, permitted or denied route, UTC timestamp and relevant correlation identifier.

4.10.2 Evidence must not include passwords, MFA codes, access tokens, refresh tokens or client secrets.

4.10.3 Sign-in failures, unexpected role claims, blocked-user attempts, session expiry and privileged actions must be reviewed during the relevant test or assurance activity.

## 5 Responsibilities

### 5.1 Role responsibilities

| Role | Responsibility |
| --- | --- |
| Security Owner | Owns this document, reviews exceptions and incidents and confirms corrective actions. |
| IAM Lead | Maintains Entra authentication, MFA configuration, administrator access and session-revocation capability within the laboratory scope. |
| Application Security Lead | Maintains portal session controls, server-side checks, secure configuration and blocked-user enforcement. |
| Manager or agency sponsor | Confirms that workers use approved identities and reports role, contract or access concerns. |
| IAM operator | Performs authorised account containment, revocation and verification tasks. |
| Worker | Protects credentials, uses only their own identity, locks and signs out of shared devices and reports suspicious authentication activity. |
| Security or audit reviewer | Reviews sign-in, application and automation evidence and reports unresolved non-compliance. |

### 5.2 Compliance monitoring and review

5.2.1 Compliance must be assessed using MFA sign-in tests, server-side role tests, direct unauthorised-request tests, shared-device session tests, signed-in Leaver denial tests, repository safety scans and audit-evidence reviews.

5.2.2 The Security Owner must review material failures, credential exposures and exceptions. Corrective actions must be retested before closure.

5.2.3 This document must be reviewed after a material authentication or session incident or a major change to Entra authentication, the application registration, session handling or privileged administration.

### 5.3 Reporting

5.3.1 Suspected credential exposure, unexpected MFA activity, unauthorised privileged use and failure of the blocked-user control must be reported promptly to the Security Owner.

5.3.2 Reports must state the affected identity or system, time, observed event, containment, owner and follow-up action without repeating the exposed secret.

### 5.4 Records management

5.4.1 Authentication tests, configuration evidence, incident records, exception approvals and corrective-action results must be stored in the approved private project location.

5.4.2 Evidence must follow the project naming, indexing, access and retention rules.

5.4.3 Secrets and unnecessary identity or resident information must be removed before evidence is retained or submitted.

## 6 Definitions

| Term | Definition |
| --- | --- |
| Authentication | Verifying the identity of a person or account attempting to sign in. |
| Blocked user | An identity marked by the application so that protected requests are denied. |
| Client secret | A confidential value used by an application to prove its identity to an identity provider. |
| MFA | Multi-factor authentication, which requires more than one type of proof during authentication. |
| OIDC | OpenID Connect, the protocol used by the care portal to receive authenticated identity information from Entra ID. |
| Session | The application's temporary record that a user has authenticated. |
| Shared device | A workstation, browser or endpoint used by more than one person. |

## 7 Related documents and guidance

- Sunhaven Care Workforce IAM Solution Design
- Sunhaven Access Management Policy and Procedure POL-01
- Sunhaven Workforce Identity Lifecycle Policy and Procedure POL-02
- Sunhaven application security configuration, test plan and evidence index
- CQUniversity Australia, *Privacy Policy and Procedure*, reference 3124, effective 12 March 2024. Structural reference only: https://delivery-cqucontenthub.stylelabs.cloud/api/public/content/privacy-policy-and-procedure.pdf
- SANS Institute, *Password Construction Standard*: https://www.sans.org/information-security-policy/password-construction-standard
- SANS Institute, *Privileged Account Management Policy*: https://www.sans.org/information-security-policy/privileged-account-management-policy

## 8 Feedback

8.1 Feedback or proposed amendments must be sent to the document owner through the project's documented change-control process.

8.2 A proposed change must identify any effect on Entra authentication, MFA, application registration, session controls, device requirements, tests and evidence.

## 9 Approval and review details

| Approval and review field | Detail |
| --- | --- |
| Approval authority | Sunhaven Service Owner |
| Required consultation | Security Owner, IAM Lead, Application Security Lead and Security or Audit Reviewer |
| Administrator | IAM Lead and Application Security Lead |
| Approval status | Draft for capstone review; not yet approved for operational use |
| Next review | 12 months after approval, or earlier following an authentication, credential or session-control incident |

### Approval and amendment history

| Version | Date | Details | Authority |
| --- | --- | --- | --- |
| 1.0 | September 2026 | Initial student-project policy draft | Project team |
| 2.0 Draft | 9 September 2026 | Restructured as a policy and procedure; added operating steps, monitoring, reporting, records, definitions and implementation status | Pending Sunhaven Service Owner approval |

## Appendix A Implementation status

| Requirement or control | Current project position | Status |
| --- | --- | --- |
| Entra ID sign-in and MFA foundation | Configured and demonstrated in the laboratory | Implemented |
| Server-side Flask role checks | Present on protected application routes | Implemented |
| Fixed 15-minute local session and blocked-user check | Present in the care portal | Implemented |
| HttpOnly and SameSite cookie settings | Present in the current Flask configuration | Implemented |
| Environment-only client secret and repository safety checking | Present in the laboratory configuration and validation workflow | Implemented |
| Shared-device sign-out and browser clearing | Performed as an operating and demonstration procedure | Manual process |
| HTTPS, Secure cookie, managed devices, kiosk controls and enterprise secret storage | Required before production deployment | Future production control |

