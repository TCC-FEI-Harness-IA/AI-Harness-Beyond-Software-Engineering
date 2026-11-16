class OfficialPublicationNotFoundError(Exception):
    """Publicação oficial inexistente, ou sessão que não pertence a ela."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Publicação oficial ou sessão '{identifier}' não encontrada.")
