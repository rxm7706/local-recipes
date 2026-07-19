import logging
import json
import httpx
from pathlib import Path
from .client import LaSuiteClient

logger = logging.getLogger(__name__)


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

    def sync_file(self, md_path: Path) -> bool:
        """Push a single markdown file to La Suite Docs.
        
        Returns True on success, or False if a connection timeout/error occurs.
        """
        content = md_path.read_text()
        title = self._extract_title(content)
        key = str(md_path)

        try:
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
            return True
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.error("Connection timeout/error syncing %s to La Suite: %s", md_path, exc)
            return False

    def sync_all(self, compiled_dir: Path) -> dict[str, list[str]]:
        """Sync all compiled wiki files to La Suite Docs.
        
        Returns a dict summarizing synced and failed files.
        """
        results = {"synced": [], "failed": []}
        for md_file in compiled_dir.rglob("*.md"):
            if md_file.name == "_index.md":
                continue
            success = self.sync_file(md_file)
            if success:
                results["synced"].append(md_file.name)
            else:
                results["failed"].append(md_file.name)
        return results

    def _extract_title(self, content: str) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled"

    def _load_mapping(self) -> dict:
        if self.MAPPING_FILE.exists():
            try:
                return json.loads(self.MAPPING_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to parse mapping file, starting fresh")
        return {}

    def _save_mapping(self) -> None:
        self.MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.MAPPING_FILE.write_text(json.dumps(self.mapping, indent=2))
