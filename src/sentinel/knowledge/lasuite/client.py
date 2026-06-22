import httpx
from pathlib import Path


class LaSuiteClient:
    """REST API client for La Suite Docs.
    
    Agents use this to push wiki articles into La Suite Docs.
    All content is written by agents — humans just read and browse.
    """

    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def create_document(self, title: str, content: str, parent_id: str | None = None) -> dict:
        """Create a new wiki article in La Suite Docs."""
        payload = {
            "title": title,
            "content": content,
        }
        if parent_id:
            payload["parent"] = parent_id

        response = httpx.post(
            f"{self.base_url}/api/v1/documents/",
            json=payload,
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    def update_document(self, doc_id: str, title: str, content: str) -> dict:
        """Update an existing wiki article (used by Linter repairs)."""
        response = httpx.patch(
            f"{self.base_url}/api/v1/documents/{doc_id}/",
            json={"title": title, "content": content},
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    def list_documents(self) -> list[dict]:
        """Fetch all documents — used by Linker to find related articles."""
        response = httpx.get(
            f"{self.base_url}/api/v1/documents/all/",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    def get_document(self, doc_id: str) -> dict:
        """Fetch a single document by ID."""
        response = httpx.get(
            f"{self.base_url}/api/v1/documents/{doc_id}/",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()
