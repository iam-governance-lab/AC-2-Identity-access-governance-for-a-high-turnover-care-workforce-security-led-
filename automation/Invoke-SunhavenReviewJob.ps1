param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Plan", "Apply")]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TenantId,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$JobPayloadPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ResultPath,

    [ValidateSet("Delegated", "Certificate")]
    [string]$AuthMode = "Delegated",

    [ValidateNotNullOrEmpty()]
    [string]$ApplicationDisplayName = "Sunhaven Care Portal - LAB",

    [ValidateNotNullOrEmpty()]
    [string]$GroupMapPath = "./config/group-object-ids.json",

    [ValidateNotNullOrEmpty()]
    [string]$AppRoleMapPath = "./config/app-role-ids.json"
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

$allowedRoles = @($roleToGroup.Keys)
$script:payload = $null
$script:writeOperations = 0
$script:actionsCompleted = [System.Collections.Generic.List[string]]::new()
$script:requiredApproval = ""
$script:servicePrincipal = $null
$script:groupMap = $null
$script:appRoleMap = $null

function Ensure-ParentDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
}

function Get-RequiredProperty {
    param(
        [Parameter(Mandatory = $true)][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $property = $Object.PSObject.Properties[$Name]
    if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
        throw "Job payload field is required: $Name"
    }
    return [string]$property.Value
}

function Get-MapValue {
    param(
        [Parameter(Mandatory = $true)][object]$Map,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Description
    )

    $property = $Map.PSObject.Properties[$Key]
    if (-not $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
        throw "$Description is missing required key: $Key"
    }
    return ([string]$property.Value).Trim()
}

function Save-Result {
    param(
        [Parameter(Mandatory = $true)][string]$Outcome,
        [Parameter(Mandatory = $true)][string]$Message,
        [bool]$BaselineVerified = $false,
        [bool]$FinalStateVerified = $false,
        [AllowNull()][object]$State = $null,
        [AllowEmptyString()][string]$ErrorMessage = ""
    )

    Ensure-ParentDirectory -Path $ResultPath

    $record = [ordered]@{
        GeneratedUtc            = [datetime]::UtcNow.ToString("o")
        Mode                    = $Mode.ToUpperInvariant()
        TenantId                = $TenantId
        JobId                   = if ($script:payload) { $script:payload.JobId } else { "" }
        Decision                = if ($script:payload) { $script:payload.Decision } else { "" }
        EmployeeId              = if ($script:payload) { $script:payload.EmployeeId } else { "" }
        UserObjectId            = if ($script:payload) { $script:payload.UserObjectId } else { "" }
        CurrentRole             = if ($script:payload) { $script:payload.CurrentRole } else { "" }
        TargetRole              = if ($script:payload) { $script:payload.TargetRole } else { "" }
        RequiredApproval        = $script:requiredApproval
        Outcome                 = $Outcome
        Message                 = $Message
        BaselineVerified        = $BaselineVerified
        FinalStateVerified      = $FinalStateVerified
        WriteOperationsExecuted = $script:writeOperations
        ActionsCompleted        = @($script:actionsCompleted)
        CurrentGroups           = @()
        CurrentAppRoles         = @()
        AccountEnabled          = $null
        JobTitle                = ""
        ErrorMessage            = $ErrorMessage
        PasswordRecorded        = $false
        TokenRecorded           = $false
        SecretRecorded          = $false
    }

    if ($State) {
        $record.CurrentGroups = @($State.ManagedGroups)
        $record.CurrentAppRoles = @($State.AppRoleNames)
        $record.AccountEnabled = $State.User.AccountEnabled
        $record.JobTitle = $State.User.JobTitle
    }

    $record |
        ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $ResultPath -Encoding utf8

    return [pscustomobject]$record
}

function Connect-SunhavenGraph {
    param([Parameter(Mandatory = $true)][bool]$WriteAccess)

    if ($AuthMode -eq "Certificate") {
        $clientId = $env:SUNHAVEN_GRAPH_CLIENT_ID
        $certificateThumbprint = $env:SUNHAVEN_GRAPH_CERT_THUMBPRINT

        if ([string]::IsNullOrWhiteSpace($clientId)) {
            throw "SUNHAVEN_GRAPH_CLIENT_ID is required for Certificate mode."
        }
        if ([string]::IsNullOrWhiteSpace($certificateThumbprint)) {
            throw "SUNHAVEN_GRAPH_CERT_THUMBPRINT is required for Certificate mode."
        }

        Connect-MgGraph `
            -TenantId $TenantId `
            -ClientId $clientId `
            -CertificateThumbprint $certificateThumbprint `
            -NoWelcome
    }
    else {
        $scopes = @(
            "User.Read.All",
            "GroupMember.Read.All",
            "Application.Read.All"
        )

        if ($WriteAccess) {
            $scopes = @(
                "User.ReadWrite.All",
                "GroupMember.ReadWrite.All",
                "Application.Read.All",
                "AppRoleAssignment.ReadWrite.All",
                "User.RevokeSessions.All"
            )
        }

        Connect-MgGraph `
            -TenantId $TenantId `
            -Scopes $scopes `
            -ContextScope CurrentUser `
            -NoWelcome
    }

    $context = Get-MgContext
    if (-not $context -or [string]$context.TenantId -ne $TenantId) {
        throw "STOP: Microsoft Graph tenant verification failed."
    }

    Write-Host "Authenticated tenant: $($context.TenantId)"
    Write-Host "Authentication mode: $AuthMode"
}

function Test-DirectGroupMembership {
    param(
        [Parameter(Mandatory = $true)][string]$GroupId,
        [Parameter(Mandatory = $true)][string]$UserId
    )

    $memberIds = @(
        Get-MgGroupMember -GroupId $GroupId -All |
            ForEach-Object { [string]$_.Id }
    )
    return ($memberIds -contains $UserId)
}

function Get-LiveState {
    $user = Get-MgUser `
        -UserId $script:payload.UserObjectId `
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

    if (-not $user) {
        throw "The exact Entra user could not be resolved."
    }
    if ([string]$user.Id -ne [string]$script:payload.UserObjectId) {
        throw "Resolved Object ID did not match the approved target."
    }
    if ([string]$user.EmployeeId -ne [string]$script:payload.EmployeeId) {
        throw "Resolved employeeId did not match the reviewed identity."
    }

    $managedGroups = @()
    foreach ($groupEntry in $script:groupMap.PSObject.Properties) {
        if (
            Test-DirectGroupMembership `
                -GroupId ([string]$groupEntry.Value) `
                -UserId ([string]$user.Id)
        ) {
            $managedGroups += [string]$groupEntry.Name
        }
    }
    $managedGroups = @($managedGroups | Sort-Object -Unique)

    $assignments = @(
        Get-MgUserAppRoleAssignment -UserId $user.Id -All |
            Where-Object {
                [string]$_.ResourceId -eq [string]$script:servicePrincipal.Id
            }
    )

    $appRoleNames = @()
    foreach ($assignment in $assignments) {
        $role = @(
            $script:servicePrincipal.AppRoles |
                Where-Object {
                    [string]$_.Id -eq [string]$assignment.AppRoleId
                }
        )
        if ($role.Count -eq 1 -and $role[0].Value) {
            $appRoleNames += [string]$role[0].Value
        }
        else {
            $appRoleNames += "UNKNOWN:$($assignment.AppRoleId)"
        }
    }
    $appRoleNames = @($appRoleNames | Sort-Object -Unique)

    return [pscustomobject]@{
        User          = $user
        ManagedGroups = @($managedGroups)
        Assignments   = @($assignments)
        AppRoleNames  = @($appRoleNames)
    }
}

function Test-BaselineState {
    param([Parameter(Mandatory = $true)][object]$State)

    $expectedGroup = $roleToGroup[$script:payload.CurrentRole]
    return (
        $State.User.AccountEnabled -eq $true -and
        $State.User.JobTitle -eq $script:payload.CurrentRole -and
        $State.ManagedGroups.Count -eq 1 -and
        $State.ManagedGroups[0] -eq $expectedGroup -and
        $State.AppRoleNames.Count -eq 1 -and
        $State.AppRoleNames[0] -eq $script:payload.CurrentRole
    )
}

function Test-DesiredState {
    param([Parameter(Mandatory = $true)][object]$State)

    if ($script:payload.Decision -eq "RemoveAccess") {
        return (
            $State.ManagedGroups.Count -eq 0 -and
            $State.AppRoleNames.Count -eq 0
        )
    }

    $targetGroup = $roleToGroup[$script:payload.TargetRole]
    return (
        $State.User.AccountEnabled -eq $true -and
        $State.User.JobTitle -eq $script:payload.TargetRole -and
        $State.User.Department -eq $script:payload.Facility -and
        $State.User.OfficeLocation -eq $script:payload.Facility -and
        $State.ManagedGroups.Count -eq 1 -and
        $State.ManagedGroups[0] -eq $targetGroup -and
        $State.AppRoleNames.Count -eq 1 -and
        $State.AppRoleNames[0] -eq $script:payload.TargetRole
    )
}

function Wait-ForDesiredState {
    for ($attempt = 1; $attempt -le 8; $attempt++) {
        $state = Get-LiveState
        if (Test-DesiredState -State $state) {
            return $state
        }
        if ($attempt -lt 8) {
            Start-Sleep -Seconds 3
        }
    }
    throw "Final Entra state did not reach the approved target."
}

function Get-AssignmentForRole {
    param(
        [Parameter(Mandatory = $true)][object]$State,
        [Parameter(Mandatory = $true)][string]$RoleName
    )

    $roleId = Get-MapValue `
        -Map $script:appRoleMap `
        -Key $RoleName `
        -Description "Application-role map"

    return @(
        $State.Assignments |
            Where-Object {
                [string]$_.AppRoleId -eq [string]$roleId
            }
    )
}

try {
    foreach ($requiredPath in @($JobPayloadPath, $GroupMapPath, $AppRoleMapPath)) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "Required file was not found: $requiredPath"
        }
    }

    $script:payload = Get-Content -LiteralPath $JobPayloadPath -Raw |
        ConvertFrom-Json

    foreach ($requiredField in @(
        "JobId",
        "Decision",
        "EmployeeId",
        "UserObjectId",
        "CurrentRole",
        "Facility"
    )) {
        $null = Get-RequiredProperty -Object $script:payload -Name $requiredField
    }

    if ($script:payload.Decision -notin @("ChangeAccess", "RemoveAccess")) {
        throw "Decision must be ChangeAccess or RemoveAccess."
    }
    if ($script:payload.CurrentRole -notin $allowedRoles) {
        throw "CurrentRole is not supported."
    }

    if ($script:payload.Decision -eq "ChangeAccess") {
        $targetRole = Get-RequiredProperty -Object $script:payload -Name "TargetRole"
        if ($targetRole -notin $allowedRoles) {
            throw "TargetRole is not supported."
        }
        if ($targetRole -eq $script:payload.CurrentRole) {
            throw "TargetRole must differ from CurrentRole."
        }
        $script:requiredApproval = (
            "MOVE {0} {1} TO {2}" -f
                $script:payload.EmployeeId,
                $script:payload.CurrentRole,
                $targetRole
        )
    }
    else {
        $script:requiredApproval = (
            "REMOVE ACCESS {0} {1}" -f
                $script:payload.EmployeeId,
                $script:payload.CurrentRole
        )
    }

    if (
        $Mode -eq "Apply" -and
        [string]$script:payload.ApprovalText -cne $script:requiredApproval
    ) {
        throw "Approval text did not match the required exact phrase."
    }

    $requiredCommands = @(
        "Connect-MgGraph",
        "Get-MgContext",
        "Get-MgUser",
        "Get-MgGroupMember",
        "Get-MgServicePrincipal",
        "Get-MgUserAppRoleAssignment"
    )
    if ($Mode -eq "Apply") {
        $requiredCommands += @(
            "Update-MgUser",
            "Remove-MgGroupMemberByRef",
            "New-MgGroupMemberByRef",
            "Remove-MgUserAppRoleAssignment",
            "New-MgUserAppRoleAssignment",
            "Revoke-MgUserSignInSession"
        )
    }
    foreach ($commandName in $requiredCommands) {
        if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
            throw "Required Microsoft Graph command is missing: $commandName"
        }
    }

    $script:groupMap = Get-Content -LiteralPath $GroupMapPath -Raw |
        ConvertFrom-Json
    $script:appRoleMap = Get-Content -LiteralPath $AppRoleMapPath -Raw |
        ConvertFrom-Json

    $null = Get-MapValue `
        -Map $script:groupMap `
        -Key $roleToGroup[$script:payload.CurrentRole] `
        -Description "Group map"
    $null = Get-MapValue `
        -Map $script:appRoleMap `
        -Key $script:payload.CurrentRole `
        -Description "Application-role map"

    if ($script:payload.Decision -eq "ChangeAccess") {
        $null = Get-MapValue `
            -Map $script:groupMap `
            -Key $roleToGroup[$script:payload.TargetRole] `
            -Description "Group map"
        $null = Get-MapValue `
            -Map $script:appRoleMap `
            -Key $script:payload.TargetRole `
            -Description "Application-role map"
    }

    Connect-SunhavenGraph -WriteAccess ($Mode -eq "Apply")

    $servicePrincipals = @(
        Get-MgServicePrincipal -All -Property @("id", "displayName", "appRoles") |
            Where-Object { $_.DisplayName -eq $ApplicationDisplayName }
    )
    if ($servicePrincipals.Count -ne 1) {
        throw (
            "Expected exactly one service principal named " +
            "'$ApplicationDisplayName', but found $($servicePrincipals.Count)."
        )
    }
    $script:servicePrincipal = $servicePrincipals[0]

    $initialState = Get-LiveState
    $alreadyDesired = Test-DesiredState -State $initialState
    if ($alreadyDesired) {
        $result = Save-Result `
            -Outcome "NO CHANGE" `
            -Message "The target state was already present." `
            -BaselineVerified $false `
            -FinalStateVerified $true `
            -State $initialState
        $result | Format-List
        exit 0
    }

    $baselineVerified = Test-BaselineState -State $initialState
    if (-not $baselineVerified) {
        $result = Save-Result `
            -Outcome "BLOCKED" `
            -Message "Live Entra state did not match the reviewed baseline." `
            -BaselineVerified $false `
            -FinalStateVerified $false `
            -State $initialState
        $result | Format-List
        exit 2
    }

    if ($Mode -eq "Plan") {
        $plannedActions = [System.Collections.Generic.List[string]]::new()
        $plannedActions.Add("REMOVE_CURRENT_APP_ROLE")
        $plannedActions.Add("REMOVE_CURRENT_GROUP")
        if ($script:payload.Decision -eq "ChangeAccess") {
            $plannedActions.Add("UPDATE_USER_ATTRIBUTES")
            $plannedActions.Add("ADD_TARGET_GROUP")
            $plannedActions.Add("ADD_TARGET_APP_ROLE")
        }
        $plannedActions.Add("REVOKE_SIGN_IN_SESSIONS")
        foreach ($action in $plannedActions) {
            $script:actionsCompleted.Add("PLANNED:$action")
        }

        $result = Save-Result `
            -Outcome "PLANNED" `
            -Message "No-write plan completed and the reviewed baseline was verified." `
            -BaselineVerified $true `
            -FinalStateVerified $false `
            -State $initialState
        $result | Format-List
        Write-Host "Required approval: $script:requiredApproval"
        Write-Host "Write operations executed: 0"
        exit 0
    }

    $currentRoleAssignments = @(Get-AssignmentForRole `
        -State $initialState `
        -RoleName $script:payload.CurrentRole)
    if ($currentRoleAssignments.Count -ne 1) {
        throw "Expected exactly one current application-role assignment."
    }

    Remove-MgUserAppRoleAssignment `
        -UserId $script:payload.UserObjectId `
        -AppRoleAssignmentId $currentRoleAssignments[0].Id `
        -Confirm:$false
    $script:writeOperations++
    $script:actionsCompleted.Add("REMOVE_CURRENT_APP_ROLE")

    $currentGroupId = Get-MapValue `
        -Map $script:groupMap `
        -Key $roleToGroup[$script:payload.CurrentRole] `
        -Description "Group map"
    Remove-MgGroupMemberByRef `
        -GroupId $currentGroupId `
        -DirectoryObjectId $script:payload.UserObjectId `
        -Confirm:$false
    $script:writeOperations++
    $script:actionsCompleted.Add("REMOVE_CURRENT_GROUP")

    if ($script:payload.Decision -eq "ChangeAccess") {
        Update-MgUser `
            -UserId $script:payload.UserObjectId `
            -BodyParameter @{
                jobTitle       = $script:payload.TargetRole
                department     = $script:payload.Facility
                officeLocation = $script:payload.Facility
            }
        $script:writeOperations++
        $script:actionsCompleted.Add("UPDATE_USER_ATTRIBUTES")

        $targetGroupId = Get-MapValue `
            -Map $script:groupMap `
            -Key $roleToGroup[$script:payload.TargetRole] `
            -Description "Group map"
        New-MgGroupMemberByRef `
            -GroupId $targetGroupId `
            -BodyParameter @{
                "@odata.id" = (
                    "https://graph.microsoft.com/v1.0/directoryObjects/" +
                    $script:payload.UserObjectId
                )
            }
        $script:writeOperations++
        $script:actionsCompleted.Add("ADD_TARGET_GROUP")

        $targetRoleId = [guid](Get-MapValue `
            -Map $script:appRoleMap `
            -Key $script:payload.TargetRole `
            -Description "Application-role map")
        $null = New-MgUserAppRoleAssignment `
            -UserId $script:payload.UserObjectId `
            -BodyParameter @{
                principalId = [guid]$script:payload.UserObjectId
                resourceId  = [guid]$script:servicePrincipal.Id
                appRoleId   = $targetRoleId
            }
        $script:writeOperations++
        $script:actionsCompleted.Add("ADD_TARGET_APP_ROLE")
    }

    Revoke-MgUserSignInSession `
        -UserId $script:payload.UserObjectId `
        -Confirm:$false | Out-Null
    $script:writeOperations++
    $script:actionsCompleted.Add("REVOKE_SIGN_IN_SESSIONS")

    $finalState = Wait-ForDesiredState
    $outcome = if ($script:payload.Decision -eq "ChangeAccess") {
        "MOVED"
    }
    else {
        "ACCESS_REMOVED"
    }

    $result = Save-Result `
        -Outcome $outcome `
        -Message "Approved access-review remediation was applied and verified." `
        -BaselineVerified $true `
        -FinalStateVerified $true `
        -State $finalState
    $result | Format-List
    Write-Host "Result: PASS"
    exit 0
}
catch {
    $errorMessage = $_.Exception.Message
    $result = Save-Result `
        -Outcome "FAILED" `
        -Message "The job failed closed." `
        -BaselineVerified $false `
        -FinalStateVerified $false `
        -ErrorMessage $errorMessage
    $result | Format-List
    Write-Host "Result: FAILED"
    Write-Host "Error: $errorMessage"
    exit 1
}
