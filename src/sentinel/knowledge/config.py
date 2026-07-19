import os
from pathlib import Path


class KnowledgeConfig:
    def __init__(
        self,
        lasuite_url: str,
        lasuite_api_token: str,
        compiled_dir: str,
        raw_dir: str,
    ):
        self.lasuite_url = lasuite_url
        self.lasuite_api_token = lasuite_api_token
        self.compiled_dir = compiled_dir
        self.raw_dir = raw_dir

    @classmethod
    def from_env(cls) -> "KnowledgeConfig":
        return cls(
            lasuite_url=os.getenv("LASUITE_BASE_URL", "https://cms.example"),
            lasuite_api_token=os.getenv("LASUITE_API_TOKEN", "mock-token"),
            compiled_dir=os.getenv("WIKI_COMPILED_DIR", "wiki/compiled"),
            raw_dir=os.getenv("WIKI_RAW_DIR", "wiki/raw"),
        )
