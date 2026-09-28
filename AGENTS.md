# AGENTS.md

Guidance for AI coding agents working in this repository. Human contributor
docs live in [CONTRIBUTING.md](CONTRIBUTING.md); this file covers
agent-specific operational notes that aren't there.

## Project

An MCP server exposing Joplin's Web Clipper REST API as tools
(`src/joplin_mcp/server.py`), backed by a REST client (`client.py`) and a
config/access-control loader (`config.py`). See
[CONTRIBUTING.md](CONTRIBUTING.md#project-structure) for the full layout.

## Setup, tests, dev loop

See [CONTRIBUTING.md](CONTRIBUTING.md#development-setup) and
[Testing changes](CONTRIBUTING.md#testing-changes). Summary: `uv sync`,
`uv run pytest`. The mocked test suite covers `config.py` and the
access-control logic in `server.py`; anything touching `client.py` or new
tool wiring needs a manual pass with the MCP inspector (see CONTRIBUTING.md).

## PR merge requirements (repo ruleset, not just CI)

`main` carries a GitHub ruleset — `require_code_owner_review: true` with
CODEOWNERS (`* @johnsarie27`) — in addition to the required
`analyze (python)` status check. **A green CI run is not enough to merge.**
Every PR, including Dependabot's, needs an approving review from the code
owner first.

- `gh pr merge --admin` does not bypass this.
- Claude Code's auto-mode classifier separately blocks both an `--admin`
  merge and a self-approval (`gh pr review --approve`) on the maintainer's
  own repo — both attempts are denied outright, not just discouraged.
- If a PR shows `mergeStateStatus: BLOCKED` with all checks green, the fix
  is a code-owner review from the maintainer, not an override. Surface this
  rather than retrying admin/self-approve variants.
- If a Dependabot PR is `BEHIND` main, update its branch first
  (`gh api -X PUT repos/johnsarie27/joplin-mcp/pulls/<n>/update-branch`) —
  this restarts required checks, so re-check status before merging.

## Releasing

See [CONTRIBUTING.md](CONTRIBUTING.md#releasing) for the tag/push mechanics.
Two things worth knowing beyond that doc:

- `release.yml` only fires on `main` and just creates a GitHub Release; there
  is no PyPI publish step. Pure dependency-bump PRs don't need a release of
  their own — the existing pattern is to let them accumulate untagged on
  `main` until the next feature/fix release, then bundle them into that
  release's "What's Changed" notes.
- The maintainer runs this server locally pinned to a release tag (not
  `main`) via `uvx --from git+...@<tag>` in local MCP client configs. After
  cutting a release, ask whether those local pins need bumping — pushing the
  tag alone does not propagate to already-running clients.
