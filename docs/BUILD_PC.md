# Build do PC.EXE no Windows 10

## Preparar ambiente

```powershell
cd PC_ENGINE
python -m venv .venv
.venv\Scripts\activate
pip install -r ..\requirements-pc.txt
copy config\config.example.json config\config.local.json
```

Define um token local para o APK falar com o PC:

```powershell
setx VST_LOCAL_TOKEN "troca-este-token-local"
```

Fecha e reabre o terminal depois do `setx`.

## Testar em modo PAPER

```powershell
python main.py
```

Verifica:

```text
http://127.0.0.1:8765/status
```

O endpoint exige header `X-Token`.

## Gerar EXE

```powershell
pip install pyinstaller
pyinstaller --onefile --name VazaoSovereignTrader PC_ENGINE\main.py
```

Resultado:

```text
dist\VazaoSovereignTrader.exe
```

## Segurança

- Nunca coloques `config.local.json` no GitHub.
- Nunca coloques chaves reais no código.
- Começa sempre em PAPER.
- Recolha pública inicial: não configurar chaves nem ligar contas de exchange. Os endpoints públicos de market data não precisam de credenciais.\n- Se uma fase futura exigir acesso privado, começar apenas com permissões estritamente read-only e sem Spot Trade, Withdraw, transferências ou execução. Nunca guardar chaves no ficheiro de configuração nem no GitHub. O VST permanece PAPER-only.
