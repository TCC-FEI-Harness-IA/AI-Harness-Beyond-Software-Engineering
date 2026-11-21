"""Operações administrativas dos resultados oficiais de benchmark.

Rode dentro do container do backend, que enxerga o armazenamento efetivo (volume `backend_data`
ou o MongoDB do compose):

    python -m src.infra.cli.official_publications_cli discover
    python -m src.infra.cli.official_publications_cli inspect --source legacy
    python -m src.infra.cli.official_publications_cli publish-initial --source legacy --published-by "admin" --apply
    python -m src.infra.cli.official_publications_cli replace --source legacy \\
        --benchmark-session-id bench_... --published-by "admin" --apply
    python -m src.infra.cli.official_publications_cli list

Sem `--apply`, `publish-initial` e `replace` só mostram o que fariam (nada é gravado).
"""
import argparse
import asyncio
import sys
from collections.abc import Callable

from dotenv import load_dotenv

from src.domain.entities.publication.battery_selection import SelectedBattery, SelectionReport
from src.domain.entities.publication.publication_outcome import PublicationOutcome
from src.domain.errors.official_battery_not_eligible_error import OfficialBatteryNotEligibleError
from src.infra.startups.official_publication_admin_startup import OfficialPublicationAdminStartup

_EXIT_OK = 0
_EXIT_REFUSED = 2


def build_parser() -> argparse.ArgumentParser:
    """Argumentos aceitos."""
    parser = argparse.ArgumentParser(prog="official_publications_cli", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("discover", help="Mostra o armazenamento efetivo e o que há nele.")
    commands.add_parser("list", help="Lista as publicações oficiais, inclusive as substituídas.")
    for name in ("inspect", "publish-initial", "replace"):
        command = commands.add_parser(name)
        command.add_argument("--source", required=True, help="'legacy' ou 'owner:<user_id>'.")
        command.add_argument("--backup-dir", default=None)
        if name != "inspect":
            command.add_argument("--published-by", required=True)
            command.add_argument("--apply", action="store_true", help="Grava de fato (backup antes).")
        if name == "replace":
            command.add_argument("--benchmark-session-id", required=True)
    return parser


async def run(
    argv: list[str], startup_factory: Callable[..., OfficialPublicationAdminStartup] = OfficialPublicationAdminStartup
) -> int:
    """Executa o comando e devolve o código de saída."""
    args = build_parser().parse_args(argv)
    try:
        startup = startup_factory(
            source_spec=getattr(args, "source", None), backup_dir=getattr(args, "backup_dir", None)
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return _EXIT_REFUSED
    if args.command == "discover":
        print("\n".join(await startup.discover()))
        return _EXIT_OK
    if args.command == "list":
        for item in await startup.list_publications():
            print(
                f"{item.id} | {item.dataset.value} | {item.status.value} | "
                f"bateria {item.source_benchmark_session_id} | "
                f"publicada em {item.published_at.isoformat()} | substitui {item.supersedes or '-'} | "
                f"substituída por {item.superseded_by or '-'}"
            )
        return _EXIT_OK
    assert startup.select_use_case is not None
    if args.command == "replace":
        return await _replace(startup, args)
    report = await startup.select_use_case.execute()
    print("\n".join(_describe_report(report)))
    if args.command == "publish-initial":
        outcomes = await startup.publish_use_case.publish_initial(
            report=report, published_by=args.published_by, apply=args.apply
        )
        print("\n".join(_describe_outcomes(outcomes, applied=args.apply)))
    return _EXIT_OK


async def _replace(startup: OfficialPublicationAdminStartup, args: argparse.Namespace) -> int:
    assert startup.select_use_case is not None
    try:
        selected = await startup.select_use_case.inspect(args.benchmark_session_id)
    except OfficialBatteryNotEligibleError as exc:
        print(f"Bateria recusada: {exc}", file=sys.stderr)
        return _EXIT_REFUSED
    print("\n".join(_describe_battery(selected)))
    outcome = await startup.publish_use_case.replace(
        selected=selected, published_by=args.published_by, apply=args.apply
    )
    print("\n".join(_describe_outcomes([outcome], applied=args.apply)))
    return _EXIT_OK


def _describe_report(report: SelectionReport) -> list[str]:
    lines = [f"Origem: {report.source_description}"]
    for selection in report.selections:
        if selection.selected is None:
            lines.append(f"{selection.dataset.value}: AUSENTE (nenhuma bateria concluída e íntegra)")
        else:
            lines.extend(_describe_battery(selection.selected))
        for discarded in selection.discarded:
            created = discarded.created_at.isoformat() if discarded.created_at else "?"
            lines.append(f"  descartada {discarded.battery_id} (criada em {created}): {'; '.join(discarded.reasons)}")
    for unreadable in report.unreadable:
        lines.append(f"ilegível {unreadable.battery_id}: {'; '.join(unreadable.reasons)}")
    return lines


def _describe_battery(selected: SelectedBattery) -> list[str]:
    battery = selected.battery
    definition = battery.benchmark
    versions = sorted({
        str(int(session.flow_version)) for session in selected.sessions if session.flow_version is not None
    })
    return [
        f"{definition.dataset.value}: {battery.id}",
        f"  criada em {battery.created_at.isoformat()} | modelo {battery.llm_config.model_name} "
        f"({battery.llm_config.provider.value}) | {battery.question_count} questões | {len(selected.sessions)} sessões",
        f"  variante/split {definition.split} | protocolo {definition.protocol} | few-shot {definition.few_shot} | "
        f"revisão {definition.revision} | seed {definition.sample_seed} | disciplinas {len(definition.subjects)} | "
        f"versões do fluxo Ralph {', '.join(versions) or '-'} | alias {battery.alias or '-'}",
    ]


def _describe_outcomes(outcomes: list[PublicationOutcome], applied: bool) -> list[str]:
    lines = [
        f"{item.dataset.value}: {item.action} | bateria {item.battery_id or '-'} | "
        f"publicação {item.publication_id or '-'}"
        f" | anterior {item.previous_publication_id or '-'} | backup {item.backup_path or '-'}"
        for item in outcomes
    ]
    if not applied:
        lines.append("inspeção: nada foi gravado (use --apply para publicar).")
    return lines


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada."""
    load_dotenv()
    return asyncio.run(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
