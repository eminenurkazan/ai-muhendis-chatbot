$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    # .env veri olarak okunur; içindeki metin PowerShell kodu olarak çalıştırılmaz.
    $settingsPath = Join-Path $PSScriptRoot '.env'
    if (Test-Path -LiteralPath $settingsPath) {
        foreach ($line in Get-Content -LiteralPath $settingsPath -Encoding UTF8) {
            if ($line -match '^\s*(JWT_SECRET_KEY|MSSQL_CONNECTION_STRING|DATABASE_URL)\s*=(.*)$') {
                $settingName = $matches[1]
                $settingValue = $matches[2].Trim()
                if (-not [Environment]::GetEnvironmentVariable($settingName, 'Process')) {
                    [Environment]::SetEnvironmentVariable($settingName, $settingValue, 'Process')
                }
            }
        }
    }
    if (-not $env:JWT_SECRET_KEY -or -not $env:MSSQL_CONNECTION_STRING) {
        throw 'JWT_SECRET_KEY ve MSSQL_CONNECTION_STRING ayarlarını .env dosyasında veya ortamda tanımla.'
    }
    $apiPort = 8000
    if ($env:API_PORT) {
        if ($env:API_PORT -notmatch '^\d{1,5}$' -or [int]$env:API_PORT -lt 1 -or [int]$env:API_PORT -gt 65535) {
            throw 'API_PORT 1 ile 65535 arasında bir port numarası olmalı.'
        }
        $apiPort = [int]$env:API_PORT
    }
    & '.\.venv\Scripts\python.exe' -m uvicorn api:app --host 127.0.0.1 --port $apiPort
    if ($LASTEXITCODE -ne 0) { throw 'API başlatılamadı.' }
} finally {
    Pop-Location
}
