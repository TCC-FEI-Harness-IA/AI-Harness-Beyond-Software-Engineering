"""Construtores de sessões persistidas usados pelos testes da exportação de benchmark."""
from datetime import UTC, datetime

from src.domain.entities.session.benchmark_details import BenchmarkDetails
from src.domain.entities.session.session import Session
from src.domain.entities.session.session_message import SessionMessage
from src.domain.enums.benchmark_inference_mode_enum import BenchmarkInferenceModeEnum
from src.domain.enums.message_source_enum import MessageSourceEnum
from src.domain.enums.model_provider_enum import ModelProviderEnum
from src.domain.enums.session_status_enum import SessionStatusEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum

_INSTANTE = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


def sessao_ralph(identificador: str = "sess_1", questao: str = "Q1") -> Session:
    """Sessão concluída do Ralph Loop, com uma mensagem e a resposta final do benchmark."""
    sessao = Session(
        id=identificador,
        user_question="Pergunta com acentuação",
        flow=ThinkingPhaseEnum.C3_FINAL_ANSWER,
        model_name="vendor/modelo",
        max_tokens=4096,
        temperature=0.0,
        status=SessionStatusEnum.RUNNING,
        created_at=_INSTANTE,
        updated_at=_INSTANTE,
        provider=ModelProviderEnum.OPEN_ROUTER,
        benchmark_details=BenchmarkDetails(
            is_banchmark=True,
            question_name=questao,
            corret_answer="A) um",
            providade_answer="RESPOSTA_FINAL: B",
            inference_mode=BenchmarkInferenceModeEnum.RALPH,
            run_id="bench_1",
            expected_alternative="A",
            selected_alternative="B",
            is_correct=False,
            duration_seconds=1.5,
            error=None,
        ),
    )
    sessao.add_message(
        SessionMessage(
            id="msg-0",
            order=0,
            timestamp=_INSTANTE,
            phase=ThinkingPhaseEnum.A1_GENERAL_CRITERIA,
            source=MessageSourceEnum.USER,
            content="Pergunta com acentuação",
            task_id=None,
            context_id=None,
            tokens_input=0,
            tokens_output=0,
            inference_time_ms=0,
            model_name=None,
        )
    )
    sessao.finish(status=SessionStatusEnum.COMPLETED, final_answer="RESPOSTA_FINAL: B")
    return sessao
