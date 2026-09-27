# SMFAA Project Plan

## Project title

**SMFAA — Sunhaven MFA Fatigue Attack Analyzer**

## Ownership

Joint contribution:

- Loojaw Manandhar — 12228795
- Adnan Salem Bawazir — 12212059

## Problem

MFA improves authentication security, but repeated prompts or repeated rejected MFA attempts can still create MFA-fatigue/push-bombing risk. Sunhaven needs a focused way to identify these patterns without replacing Entra, JML, RBAC or Flask access control.

## Implemented solution

SMFAA now provides:

- event validation;
- timestamp ordering;
- per-employee grouping;
- configurable rolling windows;
- Prompt Burst detection;
- Repeated Denial detection;
- Denial-to-Success detection;
- Sunhaven worker context enrichment;
- existing Entra-export CSV normalization;
- console, JSON and CSV findings;
- automated testing.

## Operational boundary

SMFAA detects and reports only. It does not remediate.

## Current demonstration modes

```text
--source demo       controlled dataset that triggers all rules
--source repo-entra existing sanitised Entra export from Sunhaven evidence
--source csv        user-supplied normalized event CSV
```

## Current status

Implementation complete for the local/exported-event version.

Current automated verification: **35 tests passing**.

Remaining integration work: connect a read-only live Entra sign-in source and test with the student/lab tenant. This should reuse the existing normalization and detector code rather than changing the detector design.
