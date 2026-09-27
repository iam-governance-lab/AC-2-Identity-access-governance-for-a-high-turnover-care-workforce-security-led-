# SMFAA — Sunhaven MFA Fatigue Attack Analyzer

SMFAA is a small **operational MFA-fatigue detection service** for the Sunhaven Care Workforce IAM project.

It does one job:

> Read MFA/sign-in events, detect three MFA-fatigue patterns, and create explainable findings for review.

SMFAA is read-only. It does **not** change Entra ID, MFA, JML, RBAC, Flask access, accounts or sessions.

## What is implemented

- Prompt Burst detection
- Repeated Denial detection
- Denial-to-Success detection
- configurable thresholds in `config/detection-rules.json`
- timestamp validation and ordering
- separate event windows for each employee
- read-only Sunhaven `workforce.csv` enrichment
- Entra exported sign-in CSV adapter
- JSON, CSV and console findings
- duplicate-burst suppression
- automated tests

## Folder structure

```text
Sunhaven MFA Fatigue Attack Analyzer/
├── config/
│   └── detection-rules.json
├── data/
│   ├── demo-events.csv
│   └── identity-map.csv
├── docs/
├── evidence/
├── reports/
├── src/
│   ├── detector.py
│   ├── entra_csv_adapter.py
│   ├── smfaa.py
│   └── sunhaven_adapter.py
├── tests/
│   └── test_smfaa.py
├── run_demo.bat
├── run_repo_entra.bat
├── run_tests.bat
└── requirements-dev.txt
```

## How it works

```text
MFA / sign-in events
        ↓
validate + normalize
        ↓
order by time
        ↓
group by employee
        ↓
rolling time-window checks
        ↓
Prompt Burst / Repeated Denial / Denial-to-Success
        ↓
explainable finding
        ↓
JSON / CSV / console
```

## Run the demo

From this folder:

```powershell
python src\smfaa.py --source demo
```

The included demo uses the real Sunhaven employee IDs from the repository and should produce four findings.

## Run against the existing Entra evidence in the repository

Place this folder back under the repository `services/` folder, then run:

```powershell
python src\smfaa.py --source repo-entra
```

SMFAA automatically reads:

```text
../../evidence/phase6/P6-E14_Entra-SignIn-Sanitized.csv
../../data/workforce.csv
```

The current repository export contains valid MFA-related events but does not contain enough repeated events to cross the configured fatigue thresholds, so a clean **no finding** result is expected for that evidence set.

## Run your own normalized CSV

```powershell
python src\smfaa.py --source csv --input C:\path\to\events.csv
```

Expected columns:

```text
event_id,employee_id,timestamp,event_type
```

Supported event types:

```text
MFA_PROMPT
MFA_DENIED
MFA_SUCCESS
```

## Detection defaults

| Rule | Default |
|---|---|
| Prompt Burst | 5 prompts in 2 minutes |
| Repeated Denial | 3 denials in 5 minutes |
| Denial-to-Success | 3 denials followed by success within 10 minutes |

These are project/lab thresholds and can be changed in configuration.

## Entra export mapping

The current adapter understands the sanitised Entra CSV format already stored in the repository.

For the current project evidence:

- error `50074` is treated as an MFA prompt/challenge event;
- error `500121` is treated as an MFA denial/not-completed event;
- successful MFA-related sign-ins are treated as `MFA_SUCCESS`;
- unrelated failures such as wrong password, disabled account and KMSI interruptions are ignored.

`data/identity-map.csv` contains only the fictional/test identity mappings needed for the existing repository evidence. Later live Entra integration can replace this static mapping with live employee/object-ID correlation.

## Live Entra later

The detector is already independent of the event source. Live Entra integration only needs to retrieve new sign-in records and feed them through the same normalization path.

See `docs/live-entra-integration-next.md`.

## Testing

Install the development dependency once:

```powershell
pip install -r requirements-dev.txt
```

Then run:

```powershell
python -m pytest -q
```

Current verification for this package: **35 tests passing**.
