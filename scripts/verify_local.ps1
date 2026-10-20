. (Join-Path $PSScriptRoot 'common.ps1')
$previousIntegration = $env:RUN_INTEGRATION
Push-Location $script:LabRoot
try {
    $python = Get-LabPython
    New-Item -ItemType Directory -Force -Path '.local' | Out-Null
    $env:RUN_INTEGRATION = '1'
    Invoke-LabCommand -FilePath $python -Arguments @('-m', 'pytest', '-q', '--junitxml=.local/test-results.xml')
} finally {
    if ($null -eq $previousIntegration) {
        Remove-Item Env:RUN_INTEGRATION -ErrorAction SilentlyContinue
    } else {
        $env:RUN_INTEGRATION = $previousIntegration
    }
    Pop-Location
}
