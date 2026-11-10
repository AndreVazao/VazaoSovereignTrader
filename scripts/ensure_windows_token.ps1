$ErrorActionPreference = "Stop"

$name = "VST_LOCAL_TOKEN"
$current = [Environment]::GetEnvironmentVariable($name, "User")
if ([string]::IsNullOrWhiteSpace($current)) {
    $bytes = New-Object byte[] 32
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
        $current = [Convert]::ToBase64String($bytes).Replace("+","-").Replace("/","_").TrimEnd("=")
    }
    finally {
        $random.Dispose()
        [Array]::Clear($bytes, 0, $bytes.Length)
    }

    [Environment]::SetEnvironmentVariable($name, $current, "User")
    Write-Host "Generated a new local VST_LOCAL_TOKEN for this Windows user." -ForegroundColor Green
} else {
    if ($current.Length -lt 32) {
        throw "Existing VST_LOCAL_TOKEN is too short. Replace it with a token of at least 32 characters in the Windows user environment, then rerun this helper."
    }
    Write-Host "Existing VST_LOCAL_TOKEN preserved." -ForegroundColor Green
}

Set-Item -Path "Env:$name" -Value $current
Write-Host "Local API authentication token is configured."
