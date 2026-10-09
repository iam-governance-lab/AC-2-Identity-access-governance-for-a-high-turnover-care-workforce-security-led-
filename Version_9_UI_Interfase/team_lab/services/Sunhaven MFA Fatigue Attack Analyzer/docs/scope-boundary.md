# SMFAA Scope Boundary

SMFAA is a small operational Sunhaven service that detects three MFA-fatigue patterns:

1. Prompt Burst
2. Repeated Denial
3. Denial-to-Success

It creates explainable findings from MFA/sign-in activity and does not change IAM or application state.

## In Scope

- controlled MFA/sign-in event ingestion;
- exported Microsoft Entra sign-in event ingestion;
- live Microsoft Entra sign-in log ingestion through Microsoft Graph;
- Entra event normalization;
- mapping Entra identities to Sunhaven employee identities;
- validation and timestamp ordering;
- per-employee rolling windows;
- three MFA-fatigue detectors;
- configurable detection thresholds;
- safe worker-context enrichment;
- JSON, CSV and console evidence;
- automated tests; and
- read-only Microsoft Graph access for live sign-in analysis.

## Out of Scope

- general security monitoring or SIEM functionality;
- portal access-denied monitoring;
- dormant or orphaned-account detection;
- Joiner-Mover-Leaver monitoring;
- access review;
- role or administrator drift;
- MFA or Conditional Access configuration;
- device or network analysis;
- automatic remediation;
- account disablement;
- session revocation; and
- modification of Microsoft Entra identities or Sunhaven workforce records.

## Runtime Boundary

```text
                    Microsoft Entra ID
                   Authentication + MFA
                      /           \
                     /             \
          OIDC authentication     Sign-in logs
                   /                 \
                  v                   v
      Sunhaven Flask Portal    Microsoft Graph API
                                      |
                                      v
                            entra_graph_adapter.py
                                      |
                                      v
                                    SMFAA
                                      |
                                      v
                               MFA Finding
                                      |
                                      v
                            JSON / CSV / Console
```

The Sunhaven Flask portal and SMFAA have separate operational responsibilities.

Microsoft Entra ID authenticates users and the Flask application handles application access and authorisation. SMFAA independently reads sign-in information through Microsoft Graph and analyses relevant MFA behaviour.

## Read-Only Boundary

SMFAA is a monitoring and detection component.

It may:

- read Microsoft Entra sign-in information;
- normalize relevant MFA events;
- map identities to Sunhaven employee context;
- evaluate configured MFA-fatigue rules; and
- generate findings and evidence.

It must not:

- disable or modify users;
- change MFA methods;
- change Conditional Access policies;
- modify RBAC;
- revoke user sessions;
- execute JML actions; or
- automatically remediate a finding.

Microsoft Graph access is therefore limited to the read-only permissions required for sign-in log analysis.

## Availability Boundary

SMFAA is not an authentication or authorisation dependency for the Sunhaven Care Portal.

If SMFAA is stopped or unavailable, the core Sunhaven portal should continue to authenticate and authorise users normally.

SMFAA detection may temporarily stop while the service is unavailable, but this must not prevent normal portal operation.

## Detection Boundary

SMFAA findings indicate that configured MFA-fatigue patterns were observed. A finding is security evidence for investigation and does not by itself prove that an attacker compromised an account.

The controlled demo dataset supports validation of all three detection rules.

Live Microsoft Graph testing has successfully validated sign-in event retrieval, normalization and the Repeated Denial detection scenario. Live Denial-to-Success validation currently depends on the MFA details available in the Microsoft Graph sign-in response.
