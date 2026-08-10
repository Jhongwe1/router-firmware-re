<#
.SYNOPSIS
    Run a headless Ghidra script against a binary already imported by import.ps1.

.DESCRIPTION
    Auto-analysis is cached in the project; this re-runs only the script, with
    `-noanalysis`, so a script edit costs seconds instead of minutes.

    The program database IS written back. That is the point for BoaFormTable,
    which names every recovered handler: the naming has to persist so the GUI
    session and any later script both see it. Pass -ReadOnly for scripts that
    should not be able to change anything.

.PARAMETER Label
    Project folder created by import.ps1, e.g. "2.1.2".

.PARAMETER Script
    Script base name, with or without .java — e.g. BoaFormTable.

.PARAMETER Program
    Program inside the folder. Defaults to "boa".

.PARAMETER Out
    Output path passed to the script as its first argument. Defaults to
    reports/<script-in-lowercase-minus-boa>-<Label>.json.

.EXAMPLE
    .\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaFormTable
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][string]$Script,
    [string]$Program = 'boa',
    [string]$Out,
    [string[]]$ExtraArgs = @(),
    [switch]$ReadOnly,
    [string]$Binary,
    [string]$ProjectDir = (Join-Path $env:LOCALAPPDATA 'fwre-tools\ghidra-projects'),
    [string]$ProjectName = 'totolink-n150rt'
)

$ErrorActionPreference = 'Stop'

$ghidraHome = $env:GHIDRA_INSTALL_DIR
if (-not $ghidraHome -or -not (Test-Path $ghidraHome)) {
    throw "GHIDRA_INSTALL_DIR is not set. Run tools\setup\setup-windows.ps1 first."
}
$headless = Join-Path $ghidraHome 'support\analyzeHeadless.bat'
$scriptPath = Join-Path $PSScriptRoot 'scripts'
$scriptFile = if ($Script.EndsWith('.java')) { $Script } else { "$Script.java" }
if (-not (Test-Path (Join-Path $scriptPath $scriptFile))) {
    throw "script not found: $scriptPath\$scriptFile"
}

$reportDir = Join-Path $PSScriptRoot '..\reports'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
if (-not $Out) {
    $stem = ($Script -replace '\.java$', '' -replace '^Boa', '').ToLower()
    $Out = Join-Path (Resolve-Path $reportDir) "ghidra-$stem-$Label.json"
}

# The SHA-256 of the analysed binary travels into the report. Without it a
# report says only "program: boa", which is exactly how W01 ended up with two
# files that could not be told apart. Optional, because the binary lives on a
# WSL share that may not be mounted when only re-reading a cached project.
$sha = ''
if ($Binary -and (Test-Path $Binary)) {
    $sha = (Get-FileHash -Algorithm SHA256 -Path $Binary).Hash.ToLower()
}

$ghidraArgs = @(
    $ProjectDir, "$ProjectName/$Label",
    '-process', $Program,
    '-noanalysis',
    '-scriptPath', $scriptPath,
    '-postScript', $scriptFile, $Out
)
if ($sha)             { $ghidraArgs += $sha }
if ($ExtraArgs.Count) { $ghidraArgs += $ExtraArgs }
if ($ReadOnly)        { $ghidraArgs += '-readOnly' }

Write-Host " ==>  $Script on $ProjectName/$Label/$Program" -ForegroundColor Cyan
& $headless @ghidraArgs
if ($LASTEXITCODE -ne 0) { throw "analyzeHeadless failed with exit code $LASTEXITCODE" }
if (-not (Test-Path $Out)) { throw "script produced no output at $Out" }

Write-Host "  ok   wrote $Out" -ForegroundColor Green
