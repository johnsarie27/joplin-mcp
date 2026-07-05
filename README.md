# joplin-mcp

A minimal MCP server for Joplin, built with FastMCP. Talks to Joplin's local
Web Clipper REST API.

## Tools

- `search_notes(query, limit=20)` — full-text search
- `get_note(note_id)` — fetch a note's full content
- `create_note(title, body, notebook_id)` — create a new note
- `update_note(note_id, title=None, body=None)` — edit an existing note
- `list_notebooks()` — list notebooks, to get a `notebook_id` for `create_note`

## Setup

1. In Joplin Desktop: **Tools > Options > Web Clipper**, enable the service,
   copy the auth token shown there.
2. Set the token as an environment variable (don't hardcode it in configs
   you might commit or share):
   ```
   export JOPLIN_TOKEN="paste-your-token-here"
   ```
3. Install [uv](https://docs.astral.sh/uv/) if you don't have it.

## Running it

No manual `pip install` needed — `uv run` resolves and caches dependencies
on first run.

```bash
uv run --directory /path/to/joplin-mcp joplin-mcp-server
```

## Wiring into an MCP client (Claude Desktop / Claude Code)

Add to your MCP client config:

```json
{
  "mcpServers": {
    "joplin": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/joplin-mcp", "joplin-mcp-server"],
      "env": {
        "JOPLIN_TOKEN": "paste-your-token-here"
      }
    }
  }
}
```

## Testing standalone (recommended before wiring into a client)

```bash
npx @modelcontextprotocol/inspector uv run --directory /path/to/joplin-mcp joplin-mcp-server
```

This opens a local web UI where you can call each tool manually and see
the raw request/response before trusting it to a model.

## Notes on this build

- Requires Joplin Desktop running with the Web Clipper service enabled
  (i.e. Joplin itself must be open — this doesn't run Joplin headlessly).
- `JOPLIN_HOST` / `JOPLIN_PORT` env vars override the defaults
  (`localhost` / `41184`) if needed.
- Errors from the Joplin API surface as `JoplinError` with the raw
  status/body — check these first if a tool call fails.
