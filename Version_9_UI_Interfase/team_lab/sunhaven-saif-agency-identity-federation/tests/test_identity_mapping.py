from src.saif_identity_mapping import create_identity_mapping


def test_create_identity_mapping():
    worker = {
        "workerId": "EXT001",
        "displayName": "Sarah Khan",
        "email": "sarah@sydneycare.example",
        "agencyId": "AG001"
    }

    entra_user_id = "test-entra-user-id"

    mapping = create_identity_mapping(worker, entra_user_id)

    assert mapping["workerId"] == "EXT001"
    assert mapping["agencyId"] == "AG001"
    assert mapping["externalEmail"] == "sarah@sydneycare.example"
    assert mapping["entraUserId"] == "test-entra-user-id"