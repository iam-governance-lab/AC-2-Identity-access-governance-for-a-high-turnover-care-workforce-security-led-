"""Flask Blueprint for the Sunhaven Manager access-review system."""

from __future__ import annotations

import secrets
from datetime import date

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from access_review_db import (
    ALLOWED_WORKFORCE_ROLES,
    close_campaign,
    create_campaign,
    get_campaign,
    get_item_decisions,
    get_job,
    get_job_events,
    get_review_item,
    list_campaign_items,
    list_campaigns,
    mark_expired_exceptions,
    queue_apply_job,
    record_decision,
)


CSRF_SESSION_KEY = "sunhaven_access_review_csrf"


def build_access_review_blueprint(
    *,
    auth,
    require_active_session,
    require_roles,
    identity_from_context,
    write_audit_event,
) -> Blueprint:
    blueprint = Blueprint("access_review", __name__)

    def csrf_token() -> str:
        token = session.get(CSRF_SESSION_KEY)
        if not token:
            token = secrets.token_urlsafe(32)
            session[CSRF_SESSION_KEY] = token
        return token

    def require_valid_csrf() -> None:
        expected = session.get(CSRF_SESSION_KEY, "")
        submitted = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected, submitted):
            abort(400, description="The form security token was invalid.")

    @blueprint.app_context_processor
    def access_review_template_helpers():
        return {"access_review_csrf_token": csrf_token}

    @blueprint.route("/access-review")
    @auth.login_required
    @require_active_session
    @require_roles("Manager", "Auditor")
    def dashboard(*, context):
        identity = identity_from_context(context)
        mark_expired_exceptions()
        campaigns = list_campaigns()
        write_audit_event(
            identity,
            action="OPEN_ACCESS_REVIEW",
            object_id="access-review",
            result="ALLOW",
        )
        return render_template(
            "access_review_dashboard.html",
            identity=identity,
            campaigns=campaigns,
            campaign=None,
            items=[],
            today=date.today().isoformat(),
        )

    @blueprint.route("/access-review/campaign/<int:campaign_id>")
    @auth.login_required
    @require_active_session
    @require_roles("Manager", "Auditor")
    def campaign_detail(campaign_id, *, context):
        identity = identity_from_context(context)
        mark_expired_exceptions()
        campaign = get_campaign(campaign_id)
        if not campaign:
            abort(404)
        items = list_campaign_items(campaign_id)
        write_audit_event(
            identity,
            action="READ_ACCESS_REVIEW_CAMPAIGN",
            object_id=str(campaign_id),
            result="ALLOW",
        )
        return render_template(
            "access_review_dashboard.html",
            identity=identity,
            campaigns=list_campaigns(),
            campaign=campaign,
            items=items,
            today=date.today().isoformat(),
        )

    @blueprint.route("/access-review/campaign/new", methods=["POST"])
    @auth.login_required
    @require_active_session
    @require_roles("Manager")
    def create_campaign_route(*, context):
        require_valid_csrf()
        identity = identity_from_context(context)
        try:
            campaign_id, job_id = create_campaign(
                request.form.get("campaign_name", ""),
                request.form.get("due_date", ""),
                identity["object_id"],
            )
        except (TypeError, ValueError) as error:
            write_audit_event(
                identity,
                action="CREATE_ACCESS_REVIEW_CAMPAIGN",
                object_id="access-review",
                result=f"DENY: {error}",
            )
            flash(str(error), "error")
            return redirect(url_for("access_review.dashboard"))

        write_audit_event(
            identity,
            action="CREATE_ACCESS_REVIEW_CAMPAIGN",
            object_id=str(campaign_id),
            result="ALLOW: inventory queued",
        )
        return redirect(url_for("access_review.job_detail", job_id=job_id))

    @blueprint.route("/access-review/item/<int:item_id>")
    @auth.login_required
    @require_active_session
    @require_roles("Manager", "Auditor")
    def item_detail(item_id, *, context):
        identity = identity_from_context(context)
        item = get_review_item(item_id)
        if not item:
            abort(404)
        write_audit_event(
            identity,
            action="READ_ACCESS_REVIEW_ITEM",
            object_id=str(item_id),
            result="ALLOW",
        )
        return render_template(
            "access_review_item.html",
            identity=identity,
            item=item,
            decisions=get_item_decisions(item_id),
            allowed_roles=sorted(ALLOWED_WORKFORCE_ROLES),
            today=date.today().isoformat(),
        )

    @blueprint.route(
        "/access-review/item/<int:item_id>/decision",
        methods=["POST"],
    )
    @auth.login_required
    @require_active_session
    @require_roles("Manager", "Auditor")
    def submit_decision(item_id, *, context):
        require_valid_csrf()
        identity = identity_from_context(context)
        try:
            _decision_id, plan_job_id = record_decision(
                item_id=item_id,
                decision=request.form.get("decision", ""),
                target_role=request.form.get("target_role") or None,
                reason=request.form.get("reason", ""),
                exception_expiry=(
                    request.form.get("exception_expiry") or None
                ),
                reviewer_object_id=identity["object_id"],
                reviewer_display_name=identity["display_name"],
            )
        except PermissionError as error:
            write_audit_event(
                identity,
                action="SUBMIT_ACCESS_REVIEW_DECISION",
                object_id=str(item_id),
                result=f"DENY: {error}",
            )
            abort(403, description=str(error))
        except (TypeError, ValueError) as error:
            write_audit_event(
                identity,
                action="SUBMIT_ACCESS_REVIEW_DECISION",
                object_id=str(item_id),
                result=f"DENY: {error}",
            )
            flash(str(error), "error")
            return redirect(
                url_for("access_review.item_detail", item_id=item_id)
            )

        write_audit_event(
            identity,
            action="SUBMIT_ACCESS_REVIEW_DECISION",
            object_id=str(item_id),
            result="ALLOW",
        )
        if plan_job_id:
            return redirect(
                url_for("access_review.job_detail", job_id=plan_job_id)
            )
        flash("The access-review decision was recorded.", "success")
        return redirect(url_for("access_review.item_detail", item_id=item_id))

    @blueprint.route("/access-review/job/<job_id>")
    @auth.login_required
    @require_active_session
    @require_roles("Manager", "Auditor")
    def job_detail(job_id, *, context):
        identity = identity_from_context(context)
        job = get_job(job_id)
        if not job:
            abort(404)
        write_audit_event(
            identity,
            action="READ_ACCESS_REVIEW_JOB",
            object_id=job_id,
            result="ALLOW",
        )
        return render_template(
            "access_review_job.html",
            identity=identity,
            job=job,
            events=get_job_events(job_id),
        )

    @blueprint.route("/access-review/job/<job_id>/status")
    @auth.login_required
    @require_active_session
    @require_roles("Manager", "Auditor")
    def job_status(job_id, *, context):
        job = get_job(job_id)
        if not job:
            abort(404)
        return jsonify(
            {
                "job_id": job["job_id"],
                "job_type": job["job_type"],
                "status": job["status"],
                "outcome": job["outcome"],
                "write_operations": job["write_operations"],
                "completed_at": job["completed_at"],
            }
        )

    @blueprint.route(
        "/access-review/job/<job_id>/apply",
        methods=["POST"],
    )
    @auth.login_required
    @require_active_session
    @require_roles("Manager")
    def apply_job(job_id, *, context):
        require_valid_csrf()
        identity = identity_from_context(context)
        try:
            apply_job_id = queue_apply_job(
                plan_job_id=job_id,
                approval_text=request.form.get("approval_text", ""),
                requested_by_object_id=identity["object_id"],
            )
        except (TypeError, ValueError) as error:
            write_audit_event(
                identity,
                action="QUEUE_ACCESS_REVIEW_APPLY",
                object_id=job_id,
                result=f"DENY: {error}",
            )
            flash(str(error), "error")
            return redirect(url_for("access_review.job_detail", job_id=job_id))

        write_audit_event(
            identity,
            action="QUEUE_ACCESS_REVIEW_APPLY",
            object_id=apply_job_id,
            result="ALLOW",
        )
        return redirect(
            url_for("access_review.job_detail", job_id=apply_job_id)
        )

    @blueprint.route(
        "/access-review/campaign/<int:campaign_id>/close",
        methods=["POST"],
    )
    @auth.login_required
    @require_active_session
    @require_roles("Manager")
    def close_campaign_route(campaign_id, *, context):
        require_valid_csrf()
        identity = identity_from_context(context)
        try:
            close_campaign(campaign_id, identity["object_id"])
        except ValueError as error:
            flash(str(error), "error")
            return redirect(
                url_for(
                    "access_review.campaign_detail",
                    campaign_id=campaign_id,
                )
            )

        write_audit_event(
            identity,
            action="CLOSE_ACCESS_REVIEW_CAMPAIGN",
            object_id=str(campaign_id),
            result="ALLOW",
        )
        flash("The access-review campaign was closed.", "success")
        return redirect(url_for("access_review.dashboard"))

    return blueprint
