# Build do APK Android

## Preparar ambiente

Usa Linux ou WSL no Windows.

```bash
sudo apt update
sudo apt install -y python3 python3-pip git openjdk-17-jdk zip unzip
pip install buildozer cython
```

## Compilar debug

```bash
cd MOBILE_APP
buildozer android debug
```

O APK aparece em:

```text
MOBILE_APP/bin/
```

## Release assinado

Cria uma keystore privada e guarda-a fora do GitHub.

```bash
keytool -genkey -v -keystore vazaosovereigntrader.keystore -alias vst -keyalg RSA -keysize 2048 -validity 10000
```

Depois configura assinatura localmente conforme a tua instalação do Buildozer. Nunca faças commit da keystore.

## Uso

1. Liga o PC_ENGINE no PC.
2. No APK, coloca a URL do PC, por exemplo `http://192.168.1.50:8765`.
3. Coloca o token local definido em `VST_LOCAL_TOKEN`.
4. Usa INICIAR / PAUSAR / PARAR.

O APK não guarda chaves das exchanges.
