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
   Or drop it into the `.env` file at the repo root (already gitignored)
   and pass `--env-file .env` to `uv run` instead — see below.
3. Install [uv](https://docs.astral.sh/uv/) if you don't have it.
4. Set `JOPLIN_ALLOWED_NOTEBOOKS` to a comma-separated list of notebook ids
   (get these from `list_notebooks`) — see **Access control** below.

## Running it

No manual `pip install` needed — `uv run` resolves and caches dependencies
on first run.

```bash
uv run --directory /path/to/joplin-mcp joplin-mcp-server
```

To load `JOPLIN_TOKEN` (and friends) from the `.env` file instead of
exporting them in your shell:

```bash
uv run --env-file .env --directory /path/to/joplin-mcp joplin-mcp-server
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
npx @modelcontextprotocol/inspector uv run --env-file .env --directory /path/to/joplin-mcp joplin-mcp-server
```

This opens a local web UI where you can call each tool manually and see
the raw request/response before trusting it to a model.

## Access control

`search_notes`, `get_note`, `create_note`, and `update_note` are scoped to
notebooks listed in `JOPLIN_ALLOWED_NOTEBOOKS` (comma-separated notebook
ids). This is fail-closed: if the variable is unset or empty, all four
tools refuse to operate. `list_notebooks` is unaffected since it only
returns notebook metadata, not note content, and doubles as the way to
find the ids to allowlist in the first place.

Set `JOPLIN_ALLOWED_NOTEBOOKS=*` to explicitly allow all notebooks. This
is a deliberate opt-in, distinct from leaving the variable unset.

Out-of-scope access raises a `NotebookAccessError` with a message naming
the notebook, distinct from a `JoplinError` (an actual Joplin API failure).

## Notes on this build

- Requires Joplin Desktop running with the Web Clipper service enabled
  (i.e. Joplin itself must be open — this doesn't run Joplin headlessly).
- `JOPLIN_HOST` / `JOPLIN_PORT` env vars override the defaults
  (`localhost` / `41184`) if needed.
- Errors from the Joplin API surface as `JoplinError` with the raw
  status/body — check these first if a tool call fails.

## References

- [Joplin Data API](https://joplinapp.org/help/api/references/rest_api/)

## Related projects

- [alondmnt/joplin-mcp](https://github.com/alondmnt/joplin-mcp)
- [dweigend/joplin-mcp-server](https://github.com/dweigend/joplin-mcp-server)
