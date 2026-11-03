"""Example resource: each doc is readable at `docs://{slug}`.

Resources are for data the client (or the user) pulls in as context. Tools are
for actions the model decides to take. When in doubt, start with a tool.
"""

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError

from mcp_starter.store import DocStore


def register(server: MCPServer, store: DocStore) -> None:
    @server.resource(
        "docs://{slug}",
        name="doc",
        title="Help doc",
        description="A help center article rendered as Markdown.",
        mime_type="text/markdown",
    )
    def read_doc(slug: str) -> str:
        doc = store.get(slug)
        if doc is None:
            # Clients get a clean "invalid params" error instead of a crash.
            raise ResourceNotFoundError(f"No doc with slug {slug!r}")
        tags = ", ".join(doc.tags)
        return f"# {doc.title}\n\n_Tags: {tags} | Updated: {doc.updated}_\n\n{doc.body}\n"
