from dataclasses import dataclass, field

from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.entities.benchmark.benchmark_question_run import BenchmarkQuestionRun
from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.entities.session.session import Session


@dataclass(frozen=True)
class BenchmarkSessionBundleItem:
    """Uma questão da bateria com tudo que está atrelado a ela.

    Attributes:
        run: Execução da questão registrada na bateria (desfechos dos dois fluxos).
        question: Questão original do dataset (enunciado e alternativas), ou `None` quando o
            dataset atual não a conhece mais.
        simple_session: Sessão persistida pela inferência simples, quando existe.
        ralph_session: Sessão persistida pelo Ralph Loop, quando existe.
    """

    run: BenchmarkQuestionRun
    question: BenchmarkQuestion | None = None
    simple_session: Session | None = None
    ralph_session: Session | None = None

    @property
    def sessions(self) -> list[Session]:
        """Sessões presentes, na ordem de execução (simples e depois Ralph)."""
        return [session for session in (self.simple_session, self.ralph_session) if session is not None]


@dataclass(frozen=True)
class BenchmarkSessionBundle:
    """Bateria de benchmark completa: o documento da bateria e o conteúdo de cada questão.

    É a unidade exportada e importada como ZIP.

    Attributes:
        benchmark_session: Bateria, com configuração, desfechos e totais.
        items: Uma entrada por questão, na ordem da bateria.
    """

    benchmark_session: BenchmarkSession
    items: list[BenchmarkSessionBundleItem] = field(default_factory=list)

    @property
    def sessions(self) -> list[Session]:
        """Todas as sessões presentes no pacote, na ordem da bateria."""
        return [session for item in self.items for session in item.sessions]
