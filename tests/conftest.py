import pytest

NOTEBOOKS = [
    {"id": "notebook-a-id", "title": "Notebook A", "parent_id": ""},
    {"id": "notebook-b-id", "title": "Notebook B", "parent_id": ""},
    {"id": "dup-a-id", "title": "Shared Name", "parent_id": ""},
    {"id": "dup-b-id", "title": "Shared Name", "parent_id": "notebook-a-id"},
]


class FakeJoplinClient:
    """Records calls instead of hitting a real Joplin instance."""

    def __init__(self):
        self.calls = []

    async def list_notebooks(self):
        return NOTEBOOKS

    async def create_note(self, title, body, notebook_id):
        self.calls.append(("create_note", title, body, notebook_id))
        return {"id": "new-note-id", "title": title}

    async def create_notebook(self, title, parent_id=None):
        self.calls.append(("create_notebook", title, parent_id))
        return {"id": "new-notebook-id", "title": title}

    async def get_note(self, note_id):
        self.calls.append(("get_note", note_id))
        return {
            "id": note_id,
            "title": "Existing note",
            "body": "body text",
            "parent_id": "notebook-a-id",
            "is_todo": 0,
            "todo_completed": 0,
        }


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeJoplinClient()
    monkeypatch.setattr("joplin_mcp.server.get_client", lambda: client)
    return client


@pytest.fixture
def set_config(monkeypatch):
    def _set(notebooks):
        monkeypatch.setattr(
            "joplin_mcp.server.load_config", lambda: {"notebooks": notebooks}
        )

    return _set
