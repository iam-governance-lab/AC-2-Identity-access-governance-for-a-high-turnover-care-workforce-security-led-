# SMFAA Project Plan

## Project Title

**SMFAA — Sunhaven MFA Fatigue Attack Analyzer**

## Ownership

Joint contribution:

- Loojaw Manandhar — 12228795
- Adnan Salem Bawazir — 12212059

## Problem

MFA improves authentication security, but repeated prompts or repeated rejected MFA attempts can still create MFA-fatigue or push-bombing risk.

Sunhaven needs a focused way to identify these patterns without replacing Microsoft Entra ID, JML, RBAC or Flask access control.

## Implemented Solution

SMFAA provides:

- event validation;
- timestamp ordering;
- per-employee grouping;
- configurable rolling windows;
- Prompt Burst detection;
- Repeated Denial detection;
- Denial-to-Success detection;
- Sunhaven worker context enrichment;
- exported Entra CSV normalization;
- live Microsoft Entra sign-in log ingestion through Microsoft Graph;
- Entra-to-Sunhaven identity mapping;
- console, JSON and CSV findings; and
- automated testing.

## Operational Boundary

SMFAA is a read-only monitoring and detection component.

It detects suspicious MFA-fatigue patterns and produces explainable findings for investigation.

SMFAA does not:

- disable users;
- revoke sessions;
- configure MFA;
- modify Conditional Access;
- modify RBAC;
- execute JML actions;
- modify Microsoft Entra identities; or
- automatically remediate findings.

## Current Demonstration Modes

```text
--source demo        Controlled dataset used to demonstrate detection rules
--source repo-entra  Existing sanitised Entra export from Sunhaven evidence
--source csv         User-supplied normalized event CSV
--source live-entra  Live Microsoft Entra sign-in logs through Microsoft Graph
```

## Live Microsoft Entra Integration

The live integration uses Microsoft Graph to retrieve Microsoft Entra sign-in records.

Runtime flow:

```text
Microsoft Entra ID
        |
        v
Microsoft Graph API
        |
        v
entra_graph_adapter.py
        |
        v
Normalized MFA Events
        |
        v
Existing SMFAA Detector
        |
        v
JSON / CSV / Console Findings
```

The Microsoft Entra App Registration uses:

- delegated `AuditLog.Read.All` permission;
- admin consent;
- public client flow;
- device code authentication; and
- no client secret.

The Client ID and Tenant ID are supplied through environment variables rather than being stored in the repository.

## Detection Rules

SMFAA implements three focused detection rules:

1. **Prompt Burst** — 5 MFA prompts within 2 minutes.
2. **Repeated Denial** — 3 MFA denials within 5 minutes.
3. **Denial-to-Success** — 3 MFA denials followed by a successful MFA event within 10 minutes.

The detector design is shared across controlled, exported and live input sources.

## Live Validation

Live integration with the Sunhaven Microsoft Entra environment has been completed.

Microsoft Graph sign-in records were successfully retrieved and relevant MFA events were normalized and mapped to a Sunhaven employee identity.

A controlled Test Nurse scenario successfully produced a `REPEATED_DENIAL` finding after three MFA denials occurred within five minutes.

The finding was exported through the existing SMFAA reporting process.

## Current Validation Limitation

During live testing, successful sign-in records for the test account returned:

```text
authenticationRequirement=None
authenticationDetails=None
```

in the Microsoft Graph response used by the current adapter.

The adapter intentionally does not classify every successful `errorCode 0` sign-in as `MFA_SUCCESS`, because a successful sign-in does not necessarily prove that an MFA approval occurred.

Therefore:

- live Microsoft Graph connectivity is implemented;
- live event retrieval and normalization are working;
- live Repeated Denial detection has been validated;
- Denial-to-Success detection is implemented and can be demonstrated using controlled demo data; and
- live Denial-to-Success validation currently depends on the MFA information available from Microsoft Graph.

## Current Status

The core SMFAA detection service, exported Entra integration and live Microsoft Graph integration are implemented.

The project currently supports controlled demonstration, repository Entra evidence analysis and live read-only Entra sign-in analysis.

The remaining work is focused on final documentation, evidence organization and demonstration preparation rather than implementing the live Graph connector.
