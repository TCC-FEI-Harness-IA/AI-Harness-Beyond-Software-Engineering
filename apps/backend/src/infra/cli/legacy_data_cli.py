"""Atribui o histórico anterior às contas (dados sem dono) a uma conta específica.

    python -m src.infra.cli.legacy_data_cli assign --owner usr_...            # só informa
    python -m src.infra.cli.legacy_data_cli assign --owner usr_... --apply    # copia

A origem não é alterada; dados sem dono nunca ficam públicos nem são atribuídos automaticamente.
"""
import argparse
import asyncio
import sys

from dotenv import load_dotenv

from src.infra.config.settings import Settings
from src.infra.services.legacy_data_assigner import LegacyDataAssigner

_EXIT_OK = 0
_EXIT_REFUSED = 2


def build_parser() -> argparse.ArgumentParser:
    """Argumentos aceitos."""
    parser = argparse.ArgumentParser(prog="legacy_data_cli")
    commands = parser.add_subparsers(dest="command", required=True)
    assign = commands.add_parser("assign", help="Copia o histórico legado para a conta indicada.")
    assign.add_argument("--owner", required=True, help="Identificador da conta (usr_...).")
    assign.add_argument("--apply", action="store_true", help="Copia de fato.")
    return parser


async def run(argv: list[str]) -> int:
    """Executa o comando e devolve o código de saída."""
    args = build_parser().parse_args(argv)
    try:
        assigner = LegacyDataAssigner(settings=Settings(), owner_id=args.owner)
    except ValueError as exc:
        print(str(exc).replace("Proprietário", "Proprietário inválido:"), file=sys.stderr)
        return _EXIT_REFUSED
    report = await assigner.run(apply=args.apply)
    print(f"Histórico legado: {report.batteries} baterias e {report.sessions} sessões sem dono.")
    if not args.apply:
        print("inspeção: nada foi gravado (use --apply para copiar para a conta).")
    else:
        print(f"Conta {args.owner}: {report.copied} copiadas (as já existentes foram mantidas).")
    return _EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada."""
    load_dotenv()
    return asyncio.run(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
