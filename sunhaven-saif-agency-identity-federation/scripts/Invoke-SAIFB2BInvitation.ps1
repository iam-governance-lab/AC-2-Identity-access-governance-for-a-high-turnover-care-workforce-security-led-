param(
    [Parameter(Mandatory=$true)]
    [string]$Email,

    [Parameter(Mandatory=$true)]
    [string]$DisplayName
)

$redirectUrl = "https://myapplications.microsoft.com"

$context = Get-MgContext

if ($null -eq $context) {
    Write-Host "SAIF ERROR: Microsoft Graph is not connected."
    exit 1
}

Write-Host "SAIF: Sending B2B invitation for $DisplayName"

try {
    $invitation = New-MgInvitation `
        -InvitedUserDisplayName $DisplayName `
        -InvitedUserEmailAddress $Email `
        -InviteRedirectUrl $redirectUrl `
        -SendInvitationMessage:$true `
        -ErrorAction Stop

    Write-Host "SAIF: B2B invitation created successfully."
    Write-Host "Invitation ID:" $invitation.Id
    Write-Host "Entra User ID:" $invitation.InvitedUser.Id
    $result = @{
    invitationId = $invitation.Id
    entraUserId = $invitation.InvitedUser.Id
}

$result | ConvertTo-Json
}
catch {
    Write-Host "SAIF ERROR: B2B invitation failed."
    Write-Host "Reason:" $_.Exception.Message
    exit 1
}