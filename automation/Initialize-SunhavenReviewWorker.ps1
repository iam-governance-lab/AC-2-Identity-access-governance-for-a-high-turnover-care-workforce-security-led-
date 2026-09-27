param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TenantId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$requiredCommands = @("Connect-MgGraph", "Get-MgContext", "Get-MgUser")
foreach ($commandName in $requiredCommands) {
    if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
        throw "Required Microsoft Graph command is missing: $commandName"
    }
}

Write-Host "Signing in once for the local delegated background worker."
Write-Host "This script performs zero directory writes."

Connect-MgGraph `
    -TenantId $TenantId `
    -Scopes @(
        "User.ReadWrite.All",
        "GroupMember.ReadWrite.All",
        "Application.Read.All",
        "AppRoleAssignment.ReadWrite.All",
        "User.RevokeSessions.All"
    ) `
    -ContextScope CurrentUser `
    -NoWelcome

$context = Get-MgContext
if (-not $context -or [string]$context.TenantId -ne $TenantId) {
    throw "STOP: Microsoft Graph tenant verification failed."
}

$null = Get-MgUser -Top 1 -Property "id"

Write-Host "Authenticated account: $($context.Account)"
Write-Host "Authenticated tenant: $($context.TenantId)"
Write-Host "Context scope: $($context.ContextScope)"
Write-Host "Write operations executed: 0"
Write-Host "Result: PASS"
