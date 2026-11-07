import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

from src.domain.entities.thinking.output_diagnostic import OutputDiagnostic
from src.domain.entities.thinking.output_problem import OutputProblem
from src.domain.entities.thinking.parsed_output import ParsedOutput
from src.domain.entities.thinking.validation_context import ValidationContext
from src.domain.enums.budget_limit_enum import BudgetLimitEnum
from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum
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
_ITEM_SUFFIX = "[]"
_FIELD_SEPARATOR = "."
# Strings JSON completas, com escapes: o que está dentro delas não conta como estrutura.
_STRING_LITERAL_PATTERN = re.compile(r'"(?:[^"\\]|\\.)*"', re.DOTALL)
_UNESCAPED_BACKSLASH_PATTERN = re.compile(r'\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4})|(\\)')
_STRING_DELIMITER = '"'
_CLOSING_BY_OPENING = {"{": "}", "[": "]"}
_CLOSINGS = frozenset(_CLOSING_BY_OPENING.values())
# Motivos de término em que a saída foi cortada: o que falta pode ser conteúdo, não só fechamentos.
_TRUNCATED_FINISH_REASONS = frozenset({"length"})
_NO_JSON_REASON = "No valid JSON object was found in the output."
_TRUNCATED_REASON = (
    "The output was cut off by the length limit before forming a complete JSON object."
)
_UNSUPPORTED_PHASE_REASON = "The phase does not produce structured output."


@dataclass(frozen=True)
class _Structure:
    """Leitura estrutural de um trecho: string aberta, fechamentos pendentes e fechamento trocado."""

    open_string: bool
    pending_closings: str
    mismatched: bool


@dataclass(frozen=True)
class _Extraction:
    """Objeto extraído da saída e os fechamentos acrescentados pelo reparo, quando houve."""

    parsed: dict[str, Any]
    repaired_closings: str | None


class _ContractViolation(Exception):
    """Violação do contrato da fase, convertida em `PhaseParsingError` com diagnóstico."""

    def __init__(
        self,
        code: OutputProblemCodeEnum,
        reason: str,
        field: str | None = None,
        affected_ids: tuple[str, ...] = (),
        limit: BudgetLimitEnum | None = None,
    ) -> None:
        super().__init__(reason)
        self.problem = OutputProblem(code=code, reason=reason, field=field, affected_ids=affected_ids)
        self.limit = limit


class StructuredResponseParserAdapter(IStructuredResponseParser):
    """Adapter de `IStructuredResponseParser` apoiado em `json.loads`.

    A extração é tolerante ao que os modelos realmente produzem: JSON puro,
    JSON dentro de cerca de código, JSON cercado por texto solto, ou JSON que
    terminou sem fechar as últimas chaves e colchetes. Já a validação de schema
    é estrita — a fase seguinte do fluxo só recebe uma estrutura que sabidamente
    confere com o contrato daquela etapa.

    Os reparos locais são conservadores: só a extração do JSON e o fechamento estrutural
    inequívoco, que não alteram conteúdo. Nada aqui inventa campos, completa strings
    interrompidas, preenche explicações ou muda o veredito de um relatório. Toda recusa é
    classificada (`OutputDefectEnum`) para que a correção pedida ao modelo seja a adequada.

    Toda saída avaliada ganha um diagnóstico estruturado: estado da sintaxe (válida,
    inválida ou válida após reparo), estado do contrato (válido, inválido ou não avaliado),
    código do problema com o campo e os identificadores afetados, motivo de término original
    e interrupção por comprimento — confirmada só pelo provedor; sem ele, no máximo um indício.
    """

    def __init__(self, logger: logging.Logger) -> None:
        """Inicializa o adapter.

        Args:
            logger: Logger do módulo.
        """
        self.logger = logger

    def parse_output(
        self,
        raw_output: str,
        phase: ThinkingPhaseEnum,
        validation: ValidationContext | None = None,
        finish_reason: str | None = None,
    ) -> ParsedOutput:
        """Extrai e valida o JSON produzido pelo modelo, devolvendo também o diagnóstico da saída.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.
            validation: Dados esperados pela chamada; obrigatório nas fases de verificação.
            finish_reason: Motivo de término informado pelo provedor; uma saída cortada pelo
                limite de tokens não tem os fechamentos ausentes reparados.

        Returns:
            ParsedOutput: Estrutura validada e diagnóstico de aceite.

        Raises:
            PhaseParsingError: Quando não há JSON válido, quando a fase não produz saída
                estruturada, quando o schema não confere ou quando a saída contradiz o contexto
                de validação. O erro carrega o diagnóstico da recusa.
            ValueError: Quando uma fase de verificação é chamada sem os critérios esperados.
        """
        length_interruption = LengthInterruptionEnum.classify(
            finish_reason=finish_reason, ends_incomplete=self.__ends_incomplete(raw_output=raw_output)
        )
        validator = self.__validators().get(phase)
        if validator is None:
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                diagnostic=OutputDiagnostic(
                    syntax_status=None,
                    contract_status=OutputContractStatusEnum.NOT_EVALUATED,
                    finish_reason=finish_reason,
                    length_interruption=length_interruption,
                    problem=OutputProblem(
                        code=OutputProblemCodeEnum.UNSUPPORTED_PHASE, reason=_UNSUPPORTED_PHASE_REASON
                    ),
                ),
            )

        extraction = self.__extract(raw_output=raw_output, phase=phase, finish_reason=finish_reason)
        if extraction is None:
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                diagnostic=OutputDiagnostic(
                    syntax_status=OutputSyntaxStatusEnum.INVALID,
                    contract_status=OutputContractStatusEnum.NOT_EVALUATED,
                    finish_reason=finish_reason,
                    length_interruption=length_interruption,
                    problem=OutputProblem(
                        code=OutputProblemCodeEnum.JSON_SYNTAX,
                        reason=(
                            _TRUNCATED_REASON
                            if length_interruption is LengthInterruptionEnum.CONFIRMED
                            else _NO_JSON_REASON
                        ),
                    ),
                ),
            )

        try:
            validator(extraction.parsed, phase, validation)
        except _ContractViolation as violation:
            self.__fail(
                phase=phase,
                raw_output=raw_output,
                diagnostic=OutputDiagnostic(
                    syntax_status=(
                        OutputSyntaxStatusEnum.REPAIRED
                        if extraction.repaired_closings
                        else OutputSyntaxStatusEnum.VALID
                    ),
                    contract_status=OutputContractStatusEnum.INVALID,
                    finish_reason=finish_reason,
                    length_interruption=length_interruption,
                    problem=violation.problem,
                    repaired_closings=extraction.repaired_closings,
                ),
                limit=violation.limit,
            )

        if length_interruption is LengthInterruptionEnum.CONFIRMED:
            self.logger.warning(
                "Saída da fase '%s' aceita, mas terminada pelo limite de comprimento: sem garantia de completude.",
                phase.value,
            )
        return ParsedOutput(
            parsed=extraction.parsed,
            diagnostic=OutputDiagnostic.accepted(
                finish_reason=finish_reason,
                length_interruption=length_interruption,
                repaired_closings=extraction.repaired_closings,
            ),
        )

    def __validators(
        self,
    ) -> dict[ThinkingPhaseEnum, Callable[[dict[str, Any], ThinkingPhaseEnum, ValidationContext | None], None]]:
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

    # ── Extração e sintaxe ───────────────────────────────────────────────────

    def __extract(self, raw_output: str, phase: ThinkingPhaseEnum, finish_reason: str | None) -> _Extraction | None:
        """Obtém o objeto JSON da saída bruta, tolerando cerca, texto solto e fechamentos ausentes.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.
            finish_reason: Motivo de término informado pelo provedor, quando há.

        Returns:
            _Extraction | None: Objeto extraído, ou `None` quando nenhuma estratégia devolve um objeto.
        """
        for candidate in self.__candidates(raw_output=raw_output):
            parsed = self.__load_object(candidate=candidate)
            if parsed is not None:
                return _Extraction(parsed=parsed, repaired_closings=None)

        if finish_reason not in _TRUNCATED_FINISH_REASONS:
            return self.__repair_missing_closings(raw_output=raw_output, phase=phase)
        return None

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

    def __repair_missing_closings(self, raw_output: str, phase: ThinkingPhaseEnum) -> _Extraction | None:
        """Completa o JSON que terminou sem fechar as últimas chaves e colchetes.

        Só acrescenta fechamentos ao fim: uma saída que termina dentro de uma string, com
        fechamento trocado ou a mais, ou com qualquer outro defeito continua inválida.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.
            phase: Fase de thinking que produziu a saída.

        Returns:
            _Extraction | None: Objeto reparado, ou `None` quando nenhum candidato é reparável.
        """
        for candidate in self.__repair_candidates(raw_output=raw_output):
            structure = self.__structure(candidate=candidate)
            if structure.open_string or structure.mismatched or not structure.pending_closings:
                continue

            parsed = self.__load_object(candidate=candidate + structure.pending_closings)
            if parsed is not None:
                self.logger.warning(
                    "Saída da fase '%s' reparada: fechamento(s) ausente(s) '%s' acrescentado(s) ao final.",
                    phase.value,
                    structure.pending_closings,
                )
                return _Extraction(parsed=parsed, repaired_closings=structure.pending_closings)

        return None

    def __repair_candidates(self, raw_output: str) -> list[str]:
        """Lista os trechos que podem ser um objeto JSON sem os fechamentos finais.

        Args:
            raw_output: Saída bruta devolvida pelo modelo.

        Returns:
            list[str]: Conteúdo das cercas e o trecho do primeiro `{` até o fim da saída.
        """
        candidates = [match.group(1).rstrip() for match in _FENCE_PATTERN.finditer(raw_output)]

        tail = self.__tail_from_first_opening(raw_output=raw_output)
        if tail is not None:
            candidates.append(tail)

        return candidates

    def __tail_from_first_opening(self, raw_output: str) -> str | None:
        """Recorta a saída do primeiro `{` até o fim, sem os espaços finais.

        Returns:
            str | None: Trecho recortado, ou `None` quando a saída não abre nenhum objeto.
        """
        opening = raw_output.find(_OBJECT_OPENING)
        if opening == _NOT_FOUND:
            return None
        return raw_output[opening:].rstrip()

    def __ends_incomplete(self, raw_output: str) -> bool:
        """Indica se a saída termina estruturalmente incompleta, o indício de um corte.

        Considera o trecho do primeiro `{` até o fim: terminar dentro de uma string ou com
        chaves e colchetes abertos é indício de corte — nunca confirmação, que só o provedor dá.

        Returns:
            bool: `True` quando a saída termina com string ou estrutura aberta.
        """
        tail = self.__tail_from_first_opening(raw_output=raw_output)
        if tail is None:
            return False
        structure = self.__structure(candidate=tail)
        return structure.open_string or bool(structure.pending_closings)

    def __structure(self, candidate: str) -> _Structure:
        """Lê a estrutura do candidato, ignorando o conteúdo das strings completas.

        Args:
            candidate: Trecho candidato a objeto JSON.

        Returns:
            _Structure: String aberta, fechamentos pendentes na ordem em que devem entrar e
            presença de fechamento que não corresponde à abertura pendente.
        """
        structure = _STRING_LITERAL_PATTERN.sub("", candidate)
        open_string = _STRING_DELIMITER in structure
        if open_string:
            structure = structure[: structure.index(_STRING_DELIMITER)]

        pending: list[str] = []
        for char in structure:
            if char in _CLOSING_BY_OPENING:
                pending.append(_CLOSING_BY_OPENING[char])
            elif char in _CLOSINGS and (not pending or pending.pop() != char):
                return _Structure(open_string=open_string, pending_closings="", mismatched=True)

        return _Structure(open_string=open_string, pending_closings="".join(reversed(pending)), mismatched=False)

    def __load_object(self, candidate: str) -> dict[str, Any] | None:
        """Tenta interpretar um candidato como objeto JSON.

        Args:
            candidate: Trecho candidato a objeto JSON.

        Returns:
            dict[str, Any] | None: Objeto interpretado, ou `None` quando o trecho
            não é JSON válido ou não é um objeto.
        """
        parsed = self.__loads_dict(candidate=candidate)
        if parsed is not None:
            return parsed

        if "\\" in candidate:
            repaired = _UNESCAPED_BACKSLASH_PATTERN.sub(
                lambda match: "\\\\" if match.group(1) else match.group(0),
                candidate,
            )
            parsed = self.__loads_dict(candidate=repaired)
            if parsed is not None:
                return parsed

        return self.__decode_first_of_duplicated_objects(candidate=candidate)

    def __loads_dict(self, candidate: str) -> dict[str, Any] | None:
        """Converte uma string JSON em dicionário, ou devolve `None` se falhar.

        Args:
            candidate: String candidata a JSON.

        Returns:
            dict[str, Any] | None: Dicionário decodificado, ou `None`.
        """
        try:
            parsed = json.loads(candidate)
        except ValueError:
            return None

        if not isinstance(parsed, dict):
            return None

        return parsed

    def __decode_first_of_duplicated_objects(self, candidate: str) -> dict[str, Any] | None:
        """Extrai o primeiro objeto quando o modelo emitiu dois objetos JSON seguidos.

        Args:
            candidate: Trecho candidato que falhou em `json.loads`.

        Returns:
            dict[str, Any] | None: Primeiro objeto, quando o restante também é um objeto JSON;
            `None` quando o restante é lixo ou fechamento excedente.
        """
        stripped = candidate.strip()
        try:
            first, index = json.JSONDecoder().raw_decode(stripped)
            second = json.loads(stripped[index:].strip())
        except ValueError:
            return None

        if isinstance(first, dict) and isinstance(second, dict):
            return first

        return None

    def __validate_general_criteria(
        self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, validation: ValidationContext | None
    ) -> None:
        """Valida o schema de A.1.

        Raises:
            _ContractViolation: Quando a lista de critérios gerais não confere ou repete identificadores.
        """
        field = "general_acceptance_criteria"
        criteria = self.__require_list(source=parsed, key=field, label=field, allow_empty=False)
        for criterion in criteria:
            self.__validate_criterion(criterion=criterion, container=field)
        self.__require_unique_ids(
            ids=[criterion["id"] for criterion in criteria],
            what="general criteria",
            field=self.__item_field(field, "id"),
        )

    def __validate_tasks(
        self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, validation: ValidationContext | None
    ) -> None:
        """Valida o schema de A.2 e C.2 e o lote contra o contexto de validação.

        Raises:
            _ContractViolation: Quando a lista de tarefas não confere, repete identificadores,
                reutiliza o de uma tarefa já criada ou excede o teto de tarefas do lote.
        """
        tasks = self.__require_list(source=parsed, key="tasks", label="tasks", allow_empty=False)
        criteria_container = self.__item_field("tasks", "acceptance_criteria")
        for task in tasks:
            if not isinstance(task, dict):
                raise _ContractViolation(
                    code=OutputProblemCodeEnum.SCHEMA_TYPE,
                    reason="Each item of 'tasks' must be an object.",
                    field=f"tasks{_ITEM_SUFFIX}",
                )
            for key in _TASK_TEXT_FIELDS:
                self.__require_text(
                    source=task, key=key, label=f"tasks.{key}", field=self.__item_field("tasks", key),
                    owner_id=task.get("id"),
                )
            criteria = self.__require_list(
                source=task, key="acceptance_criteria", label="acceptance_criteria", allow_empty=False,
                field=criteria_container, owner_id=task["id"],
            )
            for criterion in criteria:
                self.__validate_criterion(criterion=criterion, container=criteria_container)
            self.__require_unique_ids(
                ids=[criterion["id"] for criterion in criteria],
                what=f"criteria of task '{task['id']}'",
                field=self.__item_field(criteria_container, "id"),
            )

        self.__require_unique_ids(
            ids=[task["id"] for task in tasks], what="batch tasks", field=self.__item_field("tasks", "id")
        )
        self.__validate_batch_against_session(tasks=tasks, validation=validation)

    def __validate_batch_against_session(
        self, tasks: list[dict[str, Any]], validation: ValidationContext | None
    ) -> None:
        """Confronta o lote de tarefas com o que a sessão já tem e com o teto de tarefas.

        Raises:
            _ContractViolation: Quando o lote reutiliza o identificador de uma tarefa já criada
                ou tem mais tarefas do que a sessão ainda comporta.
        """
        if validation is None:
            return

        reused = sorted(task["id"] for task in tasks if task["id"] in validation.known_task_ids)
        if reused:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.TASK_IDS,
                reason=f"The task identifiers {_ID_LIST_SEPARATOR.join(reused)} were already used in the session.",
                field=self.__item_field("tasks", "id"),
                affected_ids=tuple(reused),
            )

        if validation.max_tasks is not None and len(tasks) > validation.max_tasks:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.TASK_LIMIT,
                reason=(
                    f"The batch has {len(tasks)} tasks, but the session holds at most {validation.max_tasks}. "
                    "Reduce the batch while keeping the tasks autonomous and single-goal."
                ),
                field="tasks",
                limit=BudgetLimitEnum.TASKS_PER_SESSION,
            )

    def __validate_task_result(
        self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, validation: ValidationContext | None
    ) -> None:
        """Valida o schema de B.1.

        Raises:
            _ContractViolation: Quando 'result' ou 'conclusion' não é uma string não vazia.
        """
        self.__require_text(source=parsed, key="result", label="result", field="result")
        self.__require_text(source=parsed, key="conclusion", label="conclusion", field="conclusion")

    def __validate_verification(
        self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, validation: ValidationContext | None
    ) -> None:
        """Valida o schema e a coerência de B.2 e C.1 contra os critérios esperados.

        O relatório só é aceito quando avalia cada critério esperado exatamente uma vez e
        quando decisão, avaliações e pendências não se contradizem. Nada aqui julga a
        veracidade semântica das avaliações: isso continua sendo do modelo verificador. Uma
        reprovação coerente é um resultado semântico normal, aceito como qualquer aprovação.

        Raises:
            _ContractViolation: Quando o schema não confere, a cobertura dos critérios é
                incompleta ou a decisão é incoerente com as avaliações e as pendências.
            ValueError: Quando o contexto de validação não informa os critérios esperados.
        """
        if validation is None or validation.expected_criteria_ids is None:
            raise ValueError(
                f"A fase '{phase.value}' exige um contexto de validação com os critérios esperados."
            )

        decision = self.__require_decision(parsed=parsed)

        evaluations = self.__require_list(
            source=parsed, key="criteria_evaluation", label="criteria_evaluation", allow_empty=True
        )
        for evaluation in evaluations:
            self.__validate_evaluation(evaluation=evaluation)

        if "unmet_criteria_ids" not in parsed:
            parsed["unmet_criteria_ids"] = [
                evaluation["criterion_id"] for evaluation in evaluations if not evaluation["met"]
            ]

        unmet = self.__require_list(
            source=parsed, key="unmet_criteria_ids", label="unmet_criteria_ids", allow_empty=True
        )
        for criterion_id in unmet:
            if not isinstance(criterion_id, str):
                raise _ContractViolation(
                    code=OutputProblemCodeEnum.SCHEMA_TYPE,
                    reason="Each item of 'unmet_criteria_ids' must be a string.",
                    field=f"unmet_criteria_ids{_ITEM_SUFFIX}",
                )

        self.__require_exact_coverage(
            evaluated_ids=[evaluation["criterion_id"] for evaluation in evaluations],
            expected_ids=validation.expected_criteria_ids,
        )
        failed_ids = [evaluation["criterion_id"] for evaluation in evaluations if not evaluation["met"]]
        self.__require_coherent_decision(decision=decision, failed_ids=failed_ids, unmet=unmet)
        self.__require_unique_ids(ids=unmet, what="pending criteria", field="unmet_criteria_ids")
        if set(unmet) != set(failed_ids):
            raise _ContractViolation(
                code=OutputProblemCodeEnum.DECISION_CONSISTENCY,
                reason=(
                    "The pending criteria in 'unmet_criteria_ids' must be exactly the criteria evaluated with "
                    f"met=false. Evaluated with met=false: [{_ID_LIST_SEPARATOR.join(failed_ids)}]; "
                    f"pending criteria reported: [{_ID_LIST_SEPARATOR.join(unmet)}]."
                ),
                field="unmet_criteria_ids",
                affected_ids=tuple(sorted(set(unmet) ^ set(failed_ids))),
            )

    def __require_decision(self, parsed: dict[str, Any]) -> str:
        """Exige um veredito conhecido no campo 'decision', sem converter valores por suposição.

        Returns:
            str: Veredito informado.

        Raises:
            _ContractViolation: Quando o campo falta, não é string ou não é um veredito conhecido.
        """
        decision = parsed.get("decision")
        if decision in tuple(VerificationDecisionEnum):
            return decision

        if "decision" not in parsed:
            code = OutputProblemCodeEnum.MISSING_FIELD
        elif not isinstance(decision, str):
            code = OutputProblemCodeEnum.SCHEMA_TYPE
        else:
            code = OutputProblemCodeEnum.INVALID_VALUE
        raise _ContractViolation(
            code=code,
            reason=f"The 'decision' field must be a known verdict. Value: '{decision}'.",
            field="decision",
        )

    def __require_exact_coverage(self, evaluated_ids: list[str], expected_ids: tuple[str, ...]) -> None:
        """Exige uma avaliação para cada critério esperado, sem omissões, repetições ou extras.

        Raises:
            _ContractViolation: Quando algum critério esperado não foi avaliado, foi avaliado
                mais de uma vez ou há avaliação de um critério desconhecido.
        """
        field = self.__item_field("criteria_evaluation", "criterion_id")
        self.__require_unique_ids(
            ids=evaluated_ids, what="evaluations (each criterion must be evaluated once)", field=field,
            repeated_message="was evaluated more than once", code=OutputProblemCodeEnum.CRITERIA_IDS,
        )
        unknown = [criterion_id for criterion_id in evaluated_ids if criterion_id not in expected_ids]
        if unknown:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.CRITERIA_IDS,
                reason=(
                    f"There are evaluations of unknown criteria: {_ID_LIST_SEPARATOR.join(unknown)}. "
                    f"Evaluate only: {_ID_LIST_SEPARATOR.join(expected_ids)}."
                ),
                field=field,
                affected_ids=tuple(unknown),
            )
        missing = [criterion_id for criterion_id in expected_ids if criterion_id not in evaluated_ids]
        if missing:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.CRITERIA_IDS,
                reason=f"Evaluations are missing for the criteria: {_ID_LIST_SEPARATOR.join(missing)}.",
                field=field,
                affected_ids=tuple(missing),
            )

    def __require_coherent_decision(self, decision: str, failed_ids: list[str], unmet: list[str]) -> None:
        """Exige que a decisão não contradiga as avaliações nem as pendências.

        A decisão nunca é corrigida aqui: uma contradição recusa a saída inteira.

        Raises:
            _ContractViolation: Quando uma aprovação convive com critério não atendido ou
                uma reprovação não aponta nenhuma pendência.
        """
        approved = decision == VerificationDecisionEnum.APPROVED
        if approved and (failed_ids or unmet):
            raise _ContractViolation(
                code=OutputProblemCodeEnum.DECISION_CONSISTENCY,
                reason=(
                    f"The decision '{decision}' is inconsistent with the evaluations: approving requires every "
                    "criterion with met=true and an empty 'unmet_criteria_ids'."
                ),
                field="decision",
                affected_ids=tuple(sorted({*failed_ids, *unmet})),
            )
        if not approved and not unmet:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.DECISION_CONSISTENCY,
                reason=(
                    f"The decision '{decision}' is inconsistent with 'unmet_criteria_ids': "
                    "rejecting requires at least one pending criterion."
                ),
                field="decision",
            )

    def __require_unique_ids(
        self,
        ids: list[str],
        what: str,
        field: str,
        repeated_message: str = "is repeated",
        code: OutputProblemCodeEnum = OutputProblemCodeEnum.DUPLICATE_ID,
    ) -> None:
        """Exige que uma lista de identificadores não tenha repetições.

        Raises:
            _ContractViolation: Quando algum identificador aparece mais de uma vez.
        """
        repeated = sorted({identifier for identifier in ids if ids.count(identifier) > 1})
        if repeated:
            raise _ContractViolation(
                code=code,
                reason=f"In {what}, the identifier {_ID_LIST_SEPARATOR.join(repeated)} {repeated_message}.",
                field=field,
                affected_ids=tuple(repeated),
            )

    def __validate_learnings(
        self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, validation: ValidationContext | None
    ) -> None:
        """Valida o schema de A.3 e B.4, onde a lista vazia é legítima.

        Raises:
            _ContractViolation: Quando 'learnings' não é uma lista de strings.
        """
        learnings = self.__require_list(source=parsed, key="learnings", label="learnings", allow_empty=True)
        for learning in learnings:
            if not isinstance(learning, str):
                raise _ContractViolation(
                    code=OutputProblemCodeEnum.SCHEMA_TYPE,
                    reason="Each item of 'learnings' must be a string.",
                    field=f"learnings{_ITEM_SUFFIX}",
                )

    def __validate_final_answer(
        self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, validation: ValidationContext | None
    ) -> None:
        """Valida o schema de C.3.

        Raises:
            _ContractViolation: Quando 'final_answer' não é uma string não vazia.
        """
        self.__require_text(source=parsed, key="final_answer", label="final_answer", field="final_answer")

    def __validate_criterion(self, criterion: Any, container: str) -> None:
        """Valida um critério de aceite individual.

        Args:
            criterion: Item da lista de critérios.
            container: Caminho da lista que contém o critério, para o campo afetado.

        Raises:
            _ContractViolation: Quando o critério não traz 'id' e 'description' preenchidos.
        """
        if not isinstance(criterion, dict):
            raise _ContractViolation(
                code=OutputProblemCodeEnum.SCHEMA_TYPE,
                reason="Each acceptance criterion must be an object.",
                field=f"{container}{_ITEM_SUFFIX}",
            )
        for key in _CRITERION_TEXT_FIELDS:
            self.__require_text(
                source=criterion, key=key, label=f"criterion.{key}", field=self.__item_field(container, key),
                owner_id=criterion.get("id"),
            )

    def __validate_evaluation(self, evaluation: Any) -> None:
        """Valida o veredito de um critério dentro de uma verificação.

        Raises:
            _ContractViolation: Quando o veredito não traz os campos esperados. O valor de 'met'
                nunca é convertido: a string "true" é recusada como tipo errado.
        """
        container = "criteria_evaluation"
        if not isinstance(evaluation, dict):
            raise _ContractViolation(
                code=OutputProblemCodeEnum.SCHEMA_TYPE,
                reason="Each item of 'criteria_evaluation' must be an object.",
                field=f"{container}{_ITEM_SUFFIX}",
            )
        self.__require_text(
            source=evaluation, key="criterion_id", label="criterion_id",
            field=self.__item_field(container, "criterion_id"),
        )
        criterion_id = evaluation["criterion_id"]
        self.__require_text(
            source=evaluation, key="justification", label="justification",
            field=self.__item_field(container, "justification"), owner_id=criterion_id,
        )
        if not isinstance(evaluation.get("met"), bool):
            raise _ContractViolation(
                code=self.__absence_or_type(source=evaluation, key="met"),
                reason="The 'met' field must be a boolean.",
                field=self.__item_field(container, "met"),
                affected_ids=(criterion_id,),
            )

    def __require_list(
        self,
        source: dict[str, Any],
        key: str,
        label: str,
        allow_empty: bool,
        field: str | None = None,
        owner_id: Any = None,
    ) -> list[Any]:
        """Exige que um campo seja uma lista, opcionalmente não vazia.

        Args:
            source: Objeto que deve conter o campo.
            key: Chave do campo no objeto.
            label: Nome do campo no motivo legível.
            allow_empty: Indica se a lista vazia é legítima.
            field: Caminho do campo afetado; por padrão, a própria chave.
            owner_id: Identificador do item dono do campo, quando conhecido.

        Returns:
            list[Any]: Lista encontrada no campo.

        Raises:
            _ContractViolation: Quando o campo falta, não é lista ou está indevidamente vazio.
        """
        value = source.get(key)
        if not isinstance(value, list):
            raise _ContractViolation(
                code=self.__absence_or_type(source=source, key=key),
                reason=f"The '{label}' field must be a list.",
                field=field or key,
                affected_ids=self.__owner(owner_id=owner_id),
            )
        if not allow_empty and not value:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.EMPTY_VALUE,
                reason=f"The '{label}' field cannot be an empty list.",
                field=field or key,
                affected_ids=self.__owner(owner_id=owner_id),
            )
        return value

    def __require_text(
        self, source: dict[str, Any], key: str, label: str, field: str, owner_id: Any = None
    ) -> None:
        """Exige que um campo seja uma string com conteúdo.

        Args:
            source: Objeto que deve conter o campo.
            key: Chave do campo no objeto.
            label: Nome do campo no motivo legível.
            field: Caminho do campo afetado.
            owner_id: Identificador do item dono do campo, quando conhecido.

        Raises:
            _ContractViolation: Quando o campo falta, não é string ou está em branco.
        """
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return

        code = (
            OutputProblemCodeEnum.EMPTY_VALUE
            if isinstance(value, str)
            else self.__absence_or_type(source=source, key=key)
        )
        raise _ContractViolation(
            code=code,
            reason=f"The '{label}' field must be a non-empty string.",
            field=field,
            affected_ids=self.__owner(owner_id=owner_id),
        )

    def __absence_or_type(self, source: dict[str, Any], key: str) -> OutputProblemCodeEnum:
        """Distingue o campo ausente do campo presente com tipo errado.

        Returns:
            OutputProblemCodeEnum: `missing_field` quando a chave falta; `schema_type` caso contrário.
        """
        if key not in source:
            return OutputProblemCodeEnum.MISSING_FIELD
        return OutputProblemCodeEnum.SCHEMA_TYPE

    def __owner(self, owner_id: Any) -> tuple[str, ...]:
        """Identificador do item dono do campo, quando é um texto utilizável.

        Returns:
            tuple[str, ...]: O identificador, ou vazio quando ele não é conhecido.
        """
        if isinstance(owner_id, str) and owner_id.strip():
            return (owner_id,)
        return ()

    def __item_field(self, container: str, key: str) -> str:
        """Caminho de um campo dentro dos itens de uma lista, como `tasks[].id`.

        Returns:
            str: Caminho do campo.
        """
        return f"{container}{_ITEM_SUFFIX}{_FIELD_SEPARATOR}{key}"

    def __fail(
        self,
        phase: ThinkingPhaseEnum,
        raw_output: str,
        diagnostic: OutputDiagnostic,
        limit: BudgetLimitEnum | None = None,
    ) -> None:
        """Registra e levanta a falha de parsing da fase, com o diagnóstico da recusa.

        Raises:
            PhaseParsingError: Sempre; por padrão, como violação do contrato da fase.
        """
        problem = diagnostic.problem
        self.logger.warning(
            "Saída da fase '%s' recusada pelo parser [%s; sintaxe=%s; contrato=%s; corte=%s]: %s",
            phase.value,
            problem.code.value,
            diagnostic.syntax_status.value if diagnostic.syntax_status is not None else None,
            diagnostic.contract_status.value,
            diagnostic.length_interruption.value,
            problem.reason,
        )
        raise PhaseParsingError(
            phase=phase,
            raw_output=self.__truncate(raw_output=raw_output),
            reason=problem.reason,
            limit=limit,
            diagnostic=diagnostic,
        )

    def __truncate(self, raw_output: str) -> str:
        """Trunca a saída bruta para caber no erro sem inundar o log.

        Returns:
            str: Saída bruta, truncada quando excede o tamanho máximo.
        """
        if len(raw_output) <= _RAW_OUTPUT_MAX_LENGTH:
            return raw_output
        return f"{raw_output[:_RAW_OUTPUT_MAX_LENGTH]}{_TRUNCATION_SUFFIX}"
