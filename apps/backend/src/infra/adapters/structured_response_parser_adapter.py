import json
import logging
import re
from typing import Any, Callable

from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.thinking_phase_enum import ThinkingPhaseEnum
from src.domain.enums.verification_decision_enum import VerificationDecisionEnum
from src.domain.errors.phase_parsing_error import PhaseParsingError
from src.domain.interfaces.structured_response_parser_interface import IStructuredResponseParser

_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_OBJECT_OPENING = "{"
_OBJECT_CLOSING = "}"
_RAW_OUTPUT_MAX_LENGTH = 500
_TRUNCATION_SUFFIX = "..."
_TASK_TEXT_FIELDS = ("id", "title", "description")
_CRITERION_TEXT_FIELDS = ("id", "description")
_NOT_FOUND = -1
_ID_LIST_SEPARATOR = ", "
# Strings JSON completas, com escapes: o que está dentro delas não conta como estrutura.
_STRING_LITERAL_PATTERN = re.compile(r'"(?:[^"\\]|\\.)*"', re.DOTALL)
_STRING_DELIMITER = '"'
_CLOSING_BY_OPENING = {"{": "}", "[": "]"}
_CLOSINGS = frozenset(_CLOSING_BY_OPENING.values())
# Motivos de término em que a saída foi cortada: o que falta pode ser conteúdo, não só fechamentos.
_TRUNCATED_FINISH_REASONS = frozenset({"length"})


class StructuredResponseParserAdapter(IStructuredResponseParser):
    """Adapter de `IStructuredResponseParser` apoiado em `json.loads`.

    A extração é tolerante ao que os modelos realmente produzem: JSON puro,
    JSON dentro de cerca de código, JSON cercado por texto solto, ou JSON que
    terminou sem fechar as últimas chaves e colchetes. Já a validação de schema
    é estrita — a fase seguinte do fluxo só recebe uma estrutura que sabidamente
    confere com o contrato daquela etapa.
    """

    def __init__(self, logger: logging.Logger) -> None:
        """Inicializa o adapter.

        Args:
            logger: Logger do módulo.
        """
        self.logger = logger

    def parse(
        self,
        raw_output: str,
        phase: ThinkingPhaseEnum,
        validation: ValidationContext | None = None,
        finish_reason: str | None = None,
    ) -> dict[str, Any]:
        """Extrai e valida o JSON produzido pelo modelo para a fase informada.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.
            validation: Dados esperados pela chamada; obrigatório nas fases de verificação.
            finish_reason: Motivo de término informado pelo provedor; uma saída cortada pelo
                limite de tokens não tem os fechamentos ausentes reparados.

        Returns:
            dict[str, Any]: Estrutura JSON já validada contra o schema da fase.

        Raises:
            PhaseParsingError: Quando não há JSON válido, quando a fase não produz
                saída estruturada, quando o schema não confere ou quando a saída
                contradiz o contexto de validação.
            ValueError: Quando uma fase de verificação é chamada sem os critérios esperados.
        """
        validator = self.__validators().get(phase)
        if validator is None:
            raise PhaseParsingError(
                phase=phase,
                raw_output=self.__truncate(raw_output=raw_output),
                reason="A fase não produz saída estruturada.",
            )

        parsed = self.__extract(raw_output=raw_output, phase=phase, finish_reason=finish_reason)
        validator(parsed, phase, raw_output, validation)
        return parsed

    def __validators(
        self,
    ) -> dict[ThinkingPhaseEnum, Callable[[dict[str, Any], ThinkingPhaseEnum, str, ValidationContext | None], None]]:
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
            ThinkingPhaseEnum.A3_PLANNING_LEARNINGS: self.__validate_learnings,
            ThinkingPhaseEnum.B4_LEARNINGS_EXTRACTION: self.__validate_learnings,
            ThinkingPhaseEnum.C3_FINAL_ANSWER: self.__validate_final_answer,
        }

    def __extract(self, raw_output: str, phase: ThinkingPhaseEnum, finish_reason: str | None) -> dict[str, Any]:
        """Obtém o objeto JSON da saída bruta, tolerando cerca, texto solto e fechamentos ausentes.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.
            finish_reason: Motivo de término informado pelo provedor, quando há.

        Returns:
            dict[str, Any]: Objeto JSON extraído.

        Raises:
            PhaseParsingError: Quando nenhuma estratégia devolve um objeto JSON.
        """
        for candidate in self.__candidates(raw_output=raw_output):
            parsed = self.__load_object(candidate=candidate)
            if parsed is not None:
                return parsed

        if finish_reason not in _TRUNCATED_FINISH_REASONS:
            parsed = self.__repair_missing_closings(raw_output=raw_output, phase=phase)
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

    def __repair_missing_closings(self, raw_output: str, phase: ThinkingPhaseEnum) -> dict[str, Any] | None:
        """Completa o JSON que terminou sem fechar as últimas chaves e colchetes.

        Só acrescenta fechamentos ao fim: uma saída que termina dentro de uma string, com
        fechamento trocado ou a mais, ou com qualquer outro defeito continua inválida.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.

        Returns:
            dict[str, Any] | None: Objeto reparado, ou `None` quando nenhum candidato é reparável.
        """
        for candidate in self.__repair_candidates(raw_output=raw_output):
            missing = self.__missing_closings(candidate=candidate)
            if not missing:
                continue

            parsed = self.__load_object(candidate=candidate + missing)
            if parsed is not None:
                self.logger.warning(
                    "Saída da fase '%s' reparada: fechamento(s) ausente(s) '%s' acrescentado(s) ao final.",
                    phase.value,
                    missing,
                )
                return parsed

        return None

    def __repair_candidates(self, raw_output: str) -> list[str]:
        """Lista os trechos que podem ser um objeto JSON sem os fechamentos finais.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.

        Returns:
            list[str]: Conteúdo das cercas e o trecho do primeiro `{` até o fim da saída.
        """
        candidates = [match.group(1).rstrip() for match in _FENCE_PATTERN.finditer(raw_output)]

        opening = raw_output.find(_OBJECT_OPENING)
        if opening != _NOT_FOUND:
            candidates.append(raw_output[opening:].rstrip())

        return candidates

    def __missing_closings(self, candidate: str) -> str:
        """Calcula os fechamentos que faltam no fim do candidato, na ordem em que devem entrar.

        Args:
            candidate: Trecho candidato a objeto JSON.

        Returns:
            str: Fechamentos ausentes, ou vazio quando não há o que reparar com segurança —
            estrutura já fechada, saída terminada dentro de uma string, ou fechamento que não
            corresponde à abertura pendente.
        """
        structure = _STRING_LITERAL_PATTERN.sub("", candidate)
        if _STRING_DELIMITER in structure:
            return ""

        pending: list[str] = []
        for char in structure:
            if char in _CLOSING_BY_OPENING:
                pending.append(_CLOSING_BY_OPENING[char])
            elif char in _CLOSINGS and (not pending or pending.pop() != char):
                return ""

        return "".join(reversed(pending))

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
        validation: ValidationContext | None,
    ) -> None:
        """Valida o schema de A.1.

        Raises:
            PhaseParsingError: Quando a lista de critérios gerais não confere ou repete identificadores.
        """
        criteria = self.__require_list(
            parsed=parsed, field="general_acceptance_criteria", phase=phase, raw_output=raw_output, allow_empty=False
        )
        for criterion in criteria:
            self.__validate_criterion(criterion=criterion, phase=phase, raw_output=raw_output)
        self.__require_unique_ids(
            ids=[criterion["id"] for criterion in criteria],
            what="critérios gerais",
            phase=phase,
            raw_output=raw_output,
        )

    def __validate_tasks(
        self,
        parsed: dict[str, Any],
        phase: ThinkingPhaseEnum,
        raw_output: str,
        validation: ValidationContext | None,
    ) -> None:
        """Valida o schema de A.2 e C.2 e o lote contra o contexto de validação.

        Raises:
            PhaseParsingError: Quando a lista de tarefas não confere, repete identificadores,
                reutiliza o de uma tarefa já criada ou excede o teto de tarefas do lote.
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
            self.__require_unique_ids(
                ids=[criterion["id"] for criterion in criteria],
                what=f"critérios da tarefa '{task['id']}'",
                phase=phase,
                raw_output=raw_output,
            )

        self.__require_unique_ids(
            ids=[task["id"] for task in tasks], what="tarefas do lote", phase=phase, raw_output=raw_output
        )
        self.__validate_batch_against_session(tasks=tasks, phase=phase, raw_output=raw_output, validation=validation)

    def __validate_batch_against_session(
        self,
        tasks: list[dict[str, Any]],
        phase: ThinkingPhaseEnum,
        raw_output: str,
        validation: ValidationContext | None,
    ) -> None:
        """Confronta o lote de tarefas com o que a sessão já tem e com o teto de tarefas.

        Raises:
            PhaseParsingError: Quando o lote reutiliza o identificador de uma tarefa já criada
                ou tem mais tarefas do que a sessão ainda comporta.
        """
        if validation is None:
            return

        reused = sorted(task["id"] for task in tasks if task["id"] in validation.known_task_ids)
        if reused:
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=f"Os identificadores de tarefa {_ID_LIST_SEPARATOR.join(reused)} já foram usados na sessão.",
            )

        if validation.max_tasks is not None and len(tasks) > validation.max_tasks:
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=(
                    f"O lote tem {len(tasks)} tarefas, mas a sessão comporta no máximo {validation.max_tasks}. "
                    "Reduza o lote preservando tarefas autônomas e de objetivo único."
                ),
                limit=BudgetLimitEnum.TASKS_PER_SESSION,
            )

    def __validate_task_result(
        self,
        parsed: dict[str, Any],
        phase: ThinkingPhaseEnum,
        raw_output: str,
        validation: ValidationContext | None,
    ) -> None:
        """Valida o schema de B.1.

        Raises:
            PhaseParsingError: Quando 'result' não é uma string não vazia.
        """
        self.__require_text(source=parsed, field="result", value=parsed.get("result"), phase=phase,
                            raw_output=raw_output)

    def __validate_verification(
        self,
        parsed: dict[str, Any],
        phase: ThinkingPhaseEnum,
        raw_output: str,
        validation: ValidationContext | None,
    ) -> None:
        """Valida o schema e a coerência de B.2 e C.1 contra os critérios esperados.

        O relatório só é aceito quando avalia cada critério esperado exatamente uma vez e
        quando decisão, avaliações e pendências não se contradizem. Nada aqui julga a
        veracidade semântica das avaliações: isso continua sendo do modelo verificador.

        Raises:
            PhaseParsingError: Quando o schema não confere, a cobertura dos critérios é
                incompleta ou a decisão é incoerente com as avaliações e as pendências.
            ValueError: Quando o contexto de validação não informa os critérios esperados.
        """
        if validation is None or validation.expected_criteria_ids is None:
            raise ValueError(
                f"A fase '{phase.value}' exige um contexto de validação com os critérios esperados."
            )

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

        self.__require_exact_coverage(
            evaluated_ids=[evaluation["criterion_id"] for evaluation in evaluations],
            expected_ids=validation.expected_criteria_ids,
            phase=phase,
            raw_output=raw_output,
        )
        failed_ids = [evaluation["criterion_id"] for evaluation in evaluations if not evaluation["met"]]
        self.__require_coherent_decision(
            decision=decision, failed_ids=failed_ids, unmet=unmet, phase=phase, raw_output=raw_output
        )
        self.__require_unique_ids(ids=unmet, what="pendências", phase=phase, raw_output=raw_output)
        if set(unmet) != set(failed_ids):
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=(
                    "As pendências em 'unmet_criteria_ids' devem ser exatamente os critérios avaliados com "
                    f"met=false. Avaliados com met=false: [{_ID_LIST_SEPARATOR.join(failed_ids)}]; "
                    f"pendências informadas: [{_ID_LIST_SEPARATOR.join(unmet)}]."
                ),
            )

    def __require_exact_coverage(
        self,
        evaluated_ids: list[str],
        expected_ids: tuple[str, ...],
        phase: ThinkingPhaseEnum,
        raw_output: str,
    ) -> None:
        """Exige uma avaliação para cada critério esperado, sem omissões, repetições ou extras.

        Raises:
            PhaseParsingError: Quando algum critério esperado não foi avaliado, foi avaliado
                mais de uma vez ou há avaliação de um critério desconhecido.
        """
        self.__require_unique_ids(
            ids=evaluated_ids, what="avaliações (cada critério deve ser avaliado uma vez)", phase=phase,
            raw_output=raw_output, repeated_message="foi avaliado mais de uma vez",
        )
        unknown = [criterion_id for criterion_id in evaluated_ids if criterion_id not in expected_ids]
        if unknown:
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=(
                    f"Há avaliações de critérios desconhecidos: {_ID_LIST_SEPARATOR.join(unknown)}. "
                    f"Avalie somente: {_ID_LIST_SEPARATOR.join(expected_ids)}."
                ),
            )
        missing = [criterion_id for criterion_id in expected_ids if criterion_id not in evaluated_ids]
        if missing:
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=f"Faltam avaliações para os critérios: {_ID_LIST_SEPARATOR.join(missing)}.",
            )

    def __require_coherent_decision(
        self,
        decision: str,
        failed_ids: list[str],
        unmet: list[str],
        phase: ThinkingPhaseEnum,
        raw_output: str,
    ) -> None:
        """Exige que a decisão não contradiga as avaliações nem as pendências.

        Raises:
            PhaseParsingError: Quando uma aprovação convive com critério não atendido ou
                uma reprovação não aponta nenhuma pendência.
        """
        approved = decision == VerificationDecisionEnum.APPROVED
        if approved and (failed_ids or unmet):
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=(
                    f"A decisão '{decision}' é incoerente com as avaliações: aprovar exige todos os critérios "
                    "com met=true e 'unmet_criteria_ids' vazia."
                ),
            )
        if not approved and not unmet:
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=(
                    f"A decisão '{decision}' é incoerente com 'unmet_criteria_ids': "
                    "reprovar exige ao menos um critério pendente."
                ),
            )

    def __require_unique_ids(
        self,
        ids: list[str],
        what: str,
        phase: ThinkingPhaseEnum,
        raw_output: str,
        repeated_message: str = "se repete",
    ) -> None:
        """Exige que uma lista de identificadores não tenha repetições.

        Raises:
            PhaseParsingError: Quando algum identificador aparece mais de uma vez.
        """
        repeated = sorted({identifier for identifier in ids if ids.count(identifier) > 1})
        if repeated:
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                reason=f"Em {what}, o identificador {_ID_LIST_SEPARATOR.join(repeated)} {repeated_message}.",
            )

    def __validate_learnings(
        self,
        parsed: dict[str, Any],
        phase: ThinkingPhaseEnum,
        raw_output: str,
        validation: ValidationContext | None,
    ) -> None:
        """Valida o schema de A.3 e B.4, onde a lista vazia é legítima.

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

    def __validate_final_answer(
        self,
        parsed: dict[str, Any],
        phase: ThinkingPhaseEnum,
        raw_output: str,
        validation: ValidationContext | None,
    ) -> None:
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

    def __fail(
        self,
        phase: ThinkingPhaseEnum,
        raw_output: str,
        reason: str,
        limit: BudgetLimitEnum | None = None,
    ) -> None:
        """Registra e levanta a falha de parsing da fase.

        Raises:
            PhaseParsingError: Sempre.
        """
        self.logger.warning("Saída da fase '%s' recusada pelo parser: %s", phase.value, reason)
        raise PhaseParsingError(
            phase=phase, raw_output=self.__truncate(raw_output=raw_output), reason=reason, limit=limit
        )

    def __truncate(self, raw_output: str) -> str:
        """Trunca a saída bruta para caber no erro sem inundar o log.

        Returns:
            str: Saída bruta, truncada quando excede o tamanho máximo.
        """
        if len(raw_output) <= _RAW_OUTPUT_MAX_LENGTH:
            return raw_output
        return f"{raw_output[:_RAW_OUTPUT_MAX_LENGTH]}{_TRUNCATION_SUFFIX}"
