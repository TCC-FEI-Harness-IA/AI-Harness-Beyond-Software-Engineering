from dataclasses import dataclass

from src.domain.entities.benchmark.benchmark_flow_outcome import BenchmarkFlowOutcome
from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.entities.session.session import Session


@dataclass(frozen=True)
class BenchmarkRalphError:
    """Questão errada no Ralph Loop, reunida com tudo que se sabe para analisá-la depois.

    Attributes:
        question_id: Identificador da questão na bateria.
        expected_alternative: Letra do gabarito registrada na bateria.
        outcome: Desfecho incorreto do Ralph Loop.
        question: Questão do dataset atual, ou `None` quando ela não existe mais nele.
        session: Sessão persistida pelo Ralph Loop, ou `None` quando não foi criada ou não existe mais.
    """

    question_id: str
    expected_alternative: str
    outcome: BenchmarkFlowOutcome
    question: BenchmarkQuestion | None
    session: Session | None
