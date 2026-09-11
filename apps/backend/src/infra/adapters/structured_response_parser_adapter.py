import json
import logging
import re
from typing import Any, Callable

from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.enums.verification_decision_enum import VerificationDecisionEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser

_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_OBJECT_OPENING = "{"
_OBJECT_CLOSING = "}"
_RAW_OUTPUT_MAX_LENGTH = 500
_TRUNCATION_SUFFIX = "..."
_TASK_TEXT_FIELDS = ("id", "title", "description", "expected_input", "expected_output")
_CRITERION_TEXT_FIELDS = ("id", "description")
_NOT_FOUND = -1


class StructuredResponseParserAdapter(IStructuredResponseParser):
    """Adapter de `IStructuredResponseParser` apoiado em `json.loads`.

    A extração é tolerante ao que os modelos realmente produzem: JSON puro,
    JSON dentro de cerca de código, ou JSON cercado por texto solto. Já a
    validação de schema é estrita — a fase seguinte do fluxo só recebe uma
    estrutura que sabidamente confere com o contrato daquela etapa.
    """

    def __init__(self, logger: logging.Logger) -> None:
        """Inicializa o adapter.

        Args:
            logger: Logger do módulo.
        """
        self.logger = logger

    def parse(self, raw_output: str, phase: ThinkingPhaseEnum) -> dict[str, Any]:
        """Extrai e valida o JSON produzido pelo modelo para a fase informada.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.

        Returns:
            dict[str, Any]: Estrutura JSON já validada contra o schema da fase.

        Raises:
            PhaseParsingError: Quando não há JSON válido, quando a fase não produz
                saída estruturada ou quando o schema não confere.
        """
        validator = self.__validators().get(phase)
        if validator is None:
            raise PhaseParsingError(
                phase=phase,
                raw_output=self.__truncate(raw_output=raw_output),
                reason="A fase não produz saída estruturada.",
            )

        parsed = self.__extract(raw_output=raw_output, phase=phase)
        validator(parsed, phase, raw_output)
        return parsed

    def __validators(
        self,
    ) -> dict[ThinkingPhaseEnum, Callable[[dict[str, Any], ThinkingPhaseEnum, str], None]]:
        """Mapa de fase para o validador de schema correspondente.

        Returns:
            dict: Validador de schema por fase que produz saída estruturada.
        """
        return {
            ThinkingPhaseEnum.A1_GENERAL_CRITERIA: self.__validate_general_criteria,
            ThinkingPhaseEnum.A2_TASK_DECOMPOSITION: self.__validate_tasks,
            ThinkingPhaseEnum.C2_ADDITIONAL_PLANNING: self.__validate_tasks,
            ThinkingPhaseEnum.B1_TASK_RESOLUTION: self.__validate_task_result,
            ThinkingPhaseEnum.B2_TASK_VERIFICATION: self.__validate_verification,
            ThinkingPhaseEnum.C1_GLOBAL_VERIFICATION: self.__validate_verification,
            ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: self.__validate_learnings,
            ThinkingPhaseEnum.C3_FINAL_ANSWER: self.__validate_final_answer,
        }

    def __extract(self, raw_output: str, phase: ThinkingPhaseEnum) -> dict[str, Any]:
        """Obtém o objeto JSON da saída bruta, tolerando cerca e texto solto.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.

        Returns:
            dict[str, Any]: Objeto JSON extraído.

        Raises:
            PhaseParsingError: Quando nenhuma estratégia devolve um objeto JSON.
        """
        for candidate in self.__candidates(raw_output=raw_output):
            parsed = self.__load_object(candidate=candidate)
            if parsed is not None:
                return parsed

        self.__fail(phase=phase, raw_output=raw_output, reason="Nenhum objeto JSON válido foi encontrado na saída.")

    def __candidates(self, raw_output: str) -> list[str]:
        """Lista os trechos candidatos a objeto JSON, na ordem de tentativa.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.

        Returns:
            list[str]: Saída inteira, conteúdo das cercas e recorte entre chaves.
        """
        candidates = [raw_output]
        candidates.extend(match.group(1) for match in _FENCE_PATTERN.finditer(raw_output))

        opening = raw_output.find(_OBJECT_OPENING)
        closing = raw_output.rfind(_OBJECT_CLOSING)
        if opening != _NOT_FOUND and closing > opening:
            candidates.append(raw_output[opening: closing + 1])

        return candidates

    def __load_object(self, candidate: str) -> dict[str, Any] | None:
        """Tenta interpretar um candidato como objeto JSON.

        Args:
            candidate: Trecho candidato a objeto JSON.

        Returns:
            dict[str, Any] | None: Objeto interpretado, ou `None` quando o trecho
            não é JSON válido ou não é um objeto.
        """
        try:
            parsed = json.loads(candidate)
        except ValueError:
            return None

        if not isinstance(parsed, dict):
            return None

        return parsed

    def __validate_general_criteria(
        self,
        parsed: dict[str, Any],
        phase: ThinkingPhaseEnum,
        raw_output: str,
    ) -> None:
        """Valida o schema de A.1.

        Raises:
            PhaseParsingError: Quando a lista de critérios gerais não confere.
        """
        criteria = self.__require_list(
            parsed=parsed, field="general_acceptance_criteria", phase=phase, raw_output=raw_output, allow_empty=False
        )
        for criterion in criteria:
            self.__validate_criterion(criterion=criterion, phase=phase, raw_output=raw_output)

    def __validate_tasks(self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, raw_output: str) -> None:
        """Valida o schema de A.2 e C.2.

        Raises:
            PhaseParsingError: Quando a lista de tarefas não confere.
        """
        tasks = self.__require_list(
            parsed=parsed, field="tasks", phase=phase, raw_output=raw_output, allow_empty=False
        )
        for task in tasks:
            if not isinstance(task, dict):
                self.__fail(phase=phase, raw_output=raw_output, reason="Cada item de 'tasks' deve ser um objeto.")
            for field in _TASK_TEXT_FIELDS:
                self.__require_text(source=task, field=f"tasks.{field}", value=task.get(field), phase=phase,
                                    raw_output=raw_output)
            criteria = self.__require_list(
                parsed=task, field="acceptance_criteria", phase=phase, raw_output=raw_output, allow_empty=False
            )
            for criterion in criteria:
                self.__validate_criterion(criterion=criterion, phase=phase, raw_output=raw_output)

    def __validate_task_result(self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, raw_output: str) -> None:
        """Valida o schema de B.1.

        Raises:
            PhaseParsingError: Quando 'result' não é uma string não vazia.
        """
        self.__require_text(source=parsed, field="result", value=parsed.get("result"), phase=phase,
                            raw_output=raw_output)

    def __validate_verification(self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, raw_output: str) -> None:
        """Valida o schema e a coerência semântica de B.2 e C.1.

        Raises:
            PhaseParsingError: Quando o schema não confere ou quando a decisão é
                incoerente com a lista de critérios não atendidos.
        """
        decision = parsed.get("decision")
        if decision not in tuple(VerificationDecisionEnum):
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=f"O campo 'decision' deve ser um veredito conhecido. Valor: '{decision}'.",
            )

        evaluations = self.__require_list(
            parsed=parsed, field="criteria_evaluation", phase=phase, raw_output=raw_output, allow_empty=True
        )
        for evaluation in evaluations:
            self.__validate_evaluation(evaluation=evaluation, phase=phase, raw_output=raw_output)

        unmet = self.__require_list(
            parsed=parsed, field="unmet_criteria_ids", phase=phase, raw_output=raw_output, allow_empty=True
        )
        for criterion_id in unmet:
            if not isinstance(criterion_id, str):
                self.__fail(
                    phase=phase,
                    raw_output=raw_output,
                    reason="Cada item de 'unmet_criteria_ids' deve ser uma string.",
                )

        approved = decision == VerificationDecisionEnum.APPROVED
        if approved is bool(unmet):
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=(
                    f"A decisão '{decision}' é incoerente com 'unmet_criteria_ids': "
                    "aprovar exige lista vazia e reprovar exige ao menos um critério."
                ),
            )

    def __validate_learnings(self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, raw_output: str) -> None:
        """Valida o schema de B.4, onde a lista vazia é legítima.

        Raises:
            PhaseParsingError: Quando 'learnings' não é uma lista de strings.
        """
        learnings = self.__require_list(
            parsed=parsed, field="learnings", phase=phase, raw_output=raw_output, allow_empty=True
        )
        for learning in learnings:
            if not isinstance(learning, str):
                self.__fail(
                    phase=phase,
                    raw_output=raw_output,
                    reason="Cada item de 'learnings' deve ser uma string.",
                )

    def __validate_final_answer(self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, raw_output: str) -> None:
        """Valida o schema de C.3.

        Raises:
            PhaseParsingError: Quando 'final_answer' não é uma string não vazia.
        """
        self.__require_text(source=parsed, field="final_answer", value=parsed.get("final_answer"), phase=phase,
                            raw_output=raw_output)

    def __validate_criterion(self, criterion: Any, phase: ThinkingPhaseEnum, raw_output: str) -> None:
        """Valida um critério de aceite individual.

        Raises:
            PhaseParsingError: Quando o critério não traz 'id' e 'description' preenchidos.
        """
        if not isinstance(criterion, dict):
            self.__fail(phase=phase, raw_output=raw_output, reason="Cada critério de aceite deve ser um objeto.")
        for field in _CRITERION_TEXT_FIELDS:
            self.__require_text(source=criterion, field=f"criterio.{field}", value=criterion.get(field), phase=phase,
                                raw_output=raw_output)

    def __validate_evaluation(self, evaluation: Any, phase: ThinkingPhaseEnum, raw_output: str) -> None:
        """Valida o veredito de um critério dentro de uma verificação.

        Raises:
            PhaseParsingError: Quando o veredito não traz os campos esperados.
        """
        if not isinstance(evaluation, dict):
            self.__fail(
                phase=phase, raw_output=raw_output, reason="Cada item de 'criteria_evaluation' deve ser um objeto."
            )
        self.__require_text(source=evaluation, field="criterion_id", value=evaluation.get("criterion_id"), phase=phase,
                            raw_output=raw_output)
        self.__require_text(source=evaluation, field="justification", value=evaluation.get("justification"),
                            phase=phase, raw_output=raw_output)
        if not isinstance(evaluation.get("met"), bool):
            self.__fail(phase=phase, raw_output=raw_output, reason="O campo 'met' deve ser booleano.")

    def __require_list(
        self,
        parsed: dict[str, Any],
        field: str,
        phase: ThinkingPhaseEnum,
        raw_output: str,
        allow_empty: bool,
    ) -> list[Any]:
        """Exige que um campo seja uma lista, opcionalmente não vazia.

        Returns:
            list[Any]: Lista encontrada no campo.

        Raises:
            PhaseParsingError: Quando o campo não é lista ou está indevidamente vazio.
        """
        value = parsed.get(field)
        if not isinstance(value, list):
            self.__fail(phase=phase, raw_output=raw_output, reason=f"O campo '{field}' deve ser uma lista.")
        if not allow_empty and not value:
            self.__fail(phase=phase, raw_output=raw_output, reason=f"O campo '{field}' não pode ser uma lista vazia.")
        return value

    def __require_text(
        self,
        source: dict[str, Any],
        field: str,
        value: Any,
        phase: ThinkingPhaseEnum,
        raw_output: str,
    ) -> None:
        """Exige que um campo seja uma string com conteúdo.

        Raises:
            PhaseParsingError: Quando o campo não é string ou está em branco.
        """
        if not isinstance(value, str) or not value.strip():
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=f"O campo '{field}' deve ser uma string não vazia.",
            )

    def __fail(self, phase: ThinkingPhaseEnum, raw_output: str, reason: str) -> None:
        """Registra e levanta a falha de parsing da fase.

        Raises:
            PhaseParsingError: Sempre.
        """
        self.logger.warning("Saída da fase '%s' recusada pelo parser: %s", phase.value, reason)
        raise PhaseParsingError(phase=phase, raw_output=self.__truncate(raw_output=raw_output), reason=reason)

    def __truncate(self, raw_output: str) -> str:
        """Trunca a saída bruta para caber no erro sem inundar o log.

        Returns:
            str: Saída bruta, truncada quando excede o tamanho máximo.
        """
        if len(raw_output) <= _RAW_OUTPUT_MAX_LENGTH:
            return raw_output
        return f"{raw_output[:_RAW_OUTPUT_MAX_LENGTH]}{_TRUNCATION_SUFFIX}"
