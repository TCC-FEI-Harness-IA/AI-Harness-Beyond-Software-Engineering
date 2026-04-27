import logging
from abc import ABC, abstractmethod


class ISettings(ABC):
    @abstractmethod
    def logger(self, module_file: str) -> logging.Logger:
        raise NotImplementedError

    @abstractmethod
    def get_var_env(self, var_name: str) -> str:
        raise NotImplementedError
