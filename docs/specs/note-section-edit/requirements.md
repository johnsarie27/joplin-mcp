# Requirements: Safe partial-edit tools for notes

Source: [GitHub issue #47](https://github.com/johnsarie27/joplin-mcp/issues/47)

## Problem / motivation

`update_note`'s `body` parameter fully overwrites a note's content. When a
caller (an LLM driving this MCP server) sends only the changed portion
instead of the complete note body, everything else is silently deleted.
This has caused repeated accidental data loss. There is currently no way to
make a targeted edit to part of a note without re-sending the entire body.

## User stories

- As an MCP client editing a note, I want to replace one exact, unique
  passage in a note's body without resending the whole note, so that I
  can't accidentally wipe unrelated content.
- As an MCP client, I want a clear error (with no write performed) when my
  target text isn't found or isn't unique, so I can correct my input before
  any data is changed.
- As an MCP client, I want to append content to the end of a note without
  needing to know or repeat its existing content, so I can add material
  (e.g. a new log entry) safely.
- As a developer reading tool descriptions, I want `update_note`'s docstring
  to state plainly that `body` replaces the whole note, so the overwrite
  behavior isn't a surprise.

## Acceptance criteria

**`update_note_section(note_id, old_str, new_str)`**

- WHEN `old_str` occurs exactly once in the note's current body, THE SYSTEM
  SHALL replace that occurrence with `new_str` and write the updated body,
  returning a confirmation naming the note.
- WHEN `old_str` occurs zero times in the note's current body, THE SYSTEM
  SHALL raise an error identifying that no match was found and SHALL NOT
  write any change.
- WHEN `old_str` occurs more than once in the note's current body, THE
  SYSTEM SHALL raise an error asking the caller to supply more surrounding
  context, SHALL include a short context snippet (surrounding characters)
  for each match to help the caller disambiguate without a separate
  `get_note` call, and SHALL NOT write any change.
- WHEN the caller lacks write access to the note's notebook (per existing
  `NotebookAccess` rules), THE SYSTEM SHALL raise `NotebookAccessError` and
  SHALL NOT write any change, consistent with `update_note`'s existing
  access check.
- Matching is an exact, case-sensitive, literal substring match (no regex,
  no whitespace normalization).

**`update_note` documentation**

- THE `update_note` tool's docstring SHALL state explicitly that `body`
  replaces the entire note body, not a patch or append, and SHALL point
  callers at `update_note_section`/`append_note_section` for partial edits.
- `update_note`'s runtime behavior is unchanged — this is a documentation-only
  acceptance criterion.

**`append_note_section(note_id, content)`**

- WHEN called, THE SYSTEM SHALL append `content` to the end of the note's
  current body and write the result, returning a confirmation naming the
  note.
- THE SYSTEM SHALL enforce the same write-access check as `update_note`.
- Open question below: separator behavior between existing body and
  appended content.

## Out of scope

- Structural/regex-based or line-number-based patch formats (e.g. diff/patch
  application). Only exact literal substring replacement is covered.
- Multi-edit batching (applying several old_str/new_str pairs in one call).
- Any change to `create_note`, `delete_note`, or other existing tools.
- Note revision history / undo (tracked separately in issue #19).

## Decisions

1. `append_note_section` is included in this pass (not deferred).
2. `append_note_section` inserts `\n\n` between the existing body and the
   appended content, unless the body is empty or already ends in one.
3. Zero-match and multiple-match errors raise the existing `JoplinError`
   (no new exception class).
4. The multiple-match error includes a short context snippet (surrounding
   characters) for each match, not just a count.

---

Approve requirements, or tell me what to change.
