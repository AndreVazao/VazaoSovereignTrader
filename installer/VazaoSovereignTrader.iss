#define AppName "VazaoSovereignTrader"
#ifndef AppVersion
  #define AppVersion "2026.10.1"
#endif
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
OutputDir=..\installer-output
OutputBaseFilename=VazaoSovereignTrader-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
Uninstallable=yes
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=no
RestartApplications=no

[Files]
Source: "build\VazaoSovereignTrader.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\VazaoSovereignTrader-MarketData.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\VazaoSovereignTrader-Radar.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\VazaoSovereignTrader-TopOfBook.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\VazaoSovereignTrader-L2.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\VazaoSovereignTrader-MarketDataService.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\ms-playwright\*"; DestDir: "{app}\ms-playwright"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "build\config\config.example.json"; DestDir: "{app}\config"; Flags: ignoreversion onlyifdoesntexist
Source: "build\config\config.example.json"; DestDir: "{app}\config"; DestName: "config.local.json"; Flags: ignoreversion onlyifdoesntexist
Source: "build\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\docs\WINDOWS_ONE_CLICK_INSTALL.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "build\docs\PUBLIC_MARKET_DATA_SERVICE.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "build\scripts\ensure_windows_token.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "build\scripts\stop_market_data_service.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion

[Dirs]
Name: "{app}\config"
Name: "{app}\data\radar"
Name: "{localappdata}\VazaoSovereignTraderData\market-data"
Name: "{app}\data\logs"
Name: "{app}\data\browser\profiles"
Name: "{app}\data\operator_exchange\INBOX"
Name: "{app}\data\operator_exchange\OUTBOX"
Name: "{app}\scripts"

[Icons]
Name: "{autodesktop}\VazaoSovereignTrader"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\VazaoSovereignTrader"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Iniciar recolha contínua"; Filename: "{app}\VazaoSovereignTrader-MarketDataService.exe"; WorkingDir: "{app}"
Name: "{group}\Parar recolha contínua"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\stop_market_data_service.ps1"""
Name: "{group}\Pasta de troca - INBOX"; Filename: "{app}\data\operator_exchange\INBOX"
Name: "{group}\Pasta de troca - OUTBOX"; Filename: "{app}\data\operator_exchange\OUTBOX"

; The supervised collector is launched manually after installation and local validation.

[UninstallRun]
; Request a cooperative shutdown before removing worker executables.
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\stop_market_data_service.ps1"""; Flags: runhidden waituntilterminated; RunOnceId: "StopVstPublicMarketDataService"
; Remove only the legacy VST tasks created by older installer versions.
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""VazaoSovereignTrader"" /F"; Flags: runhidden; RunOnceId: "RemoveLegacyVstEngineTask"
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""VazaoSovereignTrader-MarketData"" /F"; Flags: runhidden; RunOnceId: "RemoveLegacyVstMarketDataTask"
