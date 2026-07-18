"""FastMCP server exposing Joplin note operations as MCP tools."""

from functools import lru_cache

from fastmcp import FastMCP

from joplin_mcp.client import JoplinClient, JoplinError
from joplin_mcp.config import load_config

mcp = FastMCP("joplin")


class NotebookAccessError(Exception):
    """Raised when a note/notebook falls outside the configured access."""


@lru_cache
def get_client() -> JoplinClient:
    # Cached so we reuse one client/token for the life of the process,
    # but constructed lazily so a missing/invalid config fails at first
    # tool call (with a clear error) rather than at import time. Token/host/
    # port are fixed at that first call - a rotated token or changed host
    # needs a process restart to take effect (unlike the notebooks list
    # below, which is intentionally re-read live on every tool call so
    # renames/access edits take effect immediately).
    config = load_config()
    kwargs: dict[str, str] = {"token": config.get("token", "")}
    if config.get("host"):
        kwargs["host"] = config["host"]
    if config.get("port"):
        kwargs["port"] = str(config["port"])
    return JoplinClient(**kwargs)


class NotebookAccess:
    """Resolved read/write notebook access from the config's `notebooks` list."""

    def __init__(
        self,
        read_all: bool,
        write_all: bool,
        read_ids: frozenset[str],
        write_ids: frozenset[str],
    ) -> None:
        self._read_all = read_all or write_all
        self._write_all = write_all
        self._read_ids = read_ids
        self._write_ids = write_ids

    def can_read(self, notebook_id: str) -> bool:
        return self._read_all or notebook_id in self._read_ids or notebook_id in self._write_ids

    def can_write(self, notebook_id: str) -> bool:
        return self._write_all or notebook_id in self._write_ids

    def __bool__(self) -> bool:
        # `_read_all` already folds in `write_all` (write implies read), so
        # `_write_all` can never be true here while `_read_all` is false.
        return self._read_all or bool(self._read_ids) or bool(self._write_ids)


async def _notebook_access() -> NotebookAccess:
    # Each `notebooks` entry is {"id": <notebook id or name>, "access": "read"|"write"}.
    # "id" may be "*" to mean all notebooks. Entries may be a name rather than an
    # id (names aren't guaranteed unique - nested notebooks can share a title -
    # resolved against the live notebook list since a name matching more than
    # one notebook grants that access level to all of them). Missing "access"
    # defaults to "read".
    config = load_config()
    entries = config.get("notebooks", [])
    if not entries:
        return NotebookAccess(False, False, frozenset(), frozenset())

    read_all = False
    write_all = False
    raw_read: set[str] = set()
    raw_write: set[str] = set()
    for entry in entries:
        # Shape and access-level validity are already checked by load_config().
        raw_id = str(entry.get("id", "")).strip()
        access = entry.get("access", "read")
        if not raw_id:
            continue
        if raw_id == "*":
            if access == "write":
                write_all = True
            else:
                read_all = True
        elif access == "write":
            raw_write.add(raw_id)
        else:
            raw_read.add(raw_id)

    if not (raw_read or raw_write):
        return NotebookAccess(read_all, write_all, frozenset(), frozenset())

    notebooks = await get_client().list_notebooks()
    ids = {n["id"] for n in notebooks}
    by_name: dict[str, set[str]] = {}
    for n in notebooks:
        by_name.setdefault(n["title"].casefold(), set()).add(n["id"])

    def resolve(parts: set[str]) -> frozenset[str]:
        resolved: set[str] = set()
        for part in parts:
            if part in ids:
                resolved.add(part)
            else:
                resolved |= by_name.get(part.casefold(), set())
        return frozenset(resolved)

    return NotebookAccess(read_all, write_all, resolve(raw_read), resolve(raw_write))


async def _require_access() -> NotebookAccess:
    # Fail-closed: note-content tools refuse to operate until notebook access
    # is explicitly configured, rather than defaulting to unrestricted access.
    access = await _notebook_access()
    if not access:
        raise NotebookAccessError(
            "No notebooks are configured for access. Add a `notebooks` list to "
            "the config file with {\"id\": <id or name>, \"access\": \"read\"|"
            "\"write\"} entries, or {\"id\": \"*\", \"access\": ...} for all."
        )
    return access


def _more_results_note(has_more: bool, limit: int) -> str:
    # `has_more` reflects Joplin's raw, unfiltered page - it says more results
    # exist, not that the caller can read them, so the message only claims
    # the former.
    if not has_more:
        return ""
    return f"\n\n(More results exist beyond this {limit}-item page; raise `limit` to see them.)"


@mcp.tool
async def search_notes(query: str, limit: int = 20) -> str:
    """Search Joplin notes by keyword. Returns matching note titles and ids."""
    access = await _require_access()
    notes, has_more = await get_client().search_notes(query, limit=limit)
    in_scope = [n for n in notes if access.can_read(n["parent_id"])]
    more = _more_results_note(has_more, limit)
    if not in_scope:
        if notes:
            return (
                f"Found {len(notes)} note(s) matching '{query}', but none are "
                f"in a notebook you have read access to.{more}"
            )
        return f"No notes found matching '{query}'.{more}"
    lines = [f"- {n['title']} (id: {n['id']})" for n in in_scope]
    return f"Found {len(in_scope)} note(s) matching '{query}':\n" + "\n".join(lines) + more


@mcp.tool
async def get_note(note_id: str) -> str:
    """Fetch the full content of a single Joplin note by its id."""
    access = await _require_access()
    note = await get_client().get_note(note_id)
    if not access.can_read(note["parent_id"]):
        raise NotebookAccessError(
            f"Note '{note_id}' is in notebook '{note['parent_id']}', which you "
            "do not have read access to."
        )
    header = f"# {note['title']}\n(id: {note['id']}, notebook: {note['parent_id']})\n"
    if note.get("is_todo"):
        header += f"To-do: {'done' if note.get('todo_completed') else 'not done'}\n"
    return f"{header}\n{note['body']}"


@mcp.tool
async def create_note(title: str, body: str, notebook_id: str) -> str:
    """Create a new note in the given notebook. Use list_notebooks to find a notebook_id."""
    access = await _require_access()
    if not access.can_write(notebook_id):
        raise NotebookAccessError(
            f"Notebook '{notebook_id}' is not configured for write access."
        )
    note = await get_client().create_note(title, body, notebook_id)
    return f"Created note '{note['title']}' (id: {note['id']})."


@mcp.tool
async def update_note(note_id: str, title: str | None = None, body: str | None = None) -> str:
    """Update an existing note's title and/or body. Only provided fields are changed."""
    access = await _require_access()
    existing = await get_client().get_note(note_id)
    if not access.can_write(existing["parent_id"]):
        raise NotebookAccessError(
            f"Note '{note_id}' is in notebook '{existing['parent_id']}', which "
            "is not configured for write access."
        )
    note = await get_client().update_note(note_id, title=title, body=body)
    return f"Updated note '{note['title']}' (id: {note['id']})."


@mcp.tool
async def delete_note(note_id: str) -> str:
    """Delete a note by its id. Moves it to Joplin's trash rather than a permanent delete."""
    access = await _require_access()
    existing = await get_client().get_note(note_id)
    if not access.can_write(existing["parent_id"]):
        raise NotebookAccessError(
            f"Note '{note_id}' is in notebook '{existing['parent_id']}', which "
            "is not configured for write access."
        )
    await get_client().delete_note(note_id)
    return f"Deleted note '{existing['title']}' (id: {note_id})."


@mcp.tool
async def complete_todo(note_id: str, completed: bool = True) -> str:
    """Mark a to-do note complete or incomplete. Fails if the note isn't a to-do."""
    access = await _require_access()
    existing = await get_client().get_note(note_id)
    if not access.can_write(existing["parent_id"]):
        raise NotebookAccessError(
            f"Note '{note_id}' is in notebook '{existing['parent_id']}', which "
            "is not configured for write access."
        )
    if not existing.get("is_todo"):
        raise JoplinError(f"Note '{note_id}' is not a to-do (is_todo=0).")
    note = await get_client().complete_todo(note_id, completed=completed)
    state = "complete" if completed else "incomplete"
    return f"Marked '{note['title']}' (id: {note_id}) as {state}."


@mcp.tool
async def list_notes_in_notebook(notebook_id: str, limit: int = 20) -> str:
    """List notes in a notebook without a search query. Use list_notebooks to find a notebook_id."""
    access = await _require_access()
    if not access.can_read(notebook_id):
        raise NotebookAccessError(
            f"Notebook '{notebook_id}' is not configured for read access."
        )
    notes, has_more = await get_client().list_notes_in_notebook(notebook_id, limit=limit)
    more = _more_results_note(has_more, limit)
    if not notes:
        return f"No notes found in notebook '{notebook_id}'.{more}"
    lines = [f"- {n['title']} (id: {n['id']})" for n in notes]
    return f"Found {len(notes)} note(s) in notebook '{notebook_id}':\n" + "\n".join(lines) + more


@mcp.tool
async def list_notebooks() -> str:
    """List all Joplin notebooks (folders) with their ids, for use with create_note."""
    notebooks = await get_client().list_notebooks()
    lines = [f"- {n['title']} (id: {n['id']})" for n in notebooks]
    return f"{len(notebooks)} notebook(s):\n" + "\n".join(lines)


@mcp.tool
async def list_tags() -> str:
    """List all Joplin tags with their ids, for use with get_notes_by_tag."""
    tags = await get_client().list_tags()
    if not tags:
        return "No tags found."
    lines = [f"- {t['title']} (id: {t['id']})" for t in tags]
    return f"{len(tags)} tag(s):\n" + "\n".join(lines)


@mcp.tool
async def get_notes_by_tag(tag_id: str, limit: int = 20) -> str:
    """List notes with a given tag. Use list_tags to find a tag_id."""
    access = await _require_access()
    notes, has_more = await get_client().get_notes_by_tag(tag_id, limit=limit)
    in_scope = [n for n in notes if access.can_read(n["parent_id"])]
    more = _more_results_note(has_more, limit)
    if not in_scope:
        if notes:
            return (
                f"Found {len(notes)} note(s) with this tag, but none are in "
                f"a notebook you have read access to.{more}"
            )
        return f"No notes found with tag '{tag_id}'.{more}"
    lines = [f"- {n['title']} (id: {n['id']})" for n in in_scope]
    return f"Found {len(in_scope)} note(s) with tag '{tag_id}':\n" + "\n".join(lines) + more


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
