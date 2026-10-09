[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TenantId,

    [Parameter(Mandatory = $true)]
    [string]$TenantDomain,

    [string]$EmployeeId = "SC1008",

    [string]$InputPath =
        "./tests/joiner-sc1008.csv",

    [string]$DryRunPlanPath =
        "./evidence/phase5/P5-E12_Joiner-Dry-Run-Plan.csv",

    [string]$ValidatorPath =
        "./automation/Test-WorkforceInput.ps1",

    [string]$GroupIdMapPath =
        "./config/group-object-ids.json",

    [string]$AppRoleIdMapPath =
        "./config/app-role-ids.json",

    [string]$ApplicationDisplayName =
        "Sunhaven Care Portal - LAB",

    [string]$ValidationErrorPath =
        "./evidence/phase5/P5-E15_Joiner-Apply-Validation-Errors.csv",

    [string]$ValidationSummaryPath =
        "./evidence/phase5/P5-E15_Joiner-Apply-Validation.txt",

    [string]$ResultPath =
        "./evidence/phase5/P5-E16_Joiner-Apply-Result.json",

    [switch]$Apply,

    [string]$ApprovalText = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$roleGroupMap = @{
    CareWorker   = "SG-SC-CareWorkers"
    Nurse        = "SG-SC-Nurses"
    Manager      = "SG-SC-Managers"
    AgencyWorker = "SG-SC-AgencyWorkers"
    Auditor      = "SG-SC-Auditors"
}


function Ensure-ParentDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $parentDirectory = Split-Path -Parent $Path

    if (-not [string]::IsNullOrWhiteSpace($parentDirectory)) {
        New-Item `
            -ItemType Directory `
            -Path $parentDirectory `
            -Force |
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

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Description does not exist: $Path"
    }
}


function New-CryptographicPassword {
    param(
        [int]$Length = 20
    )

    if ($Length -lt 16) {
        throw "The temporary password must be at least 16 characters."
    }

    $uppercase = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    $lowercase = "abcdefghijkmnopqrstuvwxyz"
    $numbers = "23456789"
    $symbols = '!@#$%*-_=+?'
    $allCharacters =
        $uppercase + $lowercase + $numbers + $symbols

    $passwordCharacters =
        [System.Collections.Generic.List[char]]::new()

    foreach (
        $characterSet in @(
            $uppercase,
            $lowercase,
            $numbers,
            $symbols
        )
    ) {
        $position =
            [System.Security.Cryptography.RandomNumberGenerator]::GetInt32(
                $characterSet.Length
            )

        [void]$passwordCharacters.Add(
            $characterSet[$position]
        )
    }

    while ($passwordCharacters.Count -lt $Length) {
        $position =
            [System.Security.Cryptography.RandomNumberGenerator]::GetInt32(
                $allCharacters.Length
            )

        [void]$passwordCharacters.Add(
            $allCharacters[$position]
        )
    }

    for (
        $index = $passwordCharacters.Count - 1;
        $index -gt 0;
        $index--
    ) {
        $swapIndex =
            [System.Security.Cryptography.RandomNumberGenerator]::GetInt32(
                $index + 1
            )

        $temporaryCharacter = $passwordCharacters[$index]
        $passwordCharacters[$index] =
            $passwordCharacters[$swapIndex]
        $passwordCharacters[$swapIndex] =
            $temporaryCharacter
    }

    return -join $passwordCharacters
}


function Get-GraphStatusCode {
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.ErrorRecord]$ErrorRecord
    )

    $exception = $ErrorRecord.Exception
    $candidateValues =
        [System.Collections.Generic.List[object]]::new()

    foreach ($propertyName in @(
        "ResponseStatusCode",
        "StatusCode"
    )) {
        $property = $exception.PSObject.Properties[$propertyName]

        if ($property -and $null -ne $property.Value) {
            [void]$candidateValues.Add($property.Value)
        }
    }

    $responseProperty =
        $exception.PSObject.Properties["Response"]

    if ($responseProperty -and $responseProperty.Value) {
        $statusProperty =
            $responseProperty.Value.PSObject.Properties["StatusCode"]

        if ($statusProperty -and $null -ne $statusProperty.Value) {
            [void]$candidateValues.Add($statusProperty.Value)
        }
    }

    foreach ($candidateValue in $candidateValues) {
        try {
            return [int]$candidateValue
        }
        catch {
            continue
        }
    }

    return $null
}


function Test-IsTransientGraphError {
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.ErrorRecord]$ErrorRecord
    )

    $statusCode = Get-GraphStatusCode -ErrorRecord $ErrorRecord

    if ($statusCode -in @(408, 429, 500, 502, 503, 504)) {
        return $true
    }

    $message = [string]$ErrorRecord.Exception.Message
    $transientPatterns = @(
        '\bHTTP\s*(408|429|500|502|503|504)\b',
        '\bstatus(?:\s+code)?\s*[:=]?\s*' +
            '(408|429|500|502|503|504)\b',
        '\btoo many requests\b',
        '\bthrottl',
        '\btemporar(?:y|ily) unavailable\b',
        '\bservice unavailable\b',
        '\bbad gateway\b',
        '\bgateway timeout\b',
        '\brequest timed out\b',
        '\bconnection (?:reset|closed)\b'
    )

    foreach ($pattern in $transientPatterns) {
        if ($message -match $pattern) {
            return $true
        }
    }

    return $false
}


function Invoke-WithRetry {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Operation,

        [Parameter(Mandatory = $true)]
        [string]$Description,

        [int]$MaximumAttempts = 4,

        [int]$DelaySeconds = 3
    )

    for (
        $attempt = 1;
        $attempt -le $MaximumAttempts;
        $attempt++
    ) {
        try {
            return & $Operation
        }
        catch {
            $isTransient =
                Test-IsTransientGraphError -ErrorRecord $_

            if (-not $isTransient) {
                Write-Host (
                    "$Description failed with a non-transient error. " +
                    "No retry will be attempted."
                ) -ForegroundColor Red

                throw
            }

            if ($attempt -eq $MaximumAttempts) {
                throw
            }

            $retryDelaySeconds = $DelaySeconds * $attempt

            Write-Host (
                "$Description returned a transient Graph error. " +
                "Retry $attempt of $($MaximumAttempts - 1) " +
                "in $retryDelaySeconds seconds..."
            ) -ForegroundColor Yellow

            Start-Sleep -Seconds $retryDelaySeconds
        }
    }
}


function Wait-ForDesiredState {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Readback,

        [Parameter(Mandatory = $true)]
        [string]$Description,

        [int]$MaximumAttempts = 6,

        [int]$DelaySeconds = 3,

        [switch]$NotFoundMeansPending
    )

    for (
        $attempt = 1;
        $attempt -le $MaximumAttempts;
        $attempt++
    ) {
        $desiredStateReached = $false

        try {
            $desiredStateReached = [bool](& $Readback)
        }
        catch {
            $statusCode = Get-GraphStatusCode -ErrorRecord $_
            $message = [string]$_.Exception.Message
            $pendingNotFound = (
                $NotFoundMeansPending -and
                (
                    $statusCode -eq 404 -or
                    $message -match '\bHTTP\s*404\b' -or
                    $message -match '\bnot found\b'
                )
            )

            if (-not $pendingNotFound) {
                throw
            }
        }

        if ($desiredStateReached) {
            Write-Host "$Description readback: PASS"
            return $true
        }

        if ($attempt -lt $MaximumAttempts) {
            Write-Host (
                "$Description readback is pending. " +
                "Attempt $attempt of $MaximumAttempts."
            ) -ForegroundColor Yellow

            Start-Sleep -Seconds $DelaySeconds
        }
    }

    Write-Host "$Description readback: FAIL" -ForegroundColor Red
    return $false
}


function Write-SanitizedResult {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$Result,

        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    Ensure-ParentDirectory -Path $Path

    $Result |
        ConvertTo-Json -Depth 6 |
        Set-Content `
            -LiteralPath $Path `
            -Encoding utf8
}


if (-not $Apply) {
    Write-Host ""
    Write-Host "SAFE BUILD MODE" -ForegroundColor Green
    Write-Host "The -Apply switch was not supplied."
    Write-Host "No Microsoft Graph connection was made."
    Write-Host "No password was generated."
    Write-Host "No Entra user was created or modified."
    Write-Host ""
    Write-Host (
        "A future approved execution must include " +
        "-Apply and -ApprovalText `"CREATE $EmployeeId`"."
    )

    exit 0
}

$expectedApproval = "CREATE $EmployeeId"

if (
    -not [string]::Equals(
        $ApprovalText,
        $expectedApproval,
        [System.StringComparison]::Ordinal
    )
) {
    throw (
        "Approval phrase mismatch. The exact required phrase is: " +
        $expectedApproval
    )
}

$TenantDomain = $TenantDomain.Trim().ToLowerInvariant()

foreach (
    $requiredFile in @(
        @{
            Path = $InputPath
            Description = "Joiner input file"
        },
        @{
            Path = $DryRunPlanPath
            Description = "Approved dry-run plan"
        },
        @{
            Path = $ValidatorPath
            Description = "Workforce validator"
        },
        @{
            Path = $GroupIdMapPath
            Description = "Group Object ID map"
        },
        @{
            Path = $AppRoleIdMapPath
            Description = "Application role ID map"
        }
    )
) {
    Assert-FileExists `
        -Path $requiredFile.Path `
        -Description $requiredFile.Description
}

if (-not (Get-Command Set-Clipboard -ErrorAction SilentlyContinue)) {
    throw (
        "Set-Clipboard is unavailable. The script will not create " +
        "a user because it cannot perform a safe password handoff."
    )
}

Ensure-ParentDirectory -Path $ValidationErrorPath
Ensure-ParentDirectory -Path $ValidationSummaryPath
Ensure-ParentDirectory -Path $ResultPath

Write-Host ""
Write-Host "STEP 1 - Revalidate approved input" `
    -ForegroundColor Cyan

$pwshPath = (Get-Command pwsh -ErrorAction Stop).Source
$resolvedValidatorPath =
    (Resolve-Path -LiteralPath $ValidatorPath).Path
$resolvedInputPath =
    (Resolve-Path -LiteralPath $InputPath).Path

$validatorArguments = @(
    "-NoProfile",
    "-File",
    $resolvedValidatorPath,
    "-InputPath",
    $resolvedInputPath,
    "-ErrorPath",
    $ValidationErrorPath,
    "-SummaryPath",
    $ValidationSummaryPath
)

& $pwshPath @validatorArguments

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "JOINER STOPPED" -ForegroundColor Red
    Write-Host "The input failed validation."
    Write-Host "Microsoft Graph was not contacted."
    Write-Host "No identity changes were attempted."

    exit 1
}

$matchingRows = @(
    Import-Csv -LiteralPath $resolvedInputPath |
        Where-Object {
            ([string]$_.employeeId).Trim() -eq $EmployeeId
        }
)

if ($matchingRows.Count -ne 1) {
    throw (
        "Expected exactly one CSV row for employeeId " +
        "$EmployeeId, but found $($matchingRows.Count)."
    )
}

$joiner = $matchingRows[0]

$displayName = ([string]$joiner.displayName).Trim()
$mailAlias = ([string]$joiner.mailAlias).Trim()
$jobRole = ([string]$joiner.jobRole).Trim()
$facility = ([string]$joiner.facility).Trim()
$status = ([string]$joiner.status).Trim()
$endDateText = ([string]$joiner.endDate).Trim()
$expectedUpn =
    "$mailAlias@$TenantDomain".ToLowerInvariant()

if ($status -ne "Active") {
    throw (
        "Joiner $EmployeeId is not Active. " +
        "Current status: $status"
    )
}

if (-not [string]::IsNullOrWhiteSpace($endDateText)) {
    $endDate = [datetime]::ParseExact(
        $endDateText,
        "yyyy-MM-dd",
        [System.Globalization.CultureInfo]::InvariantCulture
    )

    if ($endDate.Date -le [datetime]::Today) {
        throw (
            "Joiner $EmployeeId has reached endDate " +
            "$endDateText and cannot be created."
        )
    }
}

if (-not $roleGroupMap.ContainsKey($jobRole)) {
    throw "No group mapping exists for role $jobRole."
}

$expectedGroupName = $roleGroupMap[$jobRole]

$approvedPlans = @(
    Import-Csv -LiteralPath $DryRunPlanPath |
        Where-Object {
            ([string]$_.EmployeeId).Trim() -eq $EmployeeId
        }
)

if ($approvedPlans.Count -ne 1) {
    throw (
        "Expected exactly one approved dry-run decision for " +
        "$EmployeeId."
    )
}

$approvedPlan = $approvedPlans[0]

if ($approvedPlan.Action -ne "CREATE") {
    throw (
        "The approved dry-run action is " +
        "'$($approvedPlan.Action)', not CREATE."
    )
}

if (
    -not [string]::Equals(
        [string]$approvedPlan.ExpectedUPN,
        $expectedUpn,
        [System.StringComparison]::OrdinalIgnoreCase
    )
) {
    throw (
        "The approved UPN does not match the current Joiner input."
    )
}

$groupIdMap =
    Get-Content -Raw -LiteralPath $GroupIdMapPath |
    ConvertFrom-Json -AsHashtable

$appRoleIdMap =
    Get-Content -Raw -LiteralPath $AppRoleIdMapPath |
    ConvertFrom-Json -AsHashtable

if (-not $groupIdMap.ContainsKey($expectedGroupName)) {
    throw (
        "Group ID map does not contain $expectedGroupName."
    )
}

if (-not $appRoleIdMap.ContainsKey($jobRole)) {
    throw (
        "Application role ID map does not contain $jobRole."
    )
}

$targetGroupId =
    ([string]$groupIdMap[$expectedGroupName]).Trim()

$targetAppRoleId =
    ([string]$appRoleIdMap[$jobRole]).Trim()

Write-Host ""
Write-Host "STEP 2 - Connect to the explicit lab tenant" `
    -ForegroundColor Cyan

Import-Module Microsoft.Graph.Authentication -ErrorAction Stop
Import-Module Microsoft.Graph.Users -ErrorAction Stop
Import-Module Microsoft.Graph.Groups -ErrorAction Stop
Import-Module Microsoft.Graph.Applications -ErrorAction Stop

$requiredScopes = @(
    "User.ReadWrite.All",
    "GroupMember.ReadWrite.All",
    "Application.Read.All",
    "AppRoleAssignment.ReadWrite.All"
)

$graphConnected = $false
$temporaryPassword = ""
$createdUserId = ""
$resultRecord = $null
$finalExitCode = 0

try {
    Connect-MgGraph `
        -TenantId $TenantId `
        -Scopes $requiredScopes `
        -ContextScope Process `
        -NoWelcome

    $graphConnected = $true
    $graphContext = Get-MgContext

    if ($null -eq $graphContext) {
        throw "Microsoft Graph authentication context is missing."
    }

    if (
        -not [string]::Equals(
            [string]$graphContext.TenantId,
            $TenantId,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw (
            "Wrong tenant. Expected $TenantId but connected to " +
            "$($graphContext.TenantId)."
        )
    }

    foreach ($requiredScope in $requiredScopes) {
        if ($requiredScope -notin $graphContext.Scopes) {
            throw (
                "Required Graph scope is missing: $requiredScope"
            )
        }
    }

    Write-Host "Account: $($graphContext.Account)"
    Write-Host "Tenant: $($graphContext.TenantId)"
    Write-Host "Employee ID: $EmployeeId"
    Write-Host "Expected UPN: $expectedUpn"
    Write-Host "Expected group: $expectedGroupName"
    Write-Host "Expected application role: $jobRole"

    Write-Host ""
    Write-Host "STEP 3 - Resolve immutable target objects" `
        -ForegroundColor Cyan

    $targetGroup = Get-MgGroup `
        -GroupId $targetGroupId `
        -Property @(
            "id",
            "displayName",
            "securityEnabled"
        )

    if ($null -eq $targetGroup) {
        throw "The target security group was not found."
    }

    if (
        -not [string]::Equals(
            [string]$targetGroup.DisplayName,
            $expectedGroupName,
            [System.StringComparison]::Ordinal
        )
    ) {
        throw (
            "Group ID $targetGroupId belongs to " +
            "'$($targetGroup.DisplayName)', not " +
            "'$expectedGroupName'."
        )
    }

    if (-not [bool]$targetGroup.SecurityEnabled) {
        throw "$expectedGroupName is not a security group."
    }

    $escapedApplicationName =
        $ApplicationDisplayName.Replace("'", "''")

    $servicePrincipals = @(
        Get-MgServicePrincipal `
            -Filter (
                "displayName eq '$escapedApplicationName'"
            ) `
            -All `
            -Property @(
                "id",
                "appId",
                "displayName",
                "appRoles"
            )
    )

    if ($servicePrincipals.Count -ne 1) {
        throw (
            "Expected exactly one enterprise application named " +
            "'$ApplicationDisplayName', but found " +
            "$($servicePrincipals.Count)."
        )
    }

    $servicePrincipal = $servicePrincipals[0]

    $matchingAppRoles = @(
        $servicePrincipal.AppRoles |
            Where-Object {
                ([string]$_.Id) -eq $targetAppRoleId
            }
    )

    if ($matchingAppRoles.Count -ne 1) {
        throw (
            "The saved appRoleId was not found on the " +
            "enterprise application."
        )
    }

    $targetAppRole = $matchingAppRoles[0]

    if (
        -not [string]::Equals(
            [string]$targetAppRole.Value,
            $jobRole,
            [System.StringComparison]::Ordinal
        )
    ) {
        throw (
            "The saved appRoleId represents role " +
            "'$($targetAppRole.Value)', not '$jobRole'."
        )
    }

    if (-not [bool]$targetAppRole.IsEnabled) {
        throw "The $jobRole application role is disabled."
    }

    if ("User" -notin $targetAppRole.AllowedMemberTypes) {
        throw (
            "The $jobRole application role cannot be " +
            "assigned directly to users."
        )
    }

    Write-Host ""
    Write-Host "STEP 4 - Recheck for an existing identity" `
        -ForegroundColor Cyan

    $allUsers = @(
        Get-MgUser `
            -All `
            -Property @(
                "id",
                "accountEnabled",
                "displayName",
                "employeeId",
                "userPrincipalName",
                "jobTitle",
                "department",
                "officeLocation"
            )
    )

    $candidateMap = @{}

    foreach ($directoryUser in $allUsers) {
        $employeeIdMatches = (
            -not [string]::IsNullOrWhiteSpace(
                [string]$directoryUser.EmployeeId
            ) -and
            [string]::Equals(
                ([string]$directoryUser.EmployeeId).Trim(),
                $EmployeeId,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        )

        $upnMatches = [string]::Equals(
            ([string]$directoryUser.UserPrincipalName).Trim(),
            $expectedUpn,
            [System.StringComparison]::OrdinalIgnoreCase
        )

        if ($employeeIdMatches -or $upnMatches) {
            $candidateMap[[string]$directoryUser.Id] =
                $directoryUser
        }
    }

    $existingCandidates = @($candidateMap.Values)

    if ($existingCandidates.Count -gt 1) {
        throw (
            "More than one Entra user matched employeeId or UPN. " +
            "No Joiner action was performed."
        )
    }

    if ($existingCandidates.Count -eq 1) {
        $existingUser = $existingCandidates[0]

        $differences =
            [System.Collections.Generic.List[string]]::new()

        if (
            -not [string]::Equals(
                [string]$existingUser.DisplayName,
                $displayName,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            [void]$differences.Add("displayName")
        }

        if (
            -not [string]::Equals(
                [string]$existingUser.EmployeeId,
                $EmployeeId,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            [void]$differences.Add("employeeId")
        }

        if (
            -not [string]::Equals(
                [string]$existingUser.UserPrincipalName,
                $expectedUpn,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            [void]$differences.Add("userPrincipalName")
        }

        if (
            -not [string]::Equals(
                [string]$existingUser.JobTitle,
                $jobRole,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            [void]$differences.Add("jobTitle")
        }

        if (
            -not [string]::Equals(
                [string]$existingUser.Department,
                $facility,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            [void]$differences.Add("department")
        }

        if (
            -not [string]::Equals(
                [string]$existingUser.OfficeLocation,
                $facility,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            [void]$differences.Add("officeLocation")
        }

        if (-not [bool]$existingUser.AccountEnabled) {
            [void]$differences.Add("accountEnabled")
        }

        $targetGroupMembers = @(
            Get-MgGroupMember `
                -GroupId $targetGroupId `
                -All
        )

        $hasExpectedGroup = (
            [string]$existingUser.Id -in
            @($targetGroupMembers.Id | ForEach-Object {
                [string]$_
            })
        )

        if (-not $hasExpectedGroup) {
            [void]$differences.Add(
                "group:$expectedGroupName"
            )
        }

        $existingAppAssignments = @(
            Get-MgUserAppRoleAssignment `
                -UserId $existingUser.Id `
                -All
        )

        $hasExpectedAppRole = @(
            $existingAppAssignments |
                Where-Object {
                    ([string]$_.ResourceId) -eq
                        ([string]$servicePrincipal.Id) -and
                    ([string]$_.AppRoleId) -eq
                        $targetAppRoleId
                }
        ).Count -eq 1

        if (-not $hasExpectedAppRole) {
            [void]$differences.Add("appRole:$jobRole")
        }

        if ($differences.Count -eq 0) {
            $resultRecord = [ordered]@{
                EventTimeUtc =
                    [datetime]::UtcNow.ToString("o")
                Operation = "JOINER"
                Outcome = "NO CHANGE"
                EmployeeId = $EmployeeId
                UserPrincipalName =
                    [string]$existingUser.UserPrincipalName
                UserObjectId = [string]$existingUser.Id
                TargetGroup = $expectedGroupName
                TargetGroupObjectId = $targetGroupId
                EnterpriseApplication =
                    $ApplicationDisplayName
                ServicePrincipalObjectId =
                    [string]$servicePrincipal.Id
                AppRole = $jobRole
                AppRoleId = $targetAppRoleId
                PasswordRecorded = $false
                WriteOperationsExecuted = 0
                Message = (
                    "The existing identity already matches " +
                    "the approved Joiner state."
                )
            }

            $finalExitCode = 0
        }
        else {
            $resultRecord = [ordered]@{
                EventTimeUtc =
                    [datetime]::UtcNow.ToString("o")
                Operation = "JOINER"
                Outcome = "UPDATE REQUIRED"
                EmployeeId = $EmployeeId
                UserPrincipalName =
                    [string]$existingUser.UserPrincipalName
                UserObjectId = [string]$existingUser.Id
                Differences = @($differences)
                PasswordRecorded = $false
                WriteOperationsExecuted = 0
                Message = (
                    "The Joiner workflow found an existing " +
                    "identity and refused to create a duplicate."
                )
            }

            $finalExitCode = 2
        }
    }
    else {
        Write-Host ""
        Write-Host "STEP 5 - Create the approved Joiner" `
            -ForegroundColor Cyan

        $temporaryPassword =
            New-CryptographicPassword -Length 20

        $passwordProfile = @{
            password = $temporaryPassword
            forceChangePasswordNextSignIn = $true
        }

        $newUserBody = @{
            accountEnabled = $true
            displayName = $displayName
            mailNickname = $mailAlias
            userPrincipalName = $expectedUpn
            passwordProfile = $passwordProfile
            employeeId = $EmployeeId
            jobTitle = $jobRole
            department = $facility
            officeLocation = $facility
            usageLocation = "AU"
        }

        $createdUser =
            New-MgUser `
                -BodyParameter $newUserBody

        if (
            $null -eq $createdUser -or
            [string]::IsNullOrWhiteSpace(
                [string]$createdUser.Id
            )
        ) {
            throw "Graph did not return the created user Object ID."
        }

        $createdUserId = [string]$createdUser.Id

        Write-Host "Created user Object ID: $createdUserId"

        $userReadbackVerified = Wait-ForDesiredState `
            -Description "Created user" `
            -NotFoundMeansPending `
            -Readback {
                $readbackUser = Get-MgUser `
                    -UserId $createdUserId `
                    -Property @(
                        "id",
                        "accountEnabled",
                        "employeeId",
                        "userPrincipalName"
                    )

                return (
                    [string]$readbackUser.Id -eq $createdUserId -and
                    [bool]$readbackUser.AccountEnabled -and
                    [string]$readbackUser.EmployeeId -eq $EmployeeId -and
                    [string]$readbackUser.UserPrincipalName -eq $expectedUpn
                )
            }

        if (-not $userReadbackVerified) {
            throw "Created user readback verification failed."
        }

        Invoke-WithRetry `
            -Description "Group membership assignment" `
            -Operation {
                New-MgGroupMemberByRef `
                    -GroupId $targetGroupId `
                    -OdataId (
                        "https://graph.microsoft.com/v1.0/" +
                        "directoryObjects/$createdUserId"
                    ) |
                    Out-Null
            }

        Write-Host (
            "Added group: $expectedGroupName"
        )

        $groupReadbackVerified = Wait-ForDesiredState `
            -Description "Group membership" `
            -Readback {
                $readbackMemberIds = @(
                    Get-MgGroupMember `
                        -GroupId $targetGroupId `
                        -All |
                        ForEach-Object {
                            [string]$_.Id
                        }
                )

                return ($createdUserId -in $readbackMemberIds)
            }

        if (-not $groupReadbackVerified) {
            throw "Group membership readback verification failed."
        }

        Invoke-WithRetry `
            -Description "Application role assignment" `
            -Operation {
                New-MgUserAppRoleAssignment `
                    -UserId $createdUserId `
                    -PrincipalId $createdUserId `
                    -ResourceId $servicePrincipal.Id `
                    -AppRoleId $targetAppRoleId |
                    Out-Null
            }

        Write-Host "Assigned application role: $jobRole"

        $appRoleReadbackVerified = Wait-ForDesiredState `
            -Description "Application role" `
            -Readback {
                $readbackAssignments = @(
                    Get-MgUserAppRoleAssignment `
                        -UserId $createdUserId `
                        -All
                )

                return @(
                    $readbackAssignments |
                        Where-Object {
                            [string]$_.ResourceId -eq
                                [string]$servicePrincipal.Id -and
                            [string]$_.AppRoleId -eq $targetAppRoleId
                        }
                ).Count -eq 1
            }

        if (-not $appRoleReadbackVerified) {
            throw "Application role readback verification failed."
        }

        Write-Host ""
        Write-Host "STEP 6 - Verify final desired state" `
            -ForegroundColor Cyan

        $verifiedUser =
            Get-MgUser `
                -UserId $createdUserId `
                -Property @(
                    "id",
                    "accountEnabled",
                    "displayName",
                    "employeeId",
                    "userPrincipalName",
                    "jobTitle",
                    "department",
                    "officeLocation"
                )

        if (-not [bool]$verifiedUser.AccountEnabled) {
            throw "Created user is unexpectedly disabled."
        }

        if (
            -not [string]::Equals(
                [string]$verifiedUser.EmployeeId,
                $EmployeeId,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw "Created user employeeId verification failed."
        }

        $verifiedMembers = @(
            Get-MgGroupMember `
                -GroupId $targetGroupId `
                -All
        )

        $groupVerified = (
            $createdUserId -in
            @($verifiedMembers.Id | ForEach-Object {
                [string]$_
            })
        )

        if (-not $groupVerified) {
            throw "Group membership verification failed."
        }

        $verifiedAppAssignments = @(
            Get-MgUserAppRoleAssignment `
                -UserId $createdUserId `
                -All
        )

        $appRoleVerified = @(
            $verifiedAppAssignments |
                Where-Object {
                    ([string]$_.ResourceId) -eq
                        ([string]$servicePrincipal.Id) -and
                    ([string]$_.AppRoleId) -eq
                        $targetAppRoleId
                }
        ).Count -eq 1

        if (-not $appRoleVerified) {
            throw "Application role verification failed."
        }

        $resultRecord = [ordered]@{
            EventTimeUtc = [datetime]::UtcNow.ToString("o")
            Operation = "JOINER"
            Outcome = "CREATED"
            EmployeeId = $EmployeeId
            DisplayName = $displayName
            UserPrincipalName = $expectedUpn
            UserObjectId = $createdUserId
            AccountEnabled = $true
            ForceChangePasswordNextSignIn = $true
            JobTitle = $jobRole
            Department = $facility
            OfficeLocation = $facility
            TargetGroup = $expectedGroupName
            TargetGroupObjectId = $targetGroupId
            GroupMembershipVerified = $true
            EnterpriseApplication =
                $ApplicationDisplayName
            ServicePrincipalObjectId =
                [string]$servicePrincipal.Id
            AppRole = $jobRole
            AppRoleId = $targetAppRoleId
            AppRoleVerified = $true
            PasswordRecorded = $false
            WriteOperationsExecuted = 3
            Message = (
                "One enabled Joiner identity was created " +
                "with the approved group and application role."
            )
        }

        $finalExitCode = 0
    }
}
catch {
    $safeErrorMessage = $_.Exception.Message

    if (
        -not [string]::IsNullOrWhiteSpace(
            $temporaryPassword
        )
    ) {
        $safeErrorMessage =
            $safeErrorMessage.Replace(
                $temporaryPassword,
                "[REDACTED]"
            )
    }

    $rollbackMessage = "No created user required disabling."

    if (
        -not [string]::IsNullOrWhiteSpace(
            $createdUserId
        )
    ) {
        try {
            Update-MgUser `
                -UserId $createdUserId `
                -AccountEnabled:$false

            $rollbackMessage = (
                "The partially provisioned identity was " +
                "disabled after the failure."
            )
        }
        catch {
            $rollbackMessage = (
                "WARNING: automatic disable failed. " +
                "Immediately inspect and disable Object ID " +
                "$createdUserId."
            )
        }
    }

    $resultRecord = [ordered]@{
        EventTimeUtc = [datetime]::UtcNow.ToString("o")
        Operation = "JOINER"
        Outcome = "FAILED"
        EmployeeId = $EmployeeId
        UserPrincipalName = $expectedUpn
        UserObjectId = $createdUserId
        Error = $safeErrorMessage
        Rollback = $rollbackMessage
        PasswordRecorded = $false
        Message = "Joiner provisioning did not complete."
    }

    $finalExitCode = 1
}
finally {
    if ($graphConnected) {
        Disconnect-MgGraph -ErrorAction SilentlyContinue |
            Out-Null
    }
}

Write-SanitizedResult `
    -Result $resultRecord `
    -Path $ResultPath

if (
    $resultRecord.Outcome -eq "CREATED" -and
    -not [string]::IsNullOrWhiteSpace(
        $temporaryPassword
    )
) {
    try {
        Set-Clipboard -Value $temporaryPassword

        Write-Host ""
        Write-Host "SECURE PASSWORD HANDOFF" `
            -ForegroundColor Yellow

        Write-Host (
            "The temporary password was copied to the " +
            "macOS clipboard. It was not printed or saved."
        )

        Write-Host (
            "Paste it into your password manager. " +
            "Do not paste it into evidence, Git, Notes or chat."
        )

        Read-Host (
            "After storing it securely, press Enter to " +
            "clear the clipboard"
        ) |
            Out-Null

        Set-Clipboard -Value ""
    }
    catch {
        Write-Host ""
        Write-Host (
            "The account was created, but clipboard handoff " +
            "failed. The password was not displayed or saved. " +
            "Reset the temporary password in Entra before login."
        ) -ForegroundColor Red

        $finalExitCode = 3
    }
}

$temporaryPassword = ""
$passwordProfile = $null

Write-Host ""
Write-Host "SANITIZED JOINER RESULT" `
    -ForegroundColor Cyan

Write-Host "Outcome: $($resultRecord.Outcome)"
Write-Host "Employee ID: $EmployeeId"
Write-Host "User Object ID: $($resultRecord.UserObjectId)"
Write-Host "Result file: $ResultPath"
Write-Host "Password recorded: False"

if ($resultRecord.Outcome -eq "CREATED") {
    Write-Host (
        "The next phase will verify the profile, " +
        "assignments, first sign-in, MFA and app access."
    )
}

exit $finalExitCode
