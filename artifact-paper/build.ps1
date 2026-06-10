<#
.SYNOPSIS
    Windows build for the LNI artifact paper (PowerShell equivalent of the Makefile).

.DESCRIPTION
    Runs the standard LNI biblatex build: pdflatex -> biber -> pdflatex -> pdflatex,
    producing artifact.pdf.

    IMPORTANT (engine choice): this script does NOT use whatever pdflatex/biber sit
    on PATH. On this machine the system MiKTeX has a version-mismatched LaTeX kernel
    that fails on recent packages (e.g. footmisc: "Undefined control sequence
    \IfFormatAtLeastF"). The TeX distribution that actually works -- and that ships
    lni.cls plus biber -- is the TinyTeX install that Quarto manages under
    %APPDATA%\TinyTeX. So the script defaults to that engine. Override with
    -TexBinDir if your working pdflatex/biber live elsewhere.

    lni.cls is the official GI class provided by the TeX distribution; it is not
    bundled in this folder.

    BIBLIOGRAPHY STYLE: the updated biblatex-LNI style (v0.7, 2025-01-27, from
    https://github.com/gi-ev/biblatex-lni) is bundled alongside this script as
    LNI.bbx / LNI.cbx / LNI-english.lbx / LNI-ngerman.lbx. Because pdflatex/biber
    are run from this folder, kpathsea finds these local copies *before* the
    (possibly older) ones in the TeX distribution, so the bundled version is the
    one actually used -- in particular its unified DOI formatting, as requested by
    the LNI editors. The script verifies they are present before building.

.PARAMETER Clean
    Remove build by-products (.aux/.bbl/.bcf/.blg/.log/.out/.run.xml/.toc) and exit.

.PARAMETER TexBinDir
    Directory containing pdflatex.exe/biber.exe. Defaults to Quarto's TinyTeX bin
    (%APPDATA%\TinyTeX\bin\windows).

.EXAMPLE
    pwsh ./build.ps1            # build artifact.pdf
    pwsh ./build.ps1 -Clean     # remove intermediates
#>
[CmdletBinding()]
param(
    [switch]$Clean,
    [string]$TexBinDir = (Join-Path $env:APPDATA 'TinyTeX\bin\windows')
)

$ErrorActionPreference = 'Stop'

$Doc     = 'artifact'
$WorkDir = $PSScriptRoot

# --- clean -----------------------------------------------------------------
$intermediates = '.aux', '.bbl', '.bcf', '.blg', '.log', '.out', '.run.xml', '.toc'
if ($Clean) {
    foreach ($ext in $intermediates) {
        $f = Join-Path $WorkDir "$Doc$ext"
        if (Test-Path $f) { Remove-Item $f -Force; Write-Host "removed $Doc$ext" }
    }
    Write-Host "Clean done."
    return
}

# --- locate engine ---------------------------------------------------------
$PdfLatex = Join-Path $TexBinDir 'pdflatex.exe'
$Biber    = Join-Path $TexBinDir 'biber.exe'
foreach ($exe in @($PdfLatex, $Biber)) {
    if (-not (Test-Path $exe)) {
        throw "TeX engine not found: $exe. Pass -TexBinDir <dir> with a working pdflatex/biber (Quarto's TinyTeX, not the broken system MiKTeX)."
    }
}
Write-Host "TeX engine : $TexBinDir"

# --- verify bundled biblatex-LNI style is present (local override) ----------
$lniStyle = 'LNI.bbx', 'LNI.cbx', 'LNI-english.lbx', 'LNI-ngerman.lbx'
foreach ($f in $lniStyle) {
    if (-not (Test-Path (Join-Path $WorkDir $f))) {
        throw "Bundled biblatex-LNI style file missing: $f. Copy the updated style from https://github.com/gi-ev/biblatex-lni into this folder so the local (current) version is used instead of the TeX distribution's."
    }
}
Write-Host "LNI style  : bundled (local LNI.bbx/.cbx/.lbx override the distribution)"

# --- build: pdflatex -> biber -> pdflatex x2 -------------------------------
Push-Location $WorkDir
try {
    $opts = @('-interaction=nonstopmode', '-halt-on-error', "$Doc.tex")

    Write-Host "[1/4] pdflatex (pass 1) ..."
    & $PdfLatex @opts | Out-Null
    if (-not (Test-Path "$Doc.bcf")) { throw "pass 1 produced no .bcf - see $Doc.log." }

    Write-Host "[2/4] biber ..."
    & $Biber $Doc
    if ($LASTEXITCODE -ne 0) { throw "biber failed (exit $LASTEXITCODE) - see $Doc.blg." }

    Write-Host "[3/4] pdflatex (pass 2) ..."
    & $PdfLatex @opts | Out-Null

    Write-Host "[4/4] pdflatex (pass 3) ..."
    & $PdfLatex @opts | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "final pdflatex pass failed (exit $LASTEXITCODE) - see $Doc.log." }
}
finally {
    Pop-Location
}

if (-not (Test-Path (Join-Path $WorkDir "$Doc.pdf"))) {
    throw "$Doc.pdf was not produced - check $Doc.log."
}
Write-Host "`nDone -> $Doc.pdf"
