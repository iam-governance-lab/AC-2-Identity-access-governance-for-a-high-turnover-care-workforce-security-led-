> Historical v7/v8 document. For current behavior, use Sunhaven_v9_Final_Report.md and Sunhaven_v9_Operator_Handbook.md in this directory.

# Feature preservation and release matrix

| Capability | Release 7 implementation | Status |
|---|---|---|
| Original Flask OIDC and care portal | original/app, unchanged | Preserved; own tenant required |
| Graph PowerShell JML, dry-run, approval, tenant checks, idempotence, readback | original/automation, unchanged | Preserved; no live revalidation |
| Original access review, policies and evidence | All 545 original files with SHA-256 manifest | Preserved and verified |
| Full SITAS graph/path/risk/control/reporting/adapter | Original engine + read-only portal bridge | Integrated; 66 original tests pass |
| SAIF validation, invitation, mapping, handover | Full original component; validator/preview bridge | Validation integrated; real B2B transport retained |
| SMFAA planning | original/services | Preserved documents |
| Working synthetic MFA analyzer | portal/security_workstream | Retained local implementation |
| Local JML, resident scope and notes | Existing portal services | Retained and tested |
| Reviews, tasks, policies, risks, compliance, onboarding | Existing portal modules | Retained and tested |
| Agency expiry, reminders, reports and ledger | Existing portal automation/evidence | Retained and tested |
| Access packages with independent decision, expiry and revocation | enterprise.py + protected resources | Implemented locally |
| Temporary incident response | Independently approved, 60-minute capability checked per write | Local; not Entra PIM |
| Separation of duties | Quality-review conflicts with incident-response | Local example |
| Service and agent governance | Owner, scope, lifetime, evaluation, disable | Local registry, no agent execution |
| Incident management | Open → Investigating → Contained → Resolved with evidence | Implemented locally |
| Conditional access, passkey and device what-if | Declared inputs and explanation | Simulator only |
| Live portal Graph writes | Blocked; original scripts available separately | Integration pending |
| Live agent credentials and device attestation | No production connector | Roadmap |
| Public deployment and enterprise certification | No verified deployment | Not claimed |

Original and portal databases and role schemes require an explicitly validated connector before a single live service can be claimed.

## Version 8 additions

| Capability | Delivery | Status |
|---|---|---|
| HR roster reconciliation | CSV validation, independent approval, snapshot recheck, local leaver disable and agency date update | Implemented locally; HR connector pending |
| Quarterly certification | One campaign per quarter, independent decisions, package revocation and role remediation task | Implemented locally |
| Daily scheduled check | CLI preview and idempotent quarterly campaign creation via external scheduler | Implemented; no autonomous worker installed |
| Audit handover | Ledger-checked local NDJSON export with SHA-256 result | Implemented locally; remote archive pending |
