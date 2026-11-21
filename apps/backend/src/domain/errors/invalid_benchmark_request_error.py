from src.domain.errors.ralph_error import RalphError


class InvalidBenchmarkRequestError(RalphError):
    """Levantado quando os parâmetros de uma bateria não podem ser atendidos.

    Por exemplo: mais questões do que o dataset tem, ou mais questões em paralelo que o limite.
    """
