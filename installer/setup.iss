[Setup]
AppId={{F9D8A7B6-C5D4-E3F2-A1B0-9C8D7E6F5A4B}
AppName=Multispectral Imaging System
AppVersion=1.0
AppPublisher=Karol Puczynski
DefaultDirName={autopf}\Multispectral Imaging System
DisableProgramGroupPage=yes
OutputDir=.\Output
OutputBaseFilename=MultispectralSystem_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\MultispectralSystem\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Preserve the paths used by the unchanged Python hardware loaders.
Source: "..\dlls\64_lib\*"; DestDir: "{app}\dlls\64_lib"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dlls\control\FTD2XX.dll"; DestDir: "{app}\dlls\control"; Flags: ignoreversion
Source: "..\dlls\control\KURIOS_COMMAND_LIB_Win64.dll"; DestDir: "{app}\dlls\control"; Flags: ignoreversion
Source: "..\source\data\*"; DestDir: "{app}\source\data"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Multispectral Imaging System"; Filename: "{app}\MultispectralSystem.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Multispectral Imaging System"; Filename: "{app}\MultispectralSystem.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\MultispectralSystem.exe"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,Multispectral Imaging System}"; Flags: nowait postinstall skipifsilent
