# SITAS Development Progress 3 – Sunhaven Integration Milestone

## Summary

This milestone changes SITAS from a standalone threat simulator into a read-only security-analysis component that can consume the actual Sunhaven Care project structure without modifying the operational IAM implementation.

## Implemented work

### 1. Read-only Sunhaven adapter

Added:

```text
src/sunhaven_adapter.py
```

The adapter validates and reads:

```text
data/workforce.csv
config/route-role-map.csv
config/app-role-ids.json
config/group-object-ids.json
```

It also records whether the main Joiner/Mover/Leaver, state-export and Flask artefacts are present.

### 2. Workforce-derived former-worker scenario

The adapter selects a Sunhaven workforce record marked Leaving/Inactive and generates an integrated attack-path scenario using the existing SITAS engine.

Against the current group repository, the selected TEST record is:

```text
SC1006 | CareWorker | Sydney | Leaving
```

The result is:

```text
Account control OFF → OPEN
Account control ON  → BLOCKED
Path interrupted    → YES
```

This is a simulation driven by the actual project workforce file. It does not execute the real leaver workflow.

### 3. RBAC integration

SITAS now reads the actual route-role configuration and generates a deterministic role/route matrix. The current configuration includes five app roles and five protected routes.

Example verified relationship:

```text
CareWorker → /clinical → DENY (HTTP 403)
Nurse      → /clinical → ALLOW
```

### 4. Optional sanitised evidence

SITAS can optionally read:

- worker-state CSV produced by the existing state-export format;
- sanitised leaver-result JSON.

These files are labelled as supporting snapshot evidence. SITAS does not claim they are live/current state.

### 5. Integrated reports

Added:

```text
reports/sunhaven-integration-analysis.json
reports/sunhaven-rbac-matrix.csv
reports/sunhaven-integration-report.html
```

### 6. Automated testing

Added 16 Sunhaven-integration tests.

Current full verified suite:

```text
66 passed
```

## Ownership boundary

The integration remains read-only. SITAS does not:

- execute Joiner/Mover/Leaver scripts;
- make Graph writes;
- change Entra users/groups/app roles;
- modify Flask authorization;
- configure MFA;
- manage sessions/shared devices;
- perform access reviews/remediation;
- implement the team's monitoring dashboard.

SITAS remains the threat/risk/control-analysis component and now has a direct, testable interface to the group project.
