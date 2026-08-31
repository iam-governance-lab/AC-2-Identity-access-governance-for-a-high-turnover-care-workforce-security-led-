# Sunhaven Care IAM System Requirements

## 1. Problem

Sunhaven Care has a high-turnover workforce that includes permanent staff, casual workers and agency workers. Staff regularly join, change roles and leave the organization.

This creates security risks such as:
- old accounts remaining active;
- users keeping access they no longer need;
- excessive access to sensitive information;
- difficulty reviewing who currently has access;
- pressure to give new workers access quickly.

## 2. Proposed Solution

The proposed solution is a Microsoft Entra ID based Identity and Access Management system for Sunhaven Care.

The system will:
- manage user identities;
- use role-based access control;
- require MFA;
- automate Joiner, Mover and Leaver processes;
- support access reviews;
- provide audit information and evidence.

## 3. Functional Requirements

FR-01 - The system must manage worker identities using Microsoft Entra ID.

FR-02 - The system must provision access for a new worker.

FR-03 - The system must update access when a worker changes role.

FR-04 - The system must remove or disable access when a worker leaves.

FR-05 - The system must assign access according to the worker's role.

FR-06 - The system must support Multi-Factor Authentication (MFA).

FR-07 - The system must provide worker access-state information.

FR-08 - The system must support access reviews.

FR-09 - The system must provide audit information or reports.

FR-10 - The system must demonstrate that a leaver loses access.

## 4. Security Requirements

SR-01 - Users must receive only the access required for their role.

SR-02 - Authentication must be protected using MFA.

SR-03 - Leaver accounts must not remain active.

SR-04 - Role changes must not leave unnecessary old access.

SR-05 - Audit and access-review automation must use read-only Microsoft Graph permissions where write access is not required.

SR-06 - Important identity and access activities must be auditable.

SR-07 - Sensitive credentials, secrets and tokens must not be stored in the GitHub repository.

## 5. Success Criteria

SC-01 - A new fictional worker can be provisioned successfully.

SC-02 - A worker receives access based on their assigned role.

SC-03 - MFA is successfully enforced for the agreed test scenario.

SC-04 - When a worker changes roles, old access is removed and the correct new access is assigned.

SC-05 - When a worker leaves, their access is removed and they can no longer access the protected system.

SC-06 - Worker identity and access-state information can be successfully exported.

SC-07 - Access-review information can be successfully generated.

SC-08 - Audit and security evidence can be presented during the final demonstration.
