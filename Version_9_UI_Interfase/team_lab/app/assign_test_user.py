from datetime import date

from database import get_connection, initialize_database


ROLE_RESIDENTS = {
    "CareWorker": [
        "RES-TEST-001",
        "RES-TEST-002",
    ],
    "AgencyWorker": [
        "RES-TEST-003",
    ],
}


def main():
    initialize_database()

    object_id = input(
        "Paste the TEST user's Entra object_id: "
    ).strip()

    role = input(
        "Enter CareWorker or AgencyWorker: "
    ).strip()

    if not object_id:
        raise SystemExit(
            "STOP: The object_id cannot be blank."
        )

    resident_ids = ROLE_RESIDENTS.get(role)

    if not resident_ids:
        raise SystemExit(
            "STOP: Enter exactly CareWorker or AgencyWorker."
        )

    with get_connection() as connection:
        for resident_id in resident_ids:
            connection.execute(
                """
                INSERT INTO assignments (
                    resident_id,
                    user_object_id,
                    assignment_role,
                    start_date,
                    end_date,
                    active
                )
                VALUES (?, ?, ?, ?, NULL, 1)
                ON CONFLICT (resident_id, user_object_id)
                DO UPDATE SET
                    assignment_role = excluded.assignment_role,
                    start_date = excluded.start_date,
                    end_date = NULL,
                    active = 1
                """,
                (
                    resident_id,
                    object_id,
                    role,
                    date.today().isoformat(),
                ),
            )

    print(
        f"Assigned {len(resident_ids)} TEST resident(s) "
        f"to role {role}."
    )


if __name__ == "__main__":
    main()