import json


def load_json(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


def find_agency(agencies, agency_id):
    for agency in agencies:
        if agency["agencyId"] == agency_id:
            return agency

    return None


def validate_worker(worker, agencies):
    agency = find_agency(agencies, worker["agencyId"])

    if agency is None:
        return "REJECTED - Agency not found"

    if agency["status"] != "APPROVED":
        return "REJECTED - Agency is not approved"

    email = worker["email"]
    email_domain = email.split("@")[-1]

    if email_domain != agency["domain"]:
        return "REJECTED - Email domain does not match agency"

    return "APPROVED"


def main():
    agency_data = load_json("config/saif-approved-agencies.json")
    worker_data = load_json("data/saif-agency-workers.json")

    agencies = agency_data["agencies"]
    workers = worker_data["workers"]

    print("SAIF Agency Worker Validation")
    print("-----------------------------")

    for worker in workers:
        result = validate_worker(worker, agencies)

        print(
            worker["workerId"],
            worker["displayName"],
            "-",
            result
        )


if __name__ == "__main__":
    main()