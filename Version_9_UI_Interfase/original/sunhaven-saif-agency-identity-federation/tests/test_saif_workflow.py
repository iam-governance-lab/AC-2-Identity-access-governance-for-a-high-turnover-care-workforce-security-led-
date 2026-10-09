from src.saif_workflow import process_external_worker


def fake_invitation_sender(email, display_name, script_path):
    return {
        "invitationId": "test-invitation-id",
        "entraUserId": "test-entra-user-id"
    }


def test_approved_worker_complete_workflow():
    agencies = [
        {
            "agencyId": "AG001",
            "agencyName": "Sydney Care Staffing",
            "domain": "sydneycare.example",
            "status": "APPROVED"
        }
    ]

    worker = {
        "workerId": "EXT001",
        "displayName": "Sarah Khan",
        "email": "sarah@sydneycare.example",
        "agencyId": "AG001"
    }

    result = process_external_worker(
        worker,
        agencies,
        "https://myapplications.microsoft.com",
        "test-script.ps1",
        fake_invitation_sender
    )

    assert result["status"] == "APPROVED"
    assert result["invitationId"] == "test-invitation-id"

    mapping = result["identityMapping"]

    assert mapping["workerId"] == "EXT001"
    assert mapping["agencyId"] == "AG001"
    assert mapping["externalEmail"] == "sarah@sydneycare.example"
    assert mapping["entraUserId"] == "test-entra-user-id"
    
    handover = result["iamHandover"]

    assert handover["workerId"] == "EXT001"
    assert handover["agencyId"] == "AG001"
    assert handover["externalEmail"] == "sarah@sydneycare.example"
    assert handover["entraUserId"] == "test-entra-user-id"
    assert handover["handoverTarget"] == "Existing Sunhaven IAM"
    assert handover["requestedRole"] == "AgencyWorker"


def test_blocked_worker_stops_before_invitation():
    agencies = [
        {
            "agencyId": "AG003",
            "agencyName": "Unknown Care Staffing",
            "domain": "unknowncare.example",
            "status": "BLOCKED"
        }
    ]

    worker = {
        "workerId": "EXT003",
        "displayName": "Blocked Worker",
        "email": "blocked@unknowncare.example",
        "agencyId": "AG003"
    }

    sender_called = False

    def fake_sender(email, display_name, script_path):
        nonlocal sender_called
        sender_called = True

        return {
            "invitationId": "should-not-exist",
            "entraUserId": "should-not-exist"
        }

    result = process_external_worker(
        worker,
        agencies,
        "https://myapplications.microsoft.com",
        "test-script.ps1",
        fake_sender
    )

    assert result != "APPROVED"
    assert sender_called is False