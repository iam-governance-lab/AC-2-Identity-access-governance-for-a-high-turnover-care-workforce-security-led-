> Historical checklist; version 6 proposal mapping is in `DELIVERY_MATRIX_V6.md`. Unticked tenant and video items still need authentic evidence.

> Historical project reference. For version 3 operating steps, including mandatory approved Mover execution, use the Operating and Technical Guide.

# Sunhaven Care IAM — Requirements Checklist

Tick only after the item is working and you have real evidence.

| Check | Requirement | Evidence |
|---|---|---|
| [ ] | Employee records can be added/viewed/updated | Workforce pages + SQLite data |
| [ ] | CareWorker, Nurse, Manager, AgencyWorker, Auditor, IAMOperator roles exist | Seed data + role tests |
| [ ] | Secure login works | Local demo + live Entra evidence if enabled |
| [ ] | MFA demonstrated | Entra MFA/security-default/Conditional-Access evidence |
| [ ] | Server-side RBAC protects direct requests | Allowed + HTTP 403 tests |
| [ ] | Joiner validates input and creates correct access | Dry run + final state + audit |
| [ ] | Mover removes old access before new access | Before/after employee state |
| [ ] | Leaver disables/removes/blocks access | Final state + denial evidence |
| [ ] | Agency worker requires sponsor and end date | Negative validation test |
| [ ] | Synthetic resident data only | Resident data review |
| [ ] | Resident access limited by role/assignment | Allowed + denied tests |
| [ ] | Access Review workflow works | Saved review evidence |
| [ ] | Audit log is timestamped and sanitised | Audit page + code test |
| [ ] | Compliance checker detects seeded violations | C01–C08 output |
| [ ] | Compliance checker is read-only | Design/code review |
| [ ] | GitHub contains source and individual contribution evidence | Repository/commits |
| [ ] | README/setup instructions exist | README.md |
| [ ] | Architecture is documented | ARCHITECTURE.svg |
| [ ] | Automated/repeatable tests pass | `python -m unittest discover -s tests -v` |
| [ ] | Final report explains PowerShell → Python/Graph design change | Assessment 3 report |
| [ ] | Demo video is under 10 minutes | Final video |
