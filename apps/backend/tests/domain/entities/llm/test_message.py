from datetime import UTC, datetime

from src.domain.entities.llm.message import Message
from src.domain.enums.message_source_enum import MessageSourceEnum


def test_carrega_conteudo_origem_e_timestamp() -> None:
    momento = datetime.now(tz=UTC)

    message = Message(creation_timestamp=momento, text="olá", source=MessageSourceEnum.USER)

    assert message.creation_timestamp is momento
    assert message.text == "olá"
    assert message.source is MessageSourceEnum.USER
