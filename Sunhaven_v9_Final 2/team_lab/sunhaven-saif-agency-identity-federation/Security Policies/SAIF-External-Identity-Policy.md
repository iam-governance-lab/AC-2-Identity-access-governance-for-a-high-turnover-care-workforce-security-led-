# SAIF External Identity Security Policy

## Purpose

This policy defines the security rules used by the Sunhaven Agency Identity Federation (SAIF) component.

SAIF is designed to provide a controlled way for external care-agency workers to be introduced into the existing Sunhaven Microsoft Entra identity environment.

The purpose of this policy is to make sure that an external worker is checked before SAIF allows the worker to continue to the external identity onboarding process.

SAIF does not replace the existing Sunhaven IAM system. After an external identity has been established, the existing Sunhaven identity, authentication and application access controls remain responsible for protecting Sunhaven resources.


## POL-SAIF-01 - Approved Agency

An external worker must belong to an agency that is recognised and approved by Sunhaven.

SAIF checks the worker's agency ID against the approved agency configuration.

If the agency does not exist or its status is not APPROVED, the worker must be rejected.

This prevents an unknown or blocked agency from continuing to the external identity onboarding process.


## POL-SAIF-02 - Required Worker Information

An external worker request must contain the information required by SAIF before it can be processed.

The current required information is:

- worker ID;
- display name;
- email address;
- agency ID.

If required information is missing, SAIF must reject the request.


## POL-SAIF-03 - Agency and Email Domain Check

The agency ID supplied by the worker request must match an agency in the SAIF approved agency configuration.

The worker's email domain must also match the domain configured for that agency.

A matching domain is only a preliminary consistency check. It does not prove that the worker owns the identity.

The external user's real authentication is handled through the Microsoft Entra external identity process.


## POL-SAIF-04 - Fail Closed

SAIF must reject a request when validation fails.

A rejected request must not continue to Microsoft Graph or the Microsoft Entra B2B invitation process.

Examples include:

- missing worker information;
- invalid email format;
- unknown agency;
- blocked agency;
- agency and email domain mismatch.

This provides a clear security boundary between local SAIF validation and external identity onboarding.


## POL-SAIF-05 - Controlled External Invitation

Only a worker who successfully passes SAIF validation can continue to the Microsoft Entra B2B onboarding stage.

SAIF will use the approved worker information when preparing an external identity invitation.

The invitation process must use the existing Sunhaven Microsoft Entra environment rather than creating a separate identity system.

Microsoft Entra B2B collaboration is designed to allow external business partners and guests to use their own identities when accessing resources shared by another organisation.


## POL-SAIF-06 - External Identity

SAIF must not create or store a separate password for an external agency worker.

The external worker uses an external identity supported by Microsoft Entra B2B collaboration.

After the invitation is accepted, the external user can be represented as an external or guest user in the Sunhaven Microsoft Entra environment.

SAIF will keep enough mapping information to connect the original agency-worker request with the resulting external Entra identity.


## POL-SAIF-07 - Existing Sunhaven IAM Handover

SAIF is responsible for external identity onboarding only.

SAIF does not replace the existing Sunhaven controls for:

- authentication;
- multi-factor authentication;
- role-based access;
- application authorization;
- Joiner-Mover-Leaver processes;
- session controls;
- resident access;
- access review.

After the external identity is established, these controls remain the responsibility of the existing Sunhaven IAM environment.

This keeps SAIF separate from the existing core implementation and avoids duplicating security functions already provided by the group project.


## POL-SAIF-08 - Secrets and Sensitive Information

SAIF must not store Microsoft access tokens, client secrets, passwords or other authentication secrets in the Git repository.

Any authentication information required for Microsoft Graph integration must be handled outside committed source files.

Only fictional agency and worker information is used for this student project.


## POL-SAIF-09 - Audit and Evidence

SAIF should record enough information to demonstrate whether an external identity onboarding request was accepted, rejected or failed.

Evidence should contain only the information required to demonstrate the operation.

Passwords, access tokens, client secrets and other authentication secrets must not be included in evidence.

The evidence will be used to support testing, project demonstration and assessment.


## Microsoft References

The following Microsoft documentation supports the external identity approach used by SAIF.

### Microsoft Entra B2B Collaboration

Microsoft explains that B2B collaboration allows an organisation to work with external business partners and guests while the external user can use their own identity.

https://learn.microsoft.com/en-us/entra/external-id/what-is-b2b

### Microsoft Entra External Collaboration Settings

Microsoft provides external collaboration settings for controlling who can invite external users, restricting guest access and allowing or blocking specific domains.

https://learn.microsoft.com/en-us/entra/external-id/external-collaboration-settings-configure

### Microsoft Entra B2B Guest Users

Microsoft explains how an external B2B user is represented in the organisation's directory and how guest users can be managed.

https://learn.microsoft.com/en-us/entra/external-id/user-properties

### Microsoft Entra Cross-Tenant Access

Microsoft provides cross-tenant access settings for controlling B2B collaboration between Microsoft Entra organisations.

https://learn.microsoft.com/en-us/entra/external-id/cross-tenant-access-settings-b2b-collaboration


## Current Implementation Status

The SAIF component currently implements the following security and external identity functions:

- required worker information validation;
- approved agency lookup;
- blocked and unknown agency rejection;
- email format validation;
- agency email-domain consistency checking;
- fail-closed processing when validation fails;
- Microsoft Entra B2B invitation preparation;
- Microsoft Graph B2B invitation transport;
- Microsoft Graph connection checking and error handling;
- external Entra guest identity creation;
- external identity mapping using the Entra user object ID;
- IAM handover information for the existing Sunhaven IAM environment;
- automated tests for validation, invitation preparation, Graph transport, identity mapping, IAM handover and the complete SAIF workflow.

A live Microsoft Entra B2B test was also completed in the project tenant. The test demonstrated that an external invitation could be created, delivered to the external user, redeemed, and represented in Microsoft Entra as an accepted Guest identity.

SAIF currently hands the external identity to the existing Sunhaven IAM boundary using the Entra user object ID and a requested AgencyWorker role. SAIF does not itself assign the application role or replace the existing Sunhaven authentication, RBAC, resident-access, session or JML controls.

The current automated SAIF test suite contains 13 passing tests.

This implementation is a student project and demonstration environment. Production deployment would require additional operational controls, including dedicated least-privilege administration, production external collaboration configuration, monitoring and formal agency trust processes.