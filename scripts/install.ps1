param([string]$GethPath = '')
. (Join-Path $PSScriptRoot 'common.ps1')

Push-Location $script:LabRoot
try {
    # Use the Windows Python launcher; no shell activation is necessary.
    $pythonCommand = 'python3'
    $pythonPrefix = @()
    $npmCommand = 'npm'
    if ($script:LabIsWindows) {
        $pythonCommand = 'py.exe'
        $pythonPrefix = @('-3.12')
        $npmCommand = 'npm.cmd'
    }
    Invoke-LabCommand -FilePath $pythonCommand -Arguments ($pythonPrefix + @('-c', "import sys; assert sys.version_info[:2] == (3, 12), 'Install Python 3.12'"))
    Invoke-LabCommand -FilePath 'node' -Arguments @('-e', "if(Number(process.versions.node.split('.')[0]) < 20) process.exit(1)")
    $geth = Get-LabGeth -GethPath $GethPath
    if (Test-Path -LiteralPath '.venv') {
        # Preserve an incompatible virtualenv instead of silently replacing it.
        $python = Get-LabPython
        Invoke-LabCommand -FilePath $python -Arguments @('-c', "import sys; assert sys.version_info[:2] == (3, 12), 'Rename the old .venv and rerun installation'")
    } else {
        Invoke-LabCommand -FilePath $pythonCommand -Arguments ($pythonPrefix + @('-m', 'venv', '.venv'))
        $python = Get-LabPython
    }
    Invoke-LabCommand -FilePath $python -Arguments @('-m', 'pip', 'install', '--only-binary=:all:', '--cache-dir', '.local/cache/pip', '-r', 'requirements-lock.txt')
    Invoke-LabCommand -FilePath $npmCommand -Arguments @('ci', '--cache', '.local/cache/npm', '--no-audit', '--no-fund')
    Invoke-LabCommand -FilePath $npmCommand -Arguments @('run', 'compile')
    Invoke-LabCommand -FilePath $python -Arguments @('-m', 'pytest', 'tests/test_routing.py', '-q')
    New-Item -ItemType Directory -Force -Path '.local' | Out-Null
    Set-Content -LiteralPath '.local/geth-path.txt' -Value $geth -Encoding UTF8
    Write-Host 'Installed. Open another PowerShell window and run scripts/start_geth.ps1.'
} finally {
    Pop-Location
}
