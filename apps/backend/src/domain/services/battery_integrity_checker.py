from src.domain.entities.benchmark.benchmark_session import BenchmarkSession
from src.domain.entities.session.session import Session
from src.domain.enums.benchmark_session_status_enum import BenchmarkSessionStatusEnum
from src.domain.enums.session_status_enum import SessionStatusEnum


class BatteryIntegrityChecker:
    """Regras para uma bateria virar resultado oficial.

    Exige bateria `completed`, todas as questões com os dois desfechos e cada sessão filha presente,
    legível, ligada a esta bateria e encerrada. Respostas erradas e falhas técnicas por questão são
    resultados legítimos e são preservadas; o critério nunca é a pontuação.
    """

    def battery_problems(self, battery: BenchmarkSession) -> list[str]:
        """Problemas visíveis só pelo documento da bateria."""
        if battery.status is not BenchmarkSessionStatusEnum.COMPLETED:
            return [f"status '{battery.status.value}' (só baterias concluídas são publicadas)"]
        problems: list[str] = []
        if battery.question_count == 0:
            problems.append("bateria sem questões")
        for question in battery.questions:
            if question.simple is None or question.ralph is None:
                problems.append(f"questão '{question.question_id}' sem o desfecho dos dois fluxos")
            elif question.simple.session_id is None or question.ralph.session_id is None:
                problems.append(f"questão '{question.question_id}' sem sessão registrada")
        return problems

    def session_problems(self, battery: BenchmarkSession, session_id: str, session: Session | None) -> list[str]:
        """Problemas de uma sessão filha."""
        if session is None:
            return [f"sessão '{session_id}' ausente na origem"]
        if session.benchmark_details.run_id != battery.id:
            return [f"sessão '{session_id}' pertence a outra bateria"]
        if session.status is SessionStatusEnum.RUNNING:
            return [f"sessão '{session_id}' ainda consta como em execução"]
        return []
