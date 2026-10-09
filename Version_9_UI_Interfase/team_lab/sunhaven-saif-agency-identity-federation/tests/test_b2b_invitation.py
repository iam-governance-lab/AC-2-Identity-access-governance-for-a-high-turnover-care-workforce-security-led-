from src.saif_b2b_invitation import prepare_invitation


def test_prepare_invitation():
    worker = {
        "workerId": "EXT001",
        "displayName": "Sarah Khan",
        "email": "sarah@sydneycare.example",
        "agencyId": "AG001"
    }

    redirect_url = "https://myapplications.microsoft.com"

    invitation = prepare_invitation(worker, redirect_url)

    assert invitation["invitedUserEmailAddress"] == "sarah@sydneycare.example"
    assert invitation["invitedUserDisplayName"] == "Sarah Khan"
    assert invitation["inviteRedirectUrl"] == redirect_url
    assert invitation["sendInvitationMessage"] is True