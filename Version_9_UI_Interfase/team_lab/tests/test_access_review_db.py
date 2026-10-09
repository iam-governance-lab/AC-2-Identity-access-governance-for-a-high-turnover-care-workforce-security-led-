import csv
import sqlite3
from datetime import date, timedelta

import pytest

import access_review_db as review_db


@pytest.fixture()
def temporary_database(tmp_path, monkeypatch):
    database_path = tmp_path / "test-sunhaven.db"

    def connection_factory():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(review_db, "get_connection", connection_factory)
    review_db.initialize_access_review_database()
    return tmp_path


def write_inventory(path):
    fields = [
        "CapturedUtc",
        "EmployeeId",
        "DisplayName",
        "UserPrincipalName",
        "ObjectId",
        "AccountEnabled",
        "JobRole",
        "Facility",
        "GovernedGroups",
        "CareAppRoles",
        "WriteOperationsExecuted",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "CapturedUtc": "2026-09-19T10:00:00+00:00",
                "EmployeeId": "SC2001",
                "DisplayName": "Jordan Lee TEST",
                "UserPrincipalName": "jordan.lee.test@example.invalid",
                "ObjectId": "11111111-1111-1111-1111-111111111111",
                "AccountEnabled": "True",
                "JobRole": "CareWorker",
                "Facility": "Sydney",
                "GovernedGroups": "SG-SC-CareWorkers",
                "CareAppRoles": "CareWorker",
                "WriteOperationsExecuted": "0",
            }
        )


def create_open_campaign(tmp_path):
    campaign_id, inventory_job_id = review_db.create_campaign(
        "TEST campaign",
        (date.today() + timedelta(days=7)).isoformat(),
        "manager-object-id",
    )
    job = review_db.claim_next_job()
    assert job["job_id"] == inventory_job_id

    inventory_path = tmp_path / "inventory.csv"
    write_inventory(inventory_path)
    result = review_db.import_inventory_csv(campaign_id, inventory_path)
    review_db.finish_job(
        job_id=inventory_job_id,
        status="SUCCEEDED",
        outcome="INVENTORY_IMPORTED",
        write_operations=0,
        result=result,
    )
    item = review_db.list_campaign_items(campaign_id)[0]
    return campaign_id, item


def test_retain_requires_no_background_job(temporary_database):
    _campaign_id, item = create_open_campaign(temporary_database)
    _decision_id, plan_job_id = review_db.record_decision(
        item_id=item["item_id"],
        decision="RETAIN",
        target_role=None,
        reason="Current CareWorker access remains required.",
        exception_expiry=None,
        reviewer_object_id="manager-object-id",
        reviewer_display_name="Manager TEST",
    )
    assert plan_job_id is None
    updated = review_db.get_review_item(item["item_id"])
    assert updated["remediation_status"] == "NOT_REQUIRED"


def test_change_requires_plan_before_exact_apply(temporary_database):
    _campaign_id, item = create_open_campaign(temporary_database)
    _decision_id, plan_job_id = review_db.record_decision(
        item_id=item["item_id"],
        decision="CHANGE",
        target_role="Nurse",
        reason="The worker transferred to the nursing team.",
        exception_expiry=None,
        reviewer_object_id="manager-object-id",
        reviewer_display_name="Manager TEST",
    )
    claimed = review_db.claim_next_job()
    assert claimed["job_id"] == plan_job_id
    review_db.finish_job(
        job_id=plan_job_id,
        status="SUCCEEDED",
        outcome="PLANNED",
        write_operations=0,
        result={"Outcome": "PLANNED"},
        required_approval="MOVE SC2001 CareWorker TO Nurse",
    )

    with pytest.raises(ValueError, match="did not match"):
        review_db.queue_apply_job(
            plan_job_id=plan_job_id,
            approval_text="MOVE WRONG USER",
            requested_by_object_id="manager-object-id",
        )

    apply_job_id = review_db.queue_apply_job(
        plan_job_id=plan_job_id,
        approval_text="MOVE SC2001 CareWorker TO Nurse",
        requested_by_object_id="manager-object-id",
    )
    assert review_db.get_job(apply_job_id)["status"] == "QUEUED"


def test_self_review_is_denied(temporary_database):
    _campaign_id, item = create_open_campaign(temporary_database)
    with pytest.raises(PermissionError, match="own access"):
        review_db.record_decision(
            item_id=item["item_id"],
            decision="RETAIN",
            target_role=None,
            reason="Attempting to retain my own current access.",
            exception_expiry=None,
            reviewer_object_id=item["user_object_id"],
            reviewer_display_name="Jordan Lee TEST",
        )


def test_exception_requires_future_expiry(temporary_database):
    _campaign_id, item = create_open_campaign(temporary_database)
    with pytest.raises(ValueError, match="future"):
        review_db.record_decision(
            item_id=item["item_id"],
            decision="TEMPORARY_EXCEPTION",
            target_role=None,
            reason="Short exception requested for a documented shift.",
            exception_expiry=date.today().isoformat(),
            reviewer_object_id="manager-object-id",
            reviewer_display_name="Manager TEST",
        )
