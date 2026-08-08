import pytest

from joplin_mcp.server import NotebookAccess, NotebookAccessError, _notebook_access, _require_access


# --- NotebookAccess unit tests (no I/O) ---------------------------------


def test_write_implies_read():
    access = NotebookAccess(False, True, frozenset(), frozenset({"a"}))
    assert access.can_read("a")
    assert access.can_write("a")


def test_read_only_does_not_imply_write():
    access = NotebookAccess(False, False, frozenset({"a"}), frozenset())
    assert access.can_read("a")
    assert not access.can_write("a")


def test_root_only_grant_is_falsy():
    # Regression test: a config that only grants `$root` (no read/write on
    # any notebook) must not satisfy `bool(access)` - that gate is used by
    # `_require_access()` to fail-closed note-content tools, and `$root`
    # carries no note-content access at all.
    access = NotebookAccess(False, False, frozenset(), frozenset(), can_create_root=True)
    assert not access
    assert access.can_create_root_notebook()


def test_empty_access_is_falsy():
    access = NotebookAccess(False, False, frozenset(), frozenset())
    assert not access
    assert not access.can_create_root_notebook()


def test_write_all_implies_can_create_root():
    access = NotebookAccess(False, True, frozenset(), frozenset())
    assert access.can_create_root_notebook()


# --- _notebook_access() resolution tests --------------------------------


async def test_no_notebooks_entry_grants_nothing(set_config, fake_client):
    set_config([])
    access = await _notebook_access()
    assert not access


async def test_star_read_grants_read_all(set_config, fake_client):
    set_config([{"id": "*", "access": "read"}])
    access = await _notebook_access()
    assert access.can_read("anything")
    assert not access.can_write("anything")


async def test_star_write_grants_write_all(set_config, fake_client):
    set_config([{"id": "*", "access": "write"}])
    access = await _notebook_access()
    assert access.can_read("anything")
    assert access.can_write("anything")
    assert access.can_create_root_notebook()


async def test_entry_resolved_by_exact_id(set_config, fake_client):
    set_config([{"id": "notebook-a-id", "access": "write"}])
    access = await _notebook_access()
    assert access.can_write("notebook-a-id")
    assert not access.can_write("notebook-b-id")


async def test_entry_resolved_by_name_case_insensitive(set_config, fake_client):
    set_config([{"id": "notebook a", "access": "write"}])
    access = await _notebook_access()
    assert access.can_write("notebook-a-id")


async def test_name_matching_multiple_notebooks_grants_all(set_config, fake_client):
    set_config([{"id": "Shared Name", "access": "read"}])
    access = await _notebook_access()
    assert access.can_read("dup-a-id")
    assert access.can_read("dup-b-id")


async def test_root_write_grants_create_root_but_not_note_access(set_config, fake_client):
    set_config([{"id": "$root", "access": "write"}])
    access = await _notebook_access()
    assert access.can_create_root_notebook()
    assert not access.can_read("notebook-a-id")
    assert not access.can_write("notebook-a-id")
    assert not access  # no note-content access at all


async def test_root_read_is_a_noop(set_config, fake_client):
    set_config([{"id": "$root", "access": "read"}])
    access = await _notebook_access()
    assert not access.can_create_root_notebook()


async def test_root_is_case_sensitive(set_config, fake_client):
    # "$Root" isn't the sentinel - it falls through to name/id resolution
    # and matches no real notebook, granting nothing.
    set_config([{"id": "$Root", "access": "write"}])
    access = await _notebook_access()
    assert not access.can_create_root_notebook()


async def test_root_combined_with_named_notebook(set_config, fake_client):
    set_config([{"id": "$root", "access": "write"}, {"id": "Notebook A", "access": "write"}])
    access = await _notebook_access()
    assert access.can_create_root_notebook()
    assert access.can_write("notebook-a-id")


# --- _require_access() fail-closed gate ---------------------------------


async def test_require_access_raises_on_empty_config(set_config, fake_client):
    set_config([])
    with pytest.raises(NotebookAccessError):
        await _require_access()


async def test_require_access_raises_on_root_only_config(set_config, fake_client):
    # Regression test for the fail-open bug: a $root-only config must not
    # satisfy the fail-closed gate used by note-content tools.
    set_config([{"id": "$root", "access": "write"}])
    with pytest.raises(NotebookAccessError):
        await _require_access()


async def test_require_access_passes_with_real_grant(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "read"}])
    access = await _require_access()
    assert access.can_read("notebook-a-id")
