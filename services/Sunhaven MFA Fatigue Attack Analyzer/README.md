# SMFAA — Sunhaven MFA Fatigue Attack Analyzer

SMFAA is a small **operational MFA-fatigue detection service** for the Sunhaven Care Workforce IAM project.

It does one focused job:

> Read MFA/sign-in events, detect three MFA-fatigue patterns, and create explainable findings for review.

SMFAA is read-only. It does **not** change Microsoft Entra ID, MFA, Conditional Access, JML, RBAC, Flask access, user accounts or sessions.

## What Is Implemented

- Prompt Burst detection
- Repeated Denial detection
- Denial-to-Success detection
- configurable thresholds in `config/detection-rules.json`
- timestamp validation and ordering
- separate event windows for each employee
- read-only Sunhaven workforce context enrichment
- exported Microsoft Entra sign-in CSV adapter
- live Microsoft Entra sign-in integration through Microsoft Graph
- Entra-to-Sunhaven identity mapping
- JSON, CSV and console findings
- duplicate-burst suppression
- automated tests

## Folder Structure

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
│   ├── entra_graph_adapter.py
│   ├── smfaa.py
│   └── sunhaven_adapter.py
├── tests/
│   └── test_smfaa.py
├── requirements.txt
└── requirements-dev.txt
```

## How It Works

```text
MFA / sign-in events
        |
        v
validate + normalize
        |
        v
order by time
        |
        v
group by employee
        |
        v
rolling time-window checks
        |
        v
Prompt Burst / Repeated Denial / Denial-to-Success
        |
        v
explainable finding
        |
        v
JSON / CSV / console
```

SMFAA uses the same detector regardless of whether the events come from controlled demo data, exported Entra evidence or live Microsoft Graph sign-in logs.

## Detection Defaults

| Rule | Default |
|---|---|
| Prompt Burst | 5 prompts in 2 minutes |
| Repeated Denial | 3 denials in 5 minutes |
| Denial-to-Success | 3 denials followed by success within 10 minutes |

These are project/lab thresholds and can be changed in `config/detection-rules.json`.

## Install Dependencies

For the live Microsoft Graph integration:

```powershell
python -m pip install -r requirements.txt
```

The live connector currently requires:

```text
msal==1.39.0
requests==2.34.2
```

For development/testing dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

## Run the Demo

From the SMFAA folder:

```powershell
python src\smfaa.py --source demo
```

The controlled demo dataset is used to exercise the configured MFA-fatigue detection rules.

## Run Against Existing Entra Evidence

When SMFAA is located under the repository `services/` folder, run:

```powershell
python src\smfaa.py --source repo-entra
```

SMFAA reads the existing sanitised Entra evidence and Sunhaven workforce context from the repository.

The existing repository export contains valid MFA-related events but may not contain enough repeated activity to cross the configured fatigue thresholds. A clean no-finding result can therefore be expected for below-threshold evidence.

## Run Your Own Normalized CSV

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

## Run Live Microsoft Entra Mode

SMFAA supports live read-only Microsoft Entra sign-in log retrieval through Microsoft Graph.

The Microsoft Entra App Registration requires:

- delegated Microsoft Graph `AuditLog.Read.All` permission;
- admin consent;
- public client flow enabled;
- device code authentication; and
- no client secret.

Set the required environment variables:

```text
SMFAA_CLIENT_ID
SMFAA_TENANT_ID
```

Then run:

```powershell
python src\smfaa.py --source live-entra --repo-root "<Sunhaven repository path>"
```

The live runtime flow is:

```text
Microsoft Entra ID Sign-in Logs
        |
        v
Microsoft Graph API
        |
        v
entra_graph_adapter.py
        |
        v
Normalized MFA Events
        |
        v
detector.py
        |
        v
SMFAA Findings
        |
        v
JSON / CSV / Console
```

SMFAA uses Microsoft device code authentication to obtain read-only access to the permitted sign-in information.

Access tokens, device codes, passwords and secrets must not be stored in the repository.

## Entra Event Mapping

The exported Entra adapter and live Graph adapter convert relevant sign-in activity into the normalized SMFAA event model.

For the controlled project environment:

- error `50074` can be normalized as `MFA_PROMPT`;
- error `500121` is used for `MFA_DENIED` where the controlled test evidence confirms an MFA denial;
- supported MFA success evidence can be normalized as `MFA_SUCCESS`; and
- unrelated sign-in activity is ignored by the MFA-fatigue detector.

The normalized event model is:

```text
event_id
employee_id
timestamp
event_type
```

`data/identity-map.csv` maps relevant Microsoft Entra identities to Sunhaven employee identities for detection.

## Live Validation

The live Microsoft Graph integration has been tested against the Sunhaven Microsoft Entra environment.

The Graph adapter successfully retrieved live sign-in records and normalized relevant MFA events.

A controlled Test Nurse scenario produced a live:

```text
REPEATED_DENIAL
```

finding after three MFA denials occurred within five minutes.

The finding was exported through the existing SMFAA JSON and CSV reporting process.

## Current Live Limitation

During testing, successful sign-in records for the test account returned:

```text
authenticationRequirement=None
authenticationDetails=None
```

in the Microsoft Graph response used by the current adapter.

The adapter intentionally does not classify every successful `errorCode 0` sign-in as `MFA_SUCCESS`, because a successful sign-in does not necessarily prove that an MFA approval occurred. Treating every successful sign-in as MFA success could create false-positive results.

Therefore:

- live Microsoft Graph connectivity is working;
- live event retrieval is working;
- live event normalization is working;
- live Repeated Denial detection has been validated; and
- Denial-to-Success detection is implemented, but live validation currently depends on the MFA details available from Microsoft Graph.

The controlled demo dataset can be used to exercise the Denial-to-Success rule independently of this live Graph limitation.

The current live connector also retrieves a limited set of recent Graph records and does not yet implement pagination or persistent token caching.

## Security Boundary

SMFAA is a detection component only.

It can:

- read permitted sign-in information;
- normalize relevant MFA events;
- map Entra identities to Sunhaven employee identities;
- evaluate MFA-fatigue rules; and
- generate explainable findings.

It cannot:

- disable users;
- revoke sessions;
- modify MFA methods;
- modify Conditional Access;
- modify RBAC;
- execute JML actions;
- modify Microsoft Entra identities; or
- automatically remediate findings.

If SMFAA is unavailable, the Sunhaven Care Portal should continue to authenticate and authorise users normally.

## Testing

Run the automated tests with:

```powershell
python -m pytest -q
```

The final test count should be recorded after running the current test suite rather than relying on an earlier test count.

## Documentation

Additional technical documentation is available under `docs/`, including:

- `architecture-and-design.md`
- `requirements.md`
- `scope-boundary.md`
- `SMFAA_Project_Plan.md`
- `live-entra-integration.md`
