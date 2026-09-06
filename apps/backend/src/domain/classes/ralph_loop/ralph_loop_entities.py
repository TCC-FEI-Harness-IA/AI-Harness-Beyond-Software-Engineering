from dataclasses import dataclass, field
from typing import Literal


@dataclass
class GeneralAcceptanceCriteria:
    """Resultado da Fase A.1: Critérios de aceite gerais da resposta final."""

    criteria: list[str]
    raw_response: str = ""


@dataclass
class RalphTask:
    """Resultado da Fase A.2: Tarefa de objetivo único com critérios individuais."""

    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    status: Literal["pending", "in_progress", "approved", "rejected"] = "pending"
    attempts: int = 0
    approved_result: str | None = None


@dataclass
class TaskVerificationDecision:
    """Resultado da Fase B.2: Verificação dos critérios de aceitação da tarefa."""

    approved: bool
    feedback: str
    evaluations: list[dict[str, object]] = field(default_factory=list)
    raw_response: str = ""


@dataclass
class FactualLearnings:
    """Resultado da Fase B.4: Aprendizados factuais pontuais (secas e objetivas)."""

    facts: list[str]
    raw_response: str = ""


@dataclass
class GlobalVerificationDecision:
    """Resultado da Fase C.1: Verificação global dos critérios gerais frente aos resultados."""

    approved: bool
    unmet_criteria: list[str] = field(default_factory=list)
    feedback: str = ""
    raw_response: str = ""


@dataclass
class ContextWindowInfo:
    """Metadados da janela de contexto para rastrear context rot e tokens."""

    context_id: str
    context_size: int


@dataclass
class RalphLoopStepEvent:
    """Evento emitido durante o fluxo do Ralph Loop para streaming SSE ou logging."""

    type: Literal["thinking", "result"]
    subtype: Literal[
        "setup",
        "tasks",
        "execute",
        "reasoning",
        "verify_pass",
        "verify_fail",
        "store",
        "learn",
        "reset",
        "compile",
    ]
    task: str
    content: str
    total_tokens: int
    context_window: ContextWindowInfo | None = None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "type": self.type,
            "subtype": self.subtype,
            "task": self.task,
            "content": self.content,
            "total_tokens": self.total_tokens,
        }
        if self.context_window is not None:
            data["context_window"] = {
                "context_id": self.context_window.context_id,
                "context_size": self.context_window.context_size,
            }
        return data


@dataclass
class RalphLoopExecutionSummary:
    """Resumo consolidado para chamadas síncronas de benchmark."""

    question: str
    final_answer: str
    general_criteria: list[str]
    tasks_count: int
    approved_results: dict[str, str]
    accumulated_learnings: list[str]
    total_tokens: int
    events: list[RalphLoopStepEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "final_answer": self.final_answer,
            "general_criteria": self.general_criteria,
            "tasks_count": self.tasks_count,
            "approved_results": self.approved_results,
            "accumulated_learnings": self.accumulated_learnings,
            "total_tokens": self.total_tokens,
            "events": [event.to_dict() for event in self.events],
        }
