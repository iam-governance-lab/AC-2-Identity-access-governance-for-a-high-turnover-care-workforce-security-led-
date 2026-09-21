def create_identity_mapping(worker, entra_user_id):
    mapping = {
        "workerId": worker["workerId"],
        "agencyId": worker["agencyId"],
        "externalEmail": worker["email"],
        "entraUserId": entra_user_id
    }

    return mapping