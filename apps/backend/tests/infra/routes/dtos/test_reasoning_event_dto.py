from src.infra.routes.v1.message.dtos.context_window_dto import ContextWindowDTO
from src.infra.routes.v1.message.dtos.reasoning_event_dto import ReasoningEventDTO


def test_carrega_todos_os_campos_do_contrato() -> None:
    dto = ReasoningEventDTO(
        type="thinking",
        subtype="execute",
        phase="B1",
        task="T1",
        session_id="sess_01J",
        content="markdown renderizavel",
        total_tokens=642,
        context_window=ContextWindowDTO(context_id="3a7f2b1", context_size=182),
        inference_time_ms=812,
    )

    assert dto.type == "thinking"
    assert dto.subtype == "execute"
    assert dto.phase == "B1"
    assert dto.task == "T1"
    assert dto.session_id == "sess_01J"
    assert dto.content == "markdown renderizavel"
    assert dto.total_tokens == 642
    assert dto.context_window.context_id == "3a7f2b1"
    assert dto.context_window.context_size == 182
    assert dto.inference_time_ms == 812
