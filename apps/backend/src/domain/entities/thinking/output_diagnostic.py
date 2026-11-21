from dataclasses import dataclass

from src.domain.entities.thinking.output_problem import OutputProblem
from src.domain.enums.length_interruption_enum import LengthInterruptionEnum
from src.domain.enums.output_contract_status_enum import OutputContractStatusEnum
from src.domain.enums.output_problem_code_enum import OutputProblemCodeEnum
from src.domain.enums.output_syntax_status_enum import OutputSyntaxStatusEnum

_PARSEABLE_SYNTAX = frozenset({OutputSyntaxStatusEnum.VALID, OutputSyntaxStatusEnum.REPAIRED})


@dataclass(frozen=True)
class OutputDiagnostic:
    """Diagnóstico estruturado de uma saída do modelo avaliada pelo parser.

    Separa três informações independentes: a sintaxe (havia um objeto JSON, talvez após reparo
    local?), o contrato da fase (schema e coerência) e a interrupção por comprimento. Uma saída pode
    estar truncada e ter sintaxe inválida, ou terminar com `length` e formar JSON válido; o corte
    não decide a aceitação. O conteúdo é aceito só quando o contrato é válido.

    Attributes:
        syntax_status: Estado da extração/sintaxe; `None` quando a sintaxe não chegou a ser avaliada
            (fase sem saída estruturada ou recusa sem classificação).
        contract_status: Estado do contrato da fase; não avaliado quando não há objeto JSON.
        finish_reason: Motivo de término original informado pelo provedor, quando há.
        length_interruption: Confirmação, indício ou ausência de corte por comprimento.
        problem: Problema que motivou a recusa; `None` na saída aceita.
        repaired_closings: Fechamentos acrescentados pelo reparo local, quando houve.
    """

    syntax_status: OutputSyntaxStatusEnum | None
    contract_status: OutputContractStatusEnum
    finish_reason: str | None
    length_interruption: LengthInterruptionEnum
    problem: OutputProblem | None = None
    repaired_closings: str | None = None

    def __post_init__(self) -> None:
        """Recusa combinações contraditórias de sintaxe, contrato, problema e reparo.

        Raises:
            ValueError: Quando o diagnóstico se contradiz.
        """
        parseable = self.syntax_status in _PARSEABLE_SYNTAX
        not_evaluated = self.contract_status is OutputContractStatusEnum.NOT_EVALUATED
        if parseable == not_evaluated:
            raise ValueError(
                "O contrato fica não avaliado exatamente quando não há objeto JSON: "
                f"sintaxe '{self.syntax_status}', contrato '{self.contract_status.value}'."
            )
        if (self.contract_status is OutputContractStatusEnum.VALID) != (self.problem is None):
            raise ValueError("Uma saída aceita não tem problema; uma saída recusada exige um problema.")
        syntax_problem = self.problem is not None and self.problem.code is OutputProblemCodeEnum.JSON_SYNTAX
        if (self.syntax_status is OutputSyntaxStatusEnum.INVALID) != syntax_problem:
            raise ValueError("O código 'json_syntax' corresponde exatamente à sintaxe inválida.")
        if (self.syntax_status is OutputSyntaxStatusEnum.REPAIRED) != bool(self.repaired_closings):
            raise ValueError("Os fechamentos reparados existem exatamente quando a sintaxe é válida após reparo.")

    @property
    def content_accepted(self) -> bool:
        """Informa se o conteúdo foi aceito pelo parser.

        Returns:
            bool: `True` quando o contrato da fase é válido.
        """
        return self.contract_status is OutputContractStatusEnum.VALID

    @classmethod
    def accepted(
        cls,
        finish_reason: str | None,
        length_interruption: LengthInterruptionEnum,
        repaired_closings: str | None = None,
    ) -> "OutputDiagnostic":
        """Monta o diagnóstico de uma saída aceita, com ou sem reparo local.

        Args:
            finish_reason: Motivo de término original informado pelo provedor.
            length_interruption: Confirmação, indício ou ausência de corte por comprimento.
            repaired_closings: Fechamentos acrescentados pelo reparo local, quando houve.

        Returns:
            OutputDiagnostic: Diagnóstico com contrato válido e sem problema.
        """
        return cls(
            syntax_status=OutputSyntaxStatusEnum.REPAIRED if repaired_closings else OutputSyntaxStatusEnum.VALID,
            contract_status=OutputContractStatusEnum.VALID,
            finish_reason=finish_reason,
            length_interruption=length_interruption,
            repaired_closings=repaired_closings or None,
        )

    @classmethod
    def unclassified(cls, reason: str, finish_reason: str | None) -> "OutputDiagnostic":
        """Monta o diagnóstico de uma recusa que o parser não classificou.

        Nada é presumido: a sintaxe fica desconhecida, o contrato não avaliado e o corte é derivado
        só do motivo de término, sem indício estrutural.

        Args:
            reason: Motivo legível da recusa.
            finish_reason: Motivo de término original informado pelo provedor.

        Returns:
            OutputDiagnostic: Diagnóstico de recusa com o código `unclassified`.
        """
        return cls(
            syntax_status=None,
            contract_status=OutputContractStatusEnum.NOT_EVALUATED,
            finish_reason=finish_reason,
            length_interruption=LengthInterruptionEnum.classify(finish_reason=finish_reason, ends_incomplete=False),
            problem=OutputProblem(code=OutputProblemCodeEnum.UNCLASSIFIED, reason=reason),
        )
