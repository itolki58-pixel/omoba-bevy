param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PublicHost,
    [ValidateRange(1, 65535)]
    [int]$GamePort = 4000,
    [ValidateRange(1, 65535)]
    [int]$FirstMatchPort = 41000,
    [ValidateRange(1, 100)]
    [int]$MatchCapacity = 16,
    [string]$BindIp = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($env:OMOBA_DATABASE_URL)) {
    throw "Set OMOBA_DATABASE_URL to the PostgreSQL game-runtime connection string first."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not (Test-Path (Join-Path $repoRoot "Cargo.toml"))) {
    throw "Cannot locate the OMOBA workspace root."
}
$lastMatchPort = $FirstMatchPort + $MatchCapacity - 1
if ($lastMatchPort -gt 65535) {
    throw "The match worker port range exceeds 65535."
}

Push-Location $repoRoot
try {
    $env:OMOBA_SERVER_ROLE = "lobby"
    $env:SERVER_ADDR = "$($BindIp):$GamePort"
    $env:OMOBA_MATCH_BIND_IP = $BindIp
    $env:OMOBA_MATCH_PUBLIC_HOST = $PublicHost
    $env:OMOBA_MATCH_FIRST_PORT = "$FirstMatchPort"
    $env:OMOBA_MATCH_CAPACITY = "$MatchCapacity"

    Write-Host "Starting OMOBA public lobby."
    Write-Host "Game endpoint: UDP $($env:SERVER_ADDR)"
    Write-Host ("Match workers: UDP {0}:{1}-{2}" -f $BindIp, $FirstMatchPort, $lastMatchPort)
    Write-Host "Public worker host: $PublicHost"
    Write-Host "Database URL is configured (value hidden)."

    cargo run --release --locked -p server
    if ($LASTEXITCODE -ne 0) {
        throw "OMOBA server exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
