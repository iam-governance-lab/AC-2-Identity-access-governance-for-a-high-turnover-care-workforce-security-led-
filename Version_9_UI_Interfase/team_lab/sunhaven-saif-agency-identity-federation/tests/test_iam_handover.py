from src.saif_iam_handover import create_iam_handover


def test_create_iam_handover():
    identity_mapping = {
        "workerId": "EXT001",
        "agencyId": "AG001",
        "externalEmail": "sarah@sydneycare.example",
        "entraUserId": "test-entra-user-id"
    }

    handover = create_iam_handover(identity_mapping)

    assert handover["workerId"] == "EXT001"
    assert handover["agencyId"] == "AG001"
    assert handover["externalEmail"] == "sarah@sydneycare.example"
    assert handover["entraUserId"] == "test-entra-user-id"
    assert handover["handoverTarget"] == "Existing Sunhaven IAM"
    assert handover["requestedRole"] == "AgencyWorker"