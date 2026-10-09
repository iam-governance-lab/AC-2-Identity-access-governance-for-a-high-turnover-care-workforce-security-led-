# Version 9 Final — integration and changes

## Sources and preservation

The existing complete v9 was the baseline. The active portal incorporates compatible code from the supplied v14 recovery release, which includes the intervening v10–v12.2 features and reconstructed v13 capabilities. The new outer release identifier is `9.0-final`. Existing internal migrations retain their historical numbers. The original lab is preserved unchanged under `original/`, verified against its 545-file manifest. Newer teammate material is retained under `team_lab/`.

## Capability mapping

| Area | Final location and behavior |
|---|---|
| Team MFA fatigue analyzer | Full source and CLI in team_lab; main portal Team services runs its detector in an isolated bounded subprocess, saves findings and emits an audit event. |
| Team Entra access review | Full separate Flask interface, campaign database, inventory/plan/apply worker, PowerShell scripts, tests and evidence. Tenant configuration required. |
| Team lifecycle automation | Joiner, mover, leaver, export, input validation and dry-run PowerShell scripts retained. |
| Team agency federation | SAIF validation, invitation preview and full B2B scripts retained; local original-engine bridge available. |
| Team threat simulation | SITAS models, comparisons, reports and portal-snapshot bridge retained. |
| Newer access management | Application catalogue/entitlements, request governance, shift context, sponsor intake and review workbench in main portal. |
| Newer integration operations | Local durable connector jobs, retries, webhook interfaces and configuration boundaries. External services are not represented as connected. |
| Newer workforce usability | Expanded synthetic workforce, pagination, filters, saved views, responsive navigation, notifications and operational notes. |
| Newer AI and help | Explainable access, aggregate governance briefings, role-aware local guidance and optional external model adapter. Human approval stays mandatory. |
| Security and recovery | Session/CSRF checks, role checks, self-approval separation, audit ledger, validation, backups, guarded configuration and health checks. |

## Fixes and optimization in this consolidation

- Correct release identification and a single top-level launcher for portal, simulation, detector, lab and review worker.
- Rebuilt the CSS bundle so the latest layout fixes are actually served; reinforced responsive drawer positioning and wrapping.
- Corrected risk/role help routing and added team-service help topics; regenerated the local retrieval model.
- Added MFA input size/count limits, duplicate-ID rejection, explicit event validation, execution timeout and persistent audited output.
- Corrected the new service form action discovered by real-browser testing.
- Removed eager live-Graph dependency loading from the offline detector so its demo works without optional packages.
- Added strict numeric detection-rule validation.
- Hardened the live sign-in adapter with bounded pagination, response validation, redirect refusal and Graph-origin/path validation; added simulated-network regression tests.
- Made the lab database path configurable for isolation and testing.
- Added detector source to the Docker build and separated historical reports from new verification evidence.
- Retained newer static compression/cache/ETag handling, database indexes and pagination. Recorded local HTTP timing is a smoke-test measurement, not a production load benchmark.

## Integration boundaries

The team lab is runnable as a separate interface and database; it is not silently merged with the portal's local identity database. Live Entra, Microsoft Graph, email, HRIS/rostering, external AI and SIEM destinations require their own credentials and deployment testing. The release is suitable for a comprehensive controlled demonstration, with full source available for further integration.
