import json
import logging

import pytest

from mcp_starter.cli import parse_args
from mcp_starter.config import Settings
from mcp_starter.logging_setup import JsonFormatter


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_STARTER_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_STARTER_PORT", "9001")
    settings = Settings()
    assert settings.transport == "streamable-http"
    assert settings.port == 9001


def test_settings_reject_bad_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_STARTER_TRANSPORT", "carrier-pigeon")
    with pytest.raises(ValueError, match="transport"):
        Settings()


def test_cli_flags() -> None:
    args = parse_args(["--transport", "streamable-http", "--port", "9100"])
    assert args.transport == "streamable-http"
    assert args.port == 9100
    assert args.host is None  # unset flags fall back to env/defaults


def test_json_formatter_includes_extra_fields() -> None:
    record = logging.LogRecord("mcp_starter", logging.INFO, __file__, 1, "hello", None, None)
    record.request_id = "abc"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["msg"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "abc"
