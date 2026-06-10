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

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\MultispectralSystem\MultispectralSystem.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\MultispectralSystem\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Multispectral Imaging System"; Filename: "{app}\MultispectralSystem.exe"
Name: "{autodesktop}\Multispectral Imaging System"; Filename: "{app}\MultispectralSystem.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MultispectralSystem.exe"; Description: "{cm:LaunchProgram,Multispectral Imaging System}"; Flags: nowait postinstall skipifsilent
