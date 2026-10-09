from uuid import UUID

from database import (
    block_user,
    get_blocked_user,
    initialize_database,
    unblock_user,
)


def read_object_id():
    object_id = input(
        "Paste the TEST user's Entra Object ID: "
    ).strip()

    try:
        UUID(object_id)
    except ValueError:
        raise SystemExit(
            "STOP: The Object ID must be a valid UUID."
        )

    return object_id


def show_status(object_id):
    record = get_blocked_user(object_id)

    if not record:
        print("No local application block record exists.")
        return

    print(f"Object ID: {record['user_object_id']}")
    print(f"Active block: {bool(record['active'])}")
    print(f"Blocked at: {record['blocked_at']}")
    print(f"Blocked by: {record['blocked_by']}")
    print(f"Reason: {record['reason']}")
    print(f"Unblocked at: {record['unblocked_at']}")
    print(f"Unblocked by: {record['unblocked_by']}")


def main():
    initialize_database()

    operation = input(
        "Enter operation (status, block or unblock): "
    ).strip().lower()

    if operation not in {"status", "block", "unblock"}:
        raise SystemExit(
            "STOP: Enter exactly status, block or unblock."
        )

    object_id = read_object_id()

    if operation == "status":
        show_status(object_id)
        return

    if operation == "block":
        reason = input(
            "Enter block reason: "
        ).strip()

        if not reason:
            raise SystemExit(
                "STOP: A block reason is required."
            )

        confirmation = input(
            "Type BLOCK to confirm: "
        ).strip()

        if confirmation != "BLOCK":
            raise SystemExit(
                "Cancelled: confirmation did not match."
            )

        block_user(
            object_id,
            blocked_by="LOCAL-IAM-ADMIN",
            reason=reason,
        )

        print("Local application access is now blocked.")
        show_status(object_id)
        return

    confirmation = input(
        "Type UNBLOCK to confirm: "
    ).strip()

    if confirmation != "UNBLOCK":
        raise SystemExit(
            "Cancelled: confirmation did not match."
        )

    changed = unblock_user(
        object_id,
        unblocked_by="LOCAL-IAM-ADMIN",
    )

    if changed:
        print("Local application block removed.")
    else:
        print("No active block was found.")

    show_status(object_id)


if __name__ == "__main__":
    main()