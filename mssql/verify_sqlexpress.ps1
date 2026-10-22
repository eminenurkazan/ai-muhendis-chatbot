$ErrorActionPreference = 'Stop'

$projectDir = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectDir '.venv\Scripts\python.exe'
$service = Get-Service -Name 'MSSQL$SQLEXPRESS' -ErrorAction Stop

if ($service.Status -ne 'Running') {
    throw 'SQL Server (SQLEXPRESS) calismiyor. Yonetici PowerShell acip Start-Service -Name ''MSSQL$SQLEXPRESS'' calistirin.'
}
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Proje Python ortami bulunamadi: .venv\Scripts\python.exe'
}

$previousConnection = [Environment]::GetEnvironmentVariable('MSSQL_CONNECTION_STRING', 'Process')
Push-Location -LiteralPath $projectDir

try {
    $env:MSSQL_CONNECTION_STRING = 'Driver={ODBC Driver 17 for SQL Server};Server=.\SQLEXPRESS;Database=master;Trusted_Connection=Yes;'
    & $python -m mssql.check_connection
    $testExitCode = $LASTEXITCODE
} finally {
    if ($null -eq $previousConnection) {
        Remove-Item Env:MSSQL_CONNECTION_STRING -ErrorAction SilentlyContinue
    } else {
        $env:MSSQL_CONNECTION_STRING = $previousConnection
    }
    Pop-Location
}

if ($testExitCode -ne 0) {
    throw 'Python MSSQL baglanti testi basarisiz.'
}
