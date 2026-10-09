import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import requests
from flask import Flask, abort, render_template, request, session
from identity.flask import Auth

import app_config

from database import (
    get_connection,
    initialize_database,
    is_user_blocked,
)


__version__ = "0.9.0"

app = Flask(__name__)
app.config.from_object(app_config)

SESSION_TIMEOUT_MINUTES = 15
SESSION_STARTED_AT_KEY = "sunhaven_session_started_at"

app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(
        minutes=SESSION_TIMEOUT_MINUTES
    ),
    SESSION_REFRESH_EACH_REQUEST=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

auth = Auth(
    app,
    authority=os.getenv("AUTHORITY"),
    client_id=os.getenv("CLIENT_ID"),
    client_credential=os.getenv("CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    oidc_authority=os.getenv("OIDC_AUTHORITY"),
    b2c_tenant_name=os.getenv("B2C_TENANT_NAME"),
    b2c_signup_signin_user_flow=os.getenv("SIGNUPSIGNIN_USER_FLOW"),
    b2c_edit_profile_user_flow=os.getenv("EDITPROFILE_USER_FLOW"),
    b2c_reset_password_user_flow=os.getenv("RESETPASSWORD_USER_FLOW"),
)

initialize_database()


def identity_from_context(context):
    """Return only the validated identity values required by this lab."""

    user = (context or {}).get("user") or {}
    raw_roles = user.get("roles") or []

    if isinstance(raw_roles, str):
        raw_roles = [raw_roles]

    return {
        "display_name": (
            user.get("name")
            or user.get("preferred_username")
            or "Signed-in TEST user"
        ),
        "object_id": user.get("oid"),
        "roles": set(raw_roles),
    }


def write_audit_event(identity, action, object_id, result):
    """Store a sanitized event. Tokens and secrets are never stored."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO app_audit_events (
                user_object_id,
                action,
                object_id,
                event_time,
                result
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                identity.get("object_id") or "missing-object-id",
                action,
                object_id,
                datetime.now(timezone.utc).isoformat(),
                result,
            ),
        )


def require_active_session(view_function):
    """Reject blocked users and expired local application sessions."""

    @wraps(view_function)
    def wrapped(*args, **kwargs):
        context = kwargs.get("context") or {}
        identity = identity_from_context(context)
        user_object_id = identity["object_id"]

        if not user_object_id:
            write_audit_event(
                identity,
                action=f"ACCESS {request.path}",
                object_id=request.path,
                result="DENY: missing Entra Object ID",
            )

            session.clear()

            abort(
                403,
                description=(
                    "Access was denied because the validated identity "
                    "did not contain an Entra Object ID."
                ),
            )

        if is_user_blocked(user_object_id):
            write_audit_event(
                identity,
                action=f"ACCESS {request.path}",
                object_id=user_object_id,
                result="DENY: local application block",
            )

            session.clear()

            abort(
                403,
                description=(
                    "This user's local application access has been "
                    "blocked by the leaver-control process."
                ),
            )

        session.permanent = True

        current_time = datetime.now(timezone.utc)
        session_started_at = session.get(SESSION_STARTED_AT_KEY)

        if not session_started_at:
            session[SESSION_STARTED_AT_KEY] = current_time.isoformat()

        else:
            try:
                started_time = datetime.fromisoformat(session_started_at)

                if started_time.tzinfo is None:
                    started_time = started_time.replace(
                        tzinfo=timezone.utc
                    )

            except (TypeError, ValueError):
                write_audit_event(
                    identity,
                    action=f"ACCESS {request.path}",
                    object_id=user_object_id,
                    result="DENY: invalid local session timestamp",
                )

                session.clear()

                abort(
                    403,
                    description=(
                        "The local application session was invalid. "
                        "Please sign in again."
                    ),
                )

            session_age = current_time - started_time

            if session_age >= timedelta(
                minutes=SESSION_TIMEOUT_MINUTES
            ):
                write_audit_event(
                    identity,
                    action=f"ACCESS {request.path}",
                    object_id=user_object_id,
                    result="DENY: local session expired",
                )

                session.clear()

                abort(
                    403,
                    description=(
                        "The local application session expired after "
                        f"{SESSION_TIMEOUT_MINUTES} minutes."
                    ),
                )

        return view_function(*args, **kwargs)

    return wrapped


def require_roles(*allowed_roles):
    """Permit the request only when an Entra role claim matches."""

    allowed_role_set = set(allowed_roles)

    def decorator(view_function):
        @wraps(view_function)
        def wrapped(*args, **kwargs):
            context = kwargs.get("context") or {}
            identity = identity_from_context(context)

            if not identity["object_id"]:
                write_audit_event(
                    identity,
                    action=f"ACCESS {request.path}",
                    object_id=request.path,
                    result="DENY: missing oid claim",
                )

                abort(
                    403,
                    description=(
                        "Access was denied because the identity did not "
                        "contain a valid Entra Object ID."
                    ),
                )

            if not identity["roles"].intersection(allowed_role_set):
                write_audit_event(
                    identity,
                    action=f"ACCESS {request.path}",
                    object_id=request.path,
                    result="DENY: role not permitted",
                )

                abort(
                    403,
                    description=(
                        "You authenticated successfully, but your Entra "
                        "application role cannot access this resource."
                    ),
                )

            return view_function(*args, **kwargs)

        return wrapped

    return decorator


@app.route("/")
@auth.login_required
@require_active_session
def index(*, context):
    return render_template(
        "index.html",
        user=context["user"],
        edit_profile_url=auth.get_edit_profile_url(),
        api_endpoint=os.getenv("ENDPOINT"),
        title=f"Sunhaven Care Portal - LAB v{__version__}",
    )


@app.route("/whoami")
@auth.login_required
@require_active_session
def whoami(*, context):
    identity = identity_from_context(context)

    return {
        "display_name": identity["display_name"],
        "object_id": identity["object_id"],
        "roles": sorted(identity["roles"]),
        "security_note": "No token or client secret is displayed.",
    }


@app.route("/residents")
@auth.login_required
@require_active_session
@require_roles("CareWorker", "Nurse", "Manager", "AgencyWorker")
def residents(*, context):
    identity = identity_from_context(context)

    with get_connection() as connection:
        if identity["roles"].intersection({"Nurse", "Manager"}):
            rows = connection.execute(
                """
                SELECT resident_id, display_name, facility
                FROM residents
                WHERE active = 1
                ORDER BY resident_id
                """
            ).fetchall()

        else:
            rows = connection.execute(
                """
                SELECT DISTINCT
                    residents.resident_id,
                    residents.display_name,
                    residents.facility
                FROM residents
                JOIN assignments
                  ON assignments.resident_id = residents.resident_id
                WHERE assignments.user_object_id = ?
                  AND assignments.active = 1
                  AND residents.active = 1
                  AND (
                      assignments.end_date IS NULL
                      OR assignments.end_date >= date('now')
                  )
                ORDER BY residents.resident_id
                """,
                (identity["object_id"],),
            ).fetchall()

    write_audit_event(
        identity,
        action="READ_RESIDENT_LIST",
        object_id="residents",
        result="ALLOW",
    )

    return render_template(
        "residents.html",
        residents=[dict(row) for row in rows],
        identity=identity,
    )


@app.route("/care-notes")
@auth.login_required
@require_active_session
@require_roles("CareWorker", "Nurse", "Manager", "AgencyWorker")
def care_notes(*, context):
    identity = identity_from_context(context)

    write_audit_event(
        identity,
        action="OPEN_CARE_NOTES",
        object_id="care-notes",
        result="ALLOW",
    )

    return render_template(
        "protected_page.html",
        title="Care notes",
        message="Access permitted. Only fictional TEST notes will be used.",
        identity=identity,
    )


@app.route("/clinical")
@auth.login_required
@require_active_session
@require_roles("Nurse", "Manager")
def clinical(*, context):
    identity = identity_from_context(context)

    write_audit_event(
        identity,
        action="OPEN_CLINICAL",
        object_id="clinical",
        result="ALLOW",
    )

    return render_template(
        "protected_page.html",
        title="Clinical workspace",
        message="Access permitted for the Nurse or Manager role.",
        identity=identity,
    )


@app.route("/review")
@auth.login_required
@require_active_session
@require_roles("Manager")
def review(*, context):
    identity = identity_from_context(context)

    write_audit_event(
        identity,
        action="OPEN_REVIEW",
        object_id="review",
        result="ALLOW",
    )

    return render_template(
        "protected_page.html",
        title="Manager review",
        message="Access permitted for the Manager role.",
        identity=identity,
    )


@app.route("/app-audit")
@auth.login_required
@require_active_session
@require_roles("Manager", "Auditor")
def app_audit(*, context):
    identity = identity_from_context(context)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                event_id,
                user_object_id,
                action,
                object_id,
                event_time,
                result
            FROM app_audit_events
            ORDER BY event_id DESC
            LIMIT 50
            """
        ).fetchall()

    write_audit_event(
        identity,
        action="READ_APP_AUDIT",
        object_id="app-audit",
        result="ALLOW",
    )

    return render_template(
        "app_audit.html",
        events=[dict(row) for row in rows],
        identity=identity,
    )


@app.route("/call_api")
@auth.login_required(scopes=os.getenv("SCOPE", "").split())
@require_active_session
def call_downstream_api(*, context):
    api_result = (
        requests.get(
            os.getenv("ENDPOINT"),
            headers={
                "Authorization": "Bearer " + context["access_token"]
            },
            timeout=30,
        ).json()
        if context.get("access_token")
        else "Did you forget to set the SCOPE environment variable?"
    )

    return render_template(
        "display.html",
        title="API Response",
        result=api_result,
    )


@app.errorhandler(403)
def access_denied(error):
    denial_reason = getattr(
        error,
        "description",
        "The application denied access to this resource.",
    )

    return (
        render_template(
            "403.html",
            requested_path=request.path,
            denial_reason=denial_reason,
        ),
        403,
    )