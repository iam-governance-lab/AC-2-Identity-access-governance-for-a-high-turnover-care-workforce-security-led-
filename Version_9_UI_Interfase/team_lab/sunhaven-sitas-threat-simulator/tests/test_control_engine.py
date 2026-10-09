import pytest

from control_engine import assess_control


def make_controls(
    mfa=False,
    session=False,
    account=False,
    rbac=False,
    privauth=False,
    device=False
):
    """
    Create a control configuration for automated testing.
    """

    return {
        "controls": [
            {
                "id": "CTRL-MFA",
                "enabled": mfa
            },
            {
                "id": "CTRL-SESSION",
                "enabled": session
            },
            {
                "id": "CTRL-ACCOUNT",
                "enabled": account
            },
            {
                "id": "CTRL-RBAC",
                "enabled": rbac
            },
            {
                "id": "CTRL-PRIVAUTH",
                "enabled": privauth
            },
            {
                "id": "CTRL-DEVICE",
                "enabled": device
            }
        ]
    }


def test_mfa_off_keeps_path_open():
    """
    Scenario 1 should remain open when MFA is disabled.
    """

    path = [
        "external_attacker",
        "nurse_password",
        "nurse_identity",
        "shared_workstation",
        "care_portal",
        "resident_records"
    ]

    controls = make_controls(
        mfa=False
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-MFA"
    )

    assert blocked is False
    assert "does not block" in reason


def test_mfa_on_blocks_path():
    """
    Scenario 1 should be blocked when MFA is enabled.
    """

    path = [
        "external_attacker",
        "nurse_password",
        "nurse_identity",
        "shared_workstation",
        "care_portal",
        "resident_records"
    ]

    controls = make_controls(
        mfa=True
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-MFA"
    )

    assert blocked is True
    assert "MFA blocks" in reason


def test_session_timeout_off_keeps_path_open():
    """
    Scenario 2 should remain open when Session Timeout is disabled.
    """

    path = [
        "unauthorised_person",
        "unattended_workstation",
        "active_nurse_session",
        "care_portal",
        "resident_records"
    ]

    controls = make_controls(
        session=False
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-SESSION"
    )

    assert blocked is False
    assert "does not block" in reason


def test_session_timeout_on_blocks_path():
    """
    Scenario 2 should be blocked when Session Timeout is enabled.
    """

    path = [
        "unauthorised_person",
        "unattended_workstation",
        "active_nurse_session",
        "care_portal",
        "resident_records"
    ]

    controls = make_controls(
        session=True
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-SESSION"
    )

    assert blocked is True
    assert "Session timeout" in reason


def test_account_disablement_off_keeps_path_open():
    """
    Scenario 3 should remain open when Account Disablement is disabled.
    """

    path = [
        "former_worker",
        "former_worker_identity",
        "care_portal",
        "resident_records"
    ]

    controls = make_controls(
        account=False
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-ACCOUNT"
    )

    assert blocked is False
    assert "does not block" in reason


def test_account_disablement_on_blocks_path():
    """
    Scenario 3 should be blocked when Account Disablement is enabled.
    """

    path = [
        "former_worker",
        "former_worker_identity",
        "care_portal",
        "resident_records"
    ]

    controls = make_controls(
        account=True
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-ACCOUNT"
    )

    assert blocked is True
    assert "Account disablement" in reason


def test_rbac_off_keeps_path_open():
    """
    Scenario 4 should remain open when RBAC is disabled.
    """

    path = [
        "compromised_care_worker",
        "care_worker_identity",
        "over_privileged_role",
        "restricted_admin_function",
        "resident_records"
    ]

    controls = make_controls(
        rbac=False
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-RBAC"
    )

    assert blocked is False
    assert "does not block" in reason


def test_rbac_on_blocks_path():
    """
    Scenario 4 should be blocked when RBAC is enabled.
    """

    path = [
        "compromised_care_worker",
        "care_worker_identity",
        "over_privileged_role",
        "restricted_admin_function",
        "resident_records"
    ]

    controls = make_controls(
        rbac=True
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-RBAC"
    )

    assert blocked is True
    assert "RBAC prevents" in reason


def test_privileged_reauth_off_keeps_path_open():
    """
    Scenario 5 should remain open when privileged
    re-authentication is disabled.
    """

    path = [
        "admin_attacker",
        "stolen_admin_credential",
        "privileged_admin_identity",
        "admin_console",
        "resident_records"
    ]

    controls = make_controls(
        privauth=False
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-PRIVAUTH"
    )

    assert blocked is False
    assert "does not block" in reason


def test_privileged_reauth_on_blocks_path():
    """
    Scenario 5 should be blocked when privileged
    re-authentication is enabled.
    """

    path = [
        "admin_attacker",
        "stolen_admin_credential",
        "privileged_admin_identity",
        "admin_console",
        "resident_records"
    ]

    controls = make_controls(
        privauth=True
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-PRIVAUTH"
    )

    assert blocked is True
    assert "Privileged re-authentication" in reason


def test_device_control_off_keeps_path_open():
    """
    Scenario 6 should remain open when trusted-device
    restriction is disabled.
    """

    path = [
        "device_attacker",
        "stolen_care_worker_credential",
        "remote_care_worker_identity",
        "unmanaged_device_session",
        "care_portal",
        "resident_records"
    ]

    controls = make_controls(
        device=False
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-DEVICE"
    )

    assert blocked is False
    assert "does not block" in reason


def test_device_control_on_blocks_path():
    """
    Scenario 6 should be blocked when trusted-device
    restriction is enabled.
    """

    path = [
        "device_attacker",
        "stolen_care_worker_credential",
        "remote_care_worker_identity",
        "unmanaged_device_session",
        "care_portal",
        "resident_records"
    ]

    controls = make_controls(
        device=True
    )

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-DEVICE"
    )

    assert blocked is True
    assert "Trusted device restriction" in reason


def test_unknown_control_does_not_block():
    """
    An unknown control should not block an attack path.
    """

    path = [
        "attacker",
        "asset"
    ]

    controls = make_controls()

    blocked, reason = assess_control(
        path,
        controls,
        "CTRL-UNKNOWN"
    )

    assert blocked is False
    assert "No simulation rule exists" in reason
