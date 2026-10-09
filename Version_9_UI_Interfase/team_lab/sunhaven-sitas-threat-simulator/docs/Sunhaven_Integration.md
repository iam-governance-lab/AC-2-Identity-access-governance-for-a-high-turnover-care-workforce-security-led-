# SITAS Integration with the Sunhaven Care Project

## Purpose

SITAS supports two modes:

1. **Standalone simulation** – uses SITAS JSON data and six controlled threat scenarios.
2. **Sunhaven-integrated analysis** – reads selected files from the Sunhaven Care group project through a read-only adapter.

The integration lets SITAS analyse project-specific identity risks without duplicating the team's operational IAM work.

---

## Integration Boundary

SITAS reads project artefacts but does not:

- create, update or disable Microsoft Entra users;
- run Joiner-Mover-Leaver automation;
- modify Flask application state;
- assign or remove groups or app roles;
- enforce MFA, RBAC, Conditional Access or device controls;
- perform access reviews or remediation;
- treat optional evidence files as live/current Microsoft Entra state.

SITAS remains an analysis and testing component.

---

## Data Flow

```text
Sunhaven Project Files
        ↓
Read-Only SITAS Adapter
        ↓
Workforce + Role Configuration
        ↓
SITAS Analysis Engine
Graph → BFS → Risk → Control Comparison
        ↓
JSON / CSV / HTML Reports
```

Main project files used by the adapter:

```text
data/workforce.csv
config/route-role-map.csv
config/app-role-ids.json
config/group-object-ids.json
```

The adapter can also recognise relevant JML artefacts and optional sanitised state evidence without executing them.

---

## Project Alignment

### Leaver Access

The Sunhaven project treats timely removal of leaver access as a core requirement.

SITAS reads `data/workforce.csv` and can build a former-worker scenario from a worker marked `Leaving` or `Inactive`.

In the current project snapshot, the integrated test uses fictional worker `SC1006`, marked as `Leaving`.

```text
Former Worker
→ Sunhaven Identity
→ Sunhaven Care Portal
→ Fictional Resident Records
```

Automatic comparison models:

```text
Account Disablement OFF → OPEN
Account Disablement ON  → BLOCKED
```

This demonstrates why the leaver control matters. It does not execute the real JML workflow.

### Least Privilege and RBAC

SITAS reads the project role configuration and produces a role/route matrix.

This supports analysis of excessive privilege and intended access boundaries without changing Flask or Microsoft Entra.

### MFA

Scenario 1 models stolen-credential risk and the expected effect of MFA.

SITAS does not infer live MFA status from static project files.

### Shared Sessions

Scenario 2 models risk from an unattended authenticated session.

SITAS does not manage real sessions or shared devices.

### Privileged Access

Scenario 5 models privileged-account compromise and a simulated privileged re-authentication control.

SITAS does not claim that this control is currently enforced by the main project.

### Device Controls

Scenario 6 models trusted-device restriction as a future-control scenario.

Device compliance, MDM and kiosk enforcement are not claimed as part of the current Sunhaven MVP.

---

## Optional Supporting Evidence

SITAS can also read sanitised evidence such as:

```text
worker-state CSV
leaver-result JSON
```

These files are treated only as read-only supporting evidence.

They are not described as live Microsoft Entra queries unless separately produced and verified as such.

---

## Portability

The adapter does not depend on hard-coded `C:\...` paths.

When SITAS is stored inside the main Sunhaven repository, it can detect the parent project automatically.

A separate checkout can use:

```powershell
python src/sitas.py sunhaven-status --root "C:\path\to\Sunhaven-core"
```

---

## Integrated Commands

From SITAS inside the main project:

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

---

## Generated Outputs

```text
reports/sunhaven-integration-analysis.json
reports/sunhaven-rbac-matrix.csv
reports/sunhaven-integration-report.html
```

The integration report includes:

- source inventory;
- workforce summary;
- integrated former-worker analysis;
- RBAC matrix;
- control mapping;
- integration warnings.

---

## Summary

The Sunhaven adapter makes SITAS relevant to the real group project while keeping a clear technical boundary.

The main project remains responsible for operational identity management and access enforcement. SITAS reads selected project artefacts and uses them for repeatable threat-path, risk and control-effectiveness analysis.
