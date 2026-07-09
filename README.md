# joplin-mcp

[![Release](https://img.shields.io/github/v/release/johnsarie27/joplin-mcp?sort=semver)](https://github.com/johnsarie27/joplin-mcp/releases)
[![CodeQL](https://github.com/johnsarie27/joplin-mcp/actions/workflows/codeql.yml/badge.svg)](https://github.com/johnsarie27/joplin-mcp/actions/workflows/codeql.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A minimal MCP server for Joplin, built with FastMCP. Talks to Joplin's local
Web Clipper REST API.

## Contents

- [Tools](#tools)
- [Setup](#setup)
- [Running it](#running-it)
- [Wiring into an MCP client](#wiring-into-an-mcp-client)
- [Access control](#access-control)
- [Notes on this build](#notes-on-this-build)
- [References](#references)
- [Related projects](#related-projects)
- [Contributing](#contributing)

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

### Using `uvx` instead (no local checkout needed)

`uv run --directory ...` (above) operates on a project already cloned to
disk — it needs a working copy of this repo, its `pyproject.toml`, and its
lockfile at that path. `uvx` (short for `uv tool run`) is different: it
fetches the package straight from git into uv's own cache and runs it in
an ephemeral environment, so the machine running the MCP client doesn't
need a local clone at all — just a `config.json` and `JOPLIN_CONFIG`
pointing at it.

```bash
uvx --from git+https://github.com/johnsarie27/joplin-mcp@<ref> joplin-mcp-server
```

`<ref>` can be a branch (e.g. `main`) or a commit SHA. A branch ref is
re-resolved to whatever the current tip commit is on every launch (a
network round-trip, and a fresh dependency resolve/build whenever that tip
changes) — convenient while iterating, but it means the running server can
change without you touching either client config. Pinning `<ref>` to a
specific commit SHA, per the SHA-pinning convention, freezes both the code
and its resolved dependency versions until you deliberately bump the pin —
prefer this once the repo's been stable through some real usage.

Since there's no local checkout in this mode, set `JOPLIN_CONFIG` to an
absolute path so `config.json` can still be found. Swap the `command`/`args`
in whichever client config above to `uvx`/`--from git+...` instead of
`uv`/`run --directory ...`, and add the `JOPLIN_CONFIG` env var:

```bash
claude mcp add joplin -s user -e JOPLIN_CONFIG=/path/to/config.json -- uvx --from git+https://github.com/johnsarie27/joplin-mcp@<ref> joplin-mcp-server
```

```json
{
  "mcpServers": {
    "joplin": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/johnsarie27/joplin-mcp@<ref>", "joplin-mcp-server"],
      "env": {
        "JOPLIN_CONFIG": "/path/to/config.json"
      }
    }
  }
}
```

Release tags (`v<major>.<minor>.<patch>`) are also valid refs — see
**Releasing** in [CONTRIBUTING.md](CONTRIBUTING.md) for how they're cut. Use
one as `<ref>` when pinning `uvx --from git+...@<ref>` above.

Tip: you can run the server standalone and call each tool manually before
wiring it into a client — see **Testing changes** in
[CONTRIBUTING.md](CONTRIBUTING.md).

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and
the release process.
