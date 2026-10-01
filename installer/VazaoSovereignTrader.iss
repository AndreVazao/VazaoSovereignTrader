#define AppName "VazaoSovereignTrader"
#define AppVersion "2026.10.1"
#define AppPublisher "VazaoSovereignTrader"
#define AppExeName "VazaoSovereignTrader.exe"
#define CollectorExeName "VazaoSovereignTrader-MarketData.exe"

[Setup]
AppId={{A4A0B5A5-9F0C-4C50-8C44-6E7D0F8A0B31}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\VazaoSovereignTrader
DisableProgramGroupPage=yes
OutputDir=installer-output
OutputBaseFilename=VazaoSovereignTrader-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
Uninstallable=yes
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Files]
Source: "build\VazaoSovereignTrader.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\VazaoSovereignTrader-MarketData.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\config\config.example.json"; DestDir: "{app}\config"; Flags: ignoreversion onlyifdoesntexist
Source: "build\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\docs\WINDOWS_ONE_CLICK_INSTALL.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Dirs]
Name: "{app}\config"
Name: "{app}\data\radar"
Name: "{app}\data\logs"
Name: "{app}\data\browser\profiles"
Name: "{app}\data\operator_exchange\INBOX"
Name: "{app}\data\operator_exchange\OUTBOX"

[Icons]
Name: "{autodesktop}\VazaoSovereignTrader"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\VazaoSovereignTrader"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Pasta de troca - INBOX"; Filename: "{app}\data\operator_exchange\INBOX"
Name: "{group}\Pasta de troca - OUTBOX"; Filename: "{app}\data\operator_exchange\OUTBOX"

[Run]
Filename: "{sys}\schtasks.exe"; Parameters: "/Create /TN ""VazaoSovereignTrader"" /SC ONLOGON /TR ""{app}\{#AppExeName}"" /RL LIMITED /F"; Flags: runhidden
Filename: "{sys}\schtasks.exe"; Parameters: "/Create /TN ""VazaoSovereignTrader-MarketData"" /SC ONLOGON /TR ""{app}\{#CollectorExeName}"" --config ""{app}\config\config.local.json"" --data-dir ""{app}\data\radar"" /RL LIMITED /F"; Flags: runhidden
Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Description: "Iniciar o VazaoSovereignTrader agora"; Flags: nowait postinstall skipifsilent
Filename: "{sys}\explorer.exe"; Parameters: "{app}\data\operator_exchange"; Description: "Abrir pasta de troca (INBOX / OUTBOX)"; Flags: nowait postinstall skipifsilent unchecked

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""VazaoSovereignTrader"" /F"; Flags: runhidden
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""VazaoSovereignTrader-MarketData"" /F"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data\browser\profiles"
