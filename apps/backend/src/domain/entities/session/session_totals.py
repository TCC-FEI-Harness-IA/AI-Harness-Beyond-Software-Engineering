from dataclasses import dataclass

from src.domain.entities.session.session_message import SessionMessage


@dataclass
class SessionTotals:
    """Agrega os totais acumulados de uma sessão.

    Attributes:
        total_messages: Quantidade de mensagens registradas na sessão.
        total_llm_calls: Quantidade de chamadas ao modelo realizadas na sessão.
        tokens_input: Tokens de entrada acumulados na sessão.
        tokens_output: Tokens de saída acumulados na sessão.
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
        """Acumula os totais referentes a uma mensagem registrada.

        Args:
            message: Mensagem recém-registrada na sessão.
        """
        self.total_messages += 1
        self.tokens_input += message.tokens_input
        self.tokens_output += message.tokens_output
        self.inference_time_ms += message.inference_time_ms

        if message.total_tokens > 0:
            self.total_llm_calls += 1
