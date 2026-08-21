param(
    [int]$WaitSeconds = 45,
    [int]$Days = 5,
    [string]$Profile = "",
    [string]$AnkiPath = ""
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot
$startedByScript = $false

# If Anki's window is already gone but a stale hidden process remains, clean up
# only that hidden process. A visible Anki window is never terminated here.
$existingAnki = Get-Process -Name "anki" -ErrorAction SilentlyContinue
if ($existingAnki) {
    $visibleAnki = $existingAnki | Where-Object { $_.MainWindowHandle -ne 0 }
    if ($visibleAnki) {
        Write-Error "Anki is already running with a visible window. Close it and run this script again."
        exit 2
    }
    $existingAnki | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Anki handles sync on profile open; this script waits and reads the local collection.
$anki = Get-Process -Name "anki" -ErrorAction SilentlyContinue
if (-not $anki) {
    if ($AnkiPath) {
        $ankiExe = Get-Item -LiteralPath $AnkiPath -ErrorAction SilentlyContinue
    } else {
        $knownPaths = @(
            "D:\Anki\anki.exe",
            "$env:LOCALAPPDATA\Programs\Anki\anki.exe",
            "C:\Program Files\Anki\anki.exe",
            "C:\Program Files (x86)\Anki\anki.exe"
        )
        $ankiExe = $knownPaths | ForEach-Object { Get-Item -LiteralPath $_ -ErrorAction SilentlyContinue } | Select-Object -First 1
        if (-not $ankiExe) { $ankiExe = Get-Command "anki.exe" -ErrorAction SilentlyContinue }
    }
    if ($ankiExe) {
        $ankiFilePath = if ($ankiExe.FullName) { $ankiExe.FullName } else { $ankiExe.Source }
        $startedAnki = Start-Process -FilePath $ankiFilePath -PassThru
        $startedByScript = $true
    } else {
        Write-Error "anki.exe was not found. Open Anki first, or provide -AnkiPath."
        exit 1
    }
}

Start-Sleep -Seconds $WaitSeconds

if ($startedByScript) {
    # Close gracefully so Anki releases collection.anki2/collection.anki21.
    if ($startedAnki) {
        $startedAnki.Refresh()
        $startedAnki.CloseMainWindow() | Out-Null
        if (-not $startedAnki.WaitForExit(120000)) {
            Write-Warning "Anki did not exit normally; stopping only the process started by this script."
            Stop-Process -Id $startedAnki.Id -Force
            $startedAnki.WaitForExit(30000)
        }
    }
} else {
    Write-Error "Anki is already running. Close Anki after synchronization, then run this script again."
    exit 2
}

$arguments = @('.\anki_today.py', '--local', '--days', $Days)
if ($Profile) {
    $arguments += '--profile'
    $arguments += $Profile
}
python @arguments

