# Shared by Windows PowerShell 5.1 and PowerShell 7 entry points.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:LabRoot = Split-Path -Parent $PSScriptRoot
$script:LabIsWindows = $env:OS -eq 'Windows_NT'

function Invoke-LabCommand {
    param([Parameter(Mandatory = $true)][string]$FilePath, [string[]]$Arguments = @())
    # PowerShell 5.1 does not throw automatically for native nonzero exit codes.
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): $FilePath"
    }
}

function Get-LabPython {
    if ($script:LabIsWindows) {
        $candidate = Join-Path $script:LabRoot '.venv/Scripts/python.exe'
    } else {
        $candidate = Join-Path $script:LabRoot '.venv/bin/python'
    }
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw 'Project Python is missing. Run scripts/install.ps1 first; virtualenvs cannot be copied across operating systems.'
    }
    return $candidate
}

function Get-LabGeth {
    param([string]$GethPath = '')
    $saved = Join-Path $script:LabRoot '.local/geth-path.txt'
    if (-not $GethPath) { $GethPath = $env:GETH_BIN }
    if (-not $GethPath -and (Test-Path -LiteralPath $saved)) {
        $GethPath = (Get-Content -LiteralPath $saved -Raw).Trim()
    }
    if (-not $GethPath) {
        $name = 'geth'
        if ($script:LabIsWindows) { $name = 'geth.exe' }
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue
        if ($null -ne $command) { $GethPath = $command.Source }
    }
    if (-not $GethPath -or -not (Test-Path -LiteralPath $GethPath -PathType Leaf)) {
        throw 'Geth not found. Download/extract official Geth 1.14.13 for your OS; pass -GethPath with the full executable path (see README).'
    }
    $resolved = (Resolve-Path -LiteralPath $GethPath).Path
    $info = @(Invoke-LabCommand -FilePath $resolved -Arguments @('version')) -join "`n"
    if ($info -notmatch '(?m)^Version:\s+1\.14\.13(?:-|\s|$)') {
        throw 'This lab pins Geth 1.14.13. Select that release from the official Geth downloads archive.'
    }
    return $resolved
}
