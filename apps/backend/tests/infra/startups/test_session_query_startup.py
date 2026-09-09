from src.application.usecases.get_session_usecase import GetSessionUseCase
from src.infra.startups.session_query_startup import SessionQueryStartup


def test_constroi_todo_o_grafo_sem_deixar_atributo_nulo() -> None:
    startup = SessionQueryStartup()

    assert vars(startup)
    assert all(valor is not None for valor in vars(startup).values())


def test_injeta_o_repositorio_no_caso_de_uso() -> None:
    startup = SessionQueryStartup()

    assert isinstance(startup.get_session_use_case, GetSessionUseCase)
    assert startup.get_session_use_case.repository is startup.session_repository
