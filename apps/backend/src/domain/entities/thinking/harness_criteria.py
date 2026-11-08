"""Critérios fixos que o harness acrescenta à verificação de uma tarefa (B.2).

São a única definição dos identificadores reservados e das descrições dos critérios que não têm autoria
do planejador: o critério técnico `<task_id>-TECH`, presente em toda tarefa (nova fase de validação — 02),
e o critério de revisão `<task_id>-REV`, presente só numa tarefa revisora (thinking 05). O domínio, o
caso de uso e o parser usam estas funções; nenhum outro ponto monta esses identificadores.
"""
from src.domain.entities.thinking.acceptance_criterion import AcceptanceCriterion

TECHNICAL_CRITERION_SUFFIX = "-TECH"
REVISION_CRITERION_SUFFIX = "-REV"

TECHNICAL_CRITERION_DESCRIPTION = (
    "Technical validity (fixed criterion of the harness): the result accomplishes this task's own objective on a "
    "basis compatible with the data, methods and conditions that apply. Every premise is supplied by the task or "
    "the Key Learnings or explicitly justified, and a hypothesis is not presented as an established fact; "
    "referents, units, conditions and temporal stage are preserved; the method applies under the stated "
    "conditions, and the contributions and conditions relevant to the analysis are taken into account; the "
    "reasoning actually supports the conclusion, beyond the mere presence of an explanation; calculation, text "
    "and conclusion are consistent with each other; and any approximation, hypothesis or best-fit choice has "
    "pertinent support. It covers only this task's objective: it does not require analyses that belong to other "
    "tasks, the final answer format, an external justification that was not requested or an exactness "
    "incompatible with a supported estimate."
)
REVISION_CRITERION_DESCRIPTION = (
    "The revision proposal gives, for each result under review, exactly one verdict (confirmed or superseded) "
    "that the investigation in this result demonstrates: superseded only when it identifies the concrete error "
    "in the reviewed claim, confirmed when the claim withstands the investigation. Recency, a different "
    "hypothesis or a different wording is not evidence for either verdict."
)


def technical_criterion_id(task_id: str) -> str:
    """Identificador reservado ao critério técnico de uma tarefa.

    Args:
        task_id: Identificador da tarefa.

    Returns:
        str: `<task_id>-TECH`.
    """
    return f"{task_id}{TECHNICAL_CRITERION_SUFFIX}"


def revision_criterion_id(task_id: str) -> str:
    """Identificador reservado ao critério de revisão de uma tarefa revisora.

    Args:
        task_id: Identificador da tarefa.

    Returns:
        str: `<task_id>-REV`.
    """
    return f"{task_id}{REVISION_CRITERION_SUFFIX}"


def technical_criterion(task_id: str) -> AcceptanceCriterion:
    """Critério técnico fixo com que B.2 avalia a validade da resolução de qualquer tarefa.

    Args:
        task_id: Identificador da tarefa.

    Returns:
        AcceptanceCriterion: Critério `<task_id>-TECH`, com a mesma descrição para toda tarefa.
    """
    return AcceptanceCriterion(id=technical_criterion_id(task_id), description=TECHNICAL_CRITERION_DESCRIPTION)


def revision_criterion(task_id: str) -> AcceptanceCriterion:
    """Critério com que B.2 avalia explicitamente a proposta de revisão de uma tarefa revisora.

    Args:
        task_id: Identificador da tarefa.

    Returns:
        AcceptanceCriterion: Critério `<task_id>-REV`.
    """
    return AcceptanceCriterion(id=revision_criterion_id(task_id), description=REVISION_CRITERION_DESCRIPTION)
