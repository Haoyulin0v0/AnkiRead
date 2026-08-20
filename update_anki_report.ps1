param(
    [int]$WaitSeconds = 45,
    [int]$Days = 5,
    [string]$Profile = "",
    [string]$AnkiPath = ""
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot
$startedByScript = $false

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
        Start-Process -FilePath $ankiFilePath
        $startedByScript = $true
    } else {
        Write-Error "anki.exe was not found. Open Anki first, or provide -AnkiPath."
        exit 1
    }
}

Start-Sleep -Seconds $WaitSeconds

if ($startedByScript) {
    # Close gracefully so Anki releases collection.anki2/collection.anki21.
    $anki = Get-Process -Name "anki" -ErrorAction SilentlyContinue
    if ($anki) {
        $anki.CloseMainWindow() | Out-Null
        if (-not $anki.WaitForExit(120000)) {
            Write-Error "Anki did not exit after 120 seconds; collection is still locked."
            exit 2
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

