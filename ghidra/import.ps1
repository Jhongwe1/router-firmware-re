<#
.SYNOPSIS
    Import a firmware binary into the shared Ghidra project and run full
    auto-analysis. Analysis only — scripts are run separately by analyze.ps1.

.DESCRIPTION
    Split from the W01 version on purpose. Auto-analysis of a 500 KB MIPS binary
    costs minutes and its result is *cached in the project*; a triage script
    costs seconds and gets rewritten a dozen times a day. Fusing the two meant
    every script edit paid for a re-analysis.

    Each binary lands in its own project folder:

        totolink-n150rt/<Label>/<program>

    W01 did not do this, and it was a real bug rather than a cosmetic one.
    `analyzeHeadless -import <path>` names the program after the *file*, so both
    firmware versions imported as a program called `boa`, and `-overwrite` made
    the second import silently destroy the first. The committed
    reports/ghidra-strings-*.json were still correct — each was written during
    its own import, before the next one clobbered the project — but the project
    could not be reopened to check them, and both files record
    `"program": "boa"` with no way to tell which binary produced them.
    Hence -Label folders here, and a recorded source SHA-256 in analyze.ps1.

.PARAMETER Binary
    Path to the ELF to import. Accepts a \\wsl$ path, which is how the extracted
    root filesystems are reached from Windows — see docs/workspace-layout.md.

.PARAMETER Label
    Firmware version this binary came from, e.g. "2.1.2". Becomes the project
    folder, so two versions of the same filename can coexist.

.EXAMPLE
    .\ghidra\import.ps1 -Label 2.1.2 `
      -Binary \\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Binary,
    [Parameter(Mandatory = $true)][string]$Label,
    [string]$ProjectDir = (Join-Path $env:LOCALAPPDATA 'fwre-tools\ghidra-projects'),
    [string]$ProjectName = 'totolink-n150rt'
)

$ErrorActionPreference = 'Stop'

$ghidraHome = $env:GHIDRA_INSTALL_DIR
if (-not $ghidraHome -or -not (Test-Path $ghidraHome)) {
    throw "GHIDRA_INSTALL_DIR is not set or does not exist. Run tools\setup\setup-windows.ps1 first."
}
$headless = Join-Path $ghidraHome 'support\analyzeHeadless.bat'
if (-not (Test-Path $headless)) { throw "analyzeHeadless.bat not found under $ghidraHome" }
if (-not (Test-Path $Binary))   { throw "binary not found: $Binary" }

New-Item -ItemType Directory -Force -Path $ProjectDir | Out-Null

$sha = (Get-FileHash -Algorithm SHA256 -Path $Binary).Hash.ToLower()
Write-Host " ==>  importing $Binary" -ForegroundColor Cyan
Write-Host "      project : $ProjectDir\$ProjectName/$Label" -ForegroundColor DarkGray
Write-Host "      sha256  : $sha" -ForegroundColor DarkGray

# The processor is forced to big-endian MIPS to keep the import deterministic,
# but that is a *check*, not a fix: analyze.ps1 records the language actually
# used, and W01 established the same answer independently from the ELF header
# (notes/anatomy-n150rt.md). Two sources, one answer.
$ghidraArgs = @(
    $ProjectDir, "$ProjectName/$Label",
    '-import', $Binary,
    '-processor', 'MIPS:BE:32:default',
    '-overwrite'
)

& $headless @ghidraArgs
if ($LASTEXITCODE -ne 0) { throw "analyzeHeadless failed with exit code $LASTEXITCODE" }

Write-Host "  ok   analysed and stored under $ProjectName/$Label" -ForegroundColor Green
Write-Host "       next: .\ghidra\analyze.ps1 -Label $Label -Script BoaFormTable" -ForegroundColor DarkGray
