# Sunhaven Phase 6.3 access-review remediation.
# Removes only one denied DefaultAccess enterprise-app assignment.

param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TenantId,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ExpectedDeniedObjectId,

    [ValidateNotNullOrEmpty()]
    [string]$ApplicationDisplayName = "Sunhaven Care Portal - LAB",

    [ValidateNotNullOrEmpty()]
    [string]$ReviewCsvPath =
        "./evidence/phase6/P6-E19_Completed-Access-Review.csv",

    [ValidateNotNullOrEmpty()]
    [string]$ResultPath =
        "./evidence/phase6/P6-E21_Access-Review-Remediation.json",

    [switch]$Apply,

    [string]$ApprovalText = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$defaultAccessRoleId =
    "00000000-0000-0000-0000-000000000000"

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

function Write-RemediationResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Mode,

        [Parameter(Mandatory = $true)]
        [string]$Outcome,

        [Parameter(Mandatory = $true)]
        [int]$WriteOperations,

        [Parameter(Mandatory = $true)]
        [bool]$AssignmentAbsent,

        [AllowEmptyString()]
        [string]$AssignmentId = "",

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $result = [pscustomobject][ordered]@{
        GeneratedUtc              = [datetime]::UtcNow.ToString("o")
        Mode                      = $Mode
        TenantId                  = $TenantId
        Application               = $ApplicationDisplayName
        ReviewEvidence            = $ReviewCsvPath
        ReviewDecision            = $deniedRow.ReviewDecision
        Reviewer                  = $deniedRow.Reviewer
        ReviewDate                = $deniedRow.ReviewDate
        TargetDisplayName         = $directoryUser.DisplayName
        TargetUserPrincipalName   = $directoryUser.UserPrincipalName
        TargetObjectId            = $directoryUser.Id
        ExpectedAppRole           = "DefaultAccess"
        ExpectedAppRoleId         = $defaultAccessRoleId
        AppRoleAssignmentId       = $AssignmentId
        Action                    = "REMOVE_DEFAULT_ACCESS_ASSIGNMENT"
        Outcome                   = $Outcome
        AssignmentAbsent          = $AssignmentAbsent
        WriteOperationsExecuted   = $WriteOperations
        Message                   = $Message
    }

    $result |
        ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath $ResultPath -Encoding utf8

    return $result
}

$requiredCommands = @(
    "Connect-MgGraph",
    "Get-MgContext",
    "Get-MgUser",
    "Get-MgServicePrincipal",
    "Get-MgUserAppRoleAssignment",
    "Remove-MgUserAppRoleAssignment"
)

foreach ($commandName in $requiredCommands) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required Microsoft Graph command is missing: $commandName"
    }
}

if (-not (Test-Path -LiteralPath $ReviewCsvPath)) {
    throw "Completed access-review CSV was not found: $ReviewCsvPath"
}

Ensure-ParentDirectory -Path $ResultPath

Write-Host "STEP 1 - Validate the completed manager review"

$reviewRows = @(Import-Csv -LiteralPath $ReviewCsvPath)
$deniedRows = @(
    $reviewRows |
        Where-Object {
            $_.ReviewDecision -eq "Deny"
        }
)

if ($deniedRows.Count -ne 1) {
    throw (
        "STOP: Expected exactly one Deny decision, but found " +
        "$($deniedRows.Count)."
    )
}

$deniedRow = $deniedRows[0]

if ($deniedRow.ObjectId -ne $ExpectedDeniedObjectId) {
    throw (
        "STOP: The denied Object ID does not match the approved target. " +
        "Review: $($deniedRow.ObjectId); expected: " +
        "$ExpectedDeniedObjectId."
    )
}

if ($deniedRow.CareAppRoles -ne "DefaultAccess") {
    throw (
        "STOP: The denied assignment is not exactly DefaultAccess. " +
        "Actual value: $($deniedRow.CareAppRoles)"
    )
}

if ($deniedRow.GovernedGroups -ne "<none>") {
    throw (
        "STOP: The denied row includes a governed group. " +
        "This script is intentionally limited to one app assignment."
    )
}

foreach ($requiredReviewField in @(
    "Reviewer",
    "ReviewDate",
    "Reason",
    "Remediation"
)) {
    if (
        [string]::IsNullOrWhiteSpace(
            [string]$deniedRow.$requiredReviewField
        )
    ) {
        throw "STOP: Review field is blank: $requiredReviewField"
    }
}

$requiredApproval =
    "REMOVE DEFAULTACCESS $ExpectedDeniedObjectId"

if ($Apply -and $ApprovalText -ne $requiredApproval) {
    throw (
        "STOP: Approval text did not match. Required text: " +
        $requiredApproval
    )
}

Write-Host "Decision: Deny"
Write-Host "Target: $($deniedRow.DisplayName)"
Write-Host "Object ID: $ExpectedDeniedObjectId"
Write-Host "Assignment: DefaultAccess"

Write-Host "STEP 2 - Connect to the verified tenant"

$requestedScopes = @(
    "User.Read.All",
    "Application.Read.All"
)

if ($Apply) {
    $requestedScopes += "AppRoleAssignment.ReadWrite.All"
}

Connect-MgGraph `
    -TenantId $TenantId `
    -Scopes $requestedScopes `
    -NoWelcome

$context = Get-MgContext

if (-not $context -or $context.TenantId -ne $TenantId) {
    throw "STOP: Microsoft Graph tenant verification failed."
}

Write-Host "Authenticated tenant: $($context.TenantId)"
Write-Host (
    "Mode: " +
    $(if ($Apply) { "APPLY" } else { "SAFE - NO APPLY" })
)

Write-Host "STEP 3 - Resolve and verify the exact assignment"

$directoryUser = Get-MgUser `
    -UserId $ExpectedDeniedObjectId `
    -Property @(
        "id",
        "displayName",
        "userPrincipalName",
        "accountEnabled"
    )

if (-not $directoryUser) {
    throw "STOP: The denied user could not be resolved in Entra."
}

if ($directoryUser.DisplayName -ne $deniedRow.DisplayName) {
    throw (
        "STOP: The current directory identity does not match " +
        "the reviewed identity."
    )
}

$servicePrincipals = @(
    Get-MgServicePrincipal `
        -All `
        -Property @(
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
        "STOP: Expected exactly one service principal named " +
        "'$ApplicationDisplayName', but found " +
        "$($servicePrincipals.Count)."
    )
}

$servicePrincipal = $servicePrincipals[0]

$careAssignments = @(
    Get-MgUserAppRoleAssignment `
        -UserId $directoryUser.Id `
        -All |
        Where-Object {
            [string]$_.ResourceId -eq
                [string]$servicePrincipal.Id
        }
)

$defaultAssignments = @(
    $careAssignments |
        Where-Object {
            [string]$_.AppRoleId -eq $defaultAccessRoleId
        }
)

$nonDefaultAssignments = @(
    $careAssignments |
        Where-Object {
            [string]$_.AppRoleId -ne $defaultAccessRoleId
        }
)

if ($nonDefaultAssignments.Count -gt 0) {
    throw (
        "STOP: The target now has a specific Sunhaven app role. " +
        "The reviewed state is no longer current."
    )
}

if ($defaultAssignments.Count -gt 1) {
    throw "STOP: More than one DefaultAccess assignment was found."
}

if ($defaultAssignments.Count -eq 0) {
    $result = Write-RemediationResult `
        -Mode $(if ($Apply) { "APPLY" } else { "SAFE_NO_APPLY" }) `
        -Outcome "NO CHANGE" `
        -WriteOperations 0 `
        -AssignmentAbsent $true `
        -Message "DefaultAccess was already absent."

    $result | Format-List
    exit 0
}

$assignmentId = [string]$defaultAssignments[0].Id

if (-not $Apply) {
    Write-Host "STEP 4 - Produce a no-write remediation plan"

    $result = Write-RemediationResult `
        -Mode "SAFE_NO_APPLY" `
        -Outcome "PLANNED" `
        -WriteOperations 0 `
        -AssignmentAbsent $false `
        -AssignmentId $assignmentId `
        -Message (
            "The reviewed DefaultAccess assignment is present " +
            "and ready for approved removal."
        )

    $result | Format-List
    Write-Host "Required approval text: $requiredApproval"
    exit 0
}

Write-Host "STEP 4 - Remove the single denied app assignment"

Remove-MgUserAppRoleAssignment `
    -UserId $directoryUser.Id `
    -AppRoleAssignmentId $assignmentId `
    -Confirm:$false

$remainingAssignments = @(
    Get-MgUserAppRoleAssignment `
        -UserId $directoryUser.Id `
        -All |
        Where-Object {
            [string]$_.ResourceId -eq
                [string]$servicePrincipal.Id
        }
)

if ($remainingAssignments.Count -ne 0) {
    throw (
        "STOP: The assignment removal could not be verified. " +
        "Do not continue to post-review validation."
    )
}

$result = Write-RemediationResult `
    -Mode "APPLY" `
    -Outcome "REMOVED" `
    -WriteOperations 1 `
    -AssignmentAbsent $true `
    -AssignmentId $assignmentId `
    -Message (
        "The denied DefaultAccess assignment was removed and " +
        "its absence was verified."
    )

$result | Format-List
Write-Host "Result: PASS"
