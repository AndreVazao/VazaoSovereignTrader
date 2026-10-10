# Sessão USB Android — 2026-10-10

## Resultado confirmado
- PC Windows: `PC-Vazao-Anjos`; ADB em `C:\ProgramData\chocolatey\bin\adb.exe`.
- Telemóvel ligado e autorizado via USB/ADB: Redmi `2510DRA23E`, Android 16 / SDK 36, ABI arm64.
- Pacote instalado: `pt.andrevazao.vazaosovereigntrader`, versão 0.4.0 (versionCode 1024400).
- Túnel ADB reverse criado e presente: `tcp:8765 -> tcp:8765`.
- API local do PC responde HTTP 200 em `http://127.0.0.1:8765/health`, modo PAPER.
- Serviço Flask temporário arrancado com bind exclusivo `127.0.0.1:8765`, `auto_start_paper=False` e `allow_real=False` na configuração em memória. O engine não foi iniciado. Bootstrap temporário removido depois do arranque.
- Como não existia token local, foi gerado um token aleatório criptograficamente seguro de 32 bytes e guardado na variável de ambiente de utilizador Windows `VST_LOCAL_TOKEN`. O valor nunca foi impresso nem revelado. `ensure_windows_token.ps1` falha neste Windows PowerShell/.NET porque `RandomNumberGenerator.Fill` não existe.
- A aplicação foi tentada iniciar via launcher e atividade explícita, mas não permanece em execução. Android `dumpsys activity exit-info` indica `APP CRASH(NATIVE)`, status 6 / SIGABRT. Logcat: `FORTIFY: pthread_mutex_lock called on a destroyed mutex`, thread `hwuiTask0`/`hwuiTask1`, stack em `libhwui.so` / `pthread_cond_wait`. Há crashes semelhantes em tentativas anteriores.
- O host responde localmente, mas o teste HTTP de ponta a ponta do Android não foi concluído: Toybox não inclui `wget` e o teste `nc` não devolveu resposta. O túnel está configurado, mas a conectividade funcional da app não está certificada.

## Segurança e limites
- Não se iniciou o engine, não se executaram ordens, não se contactaram exchanges, não se instalaram APKs nem se apagaram dados da aplicação.
- O serviço de diagnóstico permanece ativo no processo Python PID 1896, loopback apenas, para aproveitar a sessão USB. Não está registado como serviço persistente. O token fica no ambiente do utilizador Windows.
- A configuração persistente continua com `auto_start_paper=True` e `autonomous_execution.allow_real=True`; o processo temporário sobrepõe ambos em memória para desativar auto-start e REAL apenas nesta execução.
- `scripts/pair_android_usb.ps1` falha ao fazer parse em Windows PowerShell por codificação/acentos. O túnel foi configurado diretamente por ADB sem alterar o script.

## Próximos passos
1. Corrigir `ensure_windows_token.ps1` para Windows PowerShell 5/.NET Framework, sem imprimir segredos.
2. Corrigir e testar a codificação de `pair_android_usb.ps1`.
3. Diagnosticar o crash nativo Kivy/SDL/HWUI no Android 16; rever dependências/buildozer, produzir APK novo e instalar com `adb install -r` só depois de inspecionar o artefacto e preservar dados.
4. Quando a app abrir, definir URL `http://127.0.0.1:8765`, testar o token owner temporário e concluir emparelhamento seguro com aprovação explícita na consola física.
5. Confirmar HTTP de ponta a ponta por ADB reverse. Não iniciar PAPER automaticamente nem ativar REAL.
6. No fim, parar o serviço temporário se já não for necessário e remover o túnel com `adb reverse --remove tcp:8765`; preservar o token local se o owner pretender continuar a usá-lo.
