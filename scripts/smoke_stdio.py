"""Launch the server over stdio as a real subprocess and list what it offers.

Run it with: uv run python scripts/smoke_stdio.py
"""

import sys

import anyio
from mcp import Client, StdioServerParameters


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_starter"])
    async with Client(params) as client:
        tools = await client.list_tools()
        print("tools:", ", ".join(t.name for t in tools.tools))
        result = await client.call_tool("search_docs", {"query": "webhook"})
        print("search_docs:", result.structured_content)
        templates = await client.list_resource_templates()
        print(
            "resource templates:", ", ".join(t.uri_template for t in templates.resource_templates)
        )
        prompts = await client.list_prompts()
        print("prompts:", ", ".join(p.name for p in prompts.prompts))


if __name__ == "__main__":
    anyio.run(main)
