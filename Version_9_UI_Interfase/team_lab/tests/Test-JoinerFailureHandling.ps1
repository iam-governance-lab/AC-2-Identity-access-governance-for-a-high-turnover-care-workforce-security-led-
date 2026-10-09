[CmdletBinding()]
param(
    [ValidateNotNullOrEmpty()]
    [string]$JoinerPath =
        "./automation/Invoke-SunhavenJoiner.ps1",

    [ValidateNotNullOrEmpty()]
    [string]$ErrorPath =
        "./evidence/phase5/P5-E68_Simulated-Failure-Error.csv",

    [ValidateNotNullOrEmpty()]
    [string]$SummaryPath =
        "./evidence/phase5/P5-E69_Simulated-Failure-Summary.txt"
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


if (-not (Test-Path -LiteralPath $JoinerPath -PathType Leaf)) {
    throw "Joiner script was not found: $JoinerPath"
}

$tokens = $null
$parseErrors = $null

$joinerAst =
    [System.Management.Automation.Language.Parser]::ParseFile(
        (Resolve-Path $JoinerPath),
        [ref]$tokens,
        [ref]$parseErrors
    )

if ($parseErrors.Count -gt 0) {
    $parseErrors | Format-List
    exit 2
}

$requiredFunctionNames = @(
    "Get-GraphStatusCode",
    "Test-IsTransientGraphError",
    "Invoke-WithRetry"
)

$functionDefinitions = $joinerAst.FindAll(
    {
        param($node)

        $node -is
            [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -in $requiredFunctionNames
    },
    $true
)

if ($functionDefinitions.Count -ne $requiredFunctionNames.Count) {
    throw "The required Joiner retry functions were not found."
}

foreach ($functionDefinition in $functionDefinitions) {
    . ([scriptblock]::Create($functionDefinition.Extent.Text))
}

$script:attemptCount = 0
$capturedFailure = $null

try {
    Invoke-WithRetry `
        -Description "Controlled authorization failure" `
        -MaximumAttempts 4 `
        -DelaySeconds 0 `
        -Operation {
            $script:attemptCount++

            throw [System.UnauthorizedAccessException]::new(
                "HTTP 403 Forbidden"
            )
        }
}
catch {
    $capturedFailure = $_
}

$testPassed = (
    $null -ne $capturedFailure -and
    $script:attemptCount -eq 1
)

$result = if ($testPassed) {
    "ERROR"
}
else {
    "TEST_FAILURE"
}

$exitCode = if ($testPassed) {
    1
}
else {
    2
}

$errorRow = [pscustomobject][ordered]@{
    TestId                  = "SAFE-FAIL-001"
    Result                  = $result
    ErrorClass              = "NON_TRANSIENT_AUTHORIZATION"
    Attempts                = $script:attemptCount
    WriteOperationsExecuted = 0
    ExpectedExitCode        = 1
    SecretsRecorded         = $false
    SanitizedMessage        = (
        "Simulated HTTP 403 stopped without retry."
    )
}

Ensure-ParentDirectory -Path $ErrorPath
Ensure-ParentDirectory -Path $SummaryPath

$errorRow |
    Export-Csv `
        -LiteralPath $ErrorPath `
        -NoTypeInformation `
        -Encoding utf8

$summaryLines = @(
    "Sunhaven controlled Joiner failure test",
    "----------------------------------------",
    "Test ID: SAFE-FAIL-001",
    "Failure type: simulated HTTP 403",
    "Expected classification: non-transient",
    "Attempts observed: $($script:attemptCount)",
    "Write operations executed: 0",
    "Structured result: $result",
    "Expected process exit code: 1",
    "Secrets recorded: False",
    "Graph connection used: False",
    "Entra directory changes attempted: False",
    "Overall controlled-failure result: " +
        $(if ($testPassed) { "PASS" } else { "FAIL" })
)

$summaryLines |
    Set-Content `
        -LiteralPath $SummaryPath `
        -Encoding utf8

$summaryLines | ForEach-Object {
    Write-Host $_
}

exit $exitCode
