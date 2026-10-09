[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TenantId,

    [ValidateNotNullOrEmpty()]
    [string]$EmployeeId = "SC1008",

    [ValidateSet("CareWorker", "Nurse", "Manager", "AgencyWorker", "Auditor")]
    [string]$ExpectedCurrentRole = "Nurse",

    [ValidateNotNullOrEmpty()]
    [string]$ApplicationDisplayName = "Sunhaven Care Portal - LAB",

    [ValidateNotNullOrEmpty()]
    [string]$InputPath = "./tests/leaver-sc1008.csv",

    [ValidateNotNullOrEmpty()]
    [string]$DryRunPlanPath =
        "./evidence/phase5/P5-E49_Leaver-Dry-Run-Plan.csv",

    [ValidateNotNullOrEmpty()]
    [string]$GroupMapPath = "./config/group-object-ids.json",

    [ValidateNotNullOrEmpty()]
    [string]$AppRoleMapPath = "./config/app-role-ids.json",

    [ValidateNotNullOrEmpty()]
    [string]$LocalBlockScriptPath = "./app/manage_blocked_user.py",

    [ValidateNotNullOrEmpty()]
    [string]$PythonPath = "./.venv/bin/python",

    [ValidateNotNullOrEmpty()]
    [string]$ResultPath =
        "./evidence/phase5/P5-E52_Leaver-Apply-Result.json",

    [ValidateNotNullOrEmpty()]
    [string]$EventPath =
        "./evidence/phase5/P5-E54_Leaver-Workflow-Event.json",

    [switch]$Apply,

    [AllowEmptyString()]
    [string]$ApprovalText = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$roleToGroup = @{
    CareWorker   = "SG-SC-CareWorkers"
    Nurse        = "SG-SC-Nurses"
    Manager      = "SG-SC-Managers"
    AgencyWorker = "SG-SC-AgencyWorkers"
    Auditor      = "SG-SC-Auditors"
}

$script:actionsCompleted = [System.Collections.Generic.List[string]]::new()
$script:actionResults = [System.Collections.Generic.List[object]]::new()
$script:writeOperations = 0
$script:userId = $null
$script:userPrincipalName = $null
$script:operator = $null
$script:beforeState = $null
$script:afterState = $null
$script:sessionsRevoked = $false

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

function Assert-FileExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Description was not found: $Path"
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

    return ([string]$property.Value).Trim()
}

function Add-ActionResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [ValidateSet("SUCCESS", "NO CHANGE", "FAILED")]
        [string]$Result,

        [Parameter(Mandatory = $true)]
        [string]$Details
    )

    $script:actionResults.Add(
        [pscustomobject][ordered]@{
            Name         = $Name
            Result       = $Result
            Details      = $Details
            TimestampUtc = [datetime]::UtcNow.ToString("o")
        }
    )
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
                [string]$_.Id
            }
    )

    return ($memberIds -contains $UserId)
}

function Invoke-LocalBlockHelper {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$InputLines
    )

    $payload = (
        $InputLines -join [Environment]::NewLine
    ) + [Environment]::NewLine

    $helperOutput = @(
        $payload |
            & $PythonPath $LocalBlockScriptPath 2>&1
    )

    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output   = ($helperOutput -join [Environment]::NewLine)
    }
}

function Test-LocalBlockActive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$UserId
    )

    $statusResult = Invoke-LocalBlockHelper -InputLines @(
        "status"
        $UserId
    )

    if ($statusResult.ExitCode -ne 0) {
        throw (
            "Local block status helper failed: " +
            $statusResult.Output
        )
    }

    return (
        $statusResult.Output -match "Active block:\s+True"
    )
}

function Get-LiveLeaverState {
    param(
        [Parameter(Mandatory = $true)]
        [object]$GroupMap,

        [Parameter(Mandatory = $true)]
        [object]$ServicePrincipal
    )

    $freshUser = Get-MgUser `
        -UserId $script:userId `
        -Property @(
            "id",
            "displayName",
            "userPrincipalName",
            "employeeId",
            "jobTitle",
            "department",
            "officeLocation",
            "accountEnabled"
        )

    $managedGroups = @()

    foreach ($groupName in @($roleToGroup.Values | Sort-Object -Unique)) {
        $groupId = Get-RequiredMapValue `
            -Map $GroupMap `
            -Key $groupName `
            -MapDescription "Group map"

        if (
            Test-DirectGroupMembership `
                -GroupId $groupId `
                -UserId $script:userId
        ) {
            $managedGroups += [pscustomobject][ordered]@{
                GroupName = $groupName
                GroupId   = $groupId
            }
        }
    }

    $careAssignments = @(
        Get-MgUserAppRoleAssignment `
            -UserId $script:userId `
            -All |
            Where-Object {
                [string]$_.ResourceId -eq [string]$ServicePrincipal.Id
            }
    )

    $localBlockActive = Test-LocalBlockActive `
        -UserId $script:userId

    return [pscustomobject]@{
        User             = $freshUser
        ManagedGroups    = @($managedGroups)
        CareAssignments  = @($careAssignments)
        LocalBlockActive = $localBlockActive
    }
}


function Wait-ForLeaverState {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Condition,

        [Parameter(Mandatory = $true)]
        [string]$Description,

        [Parameter(Mandatory = $true)]
        [object]$GroupMap,

        [Parameter(Mandatory = $true)]
        [object]$ServicePrincipal,

        [int]$MaximumAttempts = 6,

        [int]$DelaySeconds = 3
    )

    for (
        $attempt = 1;
        $attempt -le $MaximumAttempts;
        $attempt++
    ) {
        $readbackState = Get-LiveLeaverState `
            -GroupMap $GroupMap `
            -ServicePrincipal $ServicePrincipal

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


function Save-SanitizedResult {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("LEAVER APPLIED", "NO CHANGE", "FAILED")]
        [string]$Outcome,

        [AllowEmptyString()]
        [string]$ErrorMessage = ""
    )

    Ensure-ParentDirectory -Path $ResultPath

    $payload = [ordered]@{
        GeneratedUtc            = [datetime]::UtcNow.ToString("o")
        Outcome                 = $Outcome
        EmployeeId              = $EmployeeId
        UserObjectId            = $script:userId
        UserPrincipalName       = $script:userPrincipalName
        ExpectedCurrentRole     = $ExpectedCurrentRole
        AccountDisabled         = $null
        GovernedGroupsRemaining = $null
        CareAppRolesRemaining   = $null
        LocalAppBlocked         = $null
        SessionsRevoked         = $script:sessionsRevoked
        ActionsCompleted        = @($script:actionsCompleted)
        ActionResults           = @($script:actionResults)
        WriteOperationsExecuted = $script:writeOperations
        PasswordRecorded        = $false
        SecretRecorded          = $false
        ErrorMessage            = $ErrorMessage
    }

    if ($script:afterState) {
        $payload.AccountDisabled = (
            $script:afterState.User.AccountEnabled -eq $false
        )
        $payload.GovernedGroupsRemaining = @(
            $script:afterState.ManagedGroups |
                ForEach-Object {
                    $_.GroupName
                }
        )
        $payload.CareAppRolesRemaining =
            $script:afterState.CareAssignments.Count
        $payload.LocalAppBlocked =
            $script:afterState.LocalBlockActive
    }

    $payload |
        ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $ResultPath -Encoding utf8
}

function Save-WorkflowEvent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Outcome,

        [AllowEmptyString()]
        [string]$ErrorMessage = ""
    )

    Ensure-ParentDirectory -Path $EventPath

    $eventId = "JML-{0}-{1}" -f (
        [datetime]::UtcNow.ToString("yyyyMMddHHmmss")
    ), $EmployeeId

    $event = [ordered]@{
        EventId        = $eventId
        EmployeeId     = $EmployeeId
        EntraObjectId  = $script:userId
        EventType      = "LEAVER"
        Operator       = $script:operator
        TimestampUtc   = [datetime]::UtcNow.ToString("o")
        Outcome        = $Outcome
        Actions        = @($script:actionResults)
        ErrorMessage   = $ErrorMessage
        SecretsRecorded = $false
    }

    $event |
        ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $EventPath -Encoding utf8
}

foreach ($requiredFile in @(
    @{
        Path = $InputPath
        Description = "Leaver input file"
    },
    @{
        Path = $DryRunPlanPath
        Description = "Approved Leaver dry-run plan"
    },
    @{
        Path = $GroupMapPath
        Description = "Group Object ID map"
    },
    @{
        Path = $AppRoleMapPath
        Description = "Application role ID map"
    },
    @{
        Path = $LocalBlockScriptPath
        Description = "Local block helper"
    },
    @{
        Path = $PythonPath
        Description = "Project Python interpreter"
    }
)) {
    Assert-FileExists `
        -Path $requiredFile.Path `
        -Description $requiredFile.Description
}

$matchingRows = @(
    Import-Csv -LiteralPath $InputPath |
        Where-Object {
            ([string]$_.employeeId).Trim() -eq $EmployeeId
        }
)

if ($matchingRows.Count -ne 1) {
    throw (
        "Expected exactly one input row for employeeId " +
        "$EmployeeId, but found $($matchingRows.Count)."
    )
}

$leaver = $matchingRows[0]
$status = ([string]$leaver.status).Trim()
$endDateText = ([string]$leaver.endDate).Trim()

if ($status -notin @("Leaving", "Inactive")) {
    throw (
        "Leaver status must be Leaving or Inactive. " +
        "Current status: $status"
    )
}

if ([string]::IsNullOrWhiteSpace($endDateText)) {
    throw "Leaver endDate is required."
}

$endDate = [datetime]::ParseExact(
    $endDateText,
    "yyyy-MM-dd",
    [System.Globalization.CultureInfo]::InvariantCulture
)

if ($endDate.Date -gt [datetime]::Today) {
    throw (
        "Leaver endDate has not been reached: $endDateText"
    )
}

if ($leaver.jobRole -ne $ExpectedCurrentRole) {
    throw (
        "Input jobRole does not match ExpectedCurrentRole. " +
        "Input: $($leaver.jobRole); expected: $ExpectedCurrentRole"
    )
}

$planRows = @(
    Import-Csv -LiteralPath $DryRunPlanPath |
        Where-Object {
            ([string]$_.EmployeeId).Trim() -eq $EmployeeId
        }
)

if ($planRows.Count -ne 1) {
    throw (
        "Expected exactly one approved dry-run plan row for " +
        "$EmployeeId, but found $($planRows.Count)."
    )
}

$approvedPlan = $planRows[0]

if ($approvedPlan.Action -ne "DISABLE") {
    throw (
        "Dry-run plan must classify $EmployeeId as DISABLE. " +
        "Actual action: $($approvedPlan.Action)"
    )
}

if ([string]::IsNullOrWhiteSpace($approvedPlan.EntraObjectId)) {
    throw "Approved dry-run plan has no Entra Object ID."
}

$approvedObjectGuid = [guid]::Empty

if (
    -not [guid]::TryParse(
        [string]$approvedPlan.EntraObjectId,
        [ref]$approvedObjectGuid
    )
) {
    throw "Approved dry-run Entra Object ID is not a valid GUID."
}

$expectedGroupName = $roleToGroup[$ExpectedCurrentRole]
$groupMap = Get-Content -LiteralPath $GroupMapPath -Raw |
    ConvertFrom-Json
$appRoleMap = Get-Content -LiteralPath $AppRoleMapPath -Raw |
    ConvertFrom-Json

$null = Get-RequiredMapValue `
    -Map $groupMap `
    -Key $expectedGroupName `
    -MapDescription "Group map"

$expectedAppRoleId = [guid](
    Get-RequiredMapValue `
        -Map $appRoleMap `
        -Key $ExpectedCurrentRole `
        -MapDescription "App-role map"
)

$requiredApproval = "LEAVE $EmployeeId"

if (-not $Apply) {
    Write-Host "Sunhaven Leaver safety check"
    Write-Host "-----------------------------"
    Write-Host "Mode: SAFE - NO APPLY"
    Write-Host "Employee ID: $EmployeeId"
    Write-Host "Expected current role: $ExpectedCurrentRole"
    Write-Host "Workforce status: $status"
    Write-Host "End date: $endDateText"
    Write-Host "Approved Object ID: $($approvedPlan.EntraObjectId)"
    Write-Host "Dry-run plan action: $($approvedPlan.Action)"
    Write-Host "Required approval text: $requiredApproval"
    Write-Host "Planned action order:"
    Write-Host "1. Disable the Entra account"
    Write-Host "2. Revoke Entra sign-in sessions"
    Write-Host "3. Remove all Sunhaven-governed groups"
    Write-Host "4. Remove Sunhaven care-app assignments"
    Write-Host "5. Block the current local app session"
    Write-Host "6. Verify and record the final state"
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
    "Get-MgServicePrincipal",
    "Get-MgUserAppRoleAssignment",
    "Remove-MgUserAppRoleAssignment",
    "Revoke-MgUserSignInSession"
)

foreach ($commandName in $requiredCommands) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required Microsoft Graph command is missing: $commandName"
    }
}

try {
    Connect-MgGraph `
        -TenantId $TenantId `
        -Scopes @(
            "User.Read.All",
            "User.EnableDisableAccount.All",
            "GroupMember.ReadWrite.All",
            "Application.Read.All",
            "AppRoleAssignment.ReadWrite.All",
            "User.RevokeSessions.All"
        ) `
        -ContextScope Process `
        -NoWelcome

    $graphContext = Get-MgContext

    if (-not $graphContext -or $graphContext.TenantId -ne $TenantId) {
        throw "Authenticated Microsoft Graph tenant did not match TenantId."
    }

    $script:operator = [string]$graphContext.Account

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
    $script:userId = [string]$user.Id
    $script:userPrincipalName = [string]$user.UserPrincipalName

    if ($script:userId -ne [string]$approvedPlan.EntraObjectId) {
        throw (
            "Live Object ID does not match the approved dry-run " +
            "Object ID. No writes attempted."
        )
    }

    if (
        -not [string]::Equals(
            $script:userPrincipalName,
            [string]$approvedPlan.CurrentUPN,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw (
            "Live UPN does not match the approved dry-run UPN. " +
            "No writes attempted."
        )
    }

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

    $script:beforeState = Get-LiveLeaverState `
        -GroupMap $groupMap `
        -ServicePrincipal $servicePrincipal

    $alreadyDesired = (
        $script:beforeState.User.AccountEnabled -eq $false -and
        $script:beforeState.ManagedGroups.Count -eq 0 -and
        $script:beforeState.CareAssignments.Count -eq 0 -and
        $script:beforeState.LocalBlockActive
    )

    if ($alreadyDesired) {
        $script:afterState = $script:beforeState

        Add-ActionResult `
            -Name "VerifyDesiredState" `
            -Result "NO CHANGE" `
            -Details "The complete Leaver target state already exists."

        Save-SanitizedResult -Outcome "NO CHANGE"
        Save-WorkflowEvent -Outcome "NO CHANGE"

        Write-Host "Outcome: NO CHANGE"
        Write-Host "Write operations executed: 0"
        exit 0
    }

    $unexpectedRoleAssignments = @(
        $script:beforeState.CareAssignments |
            Where-Object {
                [string]$_.AppRoleId -ne [string]$expectedAppRoleId
            }
    )

    if ($unexpectedRoleAssignments.Count -gt 0) {
        Write-Host (
            "Warning: additional Sunhaven care-app assignments " +
            "will be removed as governed Leaver access."
        )
    }

    Write-Host "STEP 1 - Disable the Entra account first"

    if ($script:beforeState.User.AccountEnabled -eq $true) {
        Update-MgUser `
            -UserId $script:userId `
            -BodyParameter @{
                accountEnabled = $false
            }

        $script:writeOperations++
        $script:actionsCompleted.Add("DISABLE_ACCOUNT")

        $null = Wait-ForLeaverState `
            -Description "Account disable" `
            -GroupMap $groupMap `
            -ServicePrincipal $servicePrincipal `
            -Condition {
                param($state)

                return $state.User.AccountEnabled -eq $false
            }

        Add-ActionResult `
            -Name "DisableAccount" `
            -Result "SUCCESS" `
            -Details "accountEnabled changed from True to False."
    }
    else {
        Add-ActionResult `
            -Name "DisableAccount" `
            -Result "NO CHANGE" `
            -Details "The account was already disabled."
    }

    Write-Host "STEP 2 - Revoke Entra sign-in sessions"

    $null = Revoke-MgUserSignInSession `
        -UserId $script:userId `
        -Confirm:$false

    $script:writeOperations++
    $script:sessionsRevoked = $true
    $script:actionsCompleted.Add("REVOKE_SIGN_IN_SESSIONS")

    Add-ActionResult `
        -Name "RevokeSessions" `
        -Result "SUCCESS" `
        -Details "Microsoft Graph accepted the revocation request."

    Write-Host "STEP 3 - Remove Sunhaven-governed groups"

    foreach ($membership in $script:beforeState.ManagedGroups) {
        Remove-MgGroupMemberByRef `
            -GroupId $membership.GroupId `
            -DirectoryObjectId $script:userId `
            -Confirm:$false

        $script:writeOperations++
        $script:actionsCompleted.Add(
            "REMOVE_GROUP:$($membership.GroupName)"
        )

        $removedGroupName = [string]$membership.GroupName

        $null = Wait-ForLeaverState `
            -Description "Governed group removal" `
            -GroupMap $groupMap `
            -ServicePrincipal $servicePrincipal `
            -Condition {
                param($state)

                $remainingGroupNames = @(
                    $state.ManagedGroups |
                        ForEach-Object {
                            [string]$_.GroupName
                        }
                )

                return $removedGroupName -notin $remainingGroupNames
            }

        Add-ActionResult `
            -Name "RemoveGovernedGroup" `
            -Result "SUCCESS" `
            -Details "Removed $($membership.GroupName)."
    }

    if ($script:beforeState.ManagedGroups.Count -eq 0) {
        Add-ActionResult `
            -Name "RemoveGovernedGroup" `
            -Result "NO CHANGE" `
            -Details "No Sunhaven-governed groups remained."
    }

    Write-Host "STEP 4 - Remove Sunhaven care-app assignments"

    foreach ($assignment in $script:beforeState.CareAssignments) {
        Remove-MgUserAppRoleAssignment `
            -UserId $script:userId `
            -AppRoleAssignmentId $assignment.Id `
            -Confirm:$false

        $script:writeOperations++
        $script:actionsCompleted.Add(
            "REMOVE_APP_ROLE:$($assignment.AppRoleId)"
        )

        $removedAssignmentId = [string]$assignment.Id

        $null = Wait-ForLeaverState `
            -Description "Care-app role removal" `
            -GroupMap $groupMap `
            -ServicePrincipal $servicePrincipal `
            -Condition {
                param($state)

                return @(
                    $state.CareAssignments |
                        Where-Object {
                            [string]$_.Id -eq $removedAssignmentId
                        }
                ).Count -eq 0
            }

        Add-ActionResult `
            -Name "RemoveSunhavenAppRole" `
            -Result "SUCCESS" `
            -Details "Removed assignment $($assignment.Id)."
    }

    if ($script:beforeState.CareAssignments.Count -eq 0) {
        Add-ActionResult `
            -Name "RemoveSunhavenAppRole" `
            -Result "NO CHANGE" `
            -Details "No Sunhaven care-app assignment remained."
    }

    Write-Host "STEP 5 - Block the local care-app session"

    if ($script:beforeState.LocalBlockActive) {
        Add-ActionResult `
            -Name "BlockLocalAppSession" `
            -Result "NO CHANGE" `
            -Details "The local application block was already active."
    }
    else {
        $blockReason = (
            "Automated LEAVER for $EmployeeId; endDate $endDateText"
        )

        $blockResult = Invoke-LocalBlockHelper -InputLines @(
            "block"
            $script:userId
            $blockReason
            "BLOCK"
        )

        if ($blockResult.ExitCode -ne 0) {
            throw (
                "Account containment succeeded, but the local block " +
                "helper failed: $($blockResult.Output)"
            )
        }

        if ($blockResult.Output -notmatch "Active block:\s+True") {
            throw (
                "Account containment succeeded, but the local block " +
                "helper did not confirm an active block."
            )
        }

        $script:writeOperations++
        $script:actionsCompleted.Add("BLOCK_LOCAL_APP_SESSION")

        Add-ActionResult `
            -Name "BlockLocalAppSession" `
            -Result "SUCCESS" `
            -Details "The local Flask application block is active."
    }

    Write-Host "STEP 6 - Read back and verify the final state"

    foreach ($attempt in 1..6) {
        Start-Sleep -Seconds 5

        $script:afterState = Get-LiveLeaverState `
            -GroupMap $groupMap `
            -ServicePrincipal $servicePrincipal

        $verified = (
            $script:afterState.User.AccountEnabled -eq $false -and
            $script:afterState.ManagedGroups.Count -eq 0 -and
            $script:afterState.CareAssignments.Count -eq 0 -and
            $script:afterState.LocalBlockActive
        )

        if ($verified) {
            break
        }
    }

    $finalVerified = (
        $script:afterState -and
        $script:afterState.User.AccountEnabled -eq $false -and
        $script:afterState.ManagedGroups.Count -eq 0 -and
        $script:afterState.CareAssignments.Count -eq 0 -and
        $script:afterState.LocalBlockActive
    )

    if (-not $finalVerified) {
        throw (
            "Final Leaver verification did not reach the complete " +
            "approved target state. The account remains disabled."
        )
    }

    Add-ActionResult `
        -Name "VerifyDesiredState" `
        -Result "SUCCESS" `
        -Details (
            "Account disabled, sessions revoked, governed access " +
            "removed and local block active."
        )

    Save-SanitizedResult -Outcome "LEAVER APPLIED"
    Save-WorkflowEvent -Outcome "LEAVER APPLIED"

    Write-Host "Outcome: LEAVER APPLIED"
    Write-Host "Employee ID: $EmployeeId"
    Write-Host "User Object ID: $($script:userId)"
    Write-Host "Account disabled: True"
    Write-Host "Governed groups remaining: 0"
    Write-Host "Care-app assignments remaining: 0"
    Write-Host "Local application blocked: True"
    Write-Host "Sessions revoked: True"
    Write-Host "Write operations executed: $($script:writeOperations)"
    exit 0
}
catch {
    $failureMessage = $_.Exception.Message

    Add-ActionResult `
        -Name "WorkflowError" `
        -Result "FAILED" `
        -Details $failureMessage

    Save-SanitizedResult `
        -Outcome "FAILED" `
        -ErrorMessage $failureMessage

    Save-WorkflowEvent `
        -Outcome "FAILED" `
        -ErrorMessage $failureMessage

    Write-Host "Outcome: FAILED"
    Write-Host "Error: $failureMessage"
    Write-Host (
        "Security note: this workflow does not re-enable an account " +
        "after partial Leaver containment."
    )
    Write-Host "Write operations executed: $($script:writeOperations)"
    exit 1
}
