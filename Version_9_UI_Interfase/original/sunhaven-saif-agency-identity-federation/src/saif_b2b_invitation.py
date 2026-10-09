def prepare_invitation(worker, redirect_url):
    invitation = {
        "invitedUserEmailAddress": worker["email"],
        "invitedUserDisplayName": worker["displayName"],
        "inviteRedirectUrl": redirect_url,
        "sendInvitationMessage": True
    }

    return invitation