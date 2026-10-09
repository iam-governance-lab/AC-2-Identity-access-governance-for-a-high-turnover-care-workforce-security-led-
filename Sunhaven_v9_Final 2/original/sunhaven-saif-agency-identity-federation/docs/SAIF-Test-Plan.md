# SAIF Test Plan

## 1. Purpose

The purpose of this test plan is to verify that the Sunhaven Agency Identity Federation (SAIF) component correctly validates external agency workers, prevents invalid onboarding requests, prepares Microsoft Entra B2B invitations, processes Graph results, maps external identities and prepares valid identities for handover to the existing Sunhaven IAM system.

---

## 2. Test Scope

Testing covers the main SAIF responsibilities:

- agency and worker validation;
- fail-closed processing;
- B2B invitation preparation;
- Microsoft Graph transport handling;
- external identity mapping;
- existing IAM handover; and
- complete SAIF workflow behaviour.

Authentication, MFA, RBAC, JML and Sunhaven Care Portal authorization are outside the SAIF test boundary because these remain responsibilities of the existing Sunhaven IAM implementation.

---

## 3. Automated Test Cases

| Test | Test Purpose | Expected Result |
|---|---|---|
| TC-01 | Valid worker from approved agency | Worker is approved |
| TC-02 | Worker from blocked agency | Request is rejected |
| TC-03 | Worker email does not match agency domain | Request is rejected |
| TC-04 | Worker uses unknown agency | Request is rejected |
| TC-05 | Worker request is missing agency ID | Request is rejected |
| TC-06 | Worker has invalid email | Request is rejected |
| TC-07 | Prepare B2B invitation | Correct invitation information is prepared |
| TC-08 | Successful Graph transport response | Invitation and Entra user IDs are returned |
| TC-09 | Failed Graph transport response | Processing raises an error and stops |
| TC-10 | External identity mapping | Worker is correctly mapped to Entra user object ID |
| TC-11 | IAM handover preparation | Correct worker and identity information is prepared for existing IAM |
| TC-12 | Approved complete SAIF workflow | Worker reaches identity mapping and IAM handover |
| TC-13 | Blocked complete SAIF workflow | Request stops before Graph invitation processing |

---

## 4. Automated Test Method

The automated tests are implemented using `pytest`.

From the SAIF directory, the test suite can be executed with:

```powershell
python -m pytest tests -v
```
---

## 5. Test Results

The SAIF automated test suite was executed using `pytest`.

**Result: 13 tests passed.**

The tests verify worker and agency validation, B2B invitation preparation, Graph transport handling, identity mapping, IAM handover and complete workflow behaviour.

Microsoft Graph responses are mocked during automated testing, so these tests do not create real guest identities.

---

## 6. Live B2B Verification

A separate live laboratory test was performed using Microsoft Graph and Microsoft Entra ID.

The live test confirmed that:

- a B2B invitation was successfully created;
- the invitation email was received;
- an external `Guest` identity was created in Microsoft Entra ID; and
- the invitation was redeemed and the guest state was verified as `Accepted`.

Supporting screenshots are stored in the SAIF `evidence/` directory.