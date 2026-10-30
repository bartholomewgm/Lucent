; Установщик Lucent (Inno Setup 6). Собирается из build.py:
; ISCC.exe /DAppVersion=1.0.1 installer\lucent.iss -> dist\Lucent-Setup.exe

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{7C1F4E52-3A9B-4D6E-9A41-5E2B8C0D7F13}
AppName=Lucent
AppVersion={#AppVersion}
AppVerName=Lucent {#AppVersion}
AppPublisher=bartholomewgm
AppPublisherURL=https://github.com/bartholomewgm/videoplayer
; Только для текущего пользователя: права администратора не нужны
PrivilegesRequired=lowest
DefaultDirName={autopf}\Lucent
DefaultGroupName=Lucent
DisableProgramGroupPage=yes
DisableDirPage=auto
OutputDir=..\dist
OutputBaseFilename=Lucent-Setup
SetupIconFile=..\resources\icons\lucent.ico
UninstallDisplayIcon={app}\Lucent.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
; Обновление поверх запущенной программы: закрыть её и открыть снова
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Lucent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Lucent"; Filename: "{app}\Lucent.exe"
Name: "{group}\{cm:UninstallProgram,Lucent}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Lucent"; Filename: "{app}\Lucent.exe"; Tasks: desktopicon

[Registry]
; Lucent в списке «Открыть с помощью» для видеофайлов
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "Lucent"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe\shell\open\command"; ValueType: string; ValueData: """{app}\Lucent.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe\SupportedTypes"; ValueType: string; ValueName: ".mp4"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe\SupportedTypes"; ValueType: string; ValueName: ".mkv"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe\SupportedTypes"; ValueType: string; ValueName: ".avi"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe\SupportedTypes"; ValueType: string; ValueName: ".mov"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe\SupportedTypes"; ValueType: string; ValueName: ".wmv"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe\SupportedTypes"; ValueType: string; ValueName: ".flv"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe\SupportedTypes"; ValueType: string; ValueName: ".webm"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\Applications\Lucent.exe\SupportedTypes"; ValueType: string; ValueName: ".m4v"; ValueData: ""

; Автозапуск включается в настройках программы — при удалении убираем и его
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Lucent"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Lucent.exe"; Description: "{cm:LaunchProgram,Lucent}"; Flags: nowait postinstall skipifsilent
