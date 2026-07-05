"""FastMCP server exposing Joplin note operations as MCP tools."""

from functools import lru_cache

from fastmcp import FastMCP

from joplin_mcp.client import JoplinClient

mcp = FastMCP("joplin")


@lru_cache
def get_client() -> JoplinClient:
    # Cached so we reuse one client/token for the life of the process,
    # but constructed lazily so a missing token fails at first tool call
    # (with a clear error) rather than at import time.
    return JoplinClient()


@mcp.tool
async def search_notes(query: str, limit: int = 20) -> str:
    """Search Joplin notes by keyword. Returns matching note titles and ids."""
    notes = await get_client().search_notes(query, limit=limit)
    if not notes:
        return f"No notes found matching '{query}'."
    lines = [f"- {n['title']} (id: {n['id']})" for n in notes]
    return f"Found {len(notes)} note(s) matching '{query}':\n" + "\n".join(lines)


@mcp.tool
async def get_note(note_id: str) -> str:
    """Fetch the full content of a single Joplin note by its id."""
    note = await get_client().get_note(note_id)
    return (
        f"# {note['title']}\n"
        f"(id: {note['id']}, notebook: {note['parent_id']})\n\n"
        f"{note['body']}"
    )


@mcp.tool
async def create_note(title: str, body: str, notebook_id: str) -> str:
    """Create a new note in the given notebook. Use list_notebooks to find a notebook_id."""
    note = await get_client().create_note(title, body, notebook_id)
    return f"Created note '{note['title']}' (id: {note['id']})."


@mcp.tool
async def update_note(note_id: str, title: str | None = None, body: str | None = None) -> str:
    """Update an existing note's title and/or body. Only provided fields are changed."""
    note = await get_client().update_note(note_id, title=title, body=body)
    return f"Updated note '{note['title']}' (id: {note['id']})."


@mcp.tool
async def list_notebooks() -> str:
    """List all Joplin notebooks (folders) with their ids, for use with create_note."""
    notebooks = await get_client().list_notebooks()
    lines = [f"- {n['title']} (id: {n['id']})" for n in notebooks]
    return f"{len(notebooks)} notebook(s):\n" + "\n".join(lines)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
