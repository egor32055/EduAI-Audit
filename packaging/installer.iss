#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define AppName "EduAI Audit"
#define AppExe "EduAI Audit.exe"

[Setup]
AppId={{E3AD10F7-41B4-4FB8-9DFD-9E82EC8C9C09}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=EduAI-Audit
AppPublisherURL=https://github.com/egor32055/EduAI-Audit
DefaultDirName={localappdata}\Programs\EduAI Audit
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=EduAI-Audit-Setup-{#AppVersion}
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\EduAI Audit\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Stop EduAI Audit"; Filename: "{app}\{#AppExe}"; Parameters: "--stop"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#AppExe}"; Parameters: "--stop"; Flags: runhidden waituntilterminated; RunOnceId: "StopEduAIAudit"
