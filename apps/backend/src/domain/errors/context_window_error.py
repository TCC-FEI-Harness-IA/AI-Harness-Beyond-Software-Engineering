from src.domain.errors.ralph_error import RalphError


class ContextWindowError(RalphError):
    """Levantado quando uma operação inválida é aplicada sobre uma `ContextWindow`."""
