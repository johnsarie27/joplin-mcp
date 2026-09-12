import pytest

from joplin_mcp.server import (
    JoplinError,
    NotebookAccessError,
    _append_with_separator,
    _find_all_occurrences,
    _match_context,
    append_note_section,
    create_note,
    create_notebook,
    search_notes,
    update_note_section,
)


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


# --- _find_all_occurrences -------------------------------------------------


def test_find_all_occurrences_zero_matches():
    assert _find_all_occurrences("hello world", "xyz") == []


def test_find_all_occurrences_one_match():
    assert _find_all_occurrences("hello world", "world") == [6]


def test_find_all_occurrences_multiple_matches():
    assert _find_all_occurrences("ab cd ab ef ab", "ab") == [0, 6, 12]


def test_find_all_occurrences_non_overlapping():
    # Matches str.count()'s non-overlapping semantics: "aa" in "aaaa" is 2,
    # not 3.
    assert _find_all_occurrences("aaaa", "aa") == [0, 2]


# --- _match_context ---------------------------------------------------------


def test_match_context_truncates_both_sides():
    body = "x" * 60 + "TARGET" + "y" * 60
    snippet = _match_context(body, 60, len("TARGET"))
    assert snippet.startswith("...")
    assert snippet.endswith("...")
    assert "TARGET" in snippet


def test_match_context_no_prefix_at_start():
    body = "TARGET" + "y" * 60
    snippet = _match_context(body, 0, len("TARGET"))
    assert not snippet.startswith("...")
    assert snippet.endswith("...")


def test_match_context_no_suffix_at_end():
    body = "x" * 60 + "TARGET"
    snippet = _match_context(body, 60, len("TARGET"))
    assert snippet.startswith("...")
    assert not snippet.endswith("...")


def test_match_context_escapes_newlines():
    body = "line one\nTARGET\nline three"
    snippet = _match_context(body, 9, len("TARGET"))
    assert "\\n" in snippet
    assert "\n" not in snippet


# --- _append_with_separator -------------------------------------------------


def test_append_with_separator_empty_body():
    assert _append_with_separator("", "new content") == "new content"


def test_append_with_separator_no_trailing_newline():
    assert _append_with_separator("existing", "new") == "existing\n\nnew"


def test_append_with_separator_single_trailing_newline():
    assert _append_with_separator("existing\n", "new") == "existing\n\nnew"


def test_append_with_separator_already_blank_line():
    assert _append_with_separator("existing\n\n", "new") == "existing\n\nnew"


# --- update_note_section -----------------------------------------------------


async def test_update_note_section_replaces_unique_match(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "write"}])
    fake_client.note["body"] = "the quick brown fox"
    result = await update_note_section(
        note_id="note-1", old_str="brown", new_str="red"
    )
    assert "Updated note" in result
    assert ("update_note", "note-1", None, "the quick red fox") in fake_client.calls


async def test_update_note_section_rejects_empty_old_str(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "write"}])
    with pytest.raises(JoplinError):
        await update_note_section(note_id="note-1", old_str="", new_str="x")
    assert fake_client.calls == []


async def test_update_note_section_no_match_raises_and_does_not_write(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "write"}])
    fake_client.note["body"] = "the quick brown fox"
    with pytest.raises(JoplinError):
        await update_note_section(note_id="note-1", old_str="missing", new_str="x")
    assert not any(call[0] == "update_note" for call in fake_client.calls)


async def test_update_note_section_multiple_matches_raises_with_snippets(
    set_config, fake_client
):
    set_config([{"id": "Notebook A", "access": "write"}])
    fake_client.note["body"] = "ab cd ab ef ab"
    with pytest.raises(JoplinError) as exc_info:
        await update_note_section(note_id="note-1", old_str="ab", new_str="x")
    assert "3 times" in str(exc_info.value)
    assert not any(call[0] == "update_note" for call in fake_client.calls)


async def test_update_note_section_match_is_case_sensitive(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "write"}])
    fake_client.note["body"] = "the Quick brown fox"
    with pytest.raises(JoplinError):
        await update_note_section(note_id="note-1", old_str="quick", new_str="slow")
    assert not any(call[0] == "update_note" for call in fake_client.calls)


async def test_update_note_section_requires_write_access(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "read"}])
    with pytest.raises(NotebookAccessError):
        await update_note_section(note_id="note-1", old_str="quick", new_str="slow")
    assert not any(call[0] == "update_note" for call in fake_client.calls)


# --- append_note_section ------------------------------------------------------


async def test_append_note_section_inserts_separator(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "write"}])
    fake_client.note["body"] = "existing content"
    await append_note_section(note_id="note-1", content="new content")
    assert (
        "update_note",
        "note-1",
        None,
        "existing content\n\nnew content",
    ) in fake_client.calls


async def test_append_note_section_no_extra_separator_when_already_blank(
    set_config, fake_client
):
    set_config([{"id": "Notebook A", "access": "write"}])
    fake_client.note["body"] = "existing content\n\n"
    await append_note_section(note_id="note-1", content="new content")
    assert (
        "update_note",
        "note-1",
        None,
        "existing content\n\nnew content",
    ) in fake_client.calls


async def test_append_note_section_requires_write_access(set_config, fake_client):
    set_config([{"id": "Notebook A", "access": "read"}])
    with pytest.raises(NotebookAccessError):
        await append_note_section(note_id="note-1", content="new content")
    assert not any(call[0] == "update_note" for call in fake_client.calls)
