# Sunhaven Phase 6.3 whole-access review exporter, corrected version 2.
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TenantId,

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

    $parent = Split-Path -Parent $Path

    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force |
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

Write-Host "STEP 1 - Connect with read-only Graph permissions"

Connect-MgGraph `
    -TenantId $TenantId `
    -Scopes @(
        "User.Read.All",
        "GroupMember.Read.All",
        "Application.Read.All"
    ) `
    -NoWelcome

$context = Get-MgContext

if (-not $context -or $context.TenantId -ne $TenantId) {
    throw "STOP: Microsoft Graph tenant verification failed."
}

Write-Host "Authenticated tenant: $($context.TenantId)"
Write-Host "Write permissions requested: 0"

Write-Host "STEP 2 - Read users and governed group memberships"

$userProperties = @(
    "id",
    "displayName",
    "userPrincipalName",
    "employeeId",
    "jobTitle",
    "department",
    "officeLocation",
    "accountEnabled",
    "userType"
)

$users = @(Get-MgUser -All -Property $userProperties)
$usersById = @{}

foreach ($user in $users) {
    $usersById[[string]$user.Id] = $user
}

$groupMap = Get-Content -LiteralPath $GroupMapPath -Raw |
    ConvertFrom-Json

$groupsByUserId = @{}

foreach ($groupEntry in $groupMap.PSObject.Properties) {
    $groupName = [string]$groupEntry.Name
    $groupId = [string]$groupEntry.Value

    foreach ($member in @(Get-MgGroupMember -GroupId $groupId -All)) {
        $memberId = [string]$member.Id

        if (-not $usersById.ContainsKey($memberId)) {
            continue
        }

        if (-not $groupsByUserId.ContainsKey($memberId)) {
            $groupsByUserId[$memberId] = @()
        }

        $groupsByUserId[$memberId] += $groupName
    }
}

Write-Host "STEP 3 - Read Sunhaven care-app role assignments"

$servicePrincipals = @(
    Get-MgServicePrincipal -All -Property @(
        "id",
        "displayName",
        "appRoles"
    ) |
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
$appRoleNamesById = @{}

foreach ($role in $servicePrincipal.AppRoles) {
    $roleId = [string]$role.Id
    $roleName = if ($role.Value) {
        [string]$role.Value
    }
    else {
        "UNKNOWN:$roleId"
    }

    $appRoleNamesById[$roleId] = $roleName
}

$capturedUtc = [datetime]::UtcNow.ToString("o")
$records = @()

foreach ($user in $users) {
    $userId = [string]$user.Id

    $groupNames = @()

    if ($groupsByUserId.ContainsKey($userId)) {
        $groupNames = @(
            $groupsByUserId[$userId] |
                Sort-Object -Unique
        )
    }

    $assignments = @(
        Get-MgUserAppRoleAssignment -UserId $userId -All |
            Where-Object {
                $_.ResourceId -eq $servicePrincipal.Id
            }
    )

    $roleNames = @(
        @(
            foreach ($assignment in $assignments) {
                $roleId = [string]$assignment.AppRoleId

                if (
                    $roleId -eq
                    "00000000-0000-0000-0000-000000000000"
                ) {
                    "DefaultAccess"
                }
                elseif ($appRoleNamesById.ContainsKey($roleId)) {
                    $appRoleNamesById[$roleId]
                }
                else {
                    "UNKNOWN:$roleId"
                }
            }
        ) | Sort-Object -Unique
    )

    if ($groupNames.Count -eq 0 -and $roleNames.Count -eq 0) {
        continue
    }

    $records += [pscustomobject][ordered]@{
        CapturedUtc = $capturedUtc
        EmployeeId = if ($user.EmployeeId) {
            $user.EmployeeId
        }
        else {
            "<missing>"
        }
        DisplayName = $user.DisplayName
        UserPrincipalName = $user.UserPrincipalName
        ObjectId = $user.Id
        AccountEnabled = $user.AccountEnabled
        UserType = $user.UserType
        JobRole = if ($user.JobTitle) {
            $user.JobTitle
        }
        else {
            "<missing>"
        }
        Department = if ($user.Department) {
            $user.Department
        }
        else {
            "<missing>"
        }
        Facility = if ($user.OfficeLocation) {
            $user.OfficeLocation
        }
        else {
            "<missing>"
        }
        GovernedGroups = if ($groupNames.Count) {
            $groupNames -join ";"
        }
        else {
            "<none>"
        }
        GovernedGroupCount = $groupNames.Count
        CareApplication = $servicePrincipal.DisplayName
        CareAppRoles = if ($roleNames.Count) {
            $roleNames -join ";"
        }
        else {
            "<none>"
        }
        CareAppRoleAssignmentCount = $assignments.Count
        WriteOperationsExecuted = 0
        ReviewDecision = ""
        Reviewer = ""
        ReviewDate = ""
        Reason = ""
        Remediation = ""
    }
}

$records = @($records | Sort-Object DisplayName)

if ($records.Count -eq 0) {
    throw "STOP: No Sunhaven-governed access assignments were found."
}

$duplicateObjectIds = @(
    $records |
        Group-Object ObjectId |
        Where-Object Count -gt 1
)

if ($duplicateObjectIds.Count -gt 0) {
    throw "STOP: Duplicate users were found in the inventory."
}

$records |
    Export-Csv -LiteralPath $CsvPath -NoTypeInformation -Encoding utf8

$missingEmployeeIds = @(
    $records | Where-Object EmployeeId -eq "<missing>"
).Count

$missingFacilities = @(
    $records | Where-Object Facility -eq "<missing>"
).Count

$enabledUsers = @(
    $records | Where-Object AccountEnabled -eq $true
).Count

$summary = @(
    "Sunhaven pre-review governed-access inventory"
    "---------------------------------------------"
    "Captured UTC: $capturedUtc"
    "Tenant ID: $($context.TenantId)"
    "Application: $($servicePrincipal.DisplayName)"
    "Users holding governed access: $($records.Count)"
    "Enabled access holders: $enabledUsers"
    "Missing employeeId values: $missingEmployeeIds"
    "Missing facility values: $missingFacilities"
    "Review decisions initially blank: $($records.Count)"
    "Write operations executed: 0"
    "Result: PASS"
)

$summary | Set-Content -LiteralPath $SummaryPath -Encoding utf8

Write-Host ""
$summary | ForEach-Object { Write-Host $_ }
