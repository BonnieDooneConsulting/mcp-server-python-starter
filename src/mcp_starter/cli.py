"""Command line entry point: `mcp-starter [--transport stdio|streamable-http]`."""

import argparse
import logging
from collections.abc import Sequence
from typing import get_args

from mcp_starter import __version__
from mcp_starter.config import Settings, Transport
from mcp_starter.logging_setup import configure_logging
from mcp_starter.server import build_server

logger = logging.getLogger("mcp_starter")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-starter",
        description="Run the MCP starter server. Flags override MCP_STARTER_* env vars.",
    )
    parser.add_argument("--transport", choices=get_args(Transport), help="default: stdio")
    parser.add_argument("--host", help="HTTP bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, help="HTTP port (default: 8000)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    overrides = {k: v for k, v in vars(args).items() if v is not None}
    settings = Settings(**overrides)

    configure_logging(settings.log_level, settings.log_format)
    server = build_server(settings)

    if settings.transport == "streamable-http":
        logger.info(
            "starting",
            extra={"transport": "streamable-http", "host": settings.host, "port": settings.port},
        )
        server.run(
            "streamable-http",
            host=settings.host,
            port=settings.port,
            streamable_http_path=settings.http_path,
        )
    else:
        logger.info("starting", extra={"transport": "stdio"})
        server.run("stdio")


if __name__ == "__main__":
    main()
