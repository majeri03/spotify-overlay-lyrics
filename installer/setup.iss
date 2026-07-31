; Script Inno Setup untuk EchoLyrics Windows Installer
; Compile menggunakan Inno Setup (ISCC.exe)

[Setup]
AppId={{8F5419A6-8F2D-4B94-8C1B-8728A25D619B}
AppName=EchoLyrics
AppVersion=1.0.0
AppPublisher=EchoLyrics Team
AppPublisherURL=https://github.com/echolyrics
AppSupportURL=https://github.com/echolyrics
AppUpdatesURL=https://github.com/echolyrics
DefaultDirName={autopf}\EchoLyrics
DisableProgramGroupPage=yes
LicenseFile=..\README.md
OutputBaseFilename=EchoLyrics-Setup
SetupIconFile=..\resources\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Jalankan EchoLyrics otomatis saat Windows start"; GroupDescription: "Pengaturan Tambahan:": Flags: unchecked

[Files]
Source: "..\dist\EchoLyrics.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprogramms}\EchoLyrics"; Filename: "{app}\EchoLyrics.exe"
Name: "{autodesktop}\EchoLyrics"; Filename: "{app}\EchoLyrics.exe"; Tasks: desktopicon
Name: "{userstartup}\EchoLyrics"; Filename: "{app}\EchoLyrics.exe"; Tasks: autostart

[Run]
Filename: "{app}\EchoLyrics.exe"; Description: "{cm:LaunchProgram,EchoLyrics}"; Flags: nowait postinstall skipifsilent
