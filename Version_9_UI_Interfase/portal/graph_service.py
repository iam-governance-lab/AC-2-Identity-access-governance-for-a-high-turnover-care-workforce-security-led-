"""Microsoft Graph integration.

Default GRAPH_MODE=mock provides a complete offline demonstration.
Set SUNHAVEN_GRAPH_MODE=real and configure Entra credentials to perform real Graph operations.
MSAL is imported only in real mode, so the local project has no mandatory third-party dependency.
"""
import json
import secrets
import urllib.request
import urllib.error
import config

GRAPH = "https://graph.microsoft.com/v1.0"


class GraphError(RuntimeError):
    pass


class GraphService:
    def __init__(self):
        self.mode = config.GRAPH_MODE

    def _token(self):
        if self.mode != "real":
            return "mock-token"
        if not (config.TENANT_ID and config.CLIENT_ID and config.CLIENT_SECRET):
            raise GraphError("Real Graph mode requires TENANT_ID, CLIENT_ID and CLIENT_SECRET.")
        try:
            import msal
        except ImportError as exc:
            raise GraphError("Install optional dependency: pip install msal") from exc
        app = msal.ConfidentialClientApplication(
            config.CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{config.TENANT_ID}",
            client_credential=config.CLIENT_SECRET,
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in result:
            raise GraphError(result.get("error_description", "Unable to acquire Microsoft Graph token."))
        return result["access_token"]

    def _request(self, method, path, payload=None):
        if self.mode != "real":
            return {"mock": True, "method": method, "path": path, "payload": payload}
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            GRAPH + path,
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise GraphError(f"Graph {exc.code}: {body}") from exc

    def create_or_reconcile_user(self, employee):
        if self.mode != "real":
            return {"id": employee.get("entra_object_id") or f"mock-{employee['employee_id'].lower()}", "accountEnabled": True}

        # Find by UPN/mail first.
        email = employee["email"]
        query = email.replace("'", "''")
        found = self._request("GET", f"/users?$filter=userPrincipalName%20eq%20'{query}'&$select=id,userPrincipalName,accountEnabled")
        users = found.get("value", [])
        if len(users) == 1:
            return users[0]
        if len(users) > 1:
            raise GraphError("Ambiguous Entra identity: more than one user matched.")

        # A temporary password is generated but never logged or returned to the UI.
        temp = secrets.token_urlsafe(18) + "aA1!"
        payload = {
            "accountEnabled": True,
            "displayName": employee["name"],
            "mailNickname": employee["email"].split("@")[0].replace(".", ""),
            "userPrincipalName": email,
            "jobTitle": employee["approved_role"],
            "department": employee["facility"],
            "employeeId": employee["employee_id"],
            "passwordProfile": {"forceChangePasswordNextSignIn": True, "password": temp},
        }
        return self._request("POST", "/users", payload)

    def update_profile(self, object_id, employee):
        if self.mode != "real":
            return {"id": object_id, "updated": True}
        return self._request("PATCH", f"/users/{object_id}", {
            "jobTitle": employee["approved_role"],
            "department": employee["facility"],
            "accountEnabled": True,
        })

    def disable_user(self, object_id):
        if self.mode != "real":
            return {"id": object_id, "accountEnabled": False}
        return self._request("PATCH", f"/users/{object_id}", {"accountEnabled": False})

    def revoke_sessions(self, object_id):
        if self.mode != "real":
            return {"id": object_id, "revoked": True}
        return self._request("POST", f"/users/{object_id}/revokeSignInSessions", {})

    def replace_role_group(self, object_id, new_role=None):
        """Remove configured Sunhaven role groups, then optionally add the new approved role group."""
        configured = {r: gid for r, gid in config.ROLE_GROUP_IDS.items() if gid}
        if self.mode != "real":
            return {"id": object_id, "role": new_role, "groups_considered": list(configured)}
        for role, group_id in configured.items():
            try:
                self._request("DELETE", f"/groups/{group_id}/members/{object_id}/$ref")
            except GraphError as exc:
                # Removing a non-member can return an error; we continue because final assignment is verified locally.
                if "404" not in str(exc) and "400" not in str(exc):
                    raise
        if new_role and configured.get(new_role):
            self._request("POST", f"/groups/{configured[new_role]}/members/$ref", {
                "@odata.id": f"{GRAPH}/directoryObjects/{object_id}"
            })
        return {"id": object_id, "role": new_role}
