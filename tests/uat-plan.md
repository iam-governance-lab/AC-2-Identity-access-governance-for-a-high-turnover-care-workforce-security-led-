# User Acceptance Testing (UAT) Plan

## Purpose

The purpose of UAT is to check whether the IAM system meets the main needs of the Sunhaven Care scenario.

## UAT Scenarios

### UAT-01 - New Employee

Scenario: A new employee joins Sunhaven Care.

Expected Result: The employee receives an account and the correct access based on their assigned role.

### UAT-02 - Employee Changes Role

Scenario: An employee changes to a different role.

Expected Result: The employee's old access is removed and the correct access for the new role is provided.

### UAT-03 - Employee Leaves

Scenario: An employee leaves Sunhaven Care.

Expected Result: The employee's account is disabled, and the employee can no longer sign in.

### UAT-04 - Access Review

Scenario: A manager reviews the access assigned to users.

Expected Result: Unnecessary or outdated access can be identified for removal.

## Evidence

UAT evidence will include:

- Screenshots
- Test results
- Audit logs where available
- Pass or fail status
- Notes about any problems found
