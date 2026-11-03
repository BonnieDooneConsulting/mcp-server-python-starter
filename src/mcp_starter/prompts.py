"""Example prompt template.

Prompts are reusable, parameterized messages a user can pick from the client
(they show up as slash commands in Claude Code, for example).
"""

from typing import Literal

from mcp.server import MCPServer
from mcp.server.mcpserver import Message, UserMessage
from mcp.shared.exceptions import MCPError
from mcp.types import INVALID_PARAMS

from mcp_starter.store import DocStore


def register(server: MCPServer, store: DocStore) -> None:
    @server.prompt(title="Explain a help doc")
    def explain_doc(
        slug: str, audience: Literal["customer", "engineer"] = "customer"
    ) -> list[Message]:
        """Ask the model to explain a help doc for a specific audience."""
        doc = store.get(slug)
        if doc is None:
            # Raise MCPError for errors the client should see. Any other exception
            # is reported as a generic "Internal server error".
            raise MCPError(
                code=INVALID_PARAMS,
                message=f"No doc with slug {slug!r}. Try the search_docs tool first.",
            )
        style = (
            "Keep it short, friendly, and free of jargon."
            if audience == "customer"
            else "Be precise and call out edge cases."
        )
        return [
            UserMessage(
                f"Explain this help article to a {audience}. {style}\n\n"
                f"Title: {doc.title}\n\n{doc.body}"
            )
        ]
