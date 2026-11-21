import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.domain.enums.session_storage_backend_enum import SessionStorageBackendEnum
from src.domain.interfaces.settings_interface import ISettings
from src.infra.adapters.mongo_client_adapter import MongoClientAdapter
from src.infra.repositories.owner_scope import OWNER_KEY, scoped_key, validate_owner_id

_ENCODING = "utf-8"


@dataclass(frozen=True)
class AssignmentReport:
    """Resultado da atribuição: quanto havia e quanto foi copiado nesta execução."""

    batteries: int
    sessions: int
    copied: int


class LegacyDataAssigner:
    """Copia o histórico legado (sem dono) para uma conta escolhida explicitamente.

    É uma cópia: a origem não é alterada nem apagada, e documentos que a conta já tem não são
    sobrescritos (execução idempotente). Nada fica público: a cópia é dado pessoal da conta.
    """

    def __init__(self, settings: ISettings, owner_id: str) -> None:
        """Inicializa a atribuição.

        Raises:
            ValueError: Quando o identificador da conta é inválido.
        """
        self.settings = settings
        self.owner_id = validate_owner_id(owner_id)

    async def run(self, apply: bool) -> AssignmentReport:
        """Conta (e, com `apply`, copia) baterias e sessões legadas."""
        if self.settings.ralph_session_storage_backend is SessionStorageBackendEnum.MONGODB:
            return await self.__run_mongo(apply)
        return await asyncio.to_thread(self.__run_json, apply)

    def __run_json(self, apply: bool) -> AssignmentReport:
        copied = 0
        counts: list[int] = []
        bases = (
            Path(self.settings.ralph_benchmark_sessions_storage_path),
            Path(self.settings.ralph_sessions_storage_path),
        )
        for base in bases:
            files = sorted(base.glob("*.json")) if base.is_dir() else []
            counts.append(len(files))
            target_dir = base / "owners" / self.owner_id
            for source in files:
                target = target_dir / source.name
                if not apply or target.exists():
                    continue
                target_dir.mkdir(parents=True, exist_ok=True)
                document = json.loads(source.read_text(encoding=_ENCODING))
                temporary = target.with_name(f"{target.name}.tmp")
                temporary.write_text(json.dumps({**document, OWNER_KEY: self.owner_id}, ensure_ascii=False, indent=2),
                                     encoding=_ENCODING)
                temporary.replace(target)
                copied += 1
        return AssignmentReport(batteries=counts[0], sessions=counts[1], copied=copied)

    async def __run_mongo(self, apply: bool) -> AssignmentReport:
        client = MongoClientAdapter(settings=self.settings)
        copied = 0
        counts: list[int] = []
        for collection in (client.benchmark_sessions_collection, client.sessions_collection):
            documents: list[dict[str, Any]] = await collection.find({OWNER_KEY: {"$exists": False}}).to_list(None)
            counts.append(len(documents))
            for document in documents if apply else []:
                key = scoped_key(self.owner_id, document["_id"])
                if await collection.find_one({"_id": key}) is not None:
                    continue
                await collection.insert_one({**document, "_id": key, "id": document["_id"], OWNER_KEY: self.owner_id})
                copied += 1
        return AssignmentReport(batteries=counts[0], sessions=counts[1], copied=copied)
