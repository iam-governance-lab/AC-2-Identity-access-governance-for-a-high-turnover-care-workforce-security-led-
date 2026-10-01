# Live Microsoft Entra Integration

SMFAA supports live read-only Microsoft Entra sign-in log analysis through Microsoft Graph.

The live integration retrieves Entra sign-in records, converts relevant MFA activity into the normalized SMFAA event format, and passes those events to the existing detector.

## Runtime Flow

```text
Microsoft Entra ID Sign-in Logs
        ↓
Microsoft Graph API
(AuditLog.Read.All - delegated/read-only)
        ↓
entra_graph_adapter.py
        ↓
Normalized MFA Events
        ↓
detector.py + detection-rules.json
        ↓
SMFAA Findings
        ↓
JSON / CSV Reports
