import pytest

from joplin_mcp.server import NotebookAccessError, create_note, create_notebook, search_notes


# --- create_notebook: root vs. nested, gated independently ---------------


async def test_create_notebook_root_requires_root_grant(set_config, fake_client):
    set_config([])
    with pytest.raises(NotebookAccessError):
        await create_notebook(title="New")
    assert fake_client.calls == []


async def test_create_notebook_root_succeeds_with_root_only_grant(set_config, fake_client):
    # The whole point of `$root`: root creation works even with zero
    # read/write access to any actual notebook.
    set_config([{"id": "$root", "access": "write"}])
    result = await create_notebook(title="New")
    assert "Created notebook" in result
    assert fake_client.calls == [("create_notebook", "New", None)]


async def test_create_notebook_nested_requires_write_on_parent(set_config, fake_client):
    set_config([{"id": "$root", "access": "write"}])
    with pytest.raises(NotebookAccessError):
        await create_notebook(title="New", parent_id="notebook-a-id")
    assert fake_client.calls == []


async def test_create_notebook_nested_succeeds_with_write_access(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "write"}])
    result = await create_notebook(title="New", parent_id="notebook-a-id")
    assert "Created notebook" in result
    assert fake_client.calls == [("create_notebook", "New", "notebook-a-id")]


# --- note-content tools stay fail-closed for a $root-only config ---------


async def test_search_notes_rejects_root_only_config(set_config, fake_client):
    set_config([{"id": "$root", "access": "write"}])
    with pytest.raises(NotebookAccessError):
        await search_notes(query="anything")


async def test_create_note_rejects_root_only_config(set_config, fake_client):
    set_config([{"id": "$root", "access": "write"}])
    with pytest.raises(NotebookAccessError):
        await create_note(title="t", body="b", notebook_id="notebook-a-id")
    assert fake_client.calls == []


async def test_create_note_succeeds_with_write_access(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "write"}])
    result = await create_note(title="t", body="b", notebook_id="notebook-a-id")
    assert "Created note" in result
    assert fake_client.calls == [("create_note", "t", "b", "notebook-a-id")]
