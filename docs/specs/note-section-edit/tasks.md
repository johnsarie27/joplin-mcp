# Tasks: Safe partial-edit tools for notes

Source: [requirements.md](./requirements.md) · [design.md](./design.md)

Run `uv run pytest` after each task to confirm the suite stays green
end-to-end; each task also lists its own specific verification.

- [x] 1. Add `update_note` support to `FakeJoplinClient` in
      `tests/conftest.py`: make the fixture's note body mutable
      (`self.note = {...}` instance dict instead of a hardcoded literal in
      `get_note`) and add an `update_note(note_id, title=None, body=None)`
      method that records the call in `self.calls` and updates `self.note`.
      Verify: `uv run pytest` — existing suite still passes unchanged (no
      new tests yet, this is a fixture-only change).

- [x] 2. Add `_find_all_occurrences(body: str, old_str: str) -> list[int]`
      to `src/joplin_mcp/server.py` (non-overlapping match start indices).
      Verify: new tests in `tests/test_tools.py` — zero matches returns
      `[]`; one match returns a single index; multiple non-overlapping
      matches return all indices in order; adjacent/overlapping-candidate
      matches (e.g. `old_str="aa"` in `"aaaa"`) return non-overlapping
      results consistent with `str.count`.

- [x] 3. Add `_match_context(body: str, index: int, length: int, radius: int = 40) -> str`
      to `server.py` (bounded snippet around one match, `...`-prefixed/
      suffixed when truncated, newlines escaped to literal `\n`).
      Verify: new tests — match in the middle of a long body gets both
      `...` markers; match at the very start/end of body gets only the
      applicable marker; a snippet spanning a newline renders it as `\n`
      on one line.

- [x] 4. Add `_append_with_separator(body: str, content: str) -> str` to
      `server.py` per design (empty body → `content`; body already ending
      `"\n\n"` → unchanged concatenation; otherwise `rstrip("\n")` then
      `"\n\n"` then `content`).
      Verify: new tests — empty body, body with no trailing newline, body
      ending in a single `\n`, and body already ending in `"\n\n"` each
      produce the expected joined string.

- [x] 5. Add the `update_note_section(note_id, old_str, new_str)` tool to
      `server.py`, positioned after `update_note`: reuse
      `_require_access()`/`can_write()` exactly as `update_note` does;
      raise `JoplinError` up front if `old_str == ""`; call
      `_find_all_occurrences`; raise `JoplinError` (no write) on zero
      matches; raise `JoplinError` with one `_match_context` snippet per
      match (no write) on multiple matches; on exactly one match, build
      the new body by slicing at the match index and call
      `client.update_note(note_id, body=new_body)`. Satisfies the
      `update_note_section` acceptance criteria in requirements.md.
      Verify: new tests in `tests/test_tools.py` —
      (a) single match: fake client's recorded `update_note` call carries
      the correctly-substituted body, tool returns a confirmation naming
      the note;
      (b) zero matches: `JoplinError` raised, fake client records no
      `update_note` call;
      (c) multiple matches: `JoplinError` raised whose message contains a
      snippet for each match, fake client records no `update_note` call;
      (d) empty `old_str`: `JoplinError` raised, fake client records no
      calls at all;
      (e) no write access to the note's notebook: `NotebookAccessError`
      raised, fake client records no `update_note` call (mirror the
      write-access test shape used for `create_note` in
      `test_create_note_rejects_root_only_config`).

- [x] 6. Add the `append_note_section(note_id, content)` tool to
      `server.py`, positioned after `update_note_section`: reuse the same
      access check, call `_append_with_separator`, then
      `client.update_note(note_id, body=new_body)`. Satisfies the
      `append_note_section` acceptance criteria in requirements.md.
      Verify: new tests —
      (a) non-empty body without a trailing blank line: recorded
      `update_note` body equals `body + "\n\n" + content`;
      (b) body already ending in a blank line: recorded body equals
      `body + content` with no extra separator inserted;
      (c) no write access: `NotebookAccessError` raised, fake client
      records no `update_note` call.

- [x] 7. Update `update_note`'s docstring in `server.py` to state plainly
      that `body`, if provided, replaces the entire note body (not a patch
      or append), and points callers at `update_note_section` /
      `append_note_section` for partial edits. No runtime behavior change.
      Verify: read the docstring back; confirm it names both new tools and
      the word "replaces" (or equivalent) appears; `uv run pytest` still
      green (behavior untouched).

- [x] 8. Update `README.md`: add `update_note_section` and
      `append_note_section` rows to the **Tools** table (after
      `update_note`), and add both names to the **Access control** section
      alongside the other write-scoped tools (the `write` requirement list
      and the scoping-tools list) since both require `write` access the
      same way `update_note` does.
      Verify: `grep -n "update_note_section\|append_note_section" README.md`
      shows both names in the Tools table and in the Access control
      section.

- [x] 9. Full verification pass: `uv run pytest` (entire suite green,
      including all tests added above); re-read `requirements.md`
      acceptance criteria one by one and confirm each is covered by a
      passing test or a documentation change.

---

Approve tasks, or tell me what to change. Implementation starts only after
this list is approved.
