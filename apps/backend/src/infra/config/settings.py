import logging
import os
from pathlib import Path

from src.domain.interfaces.settings_interface import ISettings


class Settings(ISettings):
    def __init__(self) -> None:
        self.__logs_configured = False
        self.__vars_env = self.__load_vars_env()

    def __load_vars_env(self) -> dict[str, str | None]:
        return {
            "openrouter_api_url": os.getenv(
                "OPENROUTER_API_URL",
                "https://openrouter.ai/api/v1/chat/completions",
            ),
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "openrouter_http_referer": os.getenv("OPENROUTER_HTTP_REFERER", ""),
            "openrouter_x_title": os.getenv("OPENROUTER_X_TITLE", ""),
            "openrouter_timeout_seconds": os.getenv("OPENROUTER_TIMEOUT_SECONDS", "30"),
            "openrouter_model": os.getenv("OPENROUTER_MODEL"),
            "openrouter_max_tokens": os.getenv("OPENROUTER_MAX_TOKENS"),
            "openrouter_temperature": os.getenv("OPENROUTER_TEMPERATURE"),
            "genai_avaliable_models": os.getenv("genai_avaliable_models", ""),
            "genai_avaliable_providers": os.getenv("genai_avaliable_providers", ""),
        }

    def get_var_env(self, var_name: str) -> str:
        env_var = self.__vars_env.get(var_name.lower())
        if env_var is None:
            raise ValueError(f"Variável de ambiente '{var_name}' não encontrada.")
        return env_var

    def logger(self, module_file: str) -> logging.Logger:
        if not self.__logs_configured:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            )
            self.__logs_configured = True

        module_relative_path = self.__get_relative_module_path(module_file=module_file)
        return logging.getLogger(module_relative_path)

    def __get_relative_module_path(self, module_file: str) -> str:
        module_path = Path(module_file).resolve()

        if "src" in module_path.parts:
            src_index = module_path.parts.index("src")
            return Path(*module_path.parts[src_index:]).as_posix()

        return module_path.name
