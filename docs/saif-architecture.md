# Sunhaven Agency Identity Federation (SAIF)

## Purpose

SAIF is a proposed technical component for the Sunhaven Care IAM project.

The main purpose of SAIF is to securely bring workers from an external care agency into the Sunhaven identity environment.

Sunhaven already manages its own workforce identities. However, an agency worker may work for another organisation and already have an external identity.

SAIF will check the external agency and worker information before the worker is onboarded into Sunhaven using Microsoft Entra B2B.

## Problem

The Sunhaven Care scenario includes casual and agency workers.

The existing Sunhaven IAM system already handles Joiner, Mover and Leaver processes for workforce identities.

SAIF focuses on a different problem:

**How can a worker who comes from an external care agency be securely introduced into the Sunhaven identity environment?**

SAIF provides a separate path for external agency identities without replacing the existing Sunhaven IAM functions.

## Proposed Solution

The planned SAIF process is:

```text
External Care Agency
        |
        v
External Agency Worker
        |
        v
SAIF Validation
        |
        v
Approved / Rejected
        |
        v
Microsoft Entra B2B
        |
        v
External / Guest Identity
        |
        v
Sunhaven Environment
```

SAIF first checks whether the external agency is approved.

It then checks whether the worker information matches the approved agency.

If the request is valid, the worker can continue to the Microsoft Entra B2B onboarding stage.

If the request is not valid, SAIF rejects it.

## SAIF Responsibilities

SAIF is planned to:

- keep a list of approved external care agencies
- receive external agency worker information
- check whether the agency is approved
- check whether the worker identity matches the agency
- reject unknown or unapproved agency requests
- prepare approved workers for Entra B2B onboarding
- integrate the approved external identity with Entra B2B
- record the result of the onboarding process

## Scope Boundary

SAIF will not manage:

- Joiner, Mover and Leaver processes
- worker start dates
- worker expiry or contract extensions
- RBAC permissions
- MFA
- session timeout
- resident access
- Flask route authorization

These functions are already part of the existing Sunhaven IAM system.

SAIF's responsibility ends after the approved external identity is established in the Sunhaven identity environment.

## Technical Structure

The planned SAIF structure is:

### Stage 1 - Approved Agency Configuration

Create a simple configuration containing the external care agencies that Sunhaven accepts.

### Stage 2 - External Worker Input

Define the information needed from an external agency worker.

### Stage 3 - Validation

Check the agency and worker information.

The request will either be approved for the next stage or rejected.

### Stage 4 - Entra B2B Onboarding

Connect an approved external worker with Microsoft Entra B2B collaboration.

### Stage 5 - Identity Mapping

Record which external worker is connected to the resulting Entra external identity.

### Stage 6 - Error Handling

Safely reject invalid, unknown or unapproved requests.

### Stage 7 - Testing and Evidence

Use fictional agency workers to test valid and invalid SAIF scenarios and collect evidence of the implementation.

## Integration with Sunhaven

SAIF will connect to the existing project like this:

```text
External Agency Worker
        |
        v
SAIF
        |
        v
Entra External Identity
        |
        v
Existing Sunhaven Authentication
        |
        v
Existing RBAC and Application Controls
```

SAIF does not replace the existing authentication, JML or authorization system.

It adds an external agency identity onboarding path before the existing Sunhaven controls.

## Current Status

SAIF is currently in the design and technical foundation stage.

The problem, purpose, scope, architecture and planned technical stages have been defined.

The next step is to create the approved agency configuration and start the SAIF validation component.