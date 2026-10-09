> Historical v7/v8 document. For current behavior, use Sunhaven_v9_Final_Report.md and Sunhaven_v9_Operator_Handbook.md in this directory.

# Release test and validation record

Executed in the current Python 3.12 environment on 24 September 2026.

| Check | Result | Evidence |
|---|---|---|
| Portal regression and new governance suite | 66 passed | evidence/portal-tests.txt |
| Original SITAS pytest suite | 66 passed | evidence/sitas-tests.txt |
| Original SAIF pytest suite | 13 passed | evidence/saif-tests.txt |
| Actual local HTTP login, twelve routes and a staged roster approval flow | Passed | evidence/http-smoke-v8.json |
| Original archive SHA-256 comparison | All 545 files match | ORIGINAL_MANIFEST.json; python run.py verify-original |
| Visual browser preview | Not verified: service blocked localhost | No visual acceptance claim |
| Live Microsoft tenant / PowerShell actions | Not executed in this release | Original historical evidence retained separately |
| Container / public deployment | Not executed | Configuration supplied for further validation |

New tests cover unauthorized direct POSTs, CSRF, self-approval, duplicates/replay, grant expiry, revocation, stale worker/request state, conflicting packages, expired agency workers, owner disablement, scope denial, identity expiry, kill switch, incident transition order, expired response privilege, policy input validation, XSS escaping, original SITAS current-worker integration and SAIF preview without invitation dispatch.

Tests use temporary synthetic databases; shipped portal data is created afresh on first run. Original SITAS and SAIF test counts are now reproduced locally, not merely copied from their historical evidence. The 14 original live core scenarios remain historical tenant evidence and were not counted as newly executed tests.

## Version 8 update

The portal suite now has **66 passing tests**. New tests exercise staged leaver disablement and session revocation, separate approver/executor, stale roster rejection, duplicate and mismatched CSV input, approved agency dates, quarterly campaign idempotence, self-review denial, temporary-access revocation, core-role remediation, scheduler access control, audit export and web CSRF/role restrictions. Original SITAS **66** and original SAIF **13** still pass separately: **145 total automated tests**. Local browser visual acceptance, live Microsoft connection and Docker remain unverified.
