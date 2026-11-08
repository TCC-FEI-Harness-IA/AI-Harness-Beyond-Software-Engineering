"""Preenche o catálogo de modelos (coleção MONGODB_MODELS_COLLECTION) com os modelos iniciais.

Uso: python scripts/seed_models.py [--overwrite]
Sem --overwrite, só cadastra os modelos que ainda não existem — edições feitas pela tela "Modelos"
são preservadas. Lê MONGODB_URI, MONGODB_DATABASE e MONGODB_MODELS_COLLECTION do .env.

Fonte: OpenRouter (páginas dos modelos e `GET /api/v1/models/{id}/endpoints`), consultada em
2026-11-07. Os preços variam por provedor; para cada modelo, todos os números vêm do mesmo provedor:
o primeiro da lista da OpenRouter (menor preço de entrada), ignorando camadas de serviço especiais
como a `flex` da OpenAI. A vazão é a mediana (p50) dos últimos 30 minutos desse provedor.
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

from src.domain.entities.llm.model_info import ModelInfo  # noqa: E402
from src.infra.adapters.mongo_client_adapter import MongoClientAdapter  # noqa: E402
from src.infra.config.settings import Settings  # noqa: E402
from src.infra.repositories.mongo_model_info_repository import MongoModelInfoRepository  # noqa: E402

INITIAL_MODELS = [
    # Provedor de referência: Wafer.
    ModelInfo("deepseek/deepseek-v4-flash-0731", "DeepSeek: DeepSeek V4 Flash 0731", 0.0434, 0.30, 1_048_576, 145),
    # Relace.
    ModelInfo("deepseek/deepseek-v4-flash", "DeepSeek: DeepSeek V4 Flash 0423", 0.0413, 0.45, 1_048_576, 116),
    # Alibaba.
    ModelInfo("qwen/qwen3.7-flash", "Qwen: Qwen3.7 Flash", 0.03, 0.13, 1_000_000, 66),
    # PrimeIntellect.
    ModelInfo("qwen/qwen3.6-35b-a3b", "Qwen: Qwen3.6 35B A3B", 0.01, 0.092, 262_144, 81),
    # DekaLLM.
    ModelInfo("qwen/qwen3-30b-a3b-instruct-2507", "Qwen: Qwen3 30B A3B Instruct 2507", 0.09, 0.30, 262_144, 85),
    # Alibaba.
    ModelInfo("qwen/qwen3.5-flash-02-23", "Qwen: Qwen3.5-Flash", 0.065, 0.26, 1_000_000, 83),
    # DeepInfra.
    ModelInfo("meta-llama/llama-3.1-8b-instruct", "Meta: Llama 3.1 8B Instruct", 0.02, 0.04, 131_072, 25),
    # Parasail.
    ModelInfo("meta-llama/llama-3.2-3b-instruct", "Meta: Llama 3.2 3B Instruct", 0.05, 0.33, 131_072, 248),
    # Cloudflare (único provedor).
    ModelInfo("meta-llama/llama-3.2-1b-instruct", "Meta: Llama 3.2 1B Instruct", 0.027, 0.201, 60_000, 127),
    # Mistral.
    ModelInfo("mistralai/ministral-3b-2512", "Mistral: Ministral 3 3B 2512", 0.10, 0.10, 131_072, 151),
    # Tencent (único provedor).
    ModelInfo("tencent/hy-mt2-30b-a3b", "Tencent: Hy-MT2-30B-A3B", 0.074, 0.295, 8_192, 105),
    # OpenAI, camada padrão (a `flex` custa metade, mas é a camada lenta).
    ModelInfo("openai/gpt-5-nano", "OpenAI: GPT-5 Nano", 0.05, 0.40, 400_000, 114),
]


async def seed(overwrite: bool) -> None:
    """Grava os modelos iniciais, pulando os já cadastrados salvo com `overwrite`."""
    settings = Settings()
    repository = MongoModelInfoRepository(
        collection=MongoClientAdapter(settings=settings).models_collection,
        logger=logging.getLogger("seed_models"),
    )
    for model in INITIAL_MODELS:
        if not overwrite and await repository.find_by_name(model_name=model.model_name) is not None:
            print(f"já cadastrado, mantido: {model.model_name}")
            continue
        await repository.save(model=model)
        print(f"gravado: {model.model_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--overwrite", action="store_true", help="substitui os modelos já cadastrados")
    args = parser.parse_args()
    load_dotenv()
    asyncio.run(seed(overwrite=args.overwrite))


if __name__ == "__main__":
    main()
