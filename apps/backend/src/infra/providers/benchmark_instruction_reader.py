from pathlib import Path

BENCHMARK_PROMPTS_PATH = Path(__file__).resolve().parents[1] / "benchmark/prompts"
_FILE_ENCODING = "utf-8"


def read_benchmark_instruction(path: Path) -> str:
    """Lê a instrução de resposta própria de um benchmark.

    Cada benchmark tem o seu arquivo, no idioma das suas questões: os vestibulares em português,
    MMLU e GPQA em inglês.

    Args:
        path: Arquivo da instrução.

    Returns:
        str: Conteúdo do arquivo, sem espaços nas bordas.

    Raises:
        ValueError: Quando o arquivo não existe ou está vazio.
    """
    try:
        instruction = path.read_text(encoding=_FILE_ENCODING).strip()
    except OSError as error:
        raise ValueError(f"Instrução do benchmark não encontrada: {path}") from error
    if not instruction:
        raise ValueError(f"Instrução do benchmark vazia: {path}")
    return instruction
