# POL-03 — Authentication and Shared-Device Security Policy

**Organisation:** Sunhaven Care
**Policy owner:** Security Owner
**Technical owners:** IAM Lead and Application Security Lead
**Version:** 1.0
**Classification:** Internal – Student Laboratory Project
**Review frequency:** At every major project milestone and after an authentication or session-control incident

## 1. Purpose

The purpose of this policy is to protect Sunhaven accounts and application sessions, particularly when workers access sensitive information from shared workplace devices.

It establishes requirements for individual authentication, MFA, session protection, sign-out and administrative access.

## 2. Scope

This policy applies to:

- All Sunhaven workforce identities.
- Microsoft Entra ID authentication.
- The Sunhaven Flask care portal.
- Shared or reused laboratory devices and browsers.
- Application sessions and cookies.
- Privileged administrator accounts.
- Authentication configuration and evidence.

## 3. Named identity requirement

Every worker must use an individual account.

Workers must not:

- Share accounts.
- Share passwords.
- Allow another person to use an active session.
- Sign in using another worker’s identity.
- Store credentials in project documents or evidence.

Administrative actions must be attributable to a named administrator.

## 4. Multi-factor authentication

MFA must be required for workforce access.

MFA registration and recovery must be protected from unauthorised modification.

Workers must not approve unexpected authentication requests.

A suspected MFA compromise must be reported and the affected account reviewed or suspended.

## 5. Password and credential protection

Passwords must not be:

- Shared with another person.
- Stored in source code.
- Committed to GitHub.
- Included in screenshots or reports.
- Reused as test evidence.
- Transmitted through unapproved communication channels.

Client secrets, tokens and recovery information must be treated as sensitive authentication information.

The laboratory application may use an environment variable for its client secret, but the secret must not be committed to the repository.

A production implementation should use managed identity, certificates or an approved secret vault.

## 6. Shared-device requirements

When using a shared device, workers must:

- Use their individual identity.
- Prevent the browser from saving credentials.
- Lock the screen when leaving the device.
- Explicitly sign out when work is complete.
- Close the browser session after signing out.
- Report a device that remains signed in as another user.

Shared workforce accounts are prohibited.

For project demonstrations, different test personas should use separate private-browser sessions, and browser state should be cleared between tests.

## 7. Application session requirements

The Sunhaven laboratory portal must:

- Use a limited local session lifetime.
- Use secure session-cookie settings appropriate to the environment.
- Protect cookies using HttpOnly.
- use SameSite protection.
- Avoid unnecessary persistent authentication information.
- Perform authorisation checks on the server.
- Deny protected requests for locally blocked users.
- Return an access-denied response when the user is not authorised.

The current laboratory target is a 15-minute local portal session.

## 8. Leaver and blocked-user sessions

Disabling an Entra account does not guarantee that an existing application session immediately disappears.

Therefore, the care portal must check the user’s blocked status on every protected request.

When a signed-in user becomes a Leaver:

- The Entra account must be disabled.
- Available Entra sessions must be revoked.
- Application access must be removed.
- The user must be added to the local blocked-user control.
- The next protected portal request must be denied.

This layered control reduces the time in which an already-signed-in Leaver could retain access.

## 9. Privileged authentication

Administrative work must use a separately authorised administrator identity.

Privileged accounts must:

- Use MFA.
- Not be shared.
- Be used only for administration.
- Receive only the required permissions.
- Have their activity logged and reviewed.

Normal CareWorker, Nurse, Manager or AgencyWorker roles must not automatically provide administrative authority.

## 10. Monitoring and evidence

Authentication and session evidence should include:

- Test persona.
- Sign-in result.
- MFA result.
- Application role claim.
- Permitted or denied route.
- UTC timestamp.
- Relevant correlation identifier.

Evidence must not include passwords, MFA codes, access tokens, refresh tokens or client secrets.

## 11. Incident response

A suspected account or session compromise must result in:

1. Account review or temporary suspension.
2. Session revocation where available.
3. Application-side blocking when necessary.
4. Credential or secret rotation where appropriate.
5. Review of sign-in and application logs.
6. Documentation of findings and corrective actions.

## 12. Exceptions

Exceptions must be documented, risk-assessed, approved and time-limited.

MFA, individual-account and secret-protection requirements must not be bypassed merely for convenience.

## 13. Compliance

Compliance is verified using:

- MFA sign-in tests.
- Server-side role tests.
- Direct unauthorised-request tests.
- Shared-device session tests.
- Signed-in Leaver denial tests.
- Secret and repository inspections.
- Audit-evidence reviews.

## 14. References

- SANS Institute, _Password Construction Standard_: https://www.sans.org/information-security-policy/password-construction-standard
- SANS Institute, _Privileged Account Management Policy_: https://www.sans.org/information-security-policy/privileged-account-management-policy
