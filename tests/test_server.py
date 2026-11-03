from typing import Any

import pytest
from mcp import Client
from mcp.shared.exceptions import MCPError
from mcp.types import INVALID_PARAMS, TextContent, TextResourceContents

pytestmark = pytest.mark.anyio

VALID_TICKET: dict[str, Any] = {
    "customer_email": "sam@example.com",
    "subject": "Webhooks keep failing",
    "description": "Every delivery to our endpoint returns a 401 since yesterday.",
    "priority": "high",
    "related_docs": ["webhooks"],
}


def error_text(result: Any) -> str:
    assert result.is_error, "expected the tool call to fail"
    block = result.content[0]
    assert isinstance(block, TextContent)
    return block.text


async def test_lists_tools(client: Client) -> None:
    result = await client.list_tools()
    names = {tool.name for tool in result.tools}
    assert names == {"search_docs", "draft_support_ticket"}

    search = next(t for t in result.tools if t.name == "search_docs")
    assert search.annotations is not None
    assert search.annotations.read_only_hint is True
    assert search.output_schema is not None


async def test_search_docs_filters_and_paginates(client: Client) -> None:
    first = await client.call_tool("search_docs", {"tag": "api", "limit": 2})
    assert not first.is_error
    data = first.structured_content
    assert data is not None
    assert data["total"] == 3
    assert [item["slug"] for item in data["items"]] == ["api-keys", "rate-limits"]
    assert data["next_offset"] == 2

    second = await client.call_tool("search_docs", {"tag": "api", "limit": 2, "offset": 2})
    data = second.structured_content
    assert data is not None
    assert [item["slug"] for item in data["items"]] == ["webhooks"]
    assert data["next_offset"] is None


async def test_search_docs_matches_text(client: Client) -> None:
    result = await client.call_tool("search_docs", {"query": "PASSWORD"})
    data = result.structured_content
    assert data is not None
    assert [item["slug"] for item in data["items"]] == ["reset-password"]
    assert data["items"][0]["uri"] == "docs://reset-password"


async def test_search_docs_rejects_bad_limit(client: Client) -> None:
    result = await client.call_tool("search_docs", {"limit": 0})
    assert "greater than or equal to 1" in error_text(result)

    result = await client.call_tool("search_docs", {"limit": 500})
    assert "less than or equal to 50" in error_text(result)


async def test_draft_ticket_happy_path(client: Client) -> None:
    result = await client.call_tool("draft_support_ticket", {"ticket": VALID_TICKET})
    assert not result.is_error
    data = result.structured_content
    assert data is not None
    assert data["draft_id"].startswith("DRAFT-")
    assert data["priority"] == "high"
    assert data["related_docs"] == ["webhooks"]


async def test_draft_ticket_is_deterministic(client: Client) -> None:
    a = await client.call_tool("draft_support_ticket", {"ticket": VALID_TICKET})
    b = await client.call_tool("draft_support_ticket", {"ticket": VALID_TICKET})
    assert a.structured_content is not None
    assert b.structured_content is not None
    assert a.structured_content["draft_id"] == b.structured_content["draft_id"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("customer_email", "not-an-email", "ticket.customer_email"),
        ("subject", "hi", "at least 5 characters"),
        ("description", "too short", "at least 20 characters"),
        ("priority", "whenever", "ticket.priority"),
        ("subject", "      ", "ticket.subject"),
    ],
)
async def test_draft_ticket_validation_errors(
    client: Client, field: str, value: str, message: str
) -> None:
    ticket = {**VALID_TICKET, field: value}
    result = await client.call_tool("draft_support_ticket", {"ticket": ticket})
    assert message in error_text(result)


async def test_draft_ticket_missing_field(client: Client) -> None:
    ticket = {k: v for k, v in VALID_TICKET.items() if k != "subject"}
    result = await client.call_tool("draft_support_ticket", {"ticket": ticket})
    text = error_text(result)
    assert "ticket.subject" in text
    assert "Field required" in text


async def test_draft_ticket_unknown_doc(client: Client) -> None:
    ticket = {**VALID_TICKET, "related_docs": ["webhooks", "does-not-exist"]}
    result = await client.call_tool("draft_support_ticket", {"ticket": ticket})
    text = error_text(result)
    assert "Unknown doc slug(s): does-not-exist" in text
    assert "webhooks" in text  # lists the valid slugs so the model can recover


async def test_unknown_tool(client: Client) -> None:
    result = await client.call_tool("nope", {})
    assert "nope" in error_text(result)


async def test_resource_template_is_listed(client: Client) -> None:
    result = await client.list_resource_templates()
    assert [t.uri_template for t in result.resource_templates] == ["docs://{slug}"]


async def test_read_doc_resource(client: Client) -> None:
    result = await client.read_resource("docs://billing-faq")
    contents = result.contents[0]
    assert isinstance(contents, TextResourceContents)
    assert contents.mime_type == "text/markdown"
    assert contents.text.startswith("# Billing FAQ")


async def test_read_missing_doc(client: Client) -> None:
    with pytest.raises(MCPError) as exc:
        await client.read_resource("docs://missing")
    assert exc.value.code == INVALID_PARAMS
    assert "missing" in exc.value.message


async def test_lists_prompts(client: Client) -> None:
    result = await client.list_prompts()
    assert [p.name for p in result.prompts] == ["explain_doc"]
    args = {a.name: a.required for a in result.prompts[0].arguments or []}
    assert args == {"slug": True, "audience": False}


async def test_get_prompt(client: Client) -> None:
    result = await client.get_prompt("explain_doc", {"slug": "api-keys", "audience": "engineer"})
    message = result.messages[0]
    assert message.role == "user"
    assert isinstance(message.content, TextContent)
    assert "Creating and rotating API keys" in message.content.text
    assert "engineer" in message.content.text


async def test_get_prompt_unknown_doc(client: Client) -> None:
    with pytest.raises(MCPError) as exc:
        await client.get_prompt("explain_doc", {"slug": "missing"})
    assert exc.value.code == INVALID_PARAMS
    assert "search_docs" in exc.value.message
