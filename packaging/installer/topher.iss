; windows installer script. builds TOPHER-Setup-<version>.exe from the payload
; directory CI's assemble-payload job produces at packaging\payload\ - the project
; source with the built frontend, bundled venv, and frozen launcher already placed
; inside it. running ISCC locally for a dry run first requires populating
; packaging\payload\ by hand the same way (see packaging\scripts\).
;
; version is passed in via /DMyAppVersion=x.y.z (see stamp_version.py) so this
; file never needs hand-editing per release; it falls back to a dev placeholder
; when compiled without that define, for local iteration.
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

#define MyAppName "TOPHER"
#define MyAppPublisher "Dante Palmieri"
#define MyAppExeName "TopherLauncher.exe"
#define MyAppURL "https://github.com/dantepalmieri/TOPHER"

; fixed, never regenerate this between releases - inno setup uses it to
; recognize "this is the same app, just a newer version" for upgrades/uninstalls
#define MyAppId "{{6F3D9B4E-8C2A-4E7D-9F1B-2A5C7E0D4B91}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\TOPHER
DefaultGroupName=TOPHER
; per-user, no admin prompt ever - a personal single-user local app has no reason
; to demand elevation just to install
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputBaseFilename=TOPHER-Setup-{#MyAppVersion}
OutputDir=..\dist
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "launchatstartup"; Description: "Launch TOPHER when Windows starts"; Flags: checkedonce

[Files]
; the whole assembled payload (assemble_payload.ps1 already excludes .git - the
; installed app never writes to its own source, so it has no reason to be a
; working git repo)
Source: "..\payload\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\TOPHER"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall TOPHER"; Filename: "{uninstallexe}"
Name: "{userstartup}\TOPHER"; Filename: "{app}\{#MyAppExeName}"; Tasks: launchatstartup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch TOPHER now"; Flags: nowait postinstall skipifsilent
