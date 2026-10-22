$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectDir '.venv\Scripts\python.exe'
if ((Get-Service -Name 'MSSQL$SQLEXPRESS').Status -ne 'Running') {
    throw 'SQL Server (SQLEXPRESS) calismiyor; once hizmeti baslatin.'
}
if (-not (Test-Path -LiteralPath $python)) { throw 'Proje Python ortami bulunamadi.' }
$previous = [Environment]::GetEnvironmentVariable('MSSQL_TEST_CONNECTION_STRING', 'Process')
Push-Location -LiteralPath $projectDir
try {
    $env:MSSQL_TEST_CONNECTION_STRING = 'Driver={ODBC Driver 17 for SQL Server};Server=.\SQLEXPRESS;Database=ServisMasasiApp;Trusted_Connection=Yes;'
    & $python -m unittest discover -s tests -p test_mssql_repository.py -v
    $testExitCode = $LASTEXITCODE
} finally {
    if ($null -eq $previous) { Remove-Item Env:MSSQL_TEST_CONNECTION_STRING -ErrorAction SilentlyContinue }
    else { $env:MSSQL_TEST_CONNECTION_STRING = $previous }
    Pop-Location
}
if ($testExitCode -ne 0) { throw 'MSSQL veri erisim testleri basarisiz.' }
