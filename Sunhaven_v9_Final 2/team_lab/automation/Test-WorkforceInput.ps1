[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$ErrorPath,

    [Parameter(Mandatory = $true)]
    [string]$SummaryPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:ValidationErrors =
    [System.Collections.Generic.List[object]]::new()

$script:SummaryLines =
    [System.Collections.Generic.List[string]]::new()

$allowedRoles = @(
    "CareWorker",
    "Nurse",
    "Manager",
    "AgencyWorker",
    "Auditor"
)

$allowedStatuses = @(
    "Active",
    "Leaving",
    "Inactive"
)

$requiredColumns = @(
    "employeeId",
    "displayName",
    "mailAlias",
    "jobRole",
    "facility",
    "status",
    "startDate",
    "endDate"
)

$requiredValueColumns = @(
    "employeeId",
    "displayName",
    "mailAlias",
    "jobRole",
    "facility",
    "status"
)


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


function Add-SummaryLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    [void]$script:SummaryLines.Add($Text)
    Write-Host $Text
}


function Add-ValidationError {
    param(
        [Parameter(Mandatory = $true)]
        [int]$RowNumber,

        [AllowEmptyString()]
        [string]$EmployeeId,

        [Parameter(Mandatory = $true)]
        [string]$Field,

        [Parameter(Mandatory = $true)]
        [string]$ErrorCode,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    [void]$script:ValidationErrors.Add(
        [pscustomobject]@{
            RowNumber = $RowNumber
            EmployeeId = $EmployeeId
            Field      = $Field
            ErrorCode  = $ErrorCode
            Message    = $Message
        }
    )
}


function Test-IsoDate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    [datetime]$parsedDate = [datetime]::MinValue

    return [datetime]::TryParseExact(
        $Value,
        "yyyy-MM-dd",
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::None,
        [ref]$parsedDate
    )
}


function Complete-Validation {
    param(
        [Parameter(Mandatory = $true)]
        [int]$RecordCount
    )

    $result = if ($script:ValidationErrors.Count -eq 0) {
        "PASS"
    }
    else {
        "FAIL"
    }

    [void]$script:SummaryLines.Add(
        "Records examined: $RecordCount"
    )

    [void]$script:SummaryLines.Add(
        "Validation errors: $($script:ValidationErrors.Count)"
    )

    [void]$script:SummaryLines.Add(
        "Result: $result"
    )

    [void]$script:SummaryLines.Add(
        "Directory changes attempted: No"
    )

    Ensure-ParentDirectory -Path $ErrorPath
    Ensure-ParentDirectory -Path $SummaryPath

    if ($script:ValidationErrors.Count -gt 0) {
        $script:ValidationErrors |
            Export-Csv `
                -LiteralPath $ErrorPath `
                -NoTypeInformation `
                -Encoding utf8
    }
    else {
        "RowNumber,EmployeeId,Field,ErrorCode,Message" |
            Set-Content `
                -LiteralPath $ErrorPath `
                -Encoding utf8
    }

    $script:SummaryLines |
        Set-Content `
            -LiteralPath $SummaryPath `
            -Encoding utf8
}


Ensure-ParentDirectory -Path $ErrorPath
Ensure-ParentDirectory -Path $SummaryPath

Add-SummaryLine "Sunhaven workforce input validation"
Add-SummaryLine "----------------------------------"
Add-SummaryLine "Validator mode: local and read-only"
Add-SummaryLine "Microsoft Graph connection: Not used"

if (-not (Test-Path -LiteralPath $InputPath)) {
    Add-ValidationError `
        -RowNumber 0 `
        -EmployeeId "" `
        -Field "file" `
        -ErrorCode "FILE_NOT_FOUND" `
        -Message "The input CSV file does not exist: $InputPath"

    Complete-Validation -RecordCount 0

    Write-Host ""
    Write-Host "Validation failed. No directory changes were attempted." `
        -ForegroundColor Red

    exit 1
}

$resolvedInputPath = (Resolve-Path -LiteralPath $InputPath).Path
Add-SummaryLine "Input file: $resolvedInputPath"

try {
    $rows = @(Import-Csv -LiteralPath $InputPath)
}
catch {
    Add-ValidationError `
        -RowNumber 0 `
        -EmployeeId "" `
        -Field "file" `
        -ErrorCode "CSV_READ_FAILED" `
        -Message $_.Exception.Message

    Complete-Validation -RecordCount 0

    Write-Host ""
    Write-Host "Validation failed. No directory changes were attempted." `
        -ForegroundColor Red

    exit 1
}

if ($rows.Count -eq 0) {
    Add-ValidationError `
        -RowNumber 0 `
        -EmployeeId "" `
        -Field "file" `
        -ErrorCode "NO_DATA_ROWS" `
        -Message "The CSV file does not contain any workforce records."

    Complete-Validation -RecordCount 0

    Write-Host ""
    Write-Host "Validation failed. No directory changes were attempted." `
        -ForegroundColor Red

    exit 1
}

$headers = @($rows[0].PSObject.Properties.Name)

foreach ($requiredColumn in $requiredColumns) {
    if ($requiredColumn -notin $headers) {
        Add-ValidationError `
            -RowNumber 1 `
            -EmployeeId "" `
            -Field $requiredColumn `
            -ErrorCode "MISSING_COLUMN" `
            -Message "Required column '$requiredColumn' is missing."
    }
}

foreach ($header in $headers) {
    if ($header -notin $requiredColumns) {
        Add-ValidationError `
            -RowNumber 1 `
            -EmployeeId "" `
            -Field $header `
            -ErrorCode "UNEXPECTED_COLUMN" `
            -Message "Unexpected column '$header' was found."
    }
}

if ($script:ValidationErrors.Count -gt 0) {
    Complete-Validation -RecordCount $rows.Count

    Write-Host ""
    Write-Host "The CSV schema is invalid." -ForegroundColor Red
    Write-Host "No workforce rows were processed."
    Write-Host "No directory changes were attempted."

    exit 1
}

$normalizedRows = [System.Collections.Generic.List[object]]::new()

for ($index = 0; $index -lt $rows.Count; $index++) {
    $row = $rows[$index]
    $rowNumber = $index + 2

    $employeeId = ([string]$row.employeeId).Trim()
    $displayName = ([string]$row.displayName).Trim()
    $mailAlias = ([string]$row.mailAlias).Trim()
    $jobRole = ([string]$row.jobRole).Trim()
    $facility = ([string]$row.facility).Trim()
    $status = ([string]$row.status).Trim()
    $startDate = ([string]$row.startDate).Trim()
    $endDate = ([string]$row.endDate).Trim()

    foreach ($requiredField in $requiredValueColumns) {
        $fieldValue = ([string]$row.$requiredField).Trim()

        if ([string]::IsNullOrWhiteSpace($fieldValue)) {
            Add-ValidationError `
                -RowNumber $rowNumber `
                -EmployeeId $employeeId `
                -Field $requiredField `
                -ErrorCode "REQUIRED_VALUE_MISSING" `
                -Message "The value for '$requiredField' cannot be blank."
        }
    }

    if (
        -not [string]::IsNullOrWhiteSpace($displayName) -and
        $displayName -notmatch "(?i)\bTEST\b"
    ) {
        Add-ValidationError `
            -RowNumber $rowNumber `
            -EmployeeId $employeeId `
            -Field "displayName" `
            -ErrorCode "TEST_MARKER_MISSING" `
            -Message "The fictional display name must contain TEST."
    }

    if (
        -not [string]::IsNullOrWhiteSpace($mailAlias) -and
        $mailAlias -notmatch "^[A-Za-z0-9][A-Za-z0-9._-]*$"
    ) {
        Add-ValidationError `
            -RowNumber $rowNumber `
            -EmployeeId $employeeId `
            -Field "mailAlias" `
            -ErrorCode "INVALID_MAIL_ALIAS" `
            -Message "The mail alias contains unsupported characters."
    }

    if (
        -not [string]::IsNullOrWhiteSpace($jobRole) -and
        $jobRole -notin $allowedRoles
    ) {
        Add-ValidationError `
            -RowNumber $rowNumber `
            -EmployeeId $employeeId `
            -Field "jobRole" `
            -ErrorCode "INVALID_JOB_ROLE" `
            -Message (
                "Role '$jobRole' is not approved. Allowed roles: " +
                ($allowedRoles -join ", ")
            )
    }

    if (
        -not [string]::IsNullOrWhiteSpace($status) -and
        $status -notin $allowedStatuses
    ) {
        Add-ValidationError `
            -RowNumber $rowNumber `
            -EmployeeId $employeeId `
            -Field "status" `
            -ErrorCode "INVALID_STATUS" `
            -Message (
                "Status '$status' is invalid. Allowed statuses: " +
                ($allowedStatuses -join ", ")
            )
    }

    $startDateValid = $true
    $endDateValid = $true

    if (-not [string]::IsNullOrWhiteSpace($startDate)) {
        $startDateValid = Test-IsoDate -Value $startDate

        if (-not $startDateValid) {
            Add-ValidationError `
                -RowNumber $rowNumber `
                -EmployeeId $employeeId `
                -Field "startDate" `
                -ErrorCode "INVALID_DATE_FORMAT" `
                -Message "startDate must use yyyy-MM-dd."
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($endDate)) {
        $endDateValid = Test-IsoDate -Value $endDate

        if (-not $endDateValid) {
            Add-ValidationError `
                -RowNumber $rowNumber `
                -EmployeeId $employeeId `
                -Field "endDate" `
                -ErrorCode "INVALID_DATE_FORMAT" `
                -Message "endDate must use yyyy-MM-dd."
        }
    }

    if (
        (
            $jobRole -eq "AgencyWorker" -or
            $status -eq "Leaving"
        ) -and
        [string]::IsNullOrWhiteSpace($endDate)
    ) {
        Add-ValidationError `
            -RowNumber $rowNumber `
            -EmployeeId $employeeId `
            -Field "endDate" `
            -ErrorCode "END_DATE_REQUIRED" `
            -Message (
                "endDate is required for AgencyWorker or Leaving records."
            )
    }

    if (
        $startDateValid -and
        $endDateValid -and
        -not [string]::IsNullOrWhiteSpace($startDate) -and
        -not [string]::IsNullOrWhiteSpace($endDate)
    ) {
        $parsedStartDate = [datetime]::ParseExact(
            $startDate,
            "yyyy-MM-dd",
            [System.Globalization.CultureInfo]::InvariantCulture
        )

        $parsedEndDate = [datetime]::ParseExact(
            $endDate,
            "yyyy-MM-dd",
            [System.Globalization.CultureInfo]::InvariantCulture
        )

        if ($parsedEndDate -lt $parsedStartDate) {
            Add-ValidationError `
                -RowNumber $rowNumber `
                -EmployeeId $employeeId `
                -Field "endDate" `
                -ErrorCode "END_DATE_BEFORE_START_DATE" `
                -Message "endDate cannot be earlier than startDate."
        }
    }

    [void]$normalizedRows.Add(
        [pscustomobject]@{
            RowNumber     = $rowNumber
            EmployeeId    = $employeeId
            EmployeeIdKey = $employeeId.ToUpperInvariant()
            MailAlias     = $mailAlias
            MailAliasKey  = $mailAlias.ToUpperInvariant()
        }
    )
}

$duplicateEmployeeIdGroups = @(
    $normalizedRows |
        Where-Object {
            -not [string]::IsNullOrWhiteSpace($_.EmployeeIdKey)
        } |
        Group-Object -Property EmployeeIdKey |
        Where-Object {
            $_.Count -gt 1
        }
)

foreach ($duplicateGroup in $duplicateEmployeeIdGroups) {
    $rowNumbers = $duplicateGroup.Group.RowNumber -join ", "

    foreach ($duplicateRow in $duplicateGroup.Group) {
        Add-ValidationError `
            -RowNumber $duplicateRow.RowNumber `
            -EmployeeId $duplicateRow.EmployeeId `
            -Field "employeeId" `
            -ErrorCode "DUPLICATE_EMPLOYEE_ID" `
            -Message (
                "employeeId '$($duplicateRow.EmployeeId)' appears " +
                "on CSV rows $rowNumbers."
            )
    }
}

$duplicateAliasGroups = @(
    $normalizedRows |
        Where-Object {
            -not [string]::IsNullOrWhiteSpace($_.MailAliasKey)
        } |
        Group-Object -Property MailAliasKey |
        Where-Object {
            $_.Count -gt 1
        }
)

foreach ($duplicateGroup in $duplicateAliasGroups) {
    $rowNumbers = $duplicateGroup.Group.RowNumber -join ", "

    foreach ($duplicateRow in $duplicateGroup.Group) {
        Add-ValidationError `
            -RowNumber $duplicateRow.RowNumber `
            -EmployeeId $duplicateRow.EmployeeId `
            -Field "mailAlias" `
            -ErrorCode "DUPLICATE_UPN_ALIAS" `
            -Message (
                "mailAlias '$($duplicateRow.MailAlias)' would create " +
                "a duplicate UPN. It appears on CSV rows $rowNumbers."
            )
    }
}

Complete-Validation -RecordCount $rows.Count

Write-Host ""

if ($script:ValidationErrors.Count -gt 0) {
    Write-Host "Validation errors:" -ForegroundColor Red

    $script:ValidationErrors |
        Format-Table `
            RowNumber,
            EmployeeId,
            Field,
            ErrorCode `
            -AutoSize

    Write-Host "Result: FAIL" -ForegroundColor Red
    Write-Host "No directory changes were attempted."

    exit 1
}

Write-Host "Result: PASS" -ForegroundColor Green
Write-Host "The input is ready for the read-only dry-run planner."
Write-Host "No directory changes were attempted."

exit 0
