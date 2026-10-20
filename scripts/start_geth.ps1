param([string]$GethPath = '')
. (Join-Path $PSScriptRoot 'common.ps1')

Push-Location $script:LabRoot
try {
    $geth = Get-LabGeth -GethPath $GethPath
    New-Item -ItemType Directory -Force -Path '.local' | Out-Null
    $dataDir = Join-Path $script:LabRoot '.local/geth'
    Write-Host 'Geth local chain 1337. Keep this terminal open; Ctrl+C stops the node.'
    Invoke-LabCommand -FilePath $geth -Arguments @(
        '--dev', '--dev.period', '1', '--datadir', $dataDir,
        '--http', '--http.addr', '127.0.0.1', '--http.port', '8545',
        '--http.api', 'eth,net,web3', '--ipcdisable', '--nodiscover',
        '--maxpeers', '0', '--verbosity', '3'
    )
} finally {
    Pop-Location
}
