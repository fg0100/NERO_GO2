param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'

$accessDir = Join-Path $env:USERPROFILE 'Documents\Codex\pickerbot-access'
$key = Join-Path $accessDir 'pickerbot_mini'
$knownHosts = Join-Path $accessDir 'known_hosts'
$stateFile = Join-Path $env:TEMP 'pickerbot-demo-view.json'
$url = 'http://127.0.0.1:8902/dashboard.html'

if (-not (Test-Path -LiteralPath $key) -or -not (Test-Path -LiteralPath $knownHosts)) {
    throw 'A Pickerbot SSH-kulcs vagy known_hosts fájl hiányzik.'
}
if (Test-Path -LiteralPath $stateFile) {
    throw "A bemutatónézethez már tartozik állapotfájl: $stateFile. Előbb futtasd a stop-demo-view.ps1 fájlt."
}
foreach ($port in 8080, 8902) {
    $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
    try { $probe.Start() }
    catch { throw "A helyi $port port már használatban van." }
    finally { $probe.Stop() }
}

$sshArgs = @(
    '-N', '-L', '127.0.0.1:8080:127.0.0.1:8080',
    '-i', $key,
    '-o', 'BatchMode=yes',
    '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=15',
    '-o', 'StrictHostKeyChecking=yes',
    '-o', "UserKnownHostsFile=$knownHosts",
    'wheeltec@192.168.123.50'
)
$tunnel = Start-Process -FilePath 'ssh.exe' -ArgumentList $sshArgs -PassThru -WindowStyle Hidden
try {
    Start-Sleep -Seconds 2
    if ($tunnel.HasExited) { throw 'Az SSH-alagút nem indult el.' }

    $serverArgs = @('-m', 'http.server', '8902', '--bind', '127.0.0.1', '--directory', $PSScriptRoot)
    $server = Start-Process -FilePath 'python.exe' -ArgumentList $serverArgs -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2
    if ($server.HasExited) { throw 'A helyi bemutatóoldal nem indult el.' }

    @{ tunnelPid = $tunnel.Id; serverPid = $server.Id } |
        ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8
    if (-not $NoBrowser) { Start-Process $url }
    Write-Host "Bemutató: $url"
    Write-Host 'Leállítás: scripts\stop-demo-view.ps1'
} catch {
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -ErrorAction SilentlyContinue }
    if (-not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue }
    throw
}
