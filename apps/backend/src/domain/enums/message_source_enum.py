from enum import StrEnum


class MessageSourceEnum(StrEnum):
    """Enum das origens de mensagens suportadas no domínio."""

    USER = "user"
    LLM_AGENT = "llm_agent"
