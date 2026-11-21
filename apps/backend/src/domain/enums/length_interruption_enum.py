from enum import StrEnum

# Motivo de término com que o provedor confirma que a geração parou no limite de tokens de saída.
_LENGTH_FINISH_REASON = "length"


class LengthInterruptionEnum(StrEnum):
    """Enum da interrupção da saída por limite de comprimento, independente da sintaxe.

    Só o provedor confirma um corte; sem o motivo de término, uma saída que termina no meio de uma
    string ou com estruturas abertas é apenas um indício. Um corte confirmado não implica sintaxe
    inválida: o modelo pode ter fechado o JSON exatamente no limite, sem garantia de completude.

    Attributes:
        CONFIRMED: O provedor informou `finish_reason == "length"`.
        SUSPECTED: Sem motivo de término, mas a saída termina estruturalmente incompleta.
        NOT_DETECTED: O provedor informou outro motivo de término.
        UNKNOWN: Sem motivo de término e sem indício de corte.
    """

    CONFIRMED = "confirmed"
    SUSPECTED = "suspected"
    NOT_DETECTED = "not_detected"
    UNKNOWN = "unknown"

    @classmethod
    def classify(cls, finish_reason: str | None, ends_incomplete: bool) -> "LengthInterruptionEnum":
        """Classifica a interrupção a partir do motivo de término e do indício estrutural.

        Args:
            finish_reason: Motivo de término informado pelo provedor, ou `None` quando não informado.
            ends_incomplete: Indica que a saída termina dentro de uma string ou com estruturas abertas.

        Returns:
            LengthInterruptionEnum: Confirmação do provedor, indício ou ausência dele.
        """
        if finish_reason == _LENGTH_FINISH_REASON:
            return cls.CONFIRMED
        if finish_reason is not None:
            return cls.NOT_DETECTED
        if ends_incomplete:
            return cls.SUSPECTED
        return cls.UNKNOWN
