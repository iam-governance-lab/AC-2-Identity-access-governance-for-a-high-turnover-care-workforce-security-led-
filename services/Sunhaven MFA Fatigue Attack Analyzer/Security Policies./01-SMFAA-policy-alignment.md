# SMFAA Policy and Project Alignment

## 1. Purpose

This document explains how **SMFAA** supports the Sunhaven Care project while keeping a clear boundary from the main IAM, Flask and broader monitoring work.

SMFAA is an MFA-fatigue detection service. It is not an IAM enforcement, access-review or compliance system.

---

## 2. Main Project Alignment

SMFAA aligns most directly with **POL-03 – Authentication and Shared Device Security Policy and Procedure** because that policy requires MFA for workforce authentication and requires unexpected MFA activity or suspected credential compromise to be reviewed and reported.

SMFAA supports this by detecting three MFA-specific patterns:

- prompt bursts;
- repeated denials;
- denial-to-success.

SMFAA also supports the Sunhaven test/evidence objectives by producing repeatable and explainable findings.

---

## 3. Position in the Sunhaven Architecture

SMFAA runs alongside the Sunhaven Flask portal.

```text
Microsoft Entra ID + MFA
        |                 \
        | OIDC             \ MFA / sign-in events
        v                   v
Sunhaven Flask Portal      SMFAA
                            |
                            v
                      MFA finding
```

The core portal does not depend on SMFAA to authenticate or authorise a user.

---

## 4. Operational Boundary

The main Sunhaven project remains responsible for:

- Microsoft Entra ID and MFA configuration;
- JML;
- RBAC;
- access review;
- Flask portal enforcement;
- broader monitoring;
- remediation.

SMFAA only receives MFA events and creates MFA-fatigue findings.

It does not:

- configure MFA;
- disable users;
- revoke sessions;
- change roles;
- execute JML;
- perform access review;
- change Flask access decisions;
- build a general monitoring dashboard;
- automatically remediate findings.

---

## 5. Privacy and Evidence

SMFAA uses fictional or sanitised MFA metadata.

It does not store:

- passwords;
- MFA codes;
- access/refresh tokens;
- client secrets;
- resident records;
- real employee information.

SMFAA may read safe fictional Sunhaven workforce context from `data/workforce.csv` in read-only mode.

A finding must be described as a **suspicious MFA-fatigue pattern**, not proof that a real attacker is present.

---

## 6. Security Principles Applied

SMFAA follows these simple project principles:

- **least data:** only the fields needed for detection are processed;
- **read-only integration:** Sunhaven workforce context is never changed;
- **separation of duties:** SMFAA detects but does not remediate;
- **explainability:** each finding states why the rule matched;
- **repeatability:** the same input and configuration should produce the same result;
- **safe evidence:** secrets and sensitive authentication material are excluded.

---

## 7. Alignment Conclusion

SMFAA is aligned with Sunhaven because MFA is a core authentication control and unexpected MFA activity should be reviewable.


