from enum import StrEnum


class BenchmarkInferenceModeEnum(StrEnum):
    """Fluxo executado para uma questão do benchmark."""

    SIMPLE = "simple"
    RALPH = "ralph"
