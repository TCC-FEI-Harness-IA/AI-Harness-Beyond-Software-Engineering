from dataclasses import dataclass

from src.domain.entities.session.session_message import SessionMessage


@dataclass
class SessionTotals:
    """Agrega os totais acumulados de uma sessão.

    Chamadas, tokens e tempo de inferência vêm exclusivamente das invocações ao modelo; as
    mensagens do histórico só são contadas como mensagens, porque o consumo que carregam é
    uma agregação para exibição e somá-lo também aqui o contaria duas vezes.

    Attributes:
        total_messages: Quantidade de mensagens registradas na sessão.
        total_llm_calls: Quantidade de chamadas ao modelo enviadas na sessão.
        tokens_input: Tokens de entrada conhecidos, acumulados na sessão.
        tokens_output: Tokens de saída conhecidos, acumulados na sessão.
        inference_time_ms: Soma do tempo das chamadas ao modelo, em milissegundos.
        wall_time_ms: Tempo de parede da sessão inteira, em milissegundos.
    """

    total_messages: int = 0
    total_llm_calls: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    inference_time_ms: int = 0
    wall_time_ms: int = 0

    @property
    def total_tokens(self) -> int:
        """Total de tokens consumidos pela sessão.

        Returns:
            int: Soma de `tokens_input` e `tokens_output`.
        """
        return self.tokens_input + self.tokens_output

    def add_message(self, message: SessionMessage) -> None:
        """Conta uma mensagem registrada na sessão, sem somar o consumo que ela exibe.

        Args:
            message: Mensagem recém-registrada na sessão.
        """
        self.total_messages += 1

    def register_invocation_start(self) -> None:
        """Conta uma chamada ao modelo no momento em que ela é enviada."""
        self.total_llm_calls += 1

    def add_usage(self, tokens_input: int | None, tokens_output: int | None, duration_ms: int) -> None:
        """Acumula o consumo conhecido de uma invocação concluída.

        Args:
            tokens_input: Tokens de entrada informados, ou `None` se desconhecidos.
            tokens_output: Tokens de saída informados, ou `None` se desconhecidos.
            duration_ms: Duração da chamada, em milissegundos.
        """
        self.tokens_input += tokens_input or 0
        self.tokens_output += tokens_output or 0
        self.inference_time_ms += duration_ms
