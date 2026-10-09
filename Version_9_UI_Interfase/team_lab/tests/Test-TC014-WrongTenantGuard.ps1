Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$sourcePath = "./automation/Invoke-SunhavenJoiner.ps1"

if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "STOP: Joiner script was not found: $sourcePath"
}

$resolvedSourcePath = (
    Resolve-Path -LiteralPath $sourcePath
).Path

$tokens = $null
$parseErrors = $null

$sourceAst = [System.Management.Automation.Language.Parser]::ParseFile(
    $resolvedSourcePath,
    [ref]$tokens,
    [ref]$parseErrors
)

if (@($parseErrors).Count -gt 0) {
    throw "STOP: The Joiner script contains PowerShell parse errors."
}

$tenantGuards = @(
    $sourceAst.FindAll(
        {
            param($node)

            $node -is [System.Management.Automation.Language.IfStatementAst] -and
            $node.Extent.Text -match "Wrong tenant\. Expected"
        },
        $true
    )
)

if ($tenantGuards.Count -ne 1) {
    throw (
        "STOP: Expected exactly one wrong-tenant guard, but found " +
        "$($tenantGuards.Count)."
    )
}

$tenantGuard = $tenantGuards[0]

$directoryWriteNames = @(
    "New-MgUser",
    "Update-MgUser",
    "Remove-MgUser",
    "New-MgGroupMemberByRef",
    "Remove-MgGroupMemberByRef",
    "New-MgUserAppRoleAssignment",
    "Remove-MgUserAppRoleAssignment"
)

$directoryWriteCommands = @(
    $sourceAst.FindAll(
        {
            param($node)

            if (
                $node -isnot [System.Management.Automation.Language.CommandAst]
            ) {
                return $false
            }

            return (
                $node.GetCommandName() -in $directoryWriteNames
            )
        },
        $true
    ) |
        Sort-Object {
            $_.Extent.StartOffset
        }
)

if ($directoryWriteCommands.Count -eq 0) {
    throw "STOP: No directory-write commands were found."
}

$firstDirectoryWrite = $directoryWriteCommands[0]

$guardBeforeFirstWrite = (
    $tenantGuard.Extent.StartOffset -lt
    $firstDirectoryWrite.Extent.StartOffset
)

$writeCommandsInsideGuard = @(
    $tenantGuard.FindAll(
        {
            param($node)

            if (
                $node -isnot [System.Management.Automation.Language.CommandAst]
            ) {
                return $false
            }

            return (
                $node.GetCommandName() -in $directoryWriteNames
            )
        },
        $true
    )
)

$TenantId = "72a753ee-6910-4a9b-a36e-e8790da83acb"
$wrongTenantId = "11111111-1111-1111-1111-111111111111"

$graphContext = [pscustomobject]@{
    TenantId = $wrongTenantId
}

$expectedError = (
    "Wrong tenant. Expected $TenantId but connected to " +
    "$wrongTenantId."
)

$guardBlocked = $false
$errorMessageMatched = $false
$capturedError = ""

$guardScript = [scriptblock]::Create(
    $tenantGuard.Extent.Text
)

try {
    & $guardScript
}
catch {
    $capturedError = $_.Exception.Message
    $guardBlocked = $true
    $errorMessageMatched = (
        $capturedError -eq $expectedError
    )
}

$passed = (
    $guardBeforeFirstWrite -and
    $writeCommandsInsideGuard.Count -eq 0 -and
    $guardBlocked -and
    $errorMessageMatched
)

$resultText = if ($passed) {
    "PASS"
}
else {
    "FAIL"
}

Write-Host "Sunhaven TC-014 wrong-tenant guard test"
Write-Host "----------------------------------------"
Write-Host "Test mode: Isolated local guard execution"
Write-Host "Microsoft Graph connection attempted: No"
Write-Host "Requested tenant: $TenantId"
Write-Host "Simulated authenticated tenant: $wrongTenantId"
Write-Host (
    "Tenant guard source line: " +
    "$($tenantGuard.Extent.StartLineNumber)"
)
Write-Host (
    "First directory-write command: " +
    "$($firstDirectoryWrite.GetCommandName())"
)
Write-Host (
    "First directory-write line: " +
    "$($firstDirectoryWrite.Extent.StartLineNumber)"
)
Write-Host "Guard occurs before first write: $guardBeforeFirstWrite"
Write-Host (
    "Write-capable commands inside executed guard: " +
    "$($writeCommandsInsideGuard.Count)"
)
Write-Host "Wrong-tenant request rejected: $guardBlocked"
Write-Host "Expected error message returned: $errorMessageMatched"
Write-Host "Directory write operations executed: 0"
Write-Host "Result: $resultText"

if (-not $passed) {
    exit 1
}