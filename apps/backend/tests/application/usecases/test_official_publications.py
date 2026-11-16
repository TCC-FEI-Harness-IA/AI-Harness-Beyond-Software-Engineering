"""Seleção, publicação inicial, idempotência, substituição e imutabilidade dos resultados oficiais."""
import copy
import logging
from dataclasses import replace
from datetime import timedelta
from itertools import count

import pytest

from src.application.usecases.publish_official_results_usecase import PublishOfficialResultsUseCase
from src.application.usecases.select_official_batteries_usecase import SelectOfficialBatteriesUseCase
from src.domain.entities.publication.source_battery import SourceBattery
from src.domain.entities.session.benchmark_details import BenchmarkDetails
from src.domain.enums.benchmark_dataset_enum import BenchmarkDatasetEnum
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.enums.publication_status_enum import PublicationStatusEnum
from src.domain.errors.official_battery_not_eligible_error import OfficialBatteryNotEligibleError
from tests.doubles.benchmark_factories import desfecho
from tests.doubles.controllable_clock import ControllableClock
from tests.doubles.publication_doubles import (
    FakePublicationBackup,
    InMemoryBenchmarkSource,
    InMemoryOfficialPublicationRepository,
    bateria_concluida,
)

V, M, G = BenchmarkDatasetEnum.VESTIBULAR, BenchmarkDatasetEnum.MMLU, BenchmarkDatasetEnum.GPQA


def _selecao(origem: InMemoryBenchmarkSource) -> SelectOfficialBatteriesUseCase:
    return SelectOfficialBatteriesUseCase(source=origem, logger=logging.getLogger("teste"))


def _publicacao(repositorio, backup, clock) -> PublishOfficialResultsUseCase:
    contador = count(1)
    return PublishOfficialResultsUseCase(
        repository=repositorio, backup=backup, clock=clock,
        id_generator=lambda: f"pub_{next(contador)}", logger=logging.getLogger("teste"),
    )


@pytest.fixture
def origem() -> InMemoryBenchmarkSource:
    origem = InMemoryBenchmarkSource()
    for battery_id, dataset, horas in [
        ("bench_v_antiga", V, 0), ("bench_v_nova", V, 10), ("bench_m", M, 5), ("bench_g", G, 7),
    ]:
        origem.add(*bateria_concluida(battery_id, dataset, horas=horas))
    return origem


# ── Seleção ──────────────────────────────────────────────────────────────────


async def test_seleciona_a_bateria_concluida_mais_recente_por_dataset(origem: InMemoryBenchmarkSource) -> None:
    relatorio = await _selecao(origem).execute()

    escolhidas = {item.dataset: item.selected.battery.id for item in relatorio.selections}
    assert escolhidas == {V: "bench_v_nova", M: "bench_m", G: "bench_g"}
    assert all(item.discarded == [] for item in relatorio.selections)
    assert relatorio.source_description == "origem em memória"
    vestibular = relatorio.selection(V).selected
    assert {sessao.id for sessao in vestibular.sessions} == set(vestibular.battery.session_ids)


async def test_nao_seleciona_pela_maior_pontuacao_e_preserva_erros_e_falhas() -> None:
    origem = InMemoryBenchmarkSource()
    origem.add(*bateria_concluida("bench_melhor", V, horas=0))
    origem.add(*bateria_concluida("bench_recente_com_falha", V, horas=1, falha_tecnica=True))

    selecionada = (await _selecao(origem).execute()).selection(V).selected

    assert selecionada.battery.id == "bench_recente_com_falha"
    assert selecionada.battery.summary(BenchmarkInferenceModeEnum.RALPH).failures >= 1


async def test_criacao_e_o_criterio_e_nao_a_ultima_alteracao() -> None:
    origem = InMemoryBenchmarkSource()
    antiga, sessoes_antigas = bateria_concluida("bench_antiga_editada", V, horas=0)
    antiga.updated_at = antiga.created_at + timedelta(days=30)
    origem.add(antiga, sessoes_antigas)
    origem.add(*bateria_concluida("bench_nova", V, horas=1))

    assert (await _selecao(origem).execute()).selection(V).selected.battery.id == "bench_nova"


async def test_empate_de_criacao_e_resolvido_pelo_identificador() -> None:
    origem = InMemoryBenchmarkSource()
    origem.add(*bateria_concluida("bench_b", V, horas=1))
    origem.add(*bateria_concluida("bench_a", V, horas=1))

    assert (await _selecao(origem).execute()).selection(V).selected.battery.id == "bench_a"


async def test_baterias_recentes_incompletas_ou_inconsistentes_sao_descartadas_com_motivo() -> None:
    origem = InMemoryBenchmarkSource()
    origem.add(*bateria_concluida("bench_valida", M, horas=0))
    interrompida, sessoes = bateria_concluida("bench_interrompida", M, horas=1)
    interrompida.status = BenchmarkSessionStatusEnum.INTERRUPTED
    origem.add(interrompida, sessoes)
    sem_sessao, sessoes = bateria_concluida("bench_sem_sessao", M, horas=2)
    origem.add(sem_sessao, sessoes[1:])
    outra_bateria, sessoes = bateria_concluida("bench_sessao_de_outra", M, horas=3)
    origem.add(outra_bateria, [])
    for sessao in sessoes:
        origem.sessions[sessao.id] = replace(
            sessao, benchmark_details=BenchmarkDetails(is_banchmark=True, run_id="bench_x")
        )
    ilegivel, sessoes = bateria_concluida("bench_sessao_ilegivel", M, horas=4)
    origem.add(ilegivel, sessoes)
    origem.sessions[sessoes[0].id] = ValueError("JSON inválido")
    incompleta, sessoes = bateria_concluida("bench_sem_desfecho", M, horas=5)
    incompleta.questions[0].ralph = None
    origem.add(incompleta, sessoes)
    rodando, sessoes = bateria_concluida("bench_sessao_rodando", M, horas=6)
    origem.add(rodando, sessoes)
    origem.sessions[sessoes[0].id].status = sessoes[0].status.__class__.RUNNING

    selecao = (await _selecao(origem).execute()).selection(M)

    assert selecao.selected.battery.id == "bench_valida"
    motivos = {item.battery_id: " ".join(item.reasons) for item in selecao.discarded}
    assert list(motivos) == [
        "bench_sessao_rodando", "bench_sem_desfecho", "bench_sessao_ilegivel", "bench_sessao_de_outra",
        "bench_sem_sessao", "bench_interrompida",
    ]
    assert "interrupted" in motivos["bench_interrompida"]
    assert "ausente" in motivos["bench_sem_sessao"]
    assert "outra bateria" in motivos["bench_sessao_de_outra"]
    assert "ilegível" in motivos["bench_sessao_ilegivel"]
    assert "desfecho" in motivos["bench_sem_desfecho"]
    assert "em execução" in motivos["bench_sessao_rodando"]


async def test_dataset_sem_bateria_valida_e_informado_como_ausente() -> None:
    origem = InMemoryBenchmarkSource()
    origem.add(*bateria_concluida("bench_v", V))
    origem.batteries.append(SourceBattery(battery_id="bench_quebrada", error="documento inválido"))

    relatorio = await _selecao(origem).execute()

    assert relatorio.selection(M).selected is None
    assert relatorio.selection(G).selected is None
    assert [item.battery_id for item in relatorio.unreadable] == ["bench_quebrada"]


async def test_inspecao_de_uma_bateria_especifica() -> None:
    origem = InMemoryBenchmarkSource()
    origem.add(*bateria_concluida("bench_v", V))
    interrompida, sessoes = bateria_concluida("bench_i", V, horas=1)
    interrompida.status = BenchmarkSessionStatusEnum.INTERRUPTED
    origem.add(interrompida, sessoes)

    assert (await _selecao(origem).inspect("bench_v")).battery.id == "bench_v"
    with pytest.raises(OfficialBatteryNotEligibleError, match="interrupted"):
        await _selecao(origem).inspect("bench_i")
    with pytest.raises(OfficialBatteryNotEligibleError, match="não encontrada"):
        await _selecao(origem).inspect("bench_inexistente")


# ── Publicação inicial ───────────────────────────────────────────────────────


async def test_inspecao_sem_aplicar_nao_escreve(origem: InMemoryBenchmarkSource) -> None:
    repositorio, backup = InMemoryOfficialPublicationRepository(), FakePublicationBackup()
    relatorio = await _selecao(origem).execute()

    resultado = await _publicacao(repositorio, backup, ControllableClock()).publish_initial(
        report=relatorio, published_by="admin", apply=False
    )

    assert [(item.dataset, item.action) for item in resultado] == [(V, "publish"), (M, "publish"), (G, "publish")]
    assert repositorio.writes == 0
    assert backup.labels == []


async def test_publica_copias_das_tres_e_faz_backup_antes(origem: InMemoryBenchmarkSource) -> None:
    repositorio, backup = InMemoryOfficialPublicationRepository(), FakePublicationBackup()
    clock = ControllableClock()
    relatorio = await _selecao(origem).execute()

    resultado = await _publicacao(repositorio, backup, clock).publish_initial(
        report=relatorio, published_by="admin@cli", apply=True
    )

    assert backup.labels == ["publish-initial"]
    assert {item.publication_id for item in resultado} == {"pub_1", "pub_2", "pub_3"}
    publicacao = repositorio.publications["pub_1"]
    assert publicacao.dataset is V
    assert publicacao.status is PublicationStatusEnum.ACTIVE
    assert publicacao.published_at == clock.now()
    assert publicacao.published_by == "admin@cli"
    assert publicacao.source_benchmark_session_id == "bench_v_nova"
    assert len(await repositorio.list_sessions("pub_1")) == len(publicacao.session_ids) == 4
    original = relatorio.selection(V).selected.battery
    assert publicacao.benchmark_session is not original
    assert publicacao.benchmark_session.benchmark == original.benchmark


async def test_publicacao_inicial_e_idempotente(origem: InMemoryBenchmarkSource) -> None:
    repositorio, backup = InMemoryOfficialPublicationRepository(), FakePublicationBackup()
    caso = _publicacao(repositorio, backup, ControllableClock())
    await caso.publish_initial(report=await _selecao(origem).execute(), published_by="admin", apply=True)
    escritas = repositorio.writes

    segunda = await caso.publish_initial(report=await _selecao(origem).execute(), published_by="admin", apply=True)

    assert {item.action for item in segunda} == {"already_published"}
    assert repositorio.writes == escritas
    assert backup.labels == ["publish-initial"]


async def test_carga_inicial_nunca_substitui_publicacao_existente(origem: InMemoryBenchmarkSource) -> None:
    repositorio = InMemoryOfficialPublicationRepository()
    caso = _publicacao(repositorio, FakePublicationBackup(), ControllableClock())
    await caso.publish_initial(report=await _selecao(origem).execute(), published_by="admin", apply=True)
    origem.add(*bateria_concluida("bench_v_mais_nova", V, horas=20))

    resultado = await caso.publish_initial(report=await _selecao(origem).execute(), published_by="admin", apply=True)

    acoes = {item.dataset: item.action for item in resultado}
    assert acoes[V] == "kept_existing"
    ativas = [item for item in repositorio.publications.values() if item.status is PublicationStatusEnum.ACTIVE]
    assert {item.source_benchmark_session_id for item in ativas} == {"bench_v_nova", "bench_m", "bench_g"}


async def test_dataset_ausente_nao_gera_publicacao_ficticia() -> None:
    origem = InMemoryBenchmarkSource()
    origem.add(*bateria_concluida("bench_v", V))
    repositorio = InMemoryOfficialPublicationRepository()

    resultado = await _publicacao(repositorio, FakePublicationBackup(), ControllableClock()).publish_initial(
        report=await _selecao(origem).execute(), published_by="admin", apply=True
    )

    assert {item.dataset: item.action for item in resultado} == {V: "publish", M: "absent", G: "absent"}
    assert len(repositorio.publications) == 1


# ── Imutabilidade e substituição ─────────────────────────────────────────────


async def test_alteracao_privada_posterior_nao_muda_a_publicacao(origem: InMemoryBenchmarkSource) -> None:
    repositorio = InMemoryOfficialPublicationRepository()
    relatorio = await _selecao(origem).execute()
    await _publicacao(repositorio, FakePublicationBackup(), ControllableClock()).publish_initial(
        report=relatorio, published_by="admin", apply=True
    )
    publicada = copy.deepcopy(repositorio.publications["pub_1"].benchmark_session)
    privada = relatorio.selection(V).selected.battery

    privada.set_alias("renomeada", at=privada.updated_at)
    privada.start_rerun(question_id="Q2", mode=BenchmarkInferenceModeEnum.RALPH, at=privada.updated_at)
    privada.record_rerun_outcome(
        question_id="Q2", outcome=desfecho(mode=BenchmarkInferenceModeEnum.RALPH, correto=True, session_id="sess_novo"),
        at=privada.updated_at,
    )
    relatorio.selection(V).selected.sessions[0].final_answer = "alterada"

    assert repositorio.publications["pub_1"].benchmark_session == publicada
    assert (await repositorio.list_sessions("pub_1"))[0].final_answer != "alterada"


async def test_substituicao_explicita_preserva_a_anterior(origem: InMemoryBenchmarkSource) -> None:
    repositorio, backup = InMemoryOfficialPublicationRepository(), FakePublicationBackup()
    clock = ControllableClock()
    caso = _publicacao(repositorio, backup, clock)
    await caso.publish_initial(report=await _selecao(origem).execute(), published_by="admin", apply=True)
    anterior = repositorio.publications["pub_1"]
    origem.add(*bateria_concluida("bench_v_substituta", V, horas=30))
    clock.advance(days=1)

    resultado = await caso.replace(
        selected=await _selecao(origem).inspect("bench_v_substituta"), published_by="admin", apply=True
    )

    nova = repositorio.publications[resultado.publication_id]
    antiga = repositorio.publications["pub_1"]
    assert nova.status is PublicationStatusEnum.ACTIVE and nova.supersedes == "pub_1"
    assert antiga.status is PublicationStatusEnum.SUPERSEDED
    assert antiga.superseded_by == nova.id and antiga.superseded_at == clock.now()
    assert antiga.published_at == anterior.published_at and antiga.id == anterior.id
    assert backup.labels[-1] == "replace-vestibular"


async def test_substituicao_sem_aplicar_nao_escreve(origem: InMemoryBenchmarkSource) -> None:
    repositorio = InMemoryOfficialPublicationRepository()
    caso = _publicacao(repositorio, FakePublicationBackup(), ControllableClock())

    resultado = await caso.replace(selected=await _selecao(origem).inspect("bench_g"), published_by="a", apply=False)

    assert resultado.action == "publish"
    assert repositorio.writes == 0


async def test_substituir_pela_mesma_bateria_nao_faz_nada(origem: InMemoryBenchmarkSource) -> None:
    repositorio = InMemoryOfficialPublicationRepository()
    caso = _publicacao(repositorio, FakePublicationBackup(), ControllableClock())
    await caso.publish_initial(report=await _selecao(origem).execute(), published_by="admin", apply=True)
    escritas = repositorio.writes

    resultado = await caso.replace(selected=await _selecao(origem).inspect("bench_m"), published_by="a", apply=True)

    assert resultado.action == "already_published"
    assert repositorio.writes == escritas


async def test_bateria_sem_questoes_ou_sem_sessao_registrada_e_descartada() -> None:
    origem = InMemoryBenchmarkSource()
    vazia, _ = bateria_concluida("bench_vazia", V, horas=2, questoes=())
    origem.add(vazia, [])
    sem_sessao, sessoes = bateria_concluida("bench_sem_registro", V, horas=1)
    sem_sessao.questions[0].simple = replace(sem_sessao.questions[0].simple, session_id=None)
    origem.add(sem_sessao, sessoes)

    selecao = (await _selecao(origem).execute()).selection(V)

    assert selecao.selected is None
    motivos = {item.battery_id: " ".join(item.reasons) for item in selecao.discarded}
    assert "sem questões" in motivos["bench_vazia"]
    assert "sem sessão registrada" in motivos["bench_sem_registro"]


async def test_substituicao_sem_publicacao_vigente_publica_a_primeira() -> None:
    origem = InMemoryBenchmarkSource()
    origem.add(*bateria_concluida("bench_g", G))
    repositorio = InMemoryOfficialPublicationRepository()

    resultado = await _publicacao(repositorio, FakePublicationBackup(), ControllableClock()).replace(
        selected=await _selecao(origem).inspect("bench_g"), published_by="admin", apply=True
    )

    assert resultado.action == "publish" and resultado.previous_publication_id is None
    assert repositorio.publications[resultado.publication_id].supersedes is None


async def test_consulta_publica_recusa_sessao_listada_mas_ausente_na_copia() -> None:
    from src.application.usecases.get_official_publication_usecase import GetOfficialPublicationUseCase
    from src.domain.errors.official_publication_not_found_error import OfficialPublicationNotFoundError

    origem = InMemoryBenchmarkSource()
    origem.add(*bateria_concluida("bench_v", V))
    repositorio = InMemoryOfficialPublicationRepository()
    await _publicacao(repositorio, FakePublicationBackup(), ControllableClock()).publish_initial(
        report=await _selecao(origem).execute(), published_by="admin", apply=True
    )
    publicacao = repositorio.publications["pub_1"]
    repositorio.sessions.pop(("pub_1", publicacao.session_ids[0]))

    with pytest.raises(OfficialPublicationNotFoundError):
        await GetOfficialPublicationUseCase(repositorio).get_session("pub_1", publicacao.session_ids[0])
