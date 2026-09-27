# Live Entra Integration — Next Step

SMFAA is fully functional now with normalized CSV input and the existing exported Entra sign-in evidence in the Sunhaven repository.

Live Entra is intentionally left as the next manual integration step.

## Target runtime flow

```text
Microsoft Entra ID
      ↓
Microsoft Graph sign-in logs (read-only)
      ↓
SMFAA Entra connector
      ↓
same normalization used by entra_csv_adapter.py
      ↓
existing detector.py
      ↓
findings
```

## What should stay unchanged

Do not rewrite the three detectors when live Entra is connected.

The live connector only needs to supply these normalized values:

```text
event_id
employee_id
timestamp
event_type
```

## Read-only boundary

The future connector should only read sign-in/MFA events. SMFAA must not request permissions to disable users, change MFA, modify roles or revoke sessions.

## Recommended implementation order later

1. Confirm the tenant can read Entra sign-in logs through Microsoft Graph.
2. Use read-only audit/sign-in permission approved by the project owner.
3. Retrieve only new sign-in records for the Sunhaven test application/users.
4. Map Entra object ID/UPN to Sunhaven `employee_id`.
5. Reuse the current event classification and detector functions.
6. Keep `--source demo` and exported CSV mode as reliable test fallbacks.
