class ExecutionNotAuthorizedError(ValueError):
    """A sessão de autenticação ou a credencial deixou de valer; nenhuma chamada LLM nova é enviada.

    Herda de `ValueError` porque é uma recusa local, antes do envio: como as demais validações
    locais, não conta como chamada nem consome orçamento.
    """
