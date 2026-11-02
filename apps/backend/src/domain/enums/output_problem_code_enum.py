from enum import StrEnum


class OutputProblemCodeEnum(StrEnum):
    """Enum dos códigos de problema que levam o parser a recusar uma saída do modelo.

    Attributes:
        JSON_SYNTAX: Nenhum objeto JSON pôde ser extraído da saída, nem com reparo local.
        UNSUPPORTED_PHASE: A fase não produz saída estruturada.
        MISSING_FIELD: Campo obrigatório ausente.
        SCHEMA_TYPE: Campo presente, mas com tipo diferente do exigido.
        EMPTY_VALUE: Texto em branco ou lista vazia onde o contrato exige conteúdo.
        INVALID_VALUE: Valor do tipo certo fora do domínio aceito (por exemplo, um veredito desconhecido).
        DUPLICATE_ID: Identificador repetido onde deveria ser único.
        CRITERIA_IDS: Avaliações que não cobrem exatamente os critérios esperados.
        DECISION_CONSISTENCY: Decisão, avaliações e pendências que se contradizem.
        TASK_IDS: Identificador de tarefa já usado na sessão.
        TASK_LIMIT: Lote de tarefas acima do teto que a sessão comporta.
        UNCLASSIFIED: Recusa sem classificação estruturada informada pelo parser.
    """

    JSON_SYNTAX = "json_syntax"
    UNSUPPORTED_PHASE = "unsupported_phase"
    MISSING_FIELD = "missing_field"
    SCHEMA_TYPE = "schema_type"
    EMPTY_VALUE = "empty_value"
    INVALID_VALUE = "invalid_value"
    DUPLICATE_ID = "duplicate_id"
    CRITERIA_IDS = "criteria_ids"
    DECISION_CONSISTENCY = "decision_consistency"
    TASK_IDS = "task_ids"
    TASK_LIMIT = "task_limit"
    UNCLASSIFIED = "unclassified"
