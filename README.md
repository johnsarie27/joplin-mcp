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
2. Install [uv](https://docs.astral.sh/uv/) if you don't have it.
3. Copy `config.example.json` to `config.json` at the repo root (already
   gitignored, so it won't be committed) and fill in:
   ```json
   {
     "token": "paste-your-token-here",
     "host": "localhost",
     "port": "41184",
     "notebooks": [
       {"id": "notebook-id-or-name", "access": "write"},
       {"id": "another-notebook-id-or-name", "access": "read"}
     ]
   }
   ```
   `host`/`port` are optional and default to `localhost`/`41184`. See
   **Access control** below for the `notebooks` list.

## Running it

No manual `pip install` needed — `uv run` resolves and caches dependencies
on first run.

```bash
uv run --directory /path/to/joplin-mcp joplin-mcp-server
```

This looks for `config.json` in the working directory (which `--directory`
sets to the repo). To keep the config file somewhere else, set
`JOPLIN_CONFIG` to its path:

```bash
JOPLIN_CONFIG=/path/to/config.json uv run --directory /path/to/joplin-mcp joplin-mcp-server
```

## Wiring into an MCP client

Both approaches below point at the repo directory, which is where
`config.json` lives — one source of truth for secrets and access config.

### Claude Code

```bash
claude mcp add joplin -s user -- uv run --directory /path/to/joplin-mcp joplin-mcp-server
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
      "args": ["run", "--directory", "/path/to/joplin-mcp", "joplin-mcp-server"]
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
client config above to `uvx`/`--from git+...` instead of `uv`/`run
--directory ...`. Set `JOPLIN_CONFIG` to an absolute path in this case,
since there's no repo checkout to hold a `config.json` next to.

## Testing standalone (recommended before wiring into a client)

```bash
npx @modelcontextprotocol/inspector uv run --directory /path/to/joplin-mcp joplin-mcp-server
```

This opens a local web UI where you can call each tool manually and see
the raw request/response before trusting it to a model.

## Access control

`search_notes`, `get_note`, `create_note`, and `update_note` are scoped by
the `notebooks` list in `config.json`. Each entry is:

```json
{"id": "notebook-id-or-name", "access": "read"}
```

`access` is `"read"` (default if omitted) or `"write"` (implies read).
`search_notes`/`get_note` require `read`; `create_note`/`update_note`
require `write`. This is fail-closed: if `notebooks` is missing, empty, or
none of its entries match a real notebook, all four tools refuse to
operate. `list_notebooks` is unaffected since it only returns notebook
metadata, not note content, and doubles as the way to find the ids/names
to list in `config.json` in the first place.

Name matching is case-insensitive (`Tech`, `tech`, and `TECH` are
equivalent) and resolved against the live notebook list on each call, so
a rename takes effect immediately. Since Joplin doesn't require notebook
names to be unique (nested notebooks can share a title), a name that
matches more than one notebook grants that access level to all of them —
use the notebook id instead (from `list_notebooks`) if you need to scope
to just one of several same-named notebooks.

Use `{"id": "*", "access": "read"}` or `{"id": "*", "access": "write"}` to
grant that access level to all notebooks. This is a deliberate opt-in,
distinct from leaving `notebooks` empty.

Out-of-scope access raises a `NotebookAccessError` with a message naming
the notebook, distinct from a `JoplinError` (an actual Joplin API failure).

## Notes on this build

- Requires Joplin Desktop running with the Web Clipper service enabled
  (i.e. Joplin itself must be open — this doesn't run Joplin headlessly).
- `host` / `port` in `config.json` override the defaults (`localhost` /
  `41184`) if needed.
- Errors from the Joplin API surface as `JoplinError` with the raw
  status/body — check these first if a tool call fails.

## References

- [Joplin Data API](https://joplinapp.org/help/api/references/rest_api/)

## Related projects

- [alondmnt/joplin-mcp](https://github.com/alondmnt/joplin-mcp)
- [dweigend/joplin-mcp-server](https://github.com/dweigend/joplin-mcp-server)
