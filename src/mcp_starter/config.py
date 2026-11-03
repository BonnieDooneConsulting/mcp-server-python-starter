"""Settings, loaded from environment variables (and an optional `.env` file).

Every field can be set with an `MCP_STARTER_` prefixed variable, for example
`MCP_STARTER_TRANSPORT=streamable-http` or `MCP_STARTER_LOG_LEVEL=DEBUG`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Transport = Literal["stdio", "streamable-http"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MCP_STARTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    server_name: str = "mcp-starter"
    transport: Transport = "stdio"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    http_path: str = "/mcp"
    log_level: LogLevel = "INFO"
    log_format: Literal["json", "text"] = "json"
