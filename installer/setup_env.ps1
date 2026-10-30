# Richtet eine eigene, vom Rest des Systems unabhaengige Python-Umgebung fuer
# VideoRepomat ein: laedt Miniconda in den App-Ordner (kein systemweiter
# Python/Conda-Eingriff), legt darin eine "videorestore"-Umgebung an und
# installiert alle benoetigten Pakete inkl. der CUDA-Version von PyTorch.
# Wird automatisch am Ende der Installation aufgerufen (siehe VideoRepomat.iss)
# - kann bei Bedarf auch von Hand erneut ausgefuehrt werden (ueberspringt
# bereits erledigte Schritte anhand der Marker-Datei).
param(
    [string]$AppDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$envRoot = Join-Path $AppDir "python-env"
$envName = "videorestore"
$envPath = Join-Path $envRoot "envs\$envName"
$pythonExe = Join-Path $envPath "python.exe"
$markerFile = Join-Path $envRoot "setup_complete.marker"

function Write-Step($text) {
    Write-Host ""
    Write-Host "=== $text ===" -ForegroundColor Cyan
}

function Assert-LastExit($what) {
    if ($LASTEXITCODE -ne 0) {
        throw "$what fehlgeschlagen (Exitcode $LASTEXITCODE)."
    }
}

if (Test-Path $markerFile) {
    Write-Host "VideoRepomat-Umgebung bereits eingerichtet, ueberspringe Setup."
    exit 0
}

Write-Step "VideoRepomat wird eingerichtet - je nach Internetverbindung 5-15 Minuten."

$condaBat = Join-Path $envRoot "condabin\conda.bat"
if (-not (Test-Path $condaBat)) {
    Write-Step "Lade Miniconda herunter ..."
    $minicondaUrl = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
    $minicondaInstaller = Join-Path $env:TEMP "VideoRepomat_Miniconda_Installer.exe"
    Invoke-WebRequest -Uri $minicondaUrl -OutFile $minicondaInstaller -UseBasicParsing

    Write-Step "Installiere eine eigene Miniconda-Basis nach $envRoot (nicht systemweit) ..."
    Start-Process -FilePath $minicondaInstaller -ArgumentList "/S", "/D=$envRoot" -Wait
    Remove-Item $minicondaInstaller -Force -ErrorAction SilentlyContinue
}

$condaExe = Join-Path $envRoot "Scripts\conda.exe"
if (-not (Test-Path $condaExe)) {
    throw "Miniconda-Installation fehlgeschlagen - conda.exe nicht gefunden unter $condaExe"
}

if (-not (Test-Path $pythonExe)) {
    Write-Step "Lege Python-Umgebung an (Python 3.11) ..."
    # -c conda-forge --override-channels statt der Anaconda-eigenen
    # Standardkanaele - die verlangen seit einiger Zeit eine explizite
    # Zustimmung zu Anacondas Nutzungsbedingungen, bevor nicht-interaktive
    # Aufrufe wie hier funktionieren (CondaToSNonInteractiveError).
    & $condaExe create -y -p $envPath -c conda-forge --override-channels python=3.11
    Assert-LastExit "conda create"
}

if (-not (Test-Path $pythonExe)) {
    throw "Anlegen der Python-Umgebung fehlgeschlagen - python.exe nicht gefunden unter $pythonExe"
}

Write-Step "Aktualisiere pip ..."
& $pythonExe -m pip install --upgrade pip
Assert-LastExit "pip-Update"

Write-Step "Installiere PyTorch mit CUDA-Unterstuetzung (das ist der groesste Download) ..."
# cu128 statt aelterer CUDA-Builds: neuere GPUs (RTX 50xx/Blackwell, sm_120)
# laufen nur damit - torch.cuda.is_available() liefert auf aelteren Builds
# zwar True, die Kernel schlagen dann aber fehl.
& $pythonExe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
Assert-LastExit "PyTorch-Installation"

Write-Step "Installiere restliche Abhaengigkeiten ..."
& $pythonExe -m pip install -r (Join-Path $AppDir "requirements.txt")
Assert-LastExit "Installation der Abhaengigkeiten"

New-Item -ItemType File -Path $markerFile -Force | Out-Null
Write-Step "Fertig! VideoRepomat kann jetzt ueber die Verknuepfung gestartet werden."
Write-Host ""
Write-Host "Hinweis: Modell-Gewichte werden erst beim ersten tatsaechlichen" -ForegroundColor Yellow
Write-Host "Gebrauch der jeweiligen Funktion automatisch nachgeladen." -ForegroundColor Yellow
