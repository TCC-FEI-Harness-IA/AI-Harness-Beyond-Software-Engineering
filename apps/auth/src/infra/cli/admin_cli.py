"""Provisionamento administrativo do serviço de autenticação.

Uso (dentro do container `auth`):

    python -m src.infra.cli.admin_cli create-admin --email admin@exemplo.com
    printf '%s\\n' "$SENHA" | python -m src.infra.cli.admin_cli create-admin --email admin@exemplo.com --password-stdin
    python -m src.infra.cli.admin_cli create-admin --email conta@exemplo.com --promote

A senha nunca é aceita como argumento (ficaria no histórico do shell e na lista de processos).
"""
import argparse
import asyncio
import getpass
import sys
from collections.abc import Callable
from typing import TextIO

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from src.domain.errors.email_already_registered_error import EmailAlreadyRegisteredError
from src.domain.errors.invalid_registration_error import InvalidRegistrationError
from src.infra.adapters.argon2_password_hasher import Argon2PasswordHasher
from src.infra.adapters.clock_adapter import ClockAdapter
from src.infra.config.settings import Settings
from src.infra.startups.auth_container import AuthContainer

_EXIT_OK = 0
_EXIT_REFUSED = 2


def build_parser() -> argparse.ArgumentParser:
    """Argumentos aceitos pela linha de comando."""
    parser = argparse.ArgumentParser(prog="admin_cli", description="Provisionamento administrativo.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-admin", help="Cria uma conta administradora ou promove uma existente.")
    create.add_argument("--email", required=True)
    create.add_argument("--promote", action="store_true", help="Promove a conta, se ela já existir.")
    create.add_argument("--password-stdin", action="store_true", help="Lê a senha da primeira linha da entrada.")
    return parser


async def run(
    argv: list[str],
    container: AuthContainer,
    stdin: TextIO = sys.stdin,
    prompt: Callable[[str], str] = getpass.getpass,
) -> int:
    """Executa o comando.

    Args:
        argv: Argumentos, sem o nome do programa.
        container: Composition root do serviço.
        stdin: Entrada usada por `--password-stdin`.
        prompt: Leitura interativa sem eco.

    Returns:
        int: 0 em caso de sucesso; 2 quando o pedido é recusado.
    """
    args = build_parser().parse_args(argv)
    await container.ensure_indexes()
    existing = await container.users.find_by_email(args.email.strip().lower())
    password: str | None = None
    if existing is None or not args.promote:
        if args.password_stdin:
            password = stdin.readline().rstrip("\n")
        else:
            password = prompt("Senha da conta administradora: ")
            if prompt("Confirme a senha: ") != password:
                print("As senhas não conferem.", file=sys.stderr)
                return _EXIT_REFUSED
    try:
        admin = await container.provision_admin.execute(email=args.email, password=password, promote=args.promote)
    except (InvalidRegistrationError, EmailAlreadyRegisteredError) as exc:
        hint = " Use --promote para promover a conta existente." if isinstance(exc, EmailAlreadyRegisteredError) else ""
        print(f"{exc}{hint}", file=sys.stderr)
        return _EXIT_REFUSED
    print(f"Conta administradora pronta: {admin.id} ({admin.email})")
    return _EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada: monta o container real a partir do ambiente."""
    load_dotenv()
    settings = Settings()
    container = AuthContainer(
        settings=settings,
        mongo_client=AsyncIOMotorClient(settings.mongodb_uri, tz_aware=True),
        clock=ClockAdapter(),
        hasher=Argon2PasswordHasher(
            time_cost=settings.argon2_time_cost,
            memory_cost_kib=settings.argon2_memory_cost_kib,
            parallelism=settings.argon2_parallelism,
        ),
    )
    return asyncio.run(run(sys.argv[1:] if argv is None else argv, container=container))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
