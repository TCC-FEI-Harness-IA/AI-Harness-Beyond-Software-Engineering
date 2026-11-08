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
from src.domain.enums.revision_verdict_enum import RevisionVerdictEnum
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
_REVISION_CRITERION_SUFFIX = "-REV"
_ABSENT_REVISIONS = (None, [])


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
            ThinkingPhaseEnum.A3_DECOMPOSITION_VALIDATION: self.__validate_plan_validation,
            ThinkingPhaseEnum.A4_PLANNING_LEARNINGS: self.__validate_learnings,
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
            self.__validate_task_links(task=task)

        self.__require_unique_ids(
            ids=[task["id"] for task in tasks], what="batch tasks", field=self.__item_field("tasks", "id")
        )
        self.__validate_batch_against_session(tasks=tasks, validation=validation)
        self.__validate_task_references(tasks=tasks, validation=validation)

    def __validate_task_links(self, task: dict[str, Any]) -> None:
        """Valida a forma dos campos opcionais `depends_on` e `review` de uma tarefa planejada.

        A ausência (ou `null`) dos dois campos mantém o contrato de uma tarefa normal. Nada é
        inferido do título ou da descrição: só estes campos estruturados mudam o estado da sessão.

        Raises:
            _ContractViolation: Quando `depends_on` não é uma lista de identificadores únicos; quando
                `review` não é um objeto com `task_ids` não vazio e sem repetição e `reason` preenchido;
                ou quando um critério planejado usa o identificador reservado ao critério de revisão.
        """
        owner = task["id"]
        if task.get("depends_on") is not None:
            self.__require_id_list(
                source=task, key="depends_on", label="depends_on", allow_empty=True,
                field=self.__item_field("tasks", "depends_on"), owner_id=owner, what=f"dependencies of task '{owner}'",
            )

        review = task.get("review")
        if review is None:
            return
        if not isinstance(review, dict):
            raise _ContractViolation(
                code=OutputProblemCodeEnum.SCHEMA_TYPE,
                reason="The 'review' field must be an object with 'task_ids' and 'reason'.",
                field=self.__item_field("tasks", "review"),
                affected_ids=(owner,),
            )
        review_field = self.__item_field("tasks", "review")
        self.__require_id_list(
            source=review, key="task_ids", label="review.task_ids", allow_empty=False,
            field=f"{review_field}{_FIELD_SEPARATOR}task_ids", owner_id=owner, what=f"review targets of task '{owner}'",
        )
        self.__require_text(
            source=review, key="reason", label="review.reason", field=f"{review_field}{_FIELD_SEPARATOR}reason",
            owner_id=owner,
        )
        reserved = f"{owner}{_REVISION_CRITERION_SUFFIX}"
        if any(criterion["id"] == reserved for criterion in task["acceptance_criteria"]):
            raise _ContractViolation(
                code=OutputProblemCodeEnum.INVALID_VALUE,
                reason=(
                    f"The criterion identifier '{reserved}' is reserved for the revision verdict of a reviewing task."
                ),
                field=self.__item_field("tasks", "acceptance_criteria[].id"),
                affected_ids=(reserved,),
            )

    def __validate_task_references(
        self, tasks: list[dict[str, Any]], validation: ValidationContext | None
    ) -> None:
        """Confronta as revisões e dependências do lote com o que a sessão pode honrar.

        Uma revisão só aponta resultados armazenados vigentes ou em revalidação, nunca a própria
        tarefa nem outra do lote, e cada resultado é revisado por no máximo uma tarefa do lote. Uma
        dependência aponta uma tarefa anterior do lote ou um resultado vigente: como só se depende do
        que vem antes, não há ciclo possível.

        Raises:
            _ContractViolation: Quando alguma referência é inexistente, fora do escopo, autorreferente,
                futura no lote ou repetida entre tarefas.
        """
        context = validation or ValidationContext()
        batch_ids = [task["id"] for task in tasks]
        reviewed_by: dict[str, str] = {}
        for position, task in enumerate(tasks):
            owner = task["id"]
            targets = (task.get("review") or {}).get("task_ids", [])
            for target in targets:
                self.__require_reviewable(owner=owner, target=target, batch_ids=batch_ids, context=context)
                if target in reviewed_by:
                    raise _ContractViolation(
                        code=OutputProblemCodeEnum.DUPLICATE_ID,
                        reason=(
                            f"The result '{target}' is reviewed by more than one task in the batch "
                            f"('{reviewed_by[target]}' and '{owner}'). Plan a single investigation for it."
                        ),
                        field=self.__item_field("tasks", "review.task_ids"),
                        affected_ids=(target,),
                    )
                reviewed_by[target] = owner
            for dependency in task.get("depends_on") or []:
                self.__require_dependable(
                    owner=owner, dependency=dependency, targets=targets, earlier=batch_ids[:position],
                    batch_ids=batch_ids, context=context,
                )

    def __require_reviewable(
        self, owner: str, target: str, batch_ids: list[str], context: ValidationContext
    ) -> None:
        """Exige que o alvo de uma revisão seja um resultado armazenado que ainda pode ser revisado.

        Raises:
            _ContractViolation: Quando o alvo é a própria tarefa, outra tarefa do lote, um resultado
                já substituído (ou ainda não armazenado) ou um identificador inexistente.
        """
        if target in context.reviewable_task_ids:
            return
        if target == owner:
            reason = f"Task '{owner}' cannot review itself."
        elif target in batch_ids:
            reason = (
                f"Task '{owner}' cannot review '{target}': that task belongs to this batch and has not been executed."
            )
        elif target in context.known_task_ids:
            reason = (
                f"The result '{target}' cannot be reviewed: it is not a stored result that is current or awaiting "
                "revalidation."
            )
        else:
            reason = f"The task '{target}' reviewed by '{owner}' does not exist in the session."
        raise _ContractViolation(
            code=OutputProblemCodeEnum.TASK_REFERENCES, reason=reason,
            field=self.__item_field("tasks", "review.task_ids"), affected_ids=(target,),
        )

    def __require_dependable(
        self,
        owner: str,
        dependency: str,
        targets: list[str],
        earlier: list[str],
        batch_ids: list[str],
        context: ValidationContext,
    ) -> None:
        """Exige que uma dependência aponte uma tarefa anterior do lote ou um resultado vigente.

        Raises:
            _ContractViolation: Quando a dependência é a própria tarefa, um resultado que ela revisa,
                uma tarefa posterior do lote, um resultado não vigente ou um identificador inexistente.
        """
        if dependency == owner:
            reason = f"Task '{owner}' cannot depend on itself."
        elif dependency in targets:
            reason = f"Task '{owner}' cannot depend on a result it reviews ('{dependency}')."
        elif dependency in earlier or dependency in context.dependable_task_ids:
            return
        elif dependency in batch_ids:
            reason = (
                f"Task '{owner}' depends on '{dependency}', a later task of this batch. Order the tasks so that each "
                "dependency comes first; a later or cyclic dependency is not allowed."
            )
        elif dependency in context.known_task_ids:
            reason = f"Task '{owner}' depends on '{dependency}', which is not a current result."
        else:
            reason = f"The task '{dependency}' on which '{owner}' depends does not exist in the session."
        raise _ContractViolation(
            code=OutputProblemCodeEnum.TASK_REFERENCES, reason=reason,
            field=self.__item_field("tasks", "depends_on"), affected_ids=(dependency,),
        )

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
        """Valida o schema de B.1 e, numa tarefa revisora, a proposta de revisão.

        Uma tarefa normal não propõe revisão: o campo `revision` ausente, nulo ou vazio é aceito; uma
        proposta preenchida é recusada. Uma tarefa revisora precisa de exatamente um veredito por
        resultado sob investigação.

        Raises:
            _ContractViolation: Quando 'result' ou 'conclusion' não é uma string não vazia, ou quando a
                proposta de revisão falta, sobra ou não cobre exatamente os resultados sob investigação.
        """
        self.__require_text(source=parsed, key="result", label="result", field="result")
        self.__require_text(source=parsed, key="conclusion", label="conclusion", field="conclusion")
        targets = validation.review_target_ids if validation is not None else None
        if targets is None:
            if parsed.get("revision") not in _ABSENT_REVISIONS:
                raise _ContractViolation(
                    code=OutputProblemCodeEnum.TASK_REFERENCES,
                    reason="This task does not review stored results; remove the 'revision' field.",
                    field="revision",
                )
            return
        self.__validate_revision(parsed=parsed, targets=targets)

    def __validate_revision(self, parsed: dict[str, Any], targets: tuple[str, ...]) -> None:
        """Valida a proposta de revisão de uma tarefa revisora contra os resultados sob investigação.

        Raises:
            _ContractViolation: Quando a proposta não é uma lista de vereditos completos e conhecidos,
                repete um alvo, traz um alvo fora da revisão ou omite um resultado sob investigação.
        """
        verdicts = self.__require_list(source=parsed, key="revision", label="revision", allow_empty=False)
        for verdict in verdicts:
            if not isinstance(verdict, dict):
                raise _ContractViolation(
                    code=OutputProblemCodeEnum.SCHEMA_TYPE,
                    reason="Each item of 'revision' must be an object.",
                    field=f"revision{_ITEM_SUFFIX}",
                )
            self.__require_text(
                source=verdict, key="task_id", label="revision.task_id", field=self.__item_field("revision", "task_id")
            )
            owner = verdict["task_id"]
            self.__require_choice(
                source=verdict, key="verdict", choices=tuple(RevisionVerdictEnum),
                reason=f"The 'verdict' field must be 'confirmed' or 'superseded'. Value: '{verdict.get('verdict')}'.",
                field=self.__item_field("revision", "verdict"), affected_ids=(owner,),
            )
            self.__require_text(
                source=verdict, key="justification", label="revision.justification",
                field=self.__item_field("revision", "justification"), owner_id=owner,
            )

        reviewed = [verdict["task_id"] for verdict in verdicts]
        field = self.__item_field("revision", "task_id")
        self.__require_unique_ids(ids=reviewed, what="revision verdicts", field=field)
        extra = [task_id for task_id in reviewed if task_id not in targets]
        missing = [task_id for task_id in targets if task_id not in reviewed]
        for ids, reason in (
            (extra, "The revision has verdicts for results that this task does not review: {ids}."),
            (missing, "The revision lacks a verdict for the results under review: {ids}."),
        ):
            if ids:
                raise _ContractViolation(
                    code=OutputProblemCodeEnum.TASK_REFERENCES,
                    reason=reason.format(ids=_ID_LIST_SEPARATOR.join(ids)),
                    field=field,
                    affected_ids=tuple(ids),
                )

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

    def __validate_plan_validation(
        self, parsed: dict[str, Any], phase: ThinkingPhaseEnum, validation: ValidationContext | None
    ) -> None:
        """Valida o relatório de A.3 contra o plano candidato julgado.

        A decisão é um booleano real; cada problema traz `task_id` e `criterion_id` (obrigatórios no
        objeto, nulos conforme o escopo), `problem` e `adjustment`. Uma reprovação coerente é aceita
        como qualquer aprovação. Nada aqui julga se o plano é bom: só tipos, referências e coerência.

        Raises:
            _ContractViolation: Quando o schema não confere, a decisão contradiz os problemas ou uma
                referência não existe no candidato julgado.
            ValueError: Quando o contexto de validação não traz a referência estrutural do candidato.
        """
        if validation is None or validation.candidate_plan is None:
            raise ValueError(f"A fase '{phase.value}' exige a referência estrutural do plano candidato.")

        approved = parsed.get("approved")
        if not isinstance(approved, bool):
            raise _ContractViolation(
                code=self.__absence_or_type(source=parsed, key="approved"),
                reason="The 'approved' field must be a JSON boolean (true or false), not a string or number.",
                field="approved",
            )
        issues = self.__require_list(source=parsed, key="issues", label="issues", allow_empty=True)
        for issue in issues:
            self.__validate_plan_issue(issue=issue, plan=validation.candidate_plan)

        if approved and issues:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.DECISION_CONSISTENCY,
                reason="An approved plan cannot have pending issues: approving requires 'issues': [].",
                field="approved",
            )
        if not approved and not issues:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.DECISION_CONSISTENCY,
                reason="A rejected plan requires at least one concrete issue in 'issues'.",
                field="approved",
            )

    def __validate_plan_issue(self, issue: Any, plan: dict[str, tuple[str, ...]]) -> None:
        """Valida um problema do relatório de A.3 e as suas referências ao candidato julgado.

        Raises:
            _ContractViolation: Quando o problema não é um objeto completo, um texto está em branco, uma
                referência não é texto nem nula, ou aponta tarefa ou critério que o candidato não tem.
        """
        container = "issues"
        if not isinstance(issue, dict):
            raise _ContractViolation(
                code=OutputProblemCodeEnum.SCHEMA_TYPE,
                reason="Each item of 'issues' must be an object.",
                field=f"{container}{_ITEM_SUFFIX}",
            )
        for key in ("task_id", "criterion_id"):
            self.__require_nullable_reference(source=issue, key=key, field=self.__item_field(container, key))
        for key in ("problem", "adjustment"):
            self.__require_text(
                source=issue, key=key, label=f"issues.{key}", field=self.__item_field(container, key),
                owner_id=issue.get("task_id"),
            )

        task_id = issue["task_id"]
        criterion_id = issue["criterion_id"]
        if task_id is None:
            if criterion_id is not None:
                raise _ContractViolation(
                    code=OutputProblemCodeEnum.TASK_REFERENCES,
                    reason=(
                        f"The criterion '{criterion_id}' is referenced without its task: fill 'task_id' with the "
                        "task that owns the criterion, or set both references to null for a plan-wide issue."
                    ),
                    field=self.__item_field(container, "task_id"),
                    affected_ids=(criterion_id,),
                )
            return
        if task_id not in plan:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.TASK_REFERENCES,
                reason=(
                    f"The task '{task_id}' does not exist in the candidate plan. "
                    f"Reference only: {_ID_LIST_SEPARATOR.join(plan)}; or null for a plan-wide issue."
                ),
                field=self.__item_field(container, "task_id"),
                affected_ids=(task_id,),
            )
        if criterion_id is not None and criterion_id not in plan[task_id]:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.CRITERIA_IDS,
                reason=(
                    f"The criterion '{criterion_id}' does not belong to task '{task_id}' in the candidate plan. "
                    f"Criteria of '{task_id}': {_ID_LIST_SEPARATOR.join(plan[task_id])}; or null for a task-wide issue."
                ),
                field=self.__item_field(container, "criterion_id"),
                affected_ids=(criterion_id,),
            )

    def __require_nullable_reference(self, source: dict[str, Any], key: str, field: str) -> None:
        """Exige uma referência presente no objeto: `null` ou um identificador preenchido.

        Raises:
            _ContractViolation: Quando a chave falta, o valor não é texto nem nulo, ou é texto em branco.
        """
        if key not in source:
            raise _ContractViolation(
                code=OutputProblemCodeEnum.MISSING_FIELD,
                reason=f"The '{key}' field is required in every issue; use null when it does not apply.",
                field=field,
            )
        value = source[key]
        if value is None:
            return
        if not isinstance(value, str):
            raise _ContractViolation(
                code=OutputProblemCodeEnum.SCHEMA_TYPE,
                reason=f"The '{key}' field must be an identifier string or null.",
                field=field,
            )
        if not value.strip():
            raise _ContractViolation(
                code=OutputProblemCodeEnum.EMPTY_VALUE,
                reason=f"The '{key}' field must be a non-empty identifier or null.",
                field=field,
            )

    def __require_decision(self, parsed: dict[str, Any]) -> str:
        """Exige um veredito conhecido no campo 'decision', sem converter valores por suposição.

        Returns:
            str: Veredito informado.

        Raises:
            _ContractViolation: Quando o campo falta, não é string ou não é um veredito conhecido.
        """
        decision = parsed.get("decision")
        self.__require_choice(
            source=parsed, key="decision", choices=tuple(VerificationDecisionEnum),
            reason=f"The 'decision' field must be a known verdict. Value: '{decision}'.", field="decision",
        )
        return decision

    def __require_choice(
        self,
        source: dict[str, Any],
        key: str,
        choices: tuple[str, ...],
        reason: str,
        field: str,
        affected_ids: tuple[str, ...] = (),
    ) -> None:
        """Exige um valor conhecido num campo, sem converter valores por suposição.

        Raises:
            _ContractViolation: Quando o campo falta, não é string ou não é um dos valores aceitos.
        """
        value = source.get(key)
        if value in choices:
            return

        if key not in source:
            code = OutputProblemCodeEnum.MISSING_FIELD
        elif not isinstance(value, str):
            code = OutputProblemCodeEnum.SCHEMA_TYPE
        else:
            code = OutputProblemCodeEnum.INVALID_VALUE
        raise _ContractViolation(code=code, reason=reason, field=field, affected_ids=affected_ids)

    def __require_id_list(
        self,
        source: dict[str, Any],
        key: str,
        label: str,
        allow_empty: bool,
        field: str,
        owner_id: str,
        what: str,
    ) -> None:
        """Exige uma lista de identificadores de tarefa preenchidos e sem repetição.

        Raises:
            _ContractViolation: Quando o campo não é lista, está indevidamente vazio, tem item que não é
                texto preenchido ou repete um identificador.
        """
        ids = self.__require_list(
            source=source, key=key, label=label, allow_empty=allow_empty, field=field, owner_id=owner_id
        )
        for identifier in ids:
            if not isinstance(identifier, str) or not identifier.strip():
                raise _ContractViolation(
                    code=OutputProblemCodeEnum.SCHEMA_TYPE,
                    reason=f"Each item of '{label}' must be a non-empty string.",
                    field=f"{field}{_ITEM_SUFFIX}",
                    affected_ids=(owner_id,),
                )
        self.__require_unique_ids(ids=ids, what=what, field=field)

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
        """Valida o schema de A.4 e B.4, onde a lista vazia é legítima.

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
