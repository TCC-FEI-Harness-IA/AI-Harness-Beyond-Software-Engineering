from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum


def test_declara_exatamente_os_backends_suportados() -> None:
    assert {member.value for member in SessionStorageBackendEnum} == {"json_file", "mongodb"}


def test_valor_dos_membros() -> None:
    assert SessionStorageBackendEnum.JSON_FILE == "json_file"
    assert SessionStorageBackendEnum.MONGODB == "mongodb"


def test_e_uma_str_enum() -> None:
    assert isinstance(SessionStorageBackendEnum.JSON_FILE, str)
