"""Example tools.

Two patterns worth copying:

* `search_docs` is a read-only lookup with simple typed arguments and pagination.
* `draft_support_ticket` takes a pydantic model as input, so the SDK validates it
  before your code runs and the model gets a clear error message when it's wrong.

Return a pydantic model and the SDK sends it back as `structured_content` (with an
output schema in the tool listing) plus a JSON text block for older clients.
"""

import hashlib
import logging
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, field_validator

from mcp_starter.store import DocStore

logger = logging.getLogger(__name__)

MAX_LIMIT = 50


class DocSummary(BaseModel):
    slug: str
    title: str
    tags: list[str]
    uri: str = Field(description="Read the full doc with this resource URI.")


class SearchResult(BaseModel):
    items: list[DocSummary]
    total: int = Field(description="Total matches before pagination.")
    offset: int
    limit: int
    next_offset: int | None = Field(description="Pass this as `offset` to get the next page.")


class TicketRequest(BaseModel):
    """What a caller needs to provide to draft a support ticket."""

    customer_email: Annotated[
        str,
        Field(
            pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            description="Customer's email address.",
            examples=["sam@example.com"],
        ),
    ]
    subject: Annotated[str, Field(min_length=5, max_length=120)]
    description: Annotated[str, Field(min_length=20, max_length=4000)]
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    related_docs: Annotated[
        list[str],
        Field(default_factory=list, max_length=5, description="Slugs of docs the customer tried."),
    ]

    @field_validator("subject", "description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class TicketDraft(BaseModel):
    draft_id: str
    customer_email: str
    subject: str
    priority: str
    related_docs: list[str]
    summary: str


def register(server: MCPServer, store: DocStore) -> None:
    @server.tool(
        title="Search help docs",
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
    )
    def search_docs(
        query: Annotated[str, Field(description="Text to look for in titles and bodies.")] = "",
        tag: Annotated[str | None, Field(description="Only return docs with this tag.")] = None,
        limit: Annotated[int, Field(ge=1, le=MAX_LIMIT, description="Page size.")] = 10,
        offset: Annotated[int, Field(ge=0, description="How many results to skip.")] = 0,
    ) -> SearchResult:
        """Search the help center docs. Returns slugs you can read via docs://{slug}."""
        matches = store.search(query, tag)
        page = matches[offset : offset + limit]
        next_offset = offset + limit if offset + limit < len(matches) else None
        logger.info(
            "search_docs",
            extra={"query": query, "tag": tag, "total": len(matches), "returned": len(page)},
        )
        return SearchResult(
            items=[
                DocSummary(slug=d.slug, title=d.title, tags=d.tags, uri=f"docs://{d.slug}")
                for d in page
            ],
            total=len(matches),
            offset=offset,
            limit=limit,
            next_offset=next_offset,
        )

    @server.tool(
        title="Draft a support ticket",
        annotations=ToolAnnotations(
            read_only_hint=True, idempotent_hint=True, open_world_hint=False
        ),
    )
    def draft_support_ticket(ticket: TicketRequest) -> TicketDraft:
        """Validate a support ticket and return a draft for a human to review.

        Nothing is sent or saved. Swap the body for a call to your ticketing system.
        """
        unknown = [slug for slug in ticket.related_docs if store.get(slug) is None]
        if unknown:
            # ToolError is for failures you expect. The message goes back to the
            # model as-is (is_error=True), so make it something it can act on.
            raise ToolError(
                f"Unknown doc slug(s): {', '.join(unknown)}. "
                f"Valid slugs: {', '.join(store.slugs())}."
            )

        digest = hashlib.sha256(
            f"{ticket.customer_email}|{ticket.subject}|{ticket.description}".encode()
        ).hexdigest()[:8]
        draft = TicketDraft(
            draft_id=f"DRAFT-{digest.upper()}",
            customer_email=ticket.customer_email,
            subject=ticket.subject,
            priority=ticket.priority,
            related_docs=ticket.related_docs,
            summary=ticket.description[:200],
        )
        logger.info("draft_support_ticket", extra={"draft_id": draft.draft_id})
        return draft
