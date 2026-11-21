import pytest

from src.infra.adapters.argon2_password_hasher import Argon2PasswordHasher

# Parâmetros baixos só para a suíte ficar rápida; o algoritmo e a biblioteca são os reais.
_RAPIDO = {"time_cost": 1, "memory_cost_kib": 8, "parallelism": 1}


def test_hash_e_argon2id_e_nao_contem_a_senha() -> None:
    hasher = Argon2PasswordHasher(**_RAPIDO)

    hashed = hasher.hash("senha secreta 123")

    assert hashed.startswith("$argon2id$")
    assert "senha secreta 123" not in hashed


def test_hashes_da_mesma_senha_usam_sal_diferente() -> None:
    hasher = Argon2PasswordHasher(**_RAPIDO)

    assert hasher.hash("mesma senha!!") != hasher.hash("mesma senha!!")


def test_verifica_senha_correta_e_recusa_errada() -> None:
    hasher = Argon2PasswordHasher(**_RAPIDO)
    hashed = hasher.hash("senha correta 1")

    assert hasher.verify(hashed, "senha correta 1") is True
    assert hasher.verify(hashed, "senha errada 1") is False


def test_hash_malformado_nunca_autentica() -> None:
    assert Argon2PasswordHasher(**_RAPIDO).verify("nao-e-um-hash", "qualquer") is False


def test_detecta_hash_com_parametros_antigos() -> None:
    antigo = Argon2PasswordHasher(**_RAPIDO).hash("senha correta 1")
    novo = Argon2PasswordHasher(time_cost=2, memory_cost_kib=16, parallelism=1)

    assert novo.needs_rehash(antigo) is True
    assert novo.needs_rehash(novo.hash("senha correta 1")) is False


def test_verificacao_ficticia_nao_falha() -> None:
    # Usada quando o e-mail não existe, para equalizar o tempo da resposta.
    Argon2PasswordHasher(**_RAPIDO).burn_verification("qualquer senha")


def test_recusa_parametros_invalidos() -> None:
    with pytest.raises(ValueError):
        Argon2PasswordHasher(time_cost=0, memory_cost_kib=8, parallelism=1)
