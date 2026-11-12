; ==============================================================================
; CardioSense Enterprise Windows Inno Setup Script
; Generates enterprise installer: CardioSense-Enterprise-2.4.0-windows-x64-Setup.exe
; Compatible with: Windows 10, Windows 11, Windows Server 2022
; ==============================================================================

#define MyAppName "CardioSense Enterprise"
#define MyAppVersion "2.4.0"
#define MyAppPublisher "American Express & CardioSense Enterprise"
#define MyAppURL "https://enterprise.cardiosense.io"
#define MyAppExeName "CardioSense.exe"

[Setup]
; Unique AppId generated for CardioSense
AppId={{D37F8E91-42C8-48F1-B89E-7539C8F929C4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}
LicenseFile=..\README.md
OutputDir=..\dist
OutputBaseFilename=CardioSense-Enterprise-{#MyAppVersion}-windows-x64-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableDirPage=auto
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a Quick Launch shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "..\dist\CardioSense\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Custom Pascal Script to verify architecture
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not Is64BitInstallMode then
  begin
    MsgBox('CardioSense Enterprise requires a 64-bit operating system (x64 or ARM64 with emulation).', mbCriticalError, MB_OK);
    Result := False;
  end;
end;
