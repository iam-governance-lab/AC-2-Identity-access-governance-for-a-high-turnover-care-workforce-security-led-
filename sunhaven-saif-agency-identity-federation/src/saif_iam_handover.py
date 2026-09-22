def create_iam_handover(identity_mapping):
    handover = {
        "workerId": identity_mapping["workerId"],
        "agencyId": identity_mapping["agencyId"],
        "externalEmail": identity_mapping["externalEmail"],
        "entraUserId": identity_mapping["entraUserId"],
        "handoverTarget": "Existing Sunhaven IAM",
        "requestedRole": "AgencyWorker"
    }

    return handover