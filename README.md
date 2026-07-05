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

## Wiring into an MCP client

Both approaches below point `uv` at the `.env` file rather than duplicating
`JOPLIN_TOKEN`/`JOPLIN_ALLOWED_NOTEBOOKS` into the client config — one
source of truth for secrets.

### Claude Code

```bash
claude mcp add joplin -s user -- uv run --env-file /path/to/joplin-mcp/.env --directory /path/to/joplin-mcp joplin-mcp-server
```

`-s user` registers it at user scope, so it's available in every Claude
Code session, not just this repo. Verify with `claude mcp get joplin`;
remove with `claude mcp remove joplin -s user`.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows), adding:

```json
{
  "mcpServers": {
    "joplin": {
      "command": "uv",
      "args": ["run", "--env-file", "/path/to/joplin-mcp/.env", "--directory", "/path/to/joplin-mcp", "joplin-mcp-server"]
    }
  }
}
```

Fully quit and restart Claude Desktop afterward — it only picks up config
changes on launch. This is the schema documented at
[support.claude.com](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
and [modelcontextprotocol.io](https://modelcontextprotocol.io/docs/develop/connect-local-servers).
Some Claude Desktop builds manage MCP servers through a Settings UI
(Extensions/Connectors) instead of this file directly — check there first
if the file on disk doesn't have an `mcpServers` key already.

### Migrating to `uvx` later

Once this repo is stable and pushed, the local `uv run --directory ...`
invocation above can be replaced with:

```bash
uvx --from git+https://github.com/johnsarie27/joplin-mcp@<pinned-sha> joplin-mcp-server
```

pinning `<pinned-sha>` to a specific commit per the SHA-pinning convention,
so client configs aren't silently pulling `main` on every run. No local
checkout needed at that point — just swap the `command`/`args` in whichever
client config above to `uvx`/`--from git+...` instead of `uv`/`run --env-file
... --directory ...`.

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
