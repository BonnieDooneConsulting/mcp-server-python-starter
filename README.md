# MCP Server Python Starter

A clean starting point for building your own MCP server in Python. Clone it, swap the example tools for yours, and you've got something you can actually ship.

[![CI](https://github.com/BonnieDooneConsulting/mcp-server-python-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/BonnieDooneConsulting/mcp-server-python-starter/actions/workflows/ci.yml)

## What this is

MCP (the Model Context Protocol) is an open standard that lets AI apps like Claude call your code, so the model can look up your data or take actions in your systems. An MCP server is the small program that exposes those capabilities, and this repo is a template for writing one well.

If you're new to the idea, I wrote a plain-English intro: [What is an MCP server?](https://bonniedoone.ai/blog/what-is-an-mcp-server)

I put this together because most MCP examples stop at "hello world." That's fine for a demo. But the first time you put one in front of a real team, you need config, logging that doesn't break stdio, input validation, tests, and a way to deploy it. That's what's here.

## What's included

- The official [`mcp` Python SDK](https://github.com/modelcontextprotocol/python-sdk) (v2), using `MCPServer`. That's the decorator-based API that used to be called `FastMCP`.
- Two example tools. `search_docs` is a read-only lookup with pagination over a small bundled dataset. `draft_support_ticket` takes a pydantic model as input, so bad input gets a clear error before your code even runs.
- A resource template, `docs://{slug}`, that returns a doc as Markdown.
- A prompt template, `explain_doc`, that shows up as a reusable prompt in clients that support them.
- Config from environment variables with pydantic-settings (`MCP_STARTER_*`, or a `.env` file).
- JSON logs to stderr. With the stdio transport, stdout is the protocol channel, so one stray `print()` can break the connection. Ruff's `T20` rule is turned on to catch those.
- Two transports: stdio (the default, for local clients) and streamable HTTP (for running it as a service).
- Tests that talk to the server through the SDK's in-memory client, plus a smoke test that launches it over real stdio.
- Ruff, Pyright in strict mode, GitHub Actions CI, and a slim Dockerfile that runs as a non-root user.

The sample data is a made-up help center for a made-up product. It's only there so the tools have something to search. There are no network calls and no secrets.

## Quick start

You'll need [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer.

```bash
git clone https://github.com/BonnieDooneConsulting/mcp-server-python-starter.git
cd mcp-server-python-starter
uv sync
```

Run it over stdio (this is what Claude Code and Claude Desktop use):

```bash
uv run mcp-starter
```

It'll sit there waiting for a client on stdin. That's expected. Press Ctrl+C to stop it.

Or run it over HTTP:

```bash
uv run mcp-starter --transport streamable-http --port 8000
# the MCP endpoint is http://127.0.0.1:8000/mcp
```

Want to poke at it in a browser first? The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is handy for that:

```bash
npx @modelcontextprotocol/inspector uv run mcp-starter
```

### Configuration

Every setting can come from a flag, an environment variable, or a `.env` file. Flags win.

| Variable | Flag | Default |
| --- | --- | --- |
| `MCP_STARTER_TRANSPORT` | `--transport` | `stdio` |
| `MCP_STARTER_HOST` | `--host` | `127.0.0.1` |
| `MCP_STARTER_PORT` | `--port` | `8000` |
| `MCP_STARTER_HTTP_PATH` | | `/mcp` |
| `MCP_STARTER_LOG_LEVEL` | `--log-level` | `INFO` |
| `MCP_STARTER_LOG_FORMAT` | | `json` (or `text`) |
| `MCP_STARTER_SERVER_NAME` | | `mcp-starter` |

## Connecting to Claude Code

Point Claude Code at your checkout:

```bash
claude mcp add mcp-starter -- uv --directory /absolute/path/to/mcp-server-python-starter run mcp-starter
```

If you're running the HTTP transport instead:

```bash
claude mcp add --transport http mcp-starter http://127.0.0.1:8000/mcp
```

Run `claude mcp list` to check that it connected, then ask Claude something like "search the help docs for webhooks."

## Connecting to Claude Desktop

Open Settings, go to Developer, and click Edit Config. That opens `claude_desktop_config.json`. Add this:

```json
{
  "mcpServers": {
    "mcp-starter": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/mcp-server-python-starter",
        "run",
        "mcp-starter"
      ]
    }
  }
}
```

Restart Claude Desktop. If it can't find `uv`, use the full path from `which uv` as the `command`. The desktop app doesn't always see the same `PATH` your terminal does, and it's a common reason a server shows up as failed.

## Adding your own tool

Tools live in `src/mcp_starter/tools.py`, inside `register()`. Type hints become the input schema, the docstring becomes the description the model reads, and a pydantic return type becomes structured output. Here's a small one:

```python
from typing import Annotated

from pydantic import BaseModel, Field


class WordCount(BaseModel):
    words: int
    characters: int


def register(server: MCPServer, store: DocStore) -> None:
    ...

    @server.tool(annotations=ToolAnnotations(read_only_hint=True))
    def count_words(
        text: Annotated[str, Field(min_length=1, max_length=10_000)],
    ) -> WordCount:
        """Count the words and characters in a piece of text."""
        return WordCount(words=len(text.split()), characters=len(text))
```

A few habits that'll save you pain later:

- Write the docstring for the model, not for you. It's how the model decides when to call your tool, so say what it does and what it returns.
- Raise `ToolError` for failures you expect, like "that customer doesn't exist." The message goes straight back to the model, so make it something it can act on. Any other exception gets hidden behind a generic error and logged with a traceback, which is what you want for real bugs.
- Keep tools small and specific. A few focused tools are easier for the model to pick between than one big tool with a `mode` argument.
- Add a test in `tests/test_server.py`. The `client` fixture hands you a connected client, so most tests are a few lines.

If you outgrow one file, split tools into a package and call each module's `register()` from `build_server()` in `server.py`.

## Running tests

```bash
uv run pytest                          # tests, all in-memory
uv run ruff check .                    # lint
uv run ruff format --check .           # formatting
uv run pyright                         # type check (strict)
uv run python scripts/smoke_stdio.py   # launch over real stdio and list tools
```

CI runs all of these on every push to `main` and every pull request, on Python 3.11 through 3.14.

Not using uv? A plain virtualenv works too:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

## Running in Docker

The image runs the HTTP transport on port 8000 as a non-root user.

```bash
docker build -t mcp-starter .
docker run --rm -p 8000:8000 mcp-starter
```

One heads-up before you put it on the internet: this template doesn't include auth. Inside the container it binds to `0.0.0.0`, and the SDK only turns on DNS rebinding protection by default when it's bound to localhost. Put it behind something that handles auth, or wire up the SDK's auth support, before you expose it.

## Project layout

```
.
├── src/mcp_starter/
│   ├── cli.py            # entry point: parses flags, sets up logging, picks a transport
│   ├── server.py         # build_server(): creates the MCPServer and registers everything
│   ├── config.py         # Settings, loaded from MCP_STARTER_* env vars
│   ├── logging_setup.py  # JSON logs to stderr
│   ├── store.py          # tiny read-only data layer over the bundled JSON
│   ├── tools.py          # search_docs, draft_support_ticket
│   ├── resources.py      # docs://{slug}
│   ├── prompts.py        # explain_doc
│   └── data/docs.json    # sample data
├── tests/                # pytest, using the SDK's in-memory client
├── scripts/smoke_stdio.py
├── Dockerfile
├── .github/workflows/ci.yml
├── pyproject.toml        # deps plus ruff, pyright, and pytest config
└── uv.lock
```

## Contributing

Issues and pull requests are welcome. Please run the checks in [Running tests](#running-tests) before opening a PR. If you're planning something big, open an issue first so we can talk it through.

## License

MIT. See [LICENSE](LICENSE).

---

Built by [Bonnie Doone Consulting](https://bonniedoone.ai). Need a custom MCP server for your team? [Let's talk](https://bonniedoone.ai/services/mcp-servers).
