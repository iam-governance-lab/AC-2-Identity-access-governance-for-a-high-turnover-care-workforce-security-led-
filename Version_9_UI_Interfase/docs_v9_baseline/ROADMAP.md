> Historical v7/v8 document. For current behavior, use Sunhaven_v9_Final_Report.md and Sunhaven_v9_Operator_Handbook.md in this directory.

# Extension roadmap — proposed, not implemented

Version 8 now includes a reviewed CSV roster import, quarterly certification campaigns, an external scheduler command and local audit export. The items below describe their live integrations and other future extensions.

There is no fixed list of every possible future feature. These are useful extensions and the evidence required to claim completion.

| Priority | Extension | Acceptance evidence |
|---|---|---|
| 1 | One live connector shared by portal and Graph scripts | Immutable-ID/role mappings, tenant checks, dry-run, approval, retry/partial-failure recovery and live readback |
| 1 | Real OIDC + MFA/passkeys | Tenant policy and allowed/denied sign-in evidence; never trust a form selection |
| 1 | SAIF invitation-to-role handover | Sponsor, redemption, identity binding, role approval and revocation tests |
| 1 | Remote audit and recovery | Off-host sink, retention, failure handling and observed restoration drill |
| 2 | Durable background job queue beyond the current cron command | Lease ownership, retries, idempotency, pause control, dead-letter queue and alerts |
| 2 | Live SCIM/HR connector beyond the reviewed CSV workflow | Validated schema, source-of-truth rules, reconciliation and replay-safe provisioning |
| 2 | Facility-scoped managers | Resource-level authorization matrix and cross-facility denial tests |
| 2 | Cross-system recurring reviews beyond the local quarterly campaigns | Membership snapshots, independent reviewers, escalation and remediation evidence |
| 2 | Device/risk feeds | Trusted attestation, missing-signal rules and fail-closed tests |
| 3 | Governed AI assistant | Read-only scope, ownership, evidence citations, injection tests and human change approval |
| 3 | Agent workload federation | Short-lived tokens, audience binding, secretless identity and revocation checks |
| 3 | Resilience and scale | Production database, worker isolation, load objectives and fault injection |

Do not describe proposals as delivered. Define user need, security boundary, implementation, test and operating procedure for each addition.
