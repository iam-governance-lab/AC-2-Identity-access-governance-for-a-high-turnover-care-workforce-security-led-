param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TenantId,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$EmployeeId,

    [ValidateNotNullOrEmpty()]
    [string]$ApplicationDisplayName = "Sunhaven Care Portal - LAB",

    [ValidateNotNullOrEmpty()]
    [string]$GroupMapPath = "./config/group-object-ids.json",

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$CsvPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$SummaryPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-ParentDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $parentDirectory = Split-Path -Parent $Path

    if ($parentDirectory) {
        New-Item `
            -ItemType Directory `
            -Path $parentDirectory `
            -Force |
            Out-Null
    }
}

$requiredCommands = @(
    "Connect-MgGraph",
    "Get-MgContext",
    "Get-MgUser",
    "Get-MgGroupMember",
    "Get-MgServicePrincipal",
    "Get-MgUserAppRoleAssignment"
)

foreach ($commandName in $requiredCommands) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required Microsoft Graph command is missing: $commandName"
    }
}

if (-not (Test-Path -LiteralPath $GroupMapPath)) {
    throw "Group mapping file was not found: $GroupMapPath"
}

Ensure-ParentDirectory -Path $CsvPath
Ensure-ParentDirectory -Path $SummaryPath

Write-Host "STEP 1 - Connect using read-only Microsoft Graph permissions"

Connect-MgGraph `
    -TenantId $TenantId `
    -Scopes @(
        "User.Read.All",
        "GroupMember.Read.All",
        "Application.Read.All"
    ) `
    -NoWelcome

$graphContext = Get-MgContext

if (-not $graphContext) {
    throw "Microsoft Graph did not return an authenticated context."
}

if ($graphContext.TenantId -ne $TenantId) {
    throw (
        "Authenticated tenant does not match the requested tenant. " +
        "Expected: $TenantId; Actual: $($graphContext.TenantId)"
    )
}

Write-Host "Authenticated account: $($graphContext.Account)"
Write-Host "Authenticated tenant: $($graphContext.TenantId)"
Write-Host "Write permissions requested: 0"

Write-Host "STEP 2 - Locate exactly one user by employeeId"

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

$allUsers = @(
    Get-MgUser `
        -All `
        -Property $userProperties
)

$matchingUsers = @(
    $allUsers |
        Where-Object {
            $_.EmployeeId -eq $EmployeeId
        }
)

if ($matchingUsers.Count -ne 1) {
    throw (
        "Expected exactly one user with employeeId $EmployeeId, " +
        "but found $($matchingUsers.Count)."
    )
}

$user = $matchingUsers[0]

Write-Host "Resolved user: $($user.UserPrincipalName)"
Write-Host "Object ID: $($user.Id)"

Write-Host "STEP 3 - Read Sunhaven-governed group memberships"

$groupMap = Get-Content `
    -LiteralPath $GroupMapPath `
    -Raw |
    ConvertFrom-Json

$governedGroups = @()

foreach ($groupEntry in $groupMap.PSObject.Properties) {
    $groupName = [string]$groupEntry.Name
    $groupId = [string]$groupEntry.Value

    $memberIds = @(
        Get-MgGroupMember `
            -GroupId $groupId `
            -All |
            ForEach-Object {
                $_.Id
            }
    )

    if ($memberIds -contains $user.Id) {
        $governedGroups += $groupName
    }
}

$governedGroups = @(
    $governedGroups |
        Sort-Object -Unique
)

Write-Host "STEP 4 - Read Sunhaven care-application roles"

$servicePrincipalProperties = @(
    "id",
    "displayName",
    "appRoles"
)

$servicePrincipals = @(
    Get-MgServicePrincipal `
        -All `
        -Property $servicePrincipalProperties |
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

$appRoleAssignments = @(
    Get-MgUserAppRoleAssignment `
        -UserId $user.Id `
        -All |
        Where-Object {
            $_.ResourceId -eq $servicePrincipal.Id
        }
)

$careAppRoles = @()

foreach ($assignment in $appRoleAssignments) {
    $matchingRole = @(
        $servicePrincipal.AppRoles |
            Where-Object {
                $_.Id -eq $assignment.AppRoleId
            }
    )

    if (
        $matchingRole.Count -eq 1 -and
        $matchingRole[0].Value
    ) {
        $careAppRoles += $matchingRole[0].Value
    }
    else {
        $careAppRoles += "UNKNOWN:$($assignment.AppRoleId)"
    }
}

$careAppRoles = @(
    $careAppRoles |
        Sort-Object -Unique
)

$governedGroupText = if ($governedGroups.Count -eq 0) {
    "<none>"
}
else {
    $governedGroups -join ";"
}

$careAppRoleText = if ($careAppRoles.Count -eq 0) {
    "<none>"
}
else {
    $careAppRoles -join ";"
}

$capturedUtc = [datetime]::UtcNow.ToString("o")

$stateRecord = [pscustomobject][ordered]@{
    CapturedUtc                  = $capturedUtc
    EmployeeId                   = $user.EmployeeId
    DisplayName                  = $user.DisplayName
    UserPrincipalName            = $user.UserPrincipalName
    ObjectId                     = $user.Id
    AccountEnabled               = $user.AccountEnabled
    JobTitle                     = $user.JobTitle
    Department                   = $user.Department
    Facility                     = $user.OfficeLocation
    GovernedGroups               = $governedGroupText
    GovernedGroupCount           = $governedGroups.Count
    CareApplication              = $servicePrincipal.DisplayName
    CareApplicationServiceId     = $servicePrincipal.Id
    CareAppRoles                 = $careAppRoleText
    CareAppRoleAssignmentCount   = $appRoleAssignments.Count
    WriteOperationsExecuted      = 0
}

$stateRecord |
    Export-Csv `
        -LiteralPath $CsvPath `
        -NoTypeInformation `
        -Encoding utf8

$summaryLines = @(
    "Sunhaven worker access-state export"
    "-----------------------------------"
    "Captured UTC: $capturedUtc"
    "Tenant ID: $($graphContext.TenantId)"
    "Authenticated account: $($graphContext.Account)"
    "Employee ID: $($user.EmployeeId)"
    "Display name: $($user.DisplayName)"
    "UPN: $($user.UserPrincipalName)"
    "Object ID: $($user.Id)"
    "Account enabled: $($user.AccountEnabled)"
    "Job title: $($user.JobTitle)"
    "Department: $($user.Department)"
    "Facility: $($user.OfficeLocation)"
    "Governed groups: $governedGroupText"
    "Care-app roles: $careAppRoleText"
    "Write operations executed: 0"
    "Result: PASS"
)

$summaryLines |
    Set-Content `
        -LiteralPath $SummaryPath `
        -Encoding utf8

Write-Host ""
$summaryLines |
    ForEach-Object {
        Write-Host $_
    }