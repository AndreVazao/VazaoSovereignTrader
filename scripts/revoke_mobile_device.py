from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PC_ENGINE.core.mobile_pairing import MobilePairingStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Revoga um token de dispositivo móvel neste PC.")
    parser.add_argument("--data-dir", default="PC_ENGINE/data/mobile_pairing")
    args = parser.parse_args()
    store = MobilePairingStore(Path(args.data_dir))
    try:
        devices = store.list_devices()
    except (OSError, RuntimeError) as exc:
        print(f"Não foi possível ler os dispositivos: {exc}", file=sys.stderr)
        return 2
    if not devices:
        print("Não existem dispositivos registados.")
        return 0
    for index, item in enumerate(devices, start=1):
        print(f"{index}. {item.get('device_name')} | {item.get('device_id')} | {item.get('status')}")
    choice = input("Número do dispositivo a revogar (Enter cancela): ").strip()
    if not choice:
        print("Cancelado.")
        return 0
    try:
        selected = devices[int(choice) - 1]
    except (ValueError, IndexError):
        print("Seleção inválida.", file=sys.stderr)
        return 2
    if selected.get("status") == "REVOKED":
        print("O dispositivo já está revogado.")
        return 0
    if input(f"Para revogar '{selected.get('device_name')}', escreve REVOGAR: ").strip() != "REVOGAR":
        print("Cancelado.")
        return 0
    try:
        store.revoke(str(selected["device_id"]))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Revogação falhou: {exc}", file=sys.stderr)
        return 2
    print("Dispositivo revogado. O token deixa de autenticar novas chamadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
