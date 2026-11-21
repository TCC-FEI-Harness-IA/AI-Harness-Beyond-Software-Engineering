import re

_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
OWNER_KEY = "owner_id"


def validate_owner_id(owner_id: str) -> str:
    """Valida o proprietário de um repositório escopado.

    O proprietário vira diretório (JSON) e prefixo de chave (MongoDB): só letras, dígitos, `_` e `-`.

    Raises:
        ValueError: Quando o identificador está vazio ou tem caracteres não permitidos.
    """
    if not _OWNER_PATTERN.fullmatch(owner_id):
        raise ValueError(f"Proprietário inválido: '{owner_id}'.")
    return owner_id


def scoped_key(owner_id: str, identifier: str) -> str:
    """Chave primária de um documento no MongoDB: `<proprietário>/<identificador>`.

    Qualificar a chave pelo dono impede colisões entre contas (dois usuários podem ter o mesmo
    identificador) e deixa documentos legados, sem dono, fora de qualquer consulta.
    """
    return f"{owner_id}/{identifier}"
