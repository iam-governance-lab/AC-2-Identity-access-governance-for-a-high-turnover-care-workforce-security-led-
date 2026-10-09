param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TenantId,

    [ValidateNotNullOrEmpty()]
    [string]$EmployeeId = "SC1008",

    [ValidateSet("CareWorker", "Nurse", "Manager", "AgencyWorker", "Auditor")]
    [string]$ExpectedCurrentRole = "CareWorker",

    [ValidateSet("CareWorker", "Nurse", "Manager", "AgencyWorker", "Auditor")]
    [string]$TargetRole = "Nurse",

    [ValidateNotNullOrEmpty()]
    [string]$TargetFacility = "Sydney",

    [ValidateNotNullOrEmpty()]
    [string]$ApplicationDisplayName = "Sunhaven Care Portal - LAB",

    [ValidateNotNullOrEmpty()]
    [string]$InputPath = "./tests/mover-sc1008-careworker-to-nurse.csv",

    [ValidateNotNullOrEmpty()]
    [string]$DryRunPlanPath = "./evidence/phase5/P5-E31_Mover-Dry-Run-Plan.csv",

    [ValidateNotNullOrEmpty()]
    [string]$GroupMapPath = "./config/group-object-ids.json",

    [ValidateNotNullOrEmpty()]
    [string]$AppRoleMapPath = "./config/app-role-ids.json",

    [ValidateNotNullOrEmpty()]
    [string]$ResultPath = "./evidence/phase5/P5-E35_Mover-Apply-Result.json",

    [switch]$Apply,

    [AllowEmptyString()]
    [string]$ApprovalText = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$roleToGroup = @{
    CareWorker  = "SG-SC-CareWorkers"
    Nurse       = "SG-SC-Nurses"
    Manager     = "SG-SC-Managers"
    AgencyWorker = "SG-SC-AgencyWorkers"
    Auditor     = "SG-SC-Auditors"
}

$script:actionsCompleted = [System.Collections.Generic.List[string]]::new()
$script:writeOperations = 0
$script:userId = $null
$script:userPrincipalName = $null
$script:oldGroupName = $roleToGroup[$ExpectedCurrentRole]
$script:newGroupName = $roleToGroup[$TargetRole]

function Ensure-ParentDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $parentDirectory = Split-Path -Parent $Path

    if ($parentDirectory) {
        New-Item -ItemType Directory -Path $parentDirectory -Force |
            Out-Null
    }
}

function Get-RequiredMapValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Map,

        [Parameter(Mandatory = $true)]
        [string]$Key,

        [Parameter(Mandatory = $true)]
        [string]$MapDescription
    )

    $property = $Map.PSObject.Properties[$Key]

    if (-not $property -or -not $property.Value) {
        throw "$MapDescription does not contain the required key: $Key"
    }

    return [string]$property.Value
}

function Test-DirectGroupMembership {
    param(
        [Parameter(Mandatory = $true)]
        [string]$GroupId,

        [Parameter(Mandatory = $true)]
        [string]$UserId
    )

    $memberIds = @(
        Get-MgGroupMember -GroupId $GroupId -All |
            ForEach-Object {
                $_.Id
            }
    )

    return ($memberIds -contains $UserId)
}

function Save-SanitizedResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Outcome,

        [AllowEmptyString()]
        [string]$ErrorMessage = "",

        [AllowNull()]
        [object]$Verification = $null
    )

    Ensure-ParentDirectory -Path $ResultPath

    $payload = [ordered]@{
        GeneratedUtc                = [datetime]::UtcNow.ToString("o")
        Outcome                     = $Outcome
        EmployeeId                  = $EmployeeId
        UserObjectId                = $script:userId
        UserPrincipalName           = $script:userPrincipalName
        ExpectedCurrentRole         = $ExpectedCurrentRole
        TargetRole                  = $TargetRole
        TargetFacility              = $TargetFacility
        OldGroup                    = $script:oldGroupName
        NewGroup                    = $script:newGroupName
        OldGroupAbsent              = $null
        NewGroupPresent             = $null
        OldAppRoleAbsent            = $null
        NewAppRolePresent           = $null
        AttributesVerified          = $null
        SessionsRevoked             = $null
        ActionsCompleted            = @($script:actionsCompleted)
        WriteOperationsExecuted     = $script:writeOperations
        PasswordRecorded            = $false
        ErrorMessage                = $ErrorMessage
    }

    if ($Verification) {
        $payload.OldGroupAbsent = $Verification.OldGroupAbsent
        $payload.NewGroupPresent = $Verification.NewGroupPresent
        $payload.OldAppRoleAbsent = $Verification.OldAppRoleAbsent
        $payload.NewAppRolePresent = $Verification.NewAppRolePresent
        $payload.AttributesVerified = $Verification.AttributesVerified
        $payload.SessionsRevoked = $Verification.SessionsRevoked
    }

    $payload |
        ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $ResultPath -Encoding utf8
}

foreach ($requiredPath in @(
    $InputPath,
    $DryRunPlanPath,
    $GroupMapPath,
    $AppRoleMapPath
)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required file was not found: $requiredPath"
    }
}

if ($ExpectedCurrentRole -eq $TargetRole) {
    throw "ExpectedCurrentRole and TargetRole must be different."
}

$inputRows = @(
    Import-Csv -LiteralPath $InputPath |
        Where-Object {
            $_.employeeId -eq $EmployeeId
        }
)

if ($inputRows.Count -ne 1) {
    throw (
        "Expected exactly one input row for employeeId $EmployeeId, " +
        "but found $($inputRows.Count)."
    )
}

$inputRow = $inputRows[0]

if ($inputRow.jobRole -ne $TargetRole) {
    throw (
        "Input jobRole does not match TargetRole. " +
        "Input: $($inputRow.jobRole); Target: $TargetRole"
    )
}

if ($inputRow.facility -ne $TargetFacility) {
    throw (
        "Input facility does not match TargetFacility. " +
        "Input: $($inputRow.facility); Target: $TargetFacility"
    )
}

if ($inputRow.status -ne "Active") {
    throw "Mover input status must be Active."
}

$planRows = @(
    Import-Csv -LiteralPath $DryRunPlanPath |
        Where-Object {
            $_.EmployeeId -eq $EmployeeId
        }
)

if ($planRows.Count -ne 1) {
    throw (
        "Expected exactly one dry-run plan row for employeeId " +
        "$EmployeeId, but found $($planRows.Count)."
    )
}

if ($planRows[0].Action -ne "UPDATE") {
    throw (
        "Dry-run plan must classify $EmployeeId as UPDATE. " +
        "Actual action: $($planRows[0].Action)"
    )
}

$groupMap = Get-Content -LiteralPath $GroupMapPath -Raw |
    ConvertFrom-Json

$appRoleMap = Get-Content -LiteralPath $AppRoleMapPath -Raw |
    ConvertFrom-Json

$oldGroupId = Get-RequiredMapValue `
    -Map $groupMap `
    -Key $script:oldGroupName `
    -MapDescription "Group map"

$newGroupId = Get-RequiredMapValue `
    -Map $groupMap `
    -Key $script:newGroupName `
    -MapDescription "Group map"

$oldAppRoleId = [guid](
    Get-RequiredMapValue `
        -Map $appRoleMap `
        -Key $ExpectedCurrentRole `
        -MapDescription "App-role map"
)

$newAppRoleId = [guid](
    Get-RequiredMapValue `
        -Map $appRoleMap `
        -Key $TargetRole `
        -MapDescription "App-role map"
)

$requiredApproval = (
    "MOVE $EmployeeId $ExpectedCurrentRole TO $TargetRole"
)

if (-not $Apply) {
    Write-Host "Sunhaven Mover safety check"
    Write-Host "----------------------------"
    Write-Host "Mode: SAFE - NO APPLY"
    Write-Host "Employee ID: $EmployeeId"
    Write-Host "Expected current role: $ExpectedCurrentRole"
    Write-Host "Target role: $TargetRole"
    Write-Host "Target facility: $TargetFacility"
    Write-Host "Old governed group: $($script:oldGroupName)"
    Write-Host "New governed group: $($script:newGroupName)"
    Write-Host "Dry-run plan action: $($planRows[0].Action)"
    Write-Host "Required approval text: $requiredApproval"
    Write-Host "Planned action order:"
    Write-Host "1. Remove old app role"
    Write-Host "2. Remove old governed group"
    Write-Host "3. Update job and facility attributes"
    Write-Host "4. Add new governed group"
    Write-Host "5. Add new app role"
    Write-Host "6. Revoke sign-in sessions"
    Write-Host "Write operations executed: 0"
    Write-Host "Result: PASS"
    exit 0
}

if ($ApprovalText -cne $requiredApproval) {
    throw (
        "Approval text did not match. Required exact text: " +
        $requiredApproval
    )
}

$requiredCommands = @(
    "Connect-MgGraph",
    "Get-MgContext",
    "Get-MgUser",
    "Update-MgUser",
    "Get-MgGroupMember",
    "Remove-MgGroupMemberByRef",
    "New-MgGroupMemberByRef",
    "Get-MgServicePrincipal",
    "Get-MgUserAppRoleAssignment",
    "Remove-MgUserAppRoleAssignment",
    "New-MgUserAppRoleAssignment",
    "Revoke-MgUserSignInSession"
)

foreach ($commandName in $requiredCommands) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required Microsoft Graph command is missing: $commandName"
    }
}

$newRoleAssignment = $null
$newGroupWasAdded = $false

try {
    Connect-MgGraph `
        -TenantId $TenantId `
        -Scopes @(
            "User.ReadWrite.All",
            "GroupMember.ReadWrite.All",
            "Application.Read.All",
            "AppRoleAssignment.ReadWrite.All",
            "User.RevokeSessions.All"
        ) `
        -NoWelcome

    $graphContext = Get-MgContext

    if (-not $graphContext -or $graphContext.TenantId -ne $TenantId) {
        throw "Authenticated Microsoft Graph tenant did not match TenantId."
    }

    $userProperties = @(
        "id",
        "displayName",
        "userPrincipalName",
        "employeeId",
        "jobTitle",
        "department",
        "officeLocation",
        "accountEnabled"
    )

    $matchingUsers = @(
        Get-MgUser -All -Property $userProperties |
            Where-Object {
                $_.EmployeeId -eq $EmployeeId
            }
    )

    if ($matchingUsers.Count -ne 1) {
        throw (
            "Expected exactly one Entra user with employeeId " +
            "$EmployeeId, but found $($matchingUsers.Count)."
        )
    }

    $user = $matchingUsers[0]
    $script:userId = $user.Id
    $script:userPrincipalName = $user.UserPrincipalName

    $servicePrincipals = @(
        Get-MgServicePrincipal `
            -All `
            -Property "id", "displayName", "appRoles" |
            Where-Object {
                $_.DisplayName -eq $ApplicationDisplayName
            }
    )

    if ($servicePrincipals.Count -ne 1) {
        throw (
            "Expected exactly one service principal named " +
            "'$ApplicationDisplayName', but found " +
            "$($servicePrincipals.Count)."
        )
    }

    $servicePrincipal = $servicePrincipals[0]

    function Get-LiveMoverState {
        $freshUser = Get-MgUser `
            -UserId $script:userId `
            -Property $userProperties

        $managedGroups = @()

        foreach ($groupName in @($roleToGroup.Values | Sort-Object -Unique)) {
            $groupId = Get-RequiredMapValue `
                -Map $groupMap `
                -Key $groupName `
                -MapDescription "Group map"

            if (
                Test-DirectGroupMembership `
                    -GroupId $groupId `
                    -UserId $script:userId
            ) {
                $managedGroups += $groupName
            }
        }

        $careAssignments = @(
            Get-MgUserAppRoleAssignment `
                -UserId $script:userId `
                -All |
                Where-Object {
                    [string]$_.ResourceId -eq [string]$servicePrincipal.Id
                }
        )

        $oldAssignments = @(
            $careAssignments |
                Where-Object {
                    [string]$_.AppRoleId -eq [string]$oldAppRoleId
                }
        )

        $newAssignments = @(
            $careAssignments |
                Where-Object {
                    [string]$_.AppRoleId -eq [string]$newAppRoleId
                }
        )

        return [pscustomobject]@{
            User                         = $freshUser
            ManagedGroups                = @($managedGroups)
            CareAssignments              = @($careAssignments)
            OldRoleAssignments           = @($oldAssignments)
            NewRoleAssignments           = @($newAssignments)
            OldGroupPresent              = (
                $managedGroups -contains $script:oldGroupName
            )
            NewGroupPresent              = (
                $managedGroups -contains $script:newGroupName
            )
            AttributesVerified           = (
                $freshUser.JobTitle -eq $TargetRole -and
                $freshUser.Department -eq $TargetFacility -and
                $freshUser.OfficeLocation -eq $TargetFacility
            )
        }
    }

    function Wait-ForMoverState {
        param(
            [Parameter(Mandatory = $true)]
            [scriptblock]$Condition,

            [Parameter(Mandatory = $true)]
            [string]$Description,

            [int]$MaximumAttempts = 6,

            [int]$DelaySeconds = 3
        )

        for (
            $attempt = 1;
            $attempt -le $MaximumAttempts;
            $attempt++
        ) {
            $readbackState = Get-LiveMoverState

            if ([bool](& $Condition $readbackState)) {
                Write-Host "$Description readback: PASS"
                return $readbackState
            }

            if ($attempt -lt $MaximumAttempts) {
                Write-Host (
                    "$Description readback is pending. " +
                    "Attempt $attempt of $MaximumAttempts."
                ) -ForegroundColor Yellow

                Start-Sleep -Seconds $DelaySeconds
            }
        }

        throw "$Description readback verification failed."
    }

    $initialState = Get-LiveMoverState

    $alreadyDesired = (
        -not $initialState.OldGroupPresent -and
        $initialState.NewGroupPresent -and
        $initialState.OldRoleAssignments.Count -eq 0 -and
        $initialState.NewRoleAssignments.Count -eq 1 -and
        $initialState.CareAssignments.Count -eq 1 -and
        $initialState.AttributesVerified
    )

    if ($alreadyDesired) {
        $verification = [pscustomobject]@{
            OldGroupAbsent      = $true
            NewGroupPresent     = $true
            OldAppRoleAbsent    = $true
            NewAppRolePresent   = $true
            AttributesVerified  = $true
            SessionsRevoked     = $false
        }

        Save-SanitizedResult `
            -Outcome "NO CHANGE" `
            -Verification $verification

        Write-Host "Outcome: NO CHANGE"
        Write-Host "Write operations executed: 0"
        exit 0
    }

    $unexpectedManagedGroups = @(
        $initialState.ManagedGroups |
            Where-Object {
                $_ -ne $script:oldGroupName
            }
    )

    $baselineValid = (
        $initialState.User.AccountEnabled -eq $true -and
        $initialState.User.JobTitle -eq $ExpectedCurrentRole -and
        $initialState.User.Department -eq $TargetFacility -and
        $initialState.User.OfficeLocation -eq $TargetFacility -and
        $initialState.OldGroupPresent -and
        -not $initialState.NewGroupPresent -and
        $unexpectedManagedGroups.Count -eq 0 -and
        $initialState.OldRoleAssignments.Count -eq 1 -and
        $initialState.NewRoleAssignments.Count -eq 0 -and
        $initialState.CareAssignments.Count -eq 1
    )

    if (-not $baselineValid) {
        $verification = [pscustomobject]@{
            OldGroupAbsent      = (-not $initialState.OldGroupPresent)
            NewGroupPresent     = $initialState.NewGroupPresent
            OldAppRoleAbsent    = (
                $initialState.OldRoleAssignments.Count -eq 0
            )
            NewAppRolePresent   = (
                $initialState.NewRoleAssignments.Count -eq 1
            )
            AttributesVerified  = $initialState.AttributesVerified
            SessionsRevoked     = $false
        }

        Save-SanitizedResult `
            -Outcome "BLOCKED" `
            -ErrorMessage (
                "Live state did not match either the approved " +
                "CareWorker baseline or the complete Nurse target state."
            ) `
            -Verification $verification

        Write-Host "Outcome: BLOCKED"
        Write-Host "Reason: Unexpected live state; no writes attempted."
        Write-Host "Write operations executed: 0"
        exit 2
    }

    $oldRoleAssignmentId = $initialState.OldRoleAssignments[0].Id

    Remove-MgUserAppRoleAssignment `
        -UserId $script:userId `
        -AppRoleAssignmentId $oldRoleAssignmentId `
        -Confirm:$false

    $script:writeOperations++
    $script:actionsCompleted.Add("REMOVE_OLD_APP_ROLE")

    $null = Wait-ForMoverState `
        -Description "Old application role removal" `
        -Condition {
            param($state)

            return $state.OldRoleAssignments.Count -eq 0
        }

    Remove-MgGroupMemberByRef `
        -GroupId $oldGroupId `
        -DirectoryObjectId $script:userId `
        -Confirm:$false

    $script:writeOperations++
    $script:actionsCompleted.Add("REMOVE_OLD_GROUP")

    $null = Wait-ForMoverState `
        -Description "Old group removal" `
        -Condition {
            param($state)

            return -not $state.OldGroupPresent
        }

    Update-MgUser `
        -UserId $script:userId `
        -BodyParameter @{
            jobTitle      = $TargetRole
            department    = $TargetFacility
            officeLocation = $TargetFacility
        }

    $script:writeOperations++
    $script:actionsCompleted.Add("UPDATE_USER_ATTRIBUTES")

    $null = Wait-ForMoverState `
        -Description "User attribute update" `
        -Condition {
            param($state)

            return $state.AttributesVerified
        }

    New-MgGroupMemberByRef `
        -GroupId $newGroupId `
        -BodyParameter @{
            "@odata.id" = (
                "https://graph.microsoft.com/v1.0/" +
                "directoryObjects/$($script:userId)"
            )
        }

    $newGroupWasAdded = $true
    $script:writeOperations++
    $script:actionsCompleted.Add("ADD_NEW_GROUP")

    $null = Wait-ForMoverState `
        -Description "New group assignment" `
        -Condition {
            param($state)

            return $state.NewGroupPresent
        }

    $newRoleAssignment = New-MgUserAppRoleAssignment `
        -UserId $script:userId `
        -BodyParameter @{
            principalId = [guid]$script:userId
            resourceId  = [guid]$servicePrincipal.Id
            appRoleId   = $newAppRoleId
        }

    $script:writeOperations++
    $script:actionsCompleted.Add("ADD_NEW_APP_ROLE")

    $null = Wait-ForMoverState `
        -Description "New application role assignment" `
        -Condition {
            param($state)

            return (
                $state.NewRoleAssignments.Count -eq 1 -and
                $state.CareAssignments.Count -eq 1
            )
        }

    $null = Revoke-MgUserSignInSession `
        -UserId $script:userId `
        -Confirm:$false

    $script:writeOperations++
    $script:actionsCompleted.Add("REVOKE_SIGN_IN_SESSIONS")

    $finalState = $null

    foreach ($attempt in 1..6) {
        Start-Sleep -Seconds 5
        $finalState = Get-LiveMoverState

        $verified = (
            -not $finalState.OldGroupPresent -and
            $finalState.NewGroupPresent -and
            $finalState.OldRoleAssignments.Count -eq 0 -and
            $finalState.NewRoleAssignments.Count -eq 1 -and
            $finalState.CareAssignments.Count -eq 1 -and
            $finalState.AttributesVerified
        )

        if ($verified) {
            break
        }
    }

    $verification = [pscustomobject]@{
        OldGroupAbsent      = (-not $finalState.OldGroupPresent)
        NewGroupPresent     = $finalState.NewGroupPresent
        OldAppRoleAbsent    = (
            $finalState.OldRoleAssignments.Count -eq 0
        )
        NewAppRolePresent   = (
            $finalState.NewRoleAssignments.Count -eq 1
        )
        AttributesVerified  = $finalState.AttributesVerified
        SessionsRevoked     = $true
    }

    $finalVerified = (
        $verification.OldGroupAbsent -and
        $verification.NewGroupPresent -and
        $verification.OldAppRoleAbsent -and
        $verification.NewAppRolePresent -and
        $verification.AttributesVerified
    )

    if (-not $finalVerified) {
        throw "Final Mover verification did not reach the approved target state."
    }

    Save-SanitizedResult `
        -Outcome "MOVED" `
        -Verification $verification

    Write-Host "Outcome: MOVED"
    Write-Host "Employee ID: $EmployeeId"
    Write-Host "User Object ID: $($script:userId)"
    Write-Host "Old role removed: True"
    Write-Host "New role verified: True"
    Write-Host "Sessions revoked: True"
    Write-Host "Write operations executed: $($script:writeOperations)"
    exit 0
}
catch {
    $originalError = $_.Exception.Message
    $cleanupMessages = @()

    if ($newRoleAssignment -and $newRoleAssignment.Id) {
        try {
            Remove-MgUserAppRoleAssignment `
                -UserId $script:userId `
                -AppRoleAssignmentId $newRoleAssignment.Id `
                -Confirm:$false

            $script:writeOperations++
            $script:actionsCompleted.Add("CLEANUP_NEW_APP_ROLE")
        }
        catch {
            $cleanupMessages += (
                "Could not clean up new app role: " +
                $_.Exception.Message
            )
        }
    }

    if ($newGroupWasAdded) {
        try {
            Remove-MgGroupMemberByRef `
                -GroupId $newGroupId `
                -DirectoryObjectId $script:userId `
                -Confirm:$false

            $script:writeOperations++
            $script:actionsCompleted.Add("CLEANUP_NEW_GROUP")
        }
        catch {
            $cleanupMessages += (
                "Could not clean up new group: " +
                $_.Exception.Message
            )
        }
    }

    $combinedError = $originalError

    if ($cleanupMessages.Count -gt 0) {
        $combinedError += " Cleanup warnings: " + (
            $cleanupMessages -join " | "
        )
    }

    Save-SanitizedResult `
        -Outcome "FAILED" `
        -ErrorMessage $combinedError

    Write-Host "Outcome: FAILED"
    Write-Host "Error: $combinedError"
    Write-Host "Write operations executed: $($script:writeOperations)"
    exit 1
}
