from src.saif_agency_validation import validate_worker


agencies = [
    {
        "agencyId": "AG001",
        "agencyName": "Sydney Care Staffing",
        "domain": "sydneycare.example",
        "status": "APPROVED"
    },
    {
        "agencyId": "AG003",
        "agencyName": "Unknown Care Staffing",
        "domain": "unknowncare.example",
        "status": "BLOCKED"
    }
]


def test_approved_worker():
    worker = {
        "workerId": "EXT001",
        "displayName": "Sarah Khan",
        "email": "sarah@sydneycare.example",
        "agencyId": "AG001"
    }

    result = validate_worker(worker, agencies)
    assert result == "APPROVED"


def test_blocked_agency():
    worker = {
        "workerId": "EXT002",
        "displayName": "Test Worker",
        "email": "worker@unknowncare.example",
        "agencyId": "AG003"
    }

    result = validate_worker(worker, agencies)
    assert result == "REJECTED - Agency is not approved"


def test_wrong_domain():
    worker = {
        "workerId": "EXT003",
        "displayName": "Test Worker",
        "email": "worker@random.example",
        "agencyId": "AG001"
    }

    result = validate_worker(worker, agencies)
    assert result == "REJECTED - Email domain does not match agency"


def test_unknown_agency():
    worker = {
        "workerId": "EXT004",
        "displayName": "Test Worker",
        "email": "worker@test.example",
        "agencyId": "AG999"
    }

    result = validate_worker(worker, agencies)
    assert result == "REJECTED - Agency not found"


def test_missing_agency_id():
    worker = {
        "workerId": "EXT005",
        "displayName": "Test Worker",
        "email": "worker@sydneycare.example"
    }

    result = validate_worker(worker, agencies)
    assert result == "REJECTED - Agency ID is missing"


def test_invalid_email():
    worker = {
        "workerId": "EXT006",
        "displayName": "Test Worker",
        "email": "invalid-email",
        "agencyId": "AG001"
    }

    result = validate_worker(worker, agencies)
    assert result == "REJECTED - Invalid email address"