import logging
import re
from pathlib import Path

from src.domain.entities.benchmark.benchmark_question import BenchmarkQuestion
from src.domain.interfaces.benchmark_question_provider_interface import IBenchmarkQuestionProvider
from src.domain.interfaces.settings_interface import ISettings

_STATEMENT_FILE = "enunciado.md"
_ANSWER_FILE = "alternativa_correta.md"
_OPTION_PATTERN = re.compile(r"^([A-E])\)\s+(.+)$", re.MULTILINE)
_EXPECTED_LETTERS = (list("ABCD"), list("ABCDE"))
_FILE_ENCODING = "utf-8"


class FileBenchmarkQuestionProvider(IBenchmarkQuestionProvider):
    """Adapter de `IBenchmarkQuestionProvider` apoiado no dataset em Markdown.

    Cada subpasta do diretório configurado é uma questão, com exatamente `enunciado.md` (enunciado
    e quatro ou cinco alternativas consecutivas a partir de `A)`) e `alternativa_correta.md`
    (letra e texto do gabarito).
    O dataset inteiro é validado na primeira leitura, antes de qualquer chamada ao modelo, e fica
    em cache na instância.
    """

    def __init__(self, settings: ISettings, logger: logging.Logger) -> None:
        """Inicializa o provider.

        Args:
            settings: Configurações da aplicação, fonte do diretório e da instrução.
            logger: Logger do módulo.
        """
        self.settings: ISettings = settings
        self.logger = logger
        self.__questions: list[BenchmarkQuestion] | None = None
        self.__instruction: str | None = None

    def list_questions(self) -> list[BenchmarkQuestion]:
        """Devolve todas as questões válidas, ordenadas pelo nome da pasta.

        Returns:
            list[BenchmarkQuestion]: Questões do dataset.

        Raises:
            ValueError: Quando o diretório não existe, está vazio ou alguma questão é inválida.
        """
        if self.__questions is None:
            self.__questions = self.__load_questions(directory=Path(self.settings.ralph_benchmark_questions_path))
            self.logger.info("%d questões de benchmark carregadas", len(self.__questions))
        return list(self.__questions)

    def answer_instruction(self) -> str:
        """Devolve a instrução de resposta anexada ao enunciado de cada questão.

        Returns:
            str: Conteúdo do arquivo de instrução.

        Raises:
            ValueError: Quando o arquivo não existe ou está vazio.
        """
        if self.__instruction is None:
            path = Path(self.settings.ralph_benchmark_prompt_path)
            try:
                instruction = path.read_text(encoding=_FILE_ENCODING).strip()
            except OSError as error:
                raise ValueError(f"Instrução do benchmark não encontrada: {path}") from error
            if not instruction:
                raise ValueError(f"Instrução do benchmark vazia: {path}")
            self.__instruction = instruction
        return self.__instruction

    def __load_questions(self, directory: Path) -> list[BenchmarkQuestion]:
        """Carrega e valida todas as pastas de questão do diretório."""
        if not directory.is_dir():
            raise ValueError(f"Diretório de questões não encontrado: {directory}")

        questions = [
            self.__load_question(folder=folder)
            for folder in sorted(path for path in directory.iterdir() if path.is_dir())
        ]
        if not questions:
            raise ValueError(f"Nenhuma questão encontrada em: {directory}")
        return questions

    def __load_question(self, folder: Path) -> BenchmarkQuestion:
        """Carrega uma questão, conferindo alternativas e gabarito.

        Raises:
            ValueError: Quando falta um arquivo, as alternativas não são `A` a `D` ou `E`, ou o gabarito
                não reproduz o texto da alternativa.
        """
        try:
            statement = (folder / _STATEMENT_FILE).read_text(encoding=_FILE_ENCODING).strip()
            answer = (folder / _ANSWER_FILE).read_text(encoding=_FILE_ENCODING).strip()
        except OSError as error:
            raise ValueError(f"Questão incompleta em {folder.name}: {error}") from error

        options = _OPTION_PATTERN.findall(statement)
        expected = _OPTION_PATTERN.fullmatch(answer)
        if [letter for letter, _ in options] not in _EXPECTED_LETTERS or expected is None:
            raise ValueError(f"Alternativas ou gabarito inválidos: {folder.name}")

        mapping = dict(options)
        if mapping.get(expected[1]) != expected[2]:
            raise ValueError(f"Texto do gabarito difere da alternativa: {folder.name}")
        return BenchmarkQuestion(
            id=folder.name,
            statement=statement,
            options=mapping,
            expected_alternative=expected[1],
        )
