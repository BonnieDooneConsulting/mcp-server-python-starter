from collections.abc import AsyncIterator

import pytest
from mcp import Client

from mcp_starter.config import Settings
from mcp_starter.server import build_server


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[Client]:
    """An MCP client connected to the server in-process (no subprocess, no network)."""
    server = build_server(Settings(log_level="WARNING"))
    async with Client(server, raise_exceptions=True) as c:
        yield c
