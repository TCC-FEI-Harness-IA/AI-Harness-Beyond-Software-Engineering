from src.domain.interfaces.id_generator_interface import IIdGenerator


class FakeIdGenerator(IIdGenerator):
    """Dublê de `IIdGenerator` com identificadores determinísticos e sequenciais."""

    def __init__(self, session_prefix: str = "sess") -> None:
        """Configura o dublê.

        Args:
            session_prefix: Prefixo aplicado aos identificadores de sessão.
        """
        self.session_prefix = session_prefix
        self.session_ids: list[str] = []
        self.message_ids: list[str] = []
        self.context_ids: list[str] = []
        self.invocation_ids: list[str] = []
        self.benchmark_session_ids: list[str] = []

    def new_session_id(self) -> str:
        """Devolve o próximo identificador de sessão da sequência."""
        self.session_ids.append(f"{self.session_prefix}_{len(self.session_ids) + 1}")
        return self.session_ids[-1]

    def new_message_id(self) -> str:
        """Devolve o próximo identificador de mensagem da sequência."""
        self.message_ids.append(f"msg_{len(self.message_ids) + 1}")
        return self.message_ids[-1]

    def new_context_id(self) -> str:
        """Devolve o próximo identificador de janela de contexto da sequência."""
        self.context_ids.append(f"ctx_{len(self.context_ids) + 1}")
        return self.context_ids[-1]

    def new_invocation_id(self) -> str:
        """Devolve o próximo identificador de invocação da sequência."""
        self.invocation_ids.append(f"inv_{len(self.invocation_ids) + 1}")
        return self.invocation_ids[-1]

    def new_benchmark_session_id(self) -> str:
        """Devolve o próximo identificador de bateria de benchmark da sequência."""
        self.benchmark_session_ids.append(f"bench_{len(self.benchmark_session_ids) + 1}")
        return self.benchmark_session_ids[-1]
