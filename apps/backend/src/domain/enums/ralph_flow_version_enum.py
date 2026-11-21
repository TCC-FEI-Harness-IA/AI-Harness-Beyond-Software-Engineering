from enum import IntEnum


class RalphFlowVersionEnum(IntEnum):
    """Versão persistida do fluxo Ralph, que define o significado das fases ambíguas do histórico.

    - `PLANNING_WITHOUT_VALIDATION` (1): A.1 → A.2 → A.3 (aprendizados do enunciado) → B/C. É a
      versão de toda sessão Ralph gravada antes do campo `flow_version`.
    - `VALIDATED_PLANNING` (2): A.1 → A.2 ⇄ A.3 (validação da decomposição) → A.4 (aprendizados do
      enunciado) → B/C. É a versão das sessões Ralph novas.

    A inferência direta não tem versão de fluxo Ralph: suas sessões não adquirem semântica de fases.
    """

    PLANNING_WITHOUT_VALIDATION = 1
    VALIDATED_PLANNING = 2

    @classmethod
    def current(cls) -> "RalphFlowVersionEnum":
        """Versão gravada nas sessões Ralph novas.

        Returns:
            RalphFlowVersionEnum: `VALIDATED_PLANNING`.
        """
        return cls.VALIDATED_PLANNING

    @classmethod
    def legacy(cls) -> "RalphFlowVersionEnum":
        """Versão atribuída a uma sessão Ralph gravada sem o campo de versão.

        Returns:
            RalphFlowVersionEnum: `PLANNING_WITHOUT_VALIDATION`.
        """
        return cls.PLANNING_WITHOUT_VALIDATION
