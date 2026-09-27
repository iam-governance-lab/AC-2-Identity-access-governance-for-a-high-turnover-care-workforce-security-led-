# SMFAA Scope Boundary

SMFAA is a small operational Sunhaven service that detects only three MFA-fatigue patterns:

1. Prompt Burst
2. Repeated Denial
3. Denial-to-Success

It creates explainable findings and does not change IAM or application state.

## In scope

- MFA/sign-in event ingestion;
- Entra-export normalization;
- validation and timestamp ordering;
- per-employee rolling windows;
- three MFA-fatigue detectors;
- configurable thresholds;
- safe worker-context enrichment;
- JSON/CSV/console evidence;
- automated tests;
- future read-only live Entra input.

## Out of scope

- general security monitoring/dashboard;
- portal access-denied monitoring;
- dormant/orphaned-account detection;
- JML monitoring;
- access review;
- role/admin drift;
- MFA/Conditional Access configuration;
- device/network analysis;
- automatic remediation;
- account disablement or session revocation.

## Runtime boundary

```text
Entra authentication + MFA
        |                 \
        | OIDC             \ sign-in events
        v                   v
Sunhaven Flask Portal      SMFAA
                            |
                            v
                       MFA finding
```

If SMFAA is stopped, the core Sunhaven portal should continue to authenticate and authorise normally.
