# Build & Installation Readiness — 2026-10-07

## Estado

O projeto está preparado para produzir e instalar as duas superfícies de distribuição:

- **Windows PC:** Inno Setup -> `VazaoSovereignTrader-Setup.exe`.
- **Android:** Buildozer em Ubuntu via GitHub Actions -> APK debug instalável.

## PC Windows

Toolchain validada no PC:
- Python 3.12.
- Inno Setup 6.7.1.
- PyInstaller.
- Playwright/Chromium.
- Git.

Comando de build:
```powershell
.\scripts\build_windows_installer.ps1
```

Saída esperada:
`installer-output\VazaoSovereignTrader-Setup.exe`.

O instalador cria o runtime local, configuração PAPER, pastas de troca e tarefas de arranque.

## Android

O Windows não é usado como host nativo do Buildozer nesta fase. O workflow `.github/workflows/android-apk.yml` compila em `ubuntu-latest` com Python 3.11, Buildozer 1.5.0 e Cython 0.29.36.

Fluxo:
1. GitHub Actions -> `Android APK` -> `Run workflow`.
2. Download do artefacto `vazaosovereigntrader-android`.
3. Ligar um Android autorizado por USB/ADB.
4. Instalar com:
```powershell
.\scripts\install_apk.ps1 -ApkPath .\caminho\VazaoSovereignTrader.apk
```
5. Abrir o cockpit e concluir o pairing protegido.

## Preflight

`scripts\release_preflight.ps1` confirma Git, Python, Inno Setup, ADB, workflows, Buildozer spec, compilação Python do mobile e um checkpoint de testes de mobile + runtime controlado.

Checkpoint local validado nesta preparação:
- **14 passed em 18.95s**.
- PowerShell syntax check: OK.
- ADB disponível.
- Inno Setup disponível.

## Segurança

Os builds e instalações não ativam REAL. O APK continua a ser cockpit/control-plane; o PC continua a ser executor autoritativo. Não são colocadas chaves de exchange no APK ou no instalador.

Antes de qualquer uso REAL continuam obrigatórios os gates de autorização humana, readiness, reconciliação, risco, frescura e ExecutionGate. Nenhum build verde equivale a autorização REAL.

## Pairing físico

O fluxo USB assistido está documentado em `docs/ANDROID_FIRST_PAIRING.md`. A validação final de ADB/Keystore deve ser feita com um dispositivo Android físico antes de considerar o pairing OEM-validado.