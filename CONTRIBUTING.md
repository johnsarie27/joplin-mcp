# Contributing

See [README.md](README.md#contents) for usage docs.

## Development setup

1. Install [uv](https://docs.astral.sh/uv/) if you don't have it.
2. Clone the repo and install dependencies:
   ```bash
   git clone https://github.com/johnsarie27/joplin-mcp.git
   cd joplin-mcp
   uv sync
   ```
3. Copy `config.example.json` to `config.json` and point it at a Joplin
   instance with the Web Clipper service enabled — see the **Setup** section
   in [README.md](README.md) for details.

## Project structure

```
src/joplin_mcp/
├── server.py   # FastMCP server and tool definitions
├── client.py   # Joplin Web Clipper REST API client
└── config.py   # config.json loading and access-control checks
```

## Testing changes

This project doesn't have an automated test suite yet. Verify changes
manually against a running Joplin instance using the MCP inspector:

```bash
npx @modelcontextprotocol/inspector uv run --directory /path/to/joplin-mcp joplin-mcp-server
```

This opens a local web UI where you can call each tool and inspect the raw
request/response. Exercise both the happy path and the access-control
failure modes (see **Access control** in [README.md](README.md)) for any
change touching `client.py` or `config.py`.

`.github/workflows/codeql.yml` runs CodeQL static analysis on every push to
`main` and on all pull requests.

## Pull requests

- Keep changes focused; avoid unrelated refactors in the same PR.
- Update `README.md` if the change affects setup, tools, or configuration.
- Match the existing code style — no linter/formatter is currently enforced.

## Releasing

Maintainers cut a release in two steps:

1. Bump `version` in `pyproject.toml` to the new `<major>.<minor>.<patch>`,
   run `uv lock` to sync `uv.lock`, and commit/push to `main`.
2. Tag that commit and push the tag:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

Pushing a tag matching `v<major>.<minor>.<patch>` triggers
`.github/workflows/release.yml`, which creates a GitHub Release with
auto-generated notes (a "What's Changed" list of merged PRs since the
previous tag).
