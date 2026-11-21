from datetime import UTC, datetime


def as_utc(value: datetime) -> datetime:
    """Garante fuso UTC em datas lidas do MongoDB (o driver devolve datas sem fuso por padrão)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
