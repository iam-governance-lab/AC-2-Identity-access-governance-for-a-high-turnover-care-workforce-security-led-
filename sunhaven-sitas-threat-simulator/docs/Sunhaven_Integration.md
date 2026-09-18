# SITAS Integration with the Sunhaven Care Project

## Purpose

SITAS now supports two operating modes:

1. **Standalone simulation mode** – uses the SITAS JSON environment and six controlled threat scenarios.
2. **Sunhaven-integrated analysis mode** – reads selected files from the actual Sunhaven Care group repository through a read-only adapter.

The integration was designed so SITAS contributes threat analysis and assurance without duplicating the operational IAM work performed by the group system.

## Integration boundary

SITAS **reads** project artefacts. It does not:

- create, update or disable Microsoft Entra users;
- execute Joiner-Mover-Leaver automation;
- modify Flask application state;
- assign or remove groups/app roles;
- make production authorization decisions;
- change MFA, Conditional Access or device settings;
- claim that an optional sanitised evidence file represents live/current state.

This keeps SITAS a separate analysis component while still making it part of the Sunhaven architecture.

## Data flow

```text
Sunhaven Care group repository
│
├── data/workforce.csv
├── config/route-role-map.csv
├── config/app-role-ids.json
├── config/group-object-ids.json
├── automation/Invoke-SunhavenLeaver.ps1
└── optional sanitised state/evidence exports
          │
          │ read only
          ▼
  src/sunhaven_adapter.py
          │
          ├── workforce summary
          ├── RBAC matrix
          ├── control-to-project mapping
          └── Sunhaven-derived leaver scenario
          │
          ▼
Existing SITAS engines
(graph → BFS → risk → control comparison)
          │
          ▼
JSON / CSV / HTML integration reports
```

## Main group-project alignment

### High-turnover workforce and leaver risk

The group project treats workforce lifecycle management as a core security requirement. SITAS reads `data/workforce.csv` and selects a record marked `Leaving` or `Inactive` for an integrated former-worker analysis.

For the current repository snapshot, `SC1006` is selected because the workforce file marks that fictional worker as `Leaving`.

The generated SITAS path is:

```text
Former Worker (SC1006)
        ↓
Sunhaven Identity (SC1006, CareWorker)
        ↓
Sunhaven Care Portal
        ↓
Fictional Resident Records
```

The automatic comparison then models:

```text
Account disablement OFF → OPEN
Account disablement ON  → BLOCKED
```

This does not execute the real leaver workflow. It demonstrates the security reason the real JML control exists.

### Least privilege and RBAC

SITAS reads:

- `config/route-role-map.csv`
- `config/app-role-ids.json`
- `config/group-object-ids.json`

It generates a role/route matrix directly from the group repository. This lets SITAS show the intended authorization boundary without changing Flask or Entra.

For example, the current configuration allows `Nurse` and `Manager` to `/clinical` while `CareWorker` is denied. That configuration supports SITAS Scenario 4 (excessive privilege/RBAC) while Rifat's application remains responsible for real enforcement.

### MFA

SITAS Scenario 1 continues to model stolen-credential risk and the expected effect of MFA. The adapter deliberately does not infer live MFA enforcement from static project files. SMFAA will later consume authentication event data as a separate analysis component.

### Shared sessions

SITAS Scenario 2 remains a controlled threat scenario showing shared-session exposure. SITAS does not manage sessions or shared devices and therefore does not overlap with session/device components owned elsewhere in the team.

### Privileged re-authentication

Scenario 5 remains a simulated security extension. SITAS does not claim that privileged re-authentication is currently enforced by the core project.

### Trusted-device restriction

Scenario 6 is explicitly a future-production control analysis. SITAS does not claim that device compliance or MDM is part of the current Sunhaven MVP.

## Supported integration sources

Required files:

```text
data/workforce.csv
config/route-role-map.csv
config/app-role-ids.json
config/group-object-ids.json
```

Optional supporting evidence:

```text
sanitised worker-state CSV from Export-SunhavenWorkerState.ps1
sanitised leaver-result JSON
```

Optional evidence is always labelled as read-only supporting evidence, not a live query.

## Portability

There are no hard-coded `C:\...` paths in the adapter.

When SITAS is stored directly inside the main Sunhaven repository, the adapter automatically detects the parent project root. A standalone SITAS checkout can use:

```powershell
python src/sitas.py sunhaven-status --root "C:\path\to\Sunhaven-core"
```

## Integrated commands

From SITAS inside the main repository:

```powershell
python src/sitas.py sunhaven-status
python src/sitas.py sunhaven-leaver
python src/sitas.py sunhaven-report
```

From a standalone SITAS checkout:

```powershell
python src/sitas.py sunhaven-status --root "C:\Sunhaven\core-downloaded"
python src/sitas.py sunhaven-leaver --root "C:\Sunhaven\core-downloaded"
python src/sitas.py sunhaven-report --root "C:\Sunhaven\core-downloaded"
```

Optional explicit evidence:

```powershell
python src/sitas.py sunhaven-leaver `
  --root "C:\Sunhaven\core-downloaded" `
  --employee-id SC1006 `
  --worker-state "C:\path\to\sanitised-worker-state.csv"
```

or:

```powershell
python src/sitas.py sunhaven-leaver `
  --root "C:\Sunhaven\core-downloaded" `
  --employee-id SC1006 `
  --leaver-result "C:\path\to\sanitised-leaver-result.json"
```

## Generated integration outputs

```text
reports/sunhaven-integration-analysis.json
reports/sunhaven-rbac-matrix.csv
reports/sunhaven-integration-report.html
```

The integration report records the source inventory, workforce summary, Sunhaven-derived former-worker analysis, RBAC matrix, control mapping and any input/configuration warnings.
