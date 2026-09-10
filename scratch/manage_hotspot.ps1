param (
    [string]$Ssid = "NERO_GO2_WIFI",
    [string]$Passphrase = "NeumannRobot2026",
    [string]$Action = "start"
)

[Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking.NetworkOperators, ContentType = WindowsRuntime] | Out-Null
[Windows.Networking.Connectivity.NetworkInformation, Windows.Networking.Connectivity, ContentType = WindowsRuntime] | Out-Null

function Wait-WinRTAction($asyncOp) {
    if (-not $asyncOp) { return }
    $timeout = 100 # 5 sec max
    while ($asyncOp -and $asyncOp.Status -and $asyncOp.Status.ToString() -eq "Started" -and $timeout -gt 0) {
        Start-Sleep -Milliseconds 50
        $timeout--
    }
    if ($asyncOp -and $asyncOp.Status) {
        Write-Host "Async Status:" $asyncOp.Status
    }
}

$profile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
if (-not $profile) {
    Write-Error "Nem található aktív internetes kapcsolat a laptopon!"
    exit 1
}

$mgr = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($profile)

if ($Action -eq "status") {
    $cfg = $mgr.GetCurrentAccessPointConfiguration()
    Write-Host "Hotspot állapota: $($mgr.TetheringOperationalState)"
    Write-Host "SSID: $($cfg.Ssid)"
    Write-Host "Jelszó: $($cfg.Passphrase)"
    Write-Host "Csatlakozott kliensek: $($mgr.ClientCount)"
    exit 0
}

# Config frissítése
$cfg = $mgr.GetCurrentAccessPointConfiguration()
$cfg.Ssid = $Ssid
$cfg.Passphrase = $Passphrase

try {
    $configOp = $mgr.ConfigureAccessPointAsync($cfg)
    Wait-WinRTAction $configOp
    Write-Host "Hotspot beállítva: SSID='$Ssid', Password='$Passphrase'"
} catch {
    Write-Host "Config módosítás elhagyva (már be volt állítva): $_"
}

if ($Action -eq "start") {
    if ($mgr.TetheringOperationalState.ToString() -ne "On") {
        Write-Host "Hotspot indítása folyamatban..."
        $startOp = $mgr.StartTetheringAsync()
        Wait-WinRTAction $startOp
        Write-Host "Hotspot állapota az indítás után: $($mgr.TetheringOperationalState)"
    } else {
        Write-Host "A Hotspot már aktív!"
    }
} elseif ($Action -eq "stop") {
    if ($mgr.TetheringOperationalState.ToString() -eq "On") {
        Write-Host "Hotspot leállítása..."
        $stopOp = $mgr.StopTetheringAsync()
        Wait-WinRTAction $stopOp
        Write-Host "Hotspot állapota a leállítás után: $($mgr.TetheringOperationalState)"
    }
}
