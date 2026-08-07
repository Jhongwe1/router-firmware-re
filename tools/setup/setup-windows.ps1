<#
.SYNOPSIS
    Provision the Windows-side analysis tooling: JDK 21 + Ghidra.

.DESCRIPTION
    Ghidra runs on the Windows side rather than inside WSL for two reasons:
      1. The GUI is materially smoother on the native display stack than through WSLg.
      2. `analyzeHeadless` on Windows can read the unpacked rootfs over \\wsl$\...,
         so there is exactly one copy of the extracted firmware (on ext4) and no
         risk of the Windows and Linux views drifting apart.

    Everything is version-pinned and hash-verified. Re-running is safe.

.PARAMETER Stage
    all | jdk | ghidra | verify

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\setup\setup-windows.ps1 all
#>
[CmdletBinding()]
param(
    [ValidateSet('all', 'jdk', 'ghidra', 'verify')]
    [string]$Stage = 'all'
)

$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------------ pinned versions
$GhidraVersion = '12.1.2'
$GhidraAsset   = 'ghidra_12.1.2_PUBLIC_20260605.zip'
$GhidraUrl     = "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GhidraVersion}_build/$GhidraAsset"
$GhidraSha256  = 'b62e81a0390618466c019c60d8c2f796ced2509c4c1aea4a37644a77272cf99d'

# Temurin is installed from the portable ZIP rather than the MSI on purpose:
# the MSI needs administrator elevation, which means a UAC prompt that a scripted
# or CI run cannot answer. The ZIP unpacks into the user profile, needs no
# elevation, and is hash-pinned like everything else here.
$JdkVersion    = '21.0.12+8'
$JdkAsset      = 'OpenJDK21U-jdk_x64_windows_hotspot_21.0.12_8.zip'
$JdkUrl        = 'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12%2B8/OpenJDK21U-jdk_x64_windows_hotspot_21.0.12_8.zip'
$JdkSha256     = '9ba963ee2371874a74185d18bc7bb2ab9407df7683300855ed7606e0662321d0'
$JdkDirName    = 'jdk-21.0.12+8'

$ToolsRoot  = Join-Path $env:LOCALAPPDATA 'fwre-tools'
$GhidraHome = Join-Path $ToolsRoot "ghidra_${GhidraVersion}_PUBLIC"
$JdkHome    = Join-Path $ToolsRoot $JdkDirName
$CacheDir   = Join-Path $env:LOCALAPPDATA 'fwre-setup'

function Write-Ok   { param($m) Write-Host "  ok   $m" -ForegroundColor Green }
function Write-Run  { param($m) Write-Host " ==>   $m" -ForegroundColor Cyan }
function Write-Warn2{ param($m) Write-Host " warn  $m" -ForegroundColor Yellow }
function Write-Err2 { param($m) Write-Host " FAIL  $m" -ForegroundColor Red }

# Download a pinned artefact into the cache and verify it before use.
# A hash mismatch deletes the file: a half-correct toolchain is worse than none.
function Get-PinnedArtifact {
    param([string]$Url, [string]$FileName, [string]$Sha256, [string]$Label)

    New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
    $path = Join-Path $CacheDir $FileName

    if (-not (Test-Path $path)) {
        Write-Run "$Label`: downloading $FileName"
        # Invoke-WebRequest with the progress bar enabled is roughly an order of
        # magnitude slower for large files; suppressing it is the known workaround.
        $prev = $ProgressPreference
        $ProgressPreference = 'SilentlyContinue'
        try   { Invoke-WebRequest -Uri $Url -OutFile $path -UseBasicParsing }
        finally { $ProgressPreference = $prev }
    } else {
        Write-Ok "$Label`: using cached download"
    }

    $actual = (Get-FileHash -Algorithm SHA256 -Path $path).Hash.ToLower()
    if ($actual -ne $Sha256) {
        Remove-Item $path -Force
        Write-Err2 "$Label SHA-256 mismatch. expected=$Sha256 actual=$actual (cached file deleted)"
        throw "$Label download integrity check failed"
    }
    Write-Ok "$Label`: SHA-256 verified"
    return $path
}

function Install-Jdk {
    if (Test-Path (Join-Path $JdkHome 'bin\java.exe')) {
        Write-Ok "JDK already installed at $JdkHome"
        return
    }
    # A system-wide java may exist and be the wrong major version; Ghidra 12
    # requires 21+. Pin our own rather than inheriting whatever is on PATH.
    $zip = Get-PinnedArtifact -Url $JdkUrl -FileName $JdkAsset -Sha256 $JdkSha256 -Label 'jdk'
    New-Item -ItemType Directory -Force -Path $ToolsRoot | Out-Null
    Write-Run "jdk: extracting to $ToolsRoot"
    Expand-Archive -Path $zip -DestinationPath $ToolsRoot -Force

    [Environment]::SetEnvironmentVariable('JAVA_HOME', $JdkHome, 'User')
    $env:JAVA_HOME = $JdkHome
    $env:PATH = "$JdkHome\bin;$env:PATH"

    # Prepend to the *user* PATH so ghidraRun.bat and analyzeHeadless find it.
    $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
    if ($userPath -notlike "*$JdkHome\bin*") {
        [Environment]::SetEnvironmentVariable('PATH', "$JdkHome\bin;$userPath", 'User')
    }
    Write-Ok "JDK $JdkVersion installed; JAVA_HOME=$JdkHome"
}

function Install-Ghidra {
    if (Test-Path (Join-Path $GhidraHome 'ghidraRun.bat')) {
        Write-Ok "Ghidra already installed at $GhidraHome"
        return
    }
    New-Item -ItemType Directory -Force -Path $ToolsRoot, $CacheDir | Out-Null
    $zip = Get-PinnedArtifact -Url $GhidraUrl -FileName $GhidraAsset -Sha256 $GhidraSha256 -Label 'ghidra'

    Write-Run "ghidra: extracting to $ToolsRoot"
    Expand-Archive -Path $zip -DestinationPath $ToolsRoot -Force

    # GHIDRA_INSTALL_DIR is the conventional variable that Ghidra scripting
    # (pyghidra, gradle extension builds, analyzeHeadless wrappers) looks for.
    [Environment]::SetEnvironmentVariable('GHIDRA_INSTALL_DIR', $GhidraHome, 'User')
    $env:GHIDRA_INSTALL_DIR = $GhidraHome
    Write-Ok "GHIDRA_INSTALL_DIR set to $GhidraHome (user scope)"
}

function Test-Toolchain {
    $fail = 0
    Write-Host ''
    Write-Host '=== G0 gate: Windows-side toolchain ===' -ForegroundColor White

    $javaExe = Join-Path $JdkHome 'bin\java.exe'
    if (Test-Path $javaExe) {
        # Use `--version` (JDK 9+), which writes to stdout. The legacy `-version`
        # writes to stderr, and in Windows PowerShell 5.1 redirecting a native
        # command's stderr wraps each line in an ErrorRecord — which under
        # $ErrorActionPreference='Stop' turns a successful version check into a
        # terminating error.
        $ver = (& $javaExe --version | Select-Object -First 1)
        Write-Ok "java  $ver"
        Write-Ok "      $javaExe"
    } else { Write-Err2 "java  MISSING at $javaExe"; $fail = 1 }

    foreach ($f in @('ghidraRun.bat', 'support\analyzeHeadless.bat')) {
        $p = Join-Path $GhidraHome $f
        if (Test-Path $p) { Write-Ok "ghidra $f" } else { Write-Err2 "ghidra $f MISSING"; $fail = 1 }
    }

    Write-Host ''
    if ($fail -eq 0) { Write-Ok 'G0 (Windows) GREEN' } else { Write-Err2 'G0 (Windows) RED'; exit 1 }
}

switch ($Stage) {
    'jdk'    { Install-Jdk }
    'ghidra' { Install-Ghidra }
    'verify' { Test-Toolchain }
    'all'    { Install-Jdk; Install-Ghidra; Test-Toolchain }
}
