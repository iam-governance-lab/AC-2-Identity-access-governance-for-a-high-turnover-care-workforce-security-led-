def get_control_enabled(controls, control_id):
    """
    Check whether a security control is enabled.
    """

    for control in controls["controls"]:
        if control["id"] == control_id:
            return control["enabled"]

    return False


def check_mfa_control(path, controls):
    """
    Check whether MFA blocks a password-based attack path.
    """

    mfa_enabled = get_control_enabled(
        controls,
        "CTRL-MFA"
    )

    if mfa_enabled:
        if "nurse_password" in path and "nurse_identity" in path:
            return True, "MFA blocks password-only authentication."

    return False, "MFA does not block this path."


def check_session_timeout_control(path, controls):
    """
    Check whether session timeout blocks reuse of an active session.
    """

    session_enabled = get_control_enabled(
        controls,
        "CTRL-SESSION"
    )

    if session_enabled:
        if "active_nurse_session" in path:
            return True, (
                "Session timeout prevents reuse of "
                "the stale active session."
            )

    return False, "Session timeout does not block this path."


def check_account_disablement_control(path, controls):
    """
    Check whether account disablement blocks a former worker identity.
    """

    account_enabled = get_control_enabled(
        controls,
        "CTRL-ACCOUNT"
    )

    if account_enabled:
        if "former_worker_identity" in path:
            return True, (
                "Account disablement prevents the former worker "
                "identity from authenticating."
            )

    return False, "Account disablement does not block this path."


def check_rbac_control(path, controls):
    """
    Check whether RBAC blocks access through excessive privilege.
    """

    rbac_enabled = get_control_enabled(
        controls,
        "CTRL-RBAC"
    )

    if rbac_enabled:
        if (
            "over_privileged_role" in path
            and "restricted_admin_function" in path
        ):
            return True, (
                "RBAC prevents the care worker identity from "
                "using the restricted administrative function."
            )

    return False, "RBAC does not block this excessive privilege path."


def check_privileged_reauth_control(path, controls):
    """
    Check whether privileged re-authentication blocks
    compromised administrator access.
    """

    privileged_auth_enabled = get_control_enabled(
        controls,
        "CTRL-PRIVAUTH"
    )

    if privileged_auth_enabled:
        if (
            "privileged_admin_identity" in path
            and "admin_console" in path
        ):
            return True, (
                "Privileged re-authentication prevents the "
                "compromised administrator identity from "
                "reaching the restricted admin console."
            )

    return False, (
        "Privileged re-authentication does not block this path."
    )


def check_device_control(path, controls):
    """
    Check whether trusted-device restrictions block
    access from an unmanaged device session.
    """

    device_control_enabled = get_control_enabled(
        controls,
        "CTRL-DEVICE"
    )

    if device_control_enabled:
        if "unmanaged_device_session" in path:
            return True, (
                "Trusted device restriction prevents the "
                "unmanaged device session from accessing "
                "the Sunhaven Care Portal."
            )

    return False, (
        "Trusted device restriction does not block this path."
    )


def assess_control(path, controls, control_id):
    """
    Run the correct security-control simulation.
    """

    if control_id == "CTRL-MFA":
        return check_mfa_control(
            path,
            controls
        )

    if control_id == "CTRL-SESSION":
        return check_session_timeout_control(
            path,
            controls
        )

    if control_id == "CTRL-ACCOUNT":
        return check_account_disablement_control(
            path,
            controls
        )

    if control_id == "CTRL-RBAC":
        return check_rbac_control(
            path,
            controls
        )

    if control_id == "CTRL-PRIVAUTH":
        return check_privileged_reauth_control(
            path,
            controls
        )

    if control_id == "CTRL-DEVICE":
        return check_device_control(
            path,
            controls
        )

    return False, f"No simulation rule exists for {control_id}."