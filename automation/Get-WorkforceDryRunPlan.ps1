[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TenantId,

    [Parameter(Mandatory = $true)]
    [string]$TenantDomain,

    [string]$InputPath = "./data/workforce.csv",

    [string]$ValidatorPath =
        "./automation/Test-WorkforceInput.ps1",

    [string]$ValidationErrorPath =
        "./evidence/phase5/P5-E07_Dry-Run-Validation-Errors.csv",

    [string]$ValidationSummaryPath =
        "./evidence/phase5/P5-E07_Dry-Run-Validation.txt",

    [string]$PlanPath =
        "./evidence/phase5/P5-E08_Dry-Run-Plan.csv",

    [string]$SummaryPath =
        "./evidence/phase5/P5-E09_Dry-Run-Summary.txt",

    [datetime]$AsOfDate = [datetime]::Today
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$roleGroupMap = @{
    CareWorker  = "SG-SC-CareWorkers"
    Nurse       = "SG-SC-Nurses"
    Manager     = "SG-SC-Managers"
    AgencyWorker = "SG-SC-AgencyWorkers"
    Auditor     = "SG-SC-Auditors"
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


function Normalize-Key {
    param(
        [AllowNull()]
        [object]$Value
    )

    if ($null -eq $Value) {
        return ""
    }

    return ([string]$Value).Trim().ToLowerInvariant()
}


function Add-ToIndex {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Index,

        [AllowEmptyString()]
        [string]$Key,

        [Parameter(Mandatory = $true)]
        [object]$Value
    )

    $normalizedKey = Normalize-Key -Value $Key

    if ([string]::IsNullOrWhiteSpace($normalizedKey)) {
        return
    }

    if (-not $Index.ContainsKey($normalizedKey)) {
        $Index[$normalizedKey] =
            [System.Collections.Generic.List[object]]::new()
    }

    [void]($Index[$normalizedKey].Add($Value))
}


function ConvertTo-ComparisonText {
    param(
        [AllowNull()]
        [object]$Value
    )

    if (
        $null -eq $Value -or
        [string]::IsNullOrWhiteSpace([string]$Value)
    ) {
        return "<blank>"
    }

    return ([string]$Value).Trim()
}


function Add-AttributeChange {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[string]]$ChangeList,

        [Parameter(Mandatory = $true)]
        [string]$Field,

        [AllowNull()]
        [object]$CurrentValue,

        [AllowNull()]
        [object]$ExpectedValue
    )

    $currentText = ConvertTo-ComparisonText -Value $CurrentValue
    $expectedText = ConvertTo-ComparisonText -Value $ExpectedValue

    if (
        -not [string]::Equals(
            $currentText,
            $expectedText,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        [void]$ChangeList.Add(
            "${Field}: '$currentText' -> '$expectedText'"
        )
    }
}


foreach (
    $outputPath in @(
        $ValidationErrorPath,
        $ValidationSummaryPath,
        $PlanPath,
        $SummaryPath
    )
) {
    Ensure-ParentDirectory -Path $outputPath
}

if (-not (Test-Path -LiteralPath $InputPath)) {
    throw "The workforce input file does not exist: $InputPath"
}

if (-not (Test-Path -LiteralPath $ValidatorPath)) {
    throw "The Step 5.1B validator does not exist: $ValidatorPath"
}

$resolvedInputPath = (Resolve-Path -LiteralPath $InputPath).Path
$resolvedValidatorPath =
    (Resolve-Path -LiteralPath $ValidatorPath).Path

$TenantDomain = $TenantDomain.Trim().ToLowerInvariant()

Write-Host ""
Write-Host "STEP 1 - Validate the workforce input" `
    -ForegroundColor Cyan

$pwshPath = (Get-Command pwsh -ErrorAction Stop).Source

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

$validatorExitCode = $LASTEXITCODE

if ($validatorExitCode -ne 0) {
    Write-Host ""
    Write-Host "DRY-RUN STOPPED" -ForegroundColor Red
    Write-Host "The input failed Step 5.1B validation."
    Write-Host "Microsoft Graph was not contacted."
    Write-Host "No directory changes were attempted."

    exit 1
}

$workforceRows = @(Import-Csv -LiteralPath $resolvedInputPath)

Write-Host ""
Write-Host "STEP 2 - Connect using read-only Graph permission" `
    -ForegroundColor Cyan

Import-Module Microsoft.Graph.Authentication -ErrorAction Stop
Import-Module Microsoft.Graph.Users -ErrorAction Stop

$graphConnected = $false
$graphFailureMessage = $null
$graphUsers = @()
$authenticatedAccount = ""
$plan = [System.Collections.Generic.List[object]]::new()
$plannerHasConflict = $false

try {
    Connect-MgGraph `
        -TenantId $TenantId `
        -Scopes "User.Read.All" `
        -ContextScope Process `
        -NoWelcome

    $graphConnected = $true
    $graphContext = Get-MgContext

    if ($null -eq $graphContext) {
        throw "Microsoft Graph did not return an authentication context."
    }

    if (
        -not [string]::Equals(
            [string]$graphContext.TenantId,
            $TenantId,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw (
            "Connected to the wrong tenant. Expected $TenantId " +
            "but received $($graphContext.TenantId)."
        )
    }

    if ("User.Read.All" -notin $graphContext.Scopes) {
        throw "The Graph session does not contain User.Read.All."
    }

    $authenticatedAccount = [string]$graphContext.Account

    Write-Host "Authenticated account: $authenticatedAccount"
    Write-Host "Authenticated tenant: $($graphContext.TenantId)"
    Write-Host "Requested permission: User.Read.All"
    Write-Host ""
    Write-Host "Reading Entra users..." -ForegroundColor Cyan

    $graphProperties = @(
        "id",
        "accountEnabled",
        "displayName",
        "employeeId",
        "userPrincipalName",
        "jobTitle",
        "officeLocation",
        "userType"
    )

    $graphUsers = @(
        Get-MgUser `
            -All `
            -Property $graphProperties
    )

    Write-Host "Users read from Entra: $($graphUsers.Count)"

    $usersByEmployeeId = @{}
    $usersByUpn = @{}

    foreach ($graphUser in $graphUsers) {
        Add-ToIndex `
            -Index $usersByEmployeeId `
            -Key ([string]$graphUser.EmployeeId) `
            -Value $graphUser

        Add-ToIndex `
            -Index $usersByUpn `
            -Key ([string]$graphUser.UserPrincipalName) `
            -Value $graphUser
    }

    Write-Host ""
    Write-Host "STEP 3 - Calculate proposed actions" `
        -ForegroundColor Cyan

    foreach ($workforceRow in $workforceRows) {
        $employeeId = ([string]$workforceRow.employeeId).Trim()
        $displayName = ([string]$workforceRow.displayName).Trim()
        $mailAlias = ([string]$workforceRow.mailAlias).Trim()
        $jobRole = ([string]$workforceRow.jobRole).Trim()
        $facility = ([string]$workforceRow.facility).Trim()
        $status = ([string]$workforceRow.status).Trim()
        $endDateText = ([string]$workforceRow.endDate).Trim()

        $expectedUpn =
            "$mailAlias@$TenantDomain".ToLowerInvariant()

        $expectedGroup = $roleGroupMap[$jobRole]

        $endDate = $null

        if (-not [string]::IsNullOrWhiteSpace($endDateText)) {
            $endDate = [datetime]::ParseExact(
                $endDateText,
                "yyyy-MM-dd",
                [System.Globalization.CultureInfo]::InvariantCulture
            )
        }

        $endDateExpired = (
            $null -ne $endDate -and
            $endDate.Date -le $AsOfDate.Date
        )

        $requiresDisabledAccount = (
            $status -eq "Inactive" -or
            $endDateExpired
        )

        $candidateMap = @{}

        $employeeKey = Normalize-Key -Value $employeeId
        $upnKey = Normalize-Key -Value $expectedUpn

        if ($usersByEmployeeId.ContainsKey($employeeKey)) {
            foreach (
                $candidate in $usersByEmployeeId[$employeeKey]
            ) {
                $candidateMap[[string]$candidate.Id] = $candidate
            }
        }

        if ($usersByUpn.ContainsKey($upnKey)) {
            foreach ($candidate in $usersByUpn[$upnKey]) {
                $candidateMap[[string]$candidate.Id] = $candidate
            }
        }

        $candidates = @($candidateMap.Values)

        if ($candidates.Count -gt 1) {
            $plannerHasConflict = $true

            $conflictUsers = @(
                $candidates |
                    ForEach-Object {
                        "$($_.UserPrincipalName) [$($_.Id)]"
                    }
            ) -join "; "

            [void]$plan.Add(
                [pscustomobject]@{
                    EmployeeId           = $employeeId
                    DisplayName          = $displayName
                    JobRole              = $jobRole
                    Facility             = $facility
                    WorkforceStatus      = $status
                    EndDate              = $endDateText
                    ExpectedUPN          = $expectedUpn
                    ExpectedGroup        = $expectedGroup
                    EntraObjectId         = ""
                    CurrentUPN           = ""
                    CurrentAccountEnabled = ""
                    Action               = "ERROR"
                    Changes              = ""
                    Reason               = (
                        "employeeId and expected UPN matched " +
                        "different Entra users: $conflictUsers"
                    )
                }
            )

            continue
        }

        if ($candidates.Count -eq 0) {
            if ($requiresDisabledAccount) {
                $action = "NO CHANGE"
                $reason = (
                    "No Entra account exists and this workforce " +
                    "record does not permit active access."
                )
            }
            else {
                $action = "CREATE"
                $reason = (
                    "No Entra user matched the employeeId or " +
                    "expected UPN."
                )
            }

            [void]$plan.Add(
                [pscustomobject]@{
                    EmployeeId           = $employeeId
                    DisplayName          = $displayName
                    JobRole              = $jobRole
                    Facility             = $facility
                    WorkforceStatus      = $status
                    EndDate              = $endDateText
                    ExpectedUPN          = $expectedUpn
                    ExpectedGroup        = $expectedGroup
                    EntraObjectId         = ""
                    CurrentUPN           = ""
                    CurrentAccountEnabled = ""
                    Action               = $action
                    Changes              = ""
                    Reason               = $reason
                }
            )

            continue
        }

        $matchedUser = $candidates[0]
        $currentAccountEnabled = [bool]$matchedUser.AccountEnabled

        if ($requiresDisabledAccount) {
            if ($currentAccountEnabled) {
                $action = "DISABLE"
                $changes = "accountEnabled: 'True' -> 'False'"
                $reason = (
                    "The workforce record is Inactive or its " +
                    "endDate has been reached."
                )
            }
            else {
                $action = "NO CHANGE"
                $changes = ""
                $reason = (
                    "The workforce record no longer permits " +
                    "access and the Entra account is already disabled."
                )
            }
        }
        else {
            $attributeChanges =
                [System.Collections.Generic.List[string]]::new()

            Add-AttributeChange `
                -ChangeList $attributeChanges `
                -Field "displayName" `
                -CurrentValue $matchedUser.DisplayName `
                -ExpectedValue $displayName

            Add-AttributeChange `
                -ChangeList $attributeChanges `
                -Field "employeeId" `
                -CurrentValue $matchedUser.EmployeeId `
                -ExpectedValue $employeeId

            Add-AttributeChange `
                -ChangeList $attributeChanges `
                -Field "userPrincipalName" `
                -CurrentValue $matchedUser.UserPrincipalName `
                -ExpectedValue $expectedUpn

            Add-AttributeChange `
                -ChangeList $attributeChanges `
                -Field "jobTitle" `
                -CurrentValue $matchedUser.JobTitle `
                -ExpectedValue $jobRole

            Add-AttributeChange `
                -ChangeList $attributeChanges `
                -Field "officeLocation" `
                -CurrentValue $matchedUser.OfficeLocation `
                -ExpectedValue $facility

            if (-not $currentAccountEnabled) {
                [void]$attributeChanges.Add(
                    "accountEnabled: 'False' -> 'True'"
                )
            }

            if ($attributeChanges.Count -gt 0) {
                $action = "UPDATE"
                $changes = $attributeChanges -join "; "
                $reason = (
                    "The Entra user exists but one or more " +
                    "attributes differ."
                )
            }
            else {
                $action = "NO CHANGE"
                $changes = ""
                $reason = (
                    "The Entra user already matches the " +
                    "workforce identity attributes."
                )
            }
        }

        [void]$plan.Add(
            [pscustomobject]@{
                EmployeeId            = $employeeId
                DisplayName           = $displayName
                JobRole               = $jobRole
                Facility              = $facility
                WorkforceStatus       = $status
                EndDate               = $endDateText
                ExpectedUPN           = $expectedUpn
                ExpectedGroup         = $expectedGroup
                EntraObjectId          = [string]$matchedUser.Id
                CurrentUPN            =
                    [string]$matchedUser.UserPrincipalName
                CurrentAccountEnabled =
                    [string]$matchedUser.AccountEnabled
                Action                = $action
                Changes               = $changes
                Reason                = $reason
            }
        )
    }
}
catch {
    $graphFailureMessage = $_.Exception.Message
}
finally {
    if ($graphConnected) {
        Disconnect-MgGraph -ErrorAction SilentlyContinue |
            Out-Null
    }
}

if (-not [string]::IsNullOrWhiteSpace($graphFailureMessage)) {
    $failureSummary = @(
        "Sunhaven workforce dry-run planner",
        "------------------------------------",
        "Generated UTC: $([datetime]::UtcNow.ToString('o'))",
        "Tenant ID: $TenantId",
        "Tenant domain: $TenantDomain",
        "Result: FAIL",
        "Error: $graphFailureMessage",
        "Write operations executed: 0"
    )

    $failureSummary |
        Set-Content `
            -LiteralPath $SummaryPath `
            -Encoding utf8

    Write-Host ""
    Write-Host "DRY-RUN FAILED" -ForegroundColor Red
    Write-Host $graphFailureMessage
    Write-Host "Write operations executed: 0"

    exit 1
}

$plan |
    Export-Csv `
        -LiteralPath $PlanPath `
        -NoTypeInformation `
        -Encoding utf8

$createCount = @(
    $plan | Where-Object Action -eq "CREATE"
).Count

$updateCount = @(
    $plan | Where-Object Action -eq "UPDATE"
).Count

$disableCount = @(
    $plan | Where-Object Action -eq "DISABLE"
).Count

$noChangeCount = @(
    $plan | Where-Object Action -eq "NO CHANGE"
).Count

$errorCount = @(
    $plan | Where-Object Action -eq "ERROR"
).Count

$overallResult = if ($plannerHasConflict) {
    "BLOCKED"
}
else {
    "PASS"
}

$summaryLines = @(
    "Sunhaven workforce Graph dry-run",
    "----------------------------------",
    "Generated UTC: $([datetime]::UtcNow.ToString('o'))",
    "As-of date: $($AsOfDate.ToString('yyyy-MM-dd'))",
    "Tenant ID: $TenantId",
    "Tenant domain: $TenantDomain",
    "Authenticated account: $authenticatedAccount",
    "Graph permission requested: User.Read.All",
    "Entra users read: $($graphUsers.Count)",
    "Workforce records examined: $($workforceRows.Count)",
    "CREATE: $createCount",
    "UPDATE: $updateCount",
    "DISABLE: $disableCount",
    "NO CHANGE: $noChangeCount",
    "ERROR: $errorCount",
    "Result: $overallResult",
    "Write operations executed: 0",
    "Plan file: $PlanPath"
)

$summaryLines |
    Set-Content `
        -LiteralPath $SummaryPath `
        -Encoding utf8

Write-Host ""
Write-Host "DRY-RUN PLAN" -ForegroundColor Cyan

$plan |
    Format-Table `
        EmployeeId,
        Action,
        ExpectedUPN,
        WorkforceStatus,
        EndDate `
        -AutoSize

Write-Host ""
Write-Host "CREATE: $createCount"
Write-Host "UPDATE: $updateCount"
Write-Host "DISABLE: $disableCount"
Write-Host "NO CHANGE: $noChangeCount"
Write-Host "ERROR: $errorCount"
Write-Host "Write operations executed: 0"
Write-Host "Plan saved to: $PlanPath"
Write-Host "Summary saved to: $SummaryPath"

if ($plannerHasConflict) {
    Write-Host ""
    Write-Host "Result: BLOCKED" -ForegroundColor Red
    Write-Host (
        "Resolve the ambiguous identity matches before " +
        "performing any lifecycle operation."
    )

    exit 2
}

Write-Host ""
Write-Host "Result: PASS" -ForegroundColor Green
Write-Host (
    "This was a read-only plan. No Entra users were changed."
)

exit 0
