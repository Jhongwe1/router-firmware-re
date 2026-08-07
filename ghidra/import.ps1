<#
.SYNOPSIS
    Import a firmware binary into Ghidra headlessly, analyse it, and emit a
    machine-readable string cross-reference report.

.DESCRIPTION
    The point of doing this headlessly is that the result is reproducible. A GUI
    session produces knowledge that lives in one person's project database; this
    produces a JSON file that can be committed, diffed between firmware
    versions, and regenerated after a Ghidra upgrade.

    The GUI is still the right tool for reading decompiled code (W03). This is
    the triage pass that decides which functions are worth opening.

.PARAMETER Binary
    Path to the ELF to import. Accepts a \\wsl$ path, which is how the extracted
    root filesystems are reached from Windows — see docs/workspace-layout.md.

.PARAMETER Label
    Short name used for the Ghidra program and the output filename, e.g. "2.1.2".

.EXAMPLE
    .\ghidra\import.ps1 -Label 2.1.2 `
      -Binary \\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Binary,
    [Parameter(Mandatory = $true)][string]$Label,
    [string]$ProjectDir = (Join-Path $env:LOCALAPPDATA 'fwre-tools\ghidra-projects'),
    [string]$ProjectName = 'totolink-n150rt',
    [string]$OutDir = (Join-Path $PSScriptRoot '..\reports')
)

$ErrorActionPreference = 'Stop'

$ghidraHome = $env:GHIDRA_INSTALL_DIR
if (-not $ghidraHome -or -not (Test-Path $ghidraHome)) {
    throw "GHIDRA_INSTALL_DIR is not set or does not exist. Run tools\setup\setup-windows.ps1 first."
}
$headless = Join-Path $ghidraHome 'support\analyzeHeadless.bat'
if (-not (Test-Path $headless)) { throw "analyzeHeadless.bat not found under $ghidraHome" }
if (-not (Test-Path $Binary))   { throw "binary not found: $Binary" }

New-Item -ItemType Directory -Force -Path $ProjectDir, $OutDir | Out-Null
$outJson    = Join-Path (Resolve-Path $OutDir) "ghidra-strings-$Label.json"
$scriptPath = Join-Path $PSScriptRoot 'scripts'
$programName = "boa-$Label"

Write-Host " ==>  importing $Binary as $programName" -ForegroundColor Cyan
Write-Host "      project : $ProjectDir\$ProjectName" -ForegroundColor DarkGray
Write-Host "      output  : $outJson" -ForegroundColor DarkGray

# Ghidra reads the ELF header itself, so the processor is not forced here: if it
# picks something other than big-endian MIPS that is a finding about the binary,
# not a setting to override. The language actually used is recorded in the JSON.
$ghidraArgs = @(
    $ProjectDir, $ProjectName,
    '-import', $Binary,
    '-processor', 'MIPS:BE:32:default',
    '-overwrite',
    '-scriptPath', $scriptPath,
    '-postScript', 'BoaStringXrefs.java', $outJson
)

& $headless @ghidraArgs
if ($LASTEXITCODE -ne 0) { throw "analyzeHeadless failed with exit code $LASTEXITCODE" }

if (-not (Test-Path $outJson)) { throw "script produced no output at $outJson" }

$report = Get-Content $outJson -Raw | ConvertFrom-Json
Write-Host ""
Write-Host "  ok   language        $($report.language)" -ForegroundColor Green
Write-Host "  ok   image base      $($report.image_base)" -ForegroundColor Green
Write-Host "  ok   functions       $($report.function_count)" -ForegroundColor Green
Write-Host "  ok   strings matched $($report.strings_matched) of $($report.strings_scanned)" -ForegroundColor Green
Write-Host "  ok   wrote           $outJson" -ForegroundColor Green
