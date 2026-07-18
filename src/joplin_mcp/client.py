"""Thin async wrapper around Joplin's local REST API (Web Clipper service)."""

import time
from typing import Any

import httpx


class JoplinError(Exception):
    """Raised when the Joplin API returns an error response."""


class JoplinClient:
    def __init__(self, token: str, host: str = "localhost", port: str = "41184") -> None:
        if not token:
            raise JoplinError(
                "No Joplin API token configured. Set `token` in the config file "
                "(Tools > Options > Web Clipper in Joplin Desktop for the value)."
            )
        self.token = token
        self.base_url = f"http://{host}:{port}"

    async def _request(
        self, method: str, path: str, params: dict | None = None, json: dict | None = None
    ) -> Any:
        params = dict(params or {})
        params["token"] = self.token
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(
                method, f"{self.base_url}{path}", params=params, json=json
            )
        if resp.status_code >= 400:
            raise JoplinError(f"Joplin API error {resp.status_code}: {resp.text}")
        if not resp.content:
            return None
        return resp.json()

    async def search_notes(self, query: str, limit: int = 20) -> list[dict]:
        data = await self._request(
            "GET",
            "/search",
            params={
                "query": query,
                "type": "note",
                "fields": "id,title,parent_id,updated_time",
                "limit": limit,
            },
        )
        return data.get("items", [])

    async def get_note(self, note_id: str) -> dict:
        return await self._request(
            "GET",
            f"/notes/{note_id}",
            params={
                "fields": "id,title,body,parent_id,created_time,updated_time,"
                "is_todo,todo_completed"
            },
        )

    async def create_note(self, title: str, body: str, notebook_id: str) -> dict:
        return await self._request(
            "POST",
            "/notes",
            json={"title": title, "body": body, "parent_id": notebook_id},
        )

    async def update_note(
        self, note_id: str, title: str | None = None, body: str | None = None
    ) -> dict:
        payload: dict[str, str] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if not payload:
            raise JoplinError("update_note requires at least one of title or body")
        return await self._request("PUT", f"/notes/{note_id}", json=payload)

    async def list_notebooks(self) -> list[dict]:
        data = await self._request(
            "GET", "/folders", params={"fields": "id,title,parent_id"}
        )
        return data.get("items", [])

    async def delete_note(self, note_id: str) -> None:
        # Joplin moves the note to its trash rather than deleting it outright
        # unless `permanent=1` is passed; we deliberately don't expose that.
        await self._request("DELETE", f"/notes/{note_id}")

    async def list_notes_in_notebook(self, notebook_id: str, limit: int = 20) -> list[dict]:
        data = await self._request(
            "GET",
            f"/folders/{notebook_id}/notes",
            params={"fields": "id,title,parent_id,updated_time", "limit": limit},
        )
        return data.get("items", [])

    async def list_tags(self) -> list[dict]:
        data = await self._request("GET", "/tags", params={"fields": "id,title"})
        return data.get("items", [])

    async def get_notes_by_tag(self, tag_id: str, limit: int = 20) -> list[dict]:
        data = await self._request(
            "GET",
            f"/tags/{tag_id}/notes",
            params={"fields": "id,title,parent_id,updated_time", "limit": limit},
        )
        return data.get("items", [])

    async def complete_todo(self, note_id: str, completed: bool) -> dict:
        # Joplin represents todo_completed as the completion timestamp (ms),
        # not a bool; 0 means not completed.
        payload = {"todo_completed": int(time.time() * 1000) if completed else 0}
        return await self._request("PUT", f"/notes/{note_id}", json=payload)
