# Version 3 operations

See Sunhaven_Care_IAM_Operating_and_Technical_Guide.docx for the complete operating procedures, permissions and technical reference.

## How the workflows work

**Joiner:** Employees → New Joiner → fill required fields → Dry run → create.
**Mover:** Employee profile → Mover → preview. Execute the change through an approved access request. Old assignments are removed.
**Leaver:** Employee profile → Process Leaver → confirm. Access and sessions are removed.
**Request:** Access requests → request a change → another manager/operator decides.
Approval captures current role/facility. Another IAM operator (not the requester) uses Execute approved change within seven days. Stale, expired or already executed approvals are rejected. The old direct Mover apply route is blocked. An operator who approved someone else’s request may also execute it.
**Notes:** Notes & handovers → select worker/category → save. Existing notes cannot be edited.
**Reviews:** Record a decision and reason. Temporary exceptions require a future expiry.
Change/Remove decisions remain pending. After remediation, close the review with evidence in Security operations. Remove closure checks that access has actually been removed.
**Evidence:** Run compliance, inspect audit metadata and export CSV files.
Events named `DEMO_FIXTURE` are synthetic examples, not executed-action evidence.

