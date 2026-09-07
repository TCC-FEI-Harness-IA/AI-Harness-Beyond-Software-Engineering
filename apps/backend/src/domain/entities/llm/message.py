
from dataclasses import dataclass
from datetime import datetime

from src.domain.enums.message_source_enum import MessageSourceEnum


@dataclass
class Message:
    """Representa a entidade base de mensagem no domínio.

    Attributes:
        creation_timestamp: Data e hora de criação da mensagem em UTC.
        text: Conteúdo textual da mensagem.
        source: Origem da mensagem.
    """

    creation_timestamp: datetime
    text: str
    source: MessageSourceEnum
