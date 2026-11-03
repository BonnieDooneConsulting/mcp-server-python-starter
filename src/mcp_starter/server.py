"""Builds the MCP server. Add your own capabilities in `build_server`."""

from mcp.server import MCPServer

from mcp_starter import __version__, prompts, resources, tools
from mcp_starter.config import Settings
from mcp_starter.store import DocStore

INSTRUCTIONS = """\
This server exposes a small help center. Use search_docs to find articles, read
docs://{slug} for the full text, and draft_support_ticket when a customer needs
a human. Drafts are never sent automatically.
"""


def build_server(settings: Settings | None = None, store: DocStore | None = None) -> MCPServer:
    settings = settings or Settings()
    store = store or DocStore.from_package()

    server = MCPServer(
        settings.server_name,
        version=__version__,
        instructions=INSTRUCTIONS,
        website_url="https://github.com/BonnieDooneConsulting/mcp-server-python-starter",
        log_level=settings.log_level,
    )

    tools.register(server, store)
    resources.register(server, store)
    prompts.register(server, store)
    return server
