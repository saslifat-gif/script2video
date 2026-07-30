#ifndef MyAppVersion
  #define MyAppVersion "1.0.10"
#endif

#define MyAppName "Script2Video Studio"
#define MyAppExeName "Script2Video Studio.exe"
#define MyAppPublisher "Script2Video"
#define MyAppURL "https://github.com/saslifat-gif/script2video"

[Setup]
AppId={{B94B72A1-D433-4C8C-B2FA-C4321E6904D2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
LicenseFile=..\..\LICENSE
DefaultDirName={localappdata}\Programs\Script2Video Studio
DefaultGroupName=Script2Video Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\release
OutputBaseFilename=Script2Video-Studio-{#MyAppVersion}-Windows-x64
SetupIconFile=script2video.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\..\dist\Script2Video Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Script2Video Studio"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Script2Video Studio"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Script2Video Studio"; Flags: nowait postinstall skipifsilent
