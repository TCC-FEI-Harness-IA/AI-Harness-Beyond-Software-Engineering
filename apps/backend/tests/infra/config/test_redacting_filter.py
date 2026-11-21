from src.infra.config.redacting_filter import redact


def test_redige_campos_de_senha() -> None:
    assert "segredo" not in redact('{"password": "segredo"}')
