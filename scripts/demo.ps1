. (Join-Path $PSScriptRoot 'common.ps1')
Push-Location $script:LabRoot
try {
    $python = Get-LabPython
    # Deploy explicitly first. Never overwrite a deployment during a demo.
    Invoke-LabCommand -FilePath $python -Arguments @('-m', 'defi_lab.cli', 'status')
    Invoke-LabCommand -FilePath $python -Arguments @('-m', 'defi_lab.cli', 'swap', '--path', 'A', 'B', '--amount', '10')
    Invoke-LabCommand -FilePath $python -Arguments @('-m', 'defi_lab.cli', 'swap', '--path', 'A', 'B', 'C', 'D', '--amount', '10')
    Invoke-LabCommand -FilePath $python -Arguments @('-m', 'defi_lab.cli', 'route', '--amount', '10', '--execute')
    Invoke-LabCommand -FilePath $python -Arguments @('-m', 'defi_lab.cli', 'flash', '--amount', '100', '--min-profit', '1')
} finally {
    Pop-Location
}
