# SAIF Design Solution

## 1. Design Problem

The Sunhaven Care scenario includes a high-turnover workforce with permanent, casual and external agency workers.

The existing Sunhaven IAM solution provides identity lifecycle, authentication and access controls. External agency workers introduce an additional identity problem because their identity originates outside Sunhaven.

SAIF addresses this problem by providing a controlled external identity onboarding path into the existing Sunhaven Microsoft Entra environment.

---

## 2. Proposed Solution

SAIF uses Microsoft Entra B2B collaboration and Microsoft Graph to onboard approved external agency workers.

The solution follows this path:

**External Agency Worker → SAIF Validation → Microsoft Graph → Microsoft Entra B2B Guest Identity → Identity Mapping → Existing Sunhaven IAM Handover**

Before B2B onboarding, SAIF checks:

- required worker information;
- approved agency status;
- email format; and
- agency/email-domain consistency.

If validation fails, processing stops. If validation succeeds, SAIF prepares and sends the B2B invitation through Microsoft Graph.

The resulting Entra user object ID is mapped to the original agency worker and prepared for handover to the existing Sunhaven IAM system.

---

## 3. Integrated Design

SAIF extends the existing Sunhaven architecture rather than creating a separate identity platform.

Internal Sunhaven workers continue through the existing IAM and JML processes. External agency workers use the SAIF validation and Microsoft Entra B2B onboarding path.

Both paths connect to the existing Microsoft Entra environment.

After SAIF completes the identity handover, the existing Sunhaven system remains responsible for authentication, MFA, role assignment, RBAC, resident access, JML and application authorization.

---

## 4. Technical Workflow

The SAIF workflow is:

1. Receive the external agency-worker request.
2. Validate the worker and approved agency.
3. Stop processing if validation fails.
4. Prepare the Microsoft Entra B2B invitation.
5. Send the invitation through Microsoft Graph.
6. Process the Graph result.
7. Map the Entra user object ID to the agency worker.
8. Prepare the identity for existing IAM handover.

This provides a fail-closed boundary before external identity onboarding.

---

## 5. Integration with Existing Sunhaven IAM

The main integration point between SAIF and the existing system is the **Microsoft Entra user object ID**.

SAIF prepares the following handover information:

- worker ID;
- agency ID;
- external email;
- Entra user object ID; and
- requested `AgencyWorker` role.

`AgencyWorker` is a requested role only. SAIF does not assign the application role or grant access to the Sunhaven Care Portal.

Authentication and authorization remain the responsibility of the existing Sunhaven IAM implementation.

---

## 6. Security Design

SAIF applies the following security controls:

- only approved agencies can continue;
- invalid requests fail closed;
- rejected workers do not reach Microsoft Graph onboarding;
- external workers use Microsoft Entra B2B rather than SAIF-managed passwords;
- Graph failures stop the workflow;
- authentication secrets are not stored in the repository; and
- existing Sunhaven access controls are not bypassed.

Detailed controls are documented in:

`../Security Policies/SAIF-External-Identity-Policy.md`

---

## 7. Component Boundary

### SAIF Responsibilities

- external agency-worker validation;
- approved agency checking;
- B2B invitation processing;
- external identity mapping; and
- IAM handover preparation.

### Existing Sunhaven IAM Responsibilities

- authentication and MFA;
- application-role assignment and RBAC;
- resident access;
- JML processes;
- session controls; and
- Sunhaven Care Portal authorization.

This separation prevents SAIF from duplicating existing group functionality.

---

## 8. Current Implementation

The current SAIF implementation includes:

- worker and agency validation;
- fail-closed workflow processing;
- Microsoft Entra B2B invitation preparation;
- Microsoft Graph integration;
- external identity mapping;
- IAM handover; and
- automated testing.

A live laboratory B2B invitation was successfully created and redeemed. The resulting Entra identity was verified as a `Guest` with `ExternalUserState: Accepted`.

The current automated test suite has **13 passing tests**.

---

## 9. Limitations

SAIF is a student laboratory implementation rather than a production identity federation platform.

Current limitations include:

- invitation redemption requires user interaction;
- SAIF does not automatically assign the requested `AgencyWorker` role;
- automated Graph transport tests use mocked results; and
- email-domain matching is a consistency check, not proof of identity ownership.