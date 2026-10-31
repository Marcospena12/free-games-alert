#define AppName "Free Games Hub"
#define AppExeName "FreeGamesHub.exe"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{53128B5A-1AD3-478C-A460-155BEE2872FB}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Marcos
DefaultDirName={localappdata}\Programs\FreeGamesHub
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=FreeGamesHub-Setup-{#AppVersion}
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
MinVersion=10.0
UsePreviousAppDir=no
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\dist\FreeGamesHub\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#AppExeName}"; Parameters: "--quit"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "QuitMonitor"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  OldExe: String;
  LegacyExe: String;
begin
  Result := '';
  OldExe := ExpandConstant('{app}\{#AppExeName}');
  LegacyExe := ExpandConstant('{localappdata}\Programs\SteamFreeGamesMonitor\SteamFreeGamesMonitor.exe');
  if FileExists(OldExe) then
  begin
    if not Exec(OldExe, '--quit', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      Result := 'Não foi possível solicitar o fechamento do aplicativo em execução.'
    else if ResultCode <> 0 then
      Result := 'Feche o Free Games Hub pela bandeja e tente novamente.';
  end
  else if FileExists(LegacyExe) then
  begin
    Exec(LegacyExe, '--quit', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

procedure MigrateLegacyAutostart;
var
  OldValue: String;
begin
  if RegQueryStringValue(
       HKCU,
       'Software\Microsoft\Windows\CurrentVersion\Run',
       'SteamFreeGamesMonitor',
       OldValue) then
  begin
    RegWriteStringValue(
      HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'FreeGamesHub',
      '"' + ExpandConstant('{app}\{#AppExeName}') + '" --hidden');
    RegDeleteValue(
      HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'SteamFreeGamesMonitor');
  end;
end;

procedure RemoveLegacyInstall;
var
  LegacyDir: String;
begin
  LegacyDir := ExpandConstant('{localappdata}\Programs\SteamFreeGamesMonitor');
  if CompareText(LegacyDir, ExpandConstant('{app}')) <> 0 then
    DelTree(LegacyDir, True, True, True);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MigrateLegacyAutostart;
    RemoveLegacyInstall;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RegDeleteValue(
      HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'FreeGamesHub'
    );
end;
