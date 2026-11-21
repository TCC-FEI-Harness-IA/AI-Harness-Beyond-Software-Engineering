from enum import StrEnum


class SessionStorageBackendEnum(StrEnum):
    """Enum dos backends suportados para persistência de sessões."""

    JSON_FILE = "json_file"
    MONGODB = "mongodb"
