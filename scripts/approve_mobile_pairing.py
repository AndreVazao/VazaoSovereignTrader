from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from PC_ENGINE.core.mobile_pairing import MobilePairingStore


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aprova explicitamente um dispositivo Android pendente no PC local."
    )
    parser.add_argument(
        "--data-dir",
        default="PC_ENGINE/data/mobile_pairing",
        help="Diretório local do registo de emparelhamento.",
    )
    args = parser.parse_args()
    store = MobilePairingStore(Path(args.data_dir))
    try:
        pending = store.list_pending()
    except (OSError, RuntimeError) as exc:
        print(f"Não foi possível ler os pedidos: {exc}", file=sys.stderr)
        return 2
    if not pending:
        print("Não existem pedidos de emparelhamento pendentes.")
        return 0
    print("PEDIDOS PENDENTES — confirma que reconheces o dispositivo físico.")
    for index, item in enumerate(pending, start=1):
        print(f"{index}. {item['device_name']} | ID: {item['challenge_id']} | expira: {item['expires_at']}")
    choice = input("Número do dispositivo a aprovar (Enter cancela): ").strip()
    if not choice:
        print("Cancelado.")
        return 0
    try:
        selected = pending[int(choice) - 1]
    except (ValueError, IndexError):
        print("Seleção inválida.", file=sys.stderr)
        return 2
    code = getpass.getpass("Introduz o código de confirmação apresentado no Android: ").strip()
    confirmation = input(f"Para autorizar '{selected['device_name']}', escreve APROVAR: ").strip()
    if confirmation != "APROVAR":
        print("Cancelado.")
        return 0
    try:
        result = store.approve(selected["challenge_id"], code)
    except (OSError, RuntimeError, ValueError, PermissionError) as exc:
        print(f"Pedido recusado: {exc}", file=sys.stderr)
        return 2
    print(f"Dispositivo aprovado: {result['device_name']}. Volta ao Android para concluir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
