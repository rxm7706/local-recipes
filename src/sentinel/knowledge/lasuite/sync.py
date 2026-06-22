from pathlib import Path
from .client import LaSuiteClient


class WikiSyncer:
    """Syncs compiled wiki markdown files → La Suite Docs.
    
    Maintains a local mapping file so we know which La Suite 
    document ID corresponds to each local markdown file.
    This lets us UPDATE articles instead of creating duplicates.
    """

    MAPPING_FILE = Path("wiki/compiled/.lasuite_ids.json")

    def __init__(self, client: LaSuiteClient):
        self.client = client
        self.mapping = self._load_mapping()

    def sync_file(self, md_path: Path) -> None:
        """Push a single markdown file to La Suite Docs."""
        content = md_path.read_text()
        title = self._extract_title(content)
        key = str(md_path)

        if key in self.mapping:
            # Article already exists — update it
            self.client.update_document(
                doc_id=self.mapping[key],
                title=title,
                content=content,
            )
        else:
            # New article — create it
            result = self.client.create_document(title=title, content=content)
            self.mapping[key] = result["id"]
            self._save_mapping()

    def sync_all(self, compiled_dir: Path) -> None:
        """Sync all compiled wiki files to La Suite Docs."""
        for md_file in compiled_dir.rglob("*.md"):
            self.sync_file(md_file)

    def _extract_title(self, content: str) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled"

    def _load_mapping(self) -> dict:
        if self.MAPPING_FILE.exists():
            import json
            return json.loads(self.MAPPING_FILE.read_text())
        return {}

    def _save_mapping(self) -> None:
        import json
        self.MAPPING_FILE.write_text(json.dumps(self.mapping, indent=2))
