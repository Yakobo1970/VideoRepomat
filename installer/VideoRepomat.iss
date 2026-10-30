; VideoRepomat Setup - Inno Setup Skript
;
; Baut ein kleines Installer-.exe (nur Quellcode, keine Bibliotheken), das
; nach dem Kopieren der Dateien automatisch setup_env.ps1 aufruft. Das legt
; eine eigene, vom restlichen System unabhaengige Miniconda-Umgebung im
; App-Ordner an und installiert dort alle Python-Pakete inkl. PyTorch/CUDA -
; das ist der eigentlich grosse Download, nicht dieser Installer selbst.
;
; Bauen:
;   "C:\Program Files\Inno Setup 7\ISCC.exe" installer\VideoRepomat.iss

#define AppName "VideoRepomat"
#define AppVersion "0.1.0"
#define AppPublisher "yakobo1970"
#define AppURL "https://www.undabtanzbar.de/software/"
#define AppExeIcon "assets\icon.ico"

[Setup]
AppId={{B7E4C1D2-5A3F-4E88-9C16-2F0D8A7B6E41}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL=https://github.com/Yakobo1970/VideoRepomat/releases
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeIcon}
SetupIconFile=..\assets\icon.ico
OutputDir=..\dist_installer
OutputBaseFilename=VideoRepomat-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
; Installiert pro Benutzer nach {localappdata} - keine Admin-Rechte noetig,
; passt zur eigenstaendigen Miniconda-Umgebung im App-Ordner.
PrivilegesRequired=lowest
LicenseFile=..\LICENSE
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Kompletter Quellcode, aber OHNE: Git-Metadaten, Python-Cache, bereits
; heruntergeladene Modell-Gewichte (werden bei Bedarf automatisch neu
; geladen), die lokale Umgebung und diesen installer-Ordner selbst (der
; wird separat kopiert, damit setup_env.ps1 nicht sich selbst rekursiv
; einschliesst).
Source: "..\*"; DestDir: "{app}"; Excludes: ".git\*,__pycache__\*,*\__pycache__\*,*\*\__pycache__\*,models\*,python-env\*,installer\*,dist_installer\*,*.pyc"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "setup_env.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\python-env\envs\videorestore\pythonw.exe"; Parameters: """{app}\main.py"""; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeIcon}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\python-env\envs\videorestore\pythonw.exe"; Parameters: """{app}\main.py"""; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeIcon}"; Tasks: desktopicon

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installer\setup_env.ps1"" -AppDir ""{app}"""; WorkingDir: "{app}"; StatusMsg: "{cm:SetupEnvStatus}"; Flags: waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python-env"
Type: filesandordirs; Name: "{app}"

[CustomMessages]
german.SetupEnvStatus=Richte Python-Umgebung ein (kann mehrere Minuten dauern) ...
english.SetupEnvStatus=Setting up Python environment (this can take several minutes) ...
