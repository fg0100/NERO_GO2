$ErrorActionPreference = 'Stop'
$stateFile = Join-Path $env:TEMP 'pickerbot-demo-view.json'
if (-not (Test-Path -LiteralPath $stateFile)) {
    Write-Host 'A bemutatónézet nem fut ezen a gépen.'
    exit 0
}
$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
foreach ($entry in @(@($state.serverPid, 'python'), @($state.tunnelPid, 'ssh'))) {
    $process = Get-Process -Id $entry[0] -ErrorAction SilentlyContinue
    if ($process -and $process.ProcessName -eq $entry[1]) {
        Stop-Process -Id $process.Id
    }
}
Remove-Item -LiteralPath $stateFile
Write-Host 'A helyi bemutatónézet leállt. A robot szolgáltatásai tovább futnak.'
