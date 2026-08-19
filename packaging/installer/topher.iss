; phase 7: windows installer script. builds TOPHER-Setup-<version>.exe from the
; payload directory CI's assemble-payload job produces at packaging\payload\ -
; that directory is a full-history git checkout (origin=dantepalmieri/TOPHER,
; pinned to the release tag) with the built frontend, bundled venv, and frozen
; launcher already placed inside it. running ISCC locally for a dry run first
; requires populating packaging\payload\ by hand the same way (see
; packaging\scripts\).
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
; per-user, no admin prompt ever - load-bearing for self-improvement mode,
; which needs the install directory to stay fully writable and git-commit-able
; with zero elevation friction
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
; the whole assembled payload, .git included on purpose (no dotfile exclusion) -
; self-improve mode needs a real, working git repo already pointed at origin
Source: "..\payload\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\TOPHER"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall TOPHER"; Filename: "{uninstallexe}"
Name: "{userstartup}\TOPHER"; Filename: "{app}\{#MyAppExeName}"; Tasks: launchatstartup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch TOPHER now"; Flags: nowait postinstall skipifsilent

[Code]
function GitIsOnPath(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/C where git', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
    and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
var
  ExistingGitDirectory: String;
  UserChoice: Integer;
begin
  Result := True;

  // warns before overwriting an existing install's .git - self-improvement
  // mode may have local commits or in-progress work that hasn't been pushed
  // yet, and this installer has no merge logic, only a plain file copy
  ExistingGitDirectory := ExpandConstant('{localappdata}\Programs\TOPHER\.git');
  if DirExists(ExistingGitDirectory) then
  begin
    UserChoice := MsgBox(
      'An existing TOPHER install was found. Installing will overwrite its files, ' +
      'including local git history. If the self-improving team has made commits ' +
      'that were not pushed yet, push them first.' + #13#10 + #13#10 +
      'Continue anyway?',
      mbConfirmation, MB_OKCANCEL);
    if UserChoice = IDCANCEL then
      Result := False;
  end;

  if Result and (not GitIsOnPath()) then
    MsgBox(
      'Git was not found on PATH. TOPHER itself will still work fully, but the ' +
      'self-improving team needs git to commit its own changes. Install Git for ' +
      'Windows from git-scm.com/download/win whenever you want that capability.',
      mbInformation, MB_OK);
end;
