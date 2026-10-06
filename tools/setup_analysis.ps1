# Regenerate every analysis artifact for one platform (default: cf2).
#   config -> file list -> ctags -> doxygen
# Usage: powershell -File tools\setup_analysis.ps1 [-Platform cf2] [-SkipDoxygen]
param(
    [string]$Platform = "cf2",
    [switch]$SkipDoxygen
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$FW = Join-Path $Root "crazyflie-firmware"
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')

Push-Location $Root
try {
    python tools\gen_config.py $Platform
    python tools\gen_filelist.py $Platform

    # ctags over the compiled firmware sources + all interface headers
    $ctagsDir = Join-Path $Root "analysis\ctags\$Platform"
    New-Item -ItemType Directory -Force $ctagsDir | Out-Null
    $list = Join-Path $ctagsDir "input.txt"
    $src = Get-Content "analysis\config\$Platform\filelist.txt" | Where-Object { $_ -notlike "vendor/*" }
    $hdr = Get-ChildItem (Join-Path $FW "src") -Recurse -Filter *.h | ForEach-Object { $_.FullName.Substring($FW.Length + 1).Replace('\', '/') }
    ($src + $hdr) | Sort-Object -Unique | Set-Content -Encoding ascii $list
    Push-Location $FW
    ctags --languages=C --kinds-C=+pxl --fields=+nKSt --extras=+q -L $list -f (Join-Path $ctagsDir "tags")
    ctags --languages=C --kinds-C=+px --fields=+nKSt --output-format=json -L $list -f (Join-Path $ctagsDir "tags.json")
    Pop-Location
    Write-Host "ctags -> $ctagsDir"

    if (-not $SkipDoxygen) { python tools\run_doxygen.py $Platform }
}
finally {
    Pop-Location
}
