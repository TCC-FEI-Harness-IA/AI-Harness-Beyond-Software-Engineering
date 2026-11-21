import hashlib

from src.infra.adapters.secure_token_generator import SecureTokenGenerator


def test_token_tem_256_bits_e_e_imprevisivel() -> None:
    gerador = SecureTokenGenerator()

    tokens = {gerador.session_token() for _ in range(50)}

    assert len(tokens) == 50
    assert all(len(token) >= 43 for token in tokens)


def test_digest_e_sha256_hex_do_token() -> None:
    gerador = SecureTokenGenerator()

    assert gerador.digest("abc") == hashlib.sha256(b"abc").hexdigest()


def test_identificadores_tem_prefixo_e_sao_unicos() -> None:
    gerador = SecureTokenGenerator()

    assert gerador.user_id().startswith("usr_")
    assert gerador.session_id().startswith("ses_")
    assert gerador.user_id() != gerador.user_id()
    assert len(gerador.csrf_token()) >= 43
