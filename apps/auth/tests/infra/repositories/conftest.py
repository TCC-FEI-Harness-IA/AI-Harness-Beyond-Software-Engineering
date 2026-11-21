import pytest
from mongomock_motor import AsyncMongoMockClient


@pytest.fixture
def mongo_client() -> AsyncMongoMockClient:
    """Cliente MongoDB em memória; um novo cliente sobre o mesmo servidor simula um reinício."""
    return AsyncMongoMockClient(tz_aware=True)
