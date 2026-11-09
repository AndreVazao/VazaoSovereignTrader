$ErrorActionPreference = "Stop"

$secureToken = Read-Host "VST_LOCAL_TOKEN (long random local API token)" -AsSecureString
if ($null -eq $secureToken) { throw "VST_LOCAL_TOKEN cannot be empty." }

$tokenPtr = [IntPtr]::Zero
try {
    $tokenPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPtr)
    if ([string]::IsNullOrWhiteSpace($token)) { throw "VST_LOCAL_TOKEN cannot be empty." }
    [Environment]::SetEnvironmentVariable("VST_LOCAL_TOKEN", $token, "User")
}
finally {
    if ($tokenPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPtr)
    }
    if ($secureToken) { $secureToken.Dispose() }
    $token = $null
}

Write-Host "VST_LOCAL_TOKEN stored as a Windows user environment variable." -ForegroundColor Green
Write-Host "This helper does not collect or store exchange API credentials."
Write-Host "Close this terminal and open a new one before starting the engine."
