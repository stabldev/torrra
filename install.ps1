#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

if (-not [Environment]::Is64BitOperatingSystem) {
  throw "torrra standalone binary requires 64-bit Windows."
}

$repo = "stabldev/torrra"
$binDir = Join-Path $env:LOCALAPPDATA "torrra\bin"
$exe = Join-Path $binDir "torrra.exe"

try {
  $release = Invoke-RestMethod "https://api.github.com/repos/$repo/releases/latest" -Headers @{ "User-Agent" = "torrra-installer" } -UseBasicParsing
  $url = ($release.assets | Where-Object name -like "*windows*.exe" | Select-Object -First 1).browser_download_url
  $version = $release.tag_name
}
catch {
  $req = [System.Net.WebRequest]::Create("https://github.com/$repo/releases/latest")
  $req.AllowAutoRedirect = $false
  $resp = $req.GetResponse()
  $version = $resp.GetResponseHeader("Location").Split('/')[-1]
  $resp.Close()
  $url = "https://github.com/$repo/releases/download/$version/torrra_${version}_windows_x86_64.exe"
}

if (-not $url) {
  throw "Failed to resolve download URL for torrra."
}

New-Item -ItemType Directory -Force -Path $binDir | Out-Null
Invoke-WebRequest -Uri $url -OutFile $exe -UseBasicParsing

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ';') -replace '\\$' -notcontains $binDir) {
  [Environment]::SetEnvironmentVariable("Path", ($userPath, $binDir -join ';').Trim(';'), "User")
}

if (($env:Path -split ';') -replace '\\$' -notcontains $binDir) {
  $env:Path = "$binDir;$env:Path"
}

Write-Host "`ntorrra $version installed successfully!" -ForegroundColor Green
Write-Host "Location: $exe" -ForegroundColor DarkGray
Write-Host "Run: torrra --help" -ForegroundColor Yellow
