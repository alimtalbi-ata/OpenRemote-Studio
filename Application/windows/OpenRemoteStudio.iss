; Inno Setup 6, per-user installation without administrator privileges.
#define MyAppName "OpenRemote Studio"
#include "version.generated.iss"
#define MyAppExeName "OpenRemoteStudio.exe"
[Setup]
AppId={{B0D34665-8872-4D91-A4D5-C11F21550E8F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Abdelhalim Talbi
DefaultDirName={localappdata}\Programs\OpenRemote Studio
DefaultGroupName=OpenRemote Studio
PrivilegesRequired=lowest
OutputDir=..\..\Binary\Installer
OutputBaseFilename=OpenRemoteStudio-V{#MyAppVersion}-Windows-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
[Files]
#ifdef SingleExeBuild
Source: "..\dist\OpenRemoteStudio.exe"; DestDir: "{app}"; Flags: ignoreversion
#else
Source: "..\dist\OpenRemoteStudio\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
#endif
[Icons]
Name: "{autoprograms}\OpenRemote Studio"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\OpenRemote Studio"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le bureau"; Flags: unchecked
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer OpenRemote Studio"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\build-log.txt"
