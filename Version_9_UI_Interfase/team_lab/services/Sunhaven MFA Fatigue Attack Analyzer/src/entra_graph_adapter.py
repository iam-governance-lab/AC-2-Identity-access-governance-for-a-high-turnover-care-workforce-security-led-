from __future__ import annotations

import os

import msal
import requests

from detector import MFAEvent, build_event
from sunhaven_adapter import resolve_employee_id


PROMPT_ERROR_CODES = {50074}
DENIAL_ERROR_CODES = {500121}


def load_graph_signins(
    workforce: dict[str, dict],
    identity_rows: list[dict],
) -> tuple[list[MFAEvent], dict]:

    client_id = os.environ.get("SMFAA_CLIENT_ID")
    tenant_id = os.environ.get("SMFAA_TENANT_ID")

    if not client_id or not tenant_id:
        raise RuntimeError(
            "SMFAA_CLIENT_ID and SMFAA_TENANT_ID must be set."
        )

    authority = f"https://login.microsoftonline.com/{tenant_id}"

    app = msal.PublicClientApplication(
        client_id,
        authority=authority,
    )

    flow = app.initiate_device_flow(
        scopes=["AuditLog.Read.All"]
    )

    if "user_code" not in flow:
        raise RuntimeError("Could not start Microsoft Graph login.")

    print(flow["message"])

    token = app.acquire_token_by_device_flow(flow)

    if "access_token" not in token:
        raise RuntimeError(
            token.get("error_description", "Microsoft Graph login failed.")
        )

    url = (
        "https://graph.microsoft.com/v1.0/"
        "auditLogs/signIns?$top=100"
    )

    # Follow only Graph's own sign-in endpoint. Never forward tokens to redirects.
    from urllib.parse import urlparse
    rows = []
    pages = 0
    while url and pages < 10:
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.netloc != 'graph.microsoft.com' or parsed.path != '/v1.0/auditLogs/signIns':
            raise RuntimeError('Unexpected Graph pagination URL.')
        response = requests.get(url, headers={'Authorization': f"Bearer {token['access_token']}"}, timeout=30, allow_redirects=False)
        if 300 <= response.status_code < 400:raise RuntimeError('Graph redirect refused.')
        response.raise_for_status()
        body=response.json()
        if not isinstance(body,dict) or not isinstance(body.get('value'),list):raise RuntimeError('Malformed Graph response.')
        if not all(isinstance(row,dict) for row in body['value']):raise RuntimeError('Malformed Graph sign-in record.')
        rows.extend(body['value']);pages += 1
        url=body.get('@odata.nextLink')
        if url is not None and not isinstance(url,str):raise RuntimeError('Malformed Graph pagination URL.')
        if len(rows)>10000:raise RuntimeError('Graph result exceeds 10,000 rows. Narrow the query.')

    events: list[MFAEvent] = []
    stats = {
        "pages": pages,
        "truncated": bool(url),
        "rows": 0,
        "normalized": 0,
        "ignored": 0,
        "unmapped": 0,
    }

    for row in rows:
        stats["rows"] += 1

        error_code = row.get("status", {}).get("errorCode", 0)
        auth_requirement = (
            row.get("authenticationRequirement") or ""
        ).lower()

        if error_code in PROMPT_ERROR_CODES:
            event_type = "MFA_PROMPT"

        elif error_code in DENIAL_ERROR_CODES:
            event_type = "MFA_DENIED"

        elif error_code == 0 and "multifactor" in auth_requirement:
            event_type = "MFA_SUCCESS"

        else:
            stats["ignored"] += 1
            continue

        employee_id = resolve_employee_id(
            row.get("userId", ""),
            row.get("userPrincipalName", ""),
            workforce,
            identity_rows,
        )

        if not employee_id:
            stats["unmapped"] += 1
            continue

        event = build_event(
            {
                "event_id": row.get("id", ""),
                "employee_id": employee_id,
                "timestamp": row.get("createdDateTime", ""),
                "event_type": event_type,
            },
            source="ENTRA_GRAPH",
        )

        events.append(event)
        stats["normalized"] += 1

    events.sort(key=lambda item: item.timestamp)

    return events, stats