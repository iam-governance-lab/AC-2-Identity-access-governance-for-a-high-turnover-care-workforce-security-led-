# IAM System Test Cases

| Test ID | Feature | Test Action | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| TC-01 | User Creation | Create a new test user | User account is created successfully | Not Tested | Not Tested |
| TC-02 | RBAC | Assign an approved role to the test user | User receives access based on the assigned role | Not Tested | Not Tested |
| TC-03 | MFA | Sign in using a test account | MFA verification is required | Not Tested | Not Tested |
| TC-04 | Mover | Change the test user's role | Old access is removed and new role access is added | Not Tested | Not Tested |
| TC-05 | Leaver | Disable a departing test user | User cannot sign in | Not Tested | Not Tested |
| TC-06 | Audit Log | Review account changes | Relevant account changes appear in the audit log | Not Tested | Not Tested |
| TC-07 | Access Review | Review current user permissions | Unnecessary or outdated access can be identified | Not Tested | Not Tested |
