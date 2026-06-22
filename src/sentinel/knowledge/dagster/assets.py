from dagster import (
    asset, sensor, RunRequest, SensorEvaluationContext,
    define_asset_job, AssetExecutionContext
)
from pathlib import Path
from ..crews.compilation_crew import run_compilation_crew
from ..config import KnowledgeConfig


@asset(group_name="knowledge_base")
def wiki_index(context: AssetExecutionContext) -> None:
    """The compiled wiki index — rebuilt whenever new articles are compiled."""
    config = KnowledgeConfig.from_env()
    compiled_dir = Path(config.compiled_dir)
    
    # Build index from all compiled articles
    articles = list(compiled_dir.rglob("*.md"))
    index_lines = ["# Wiki Index\n"]
    for article in sorted(articles):
        title = article.stem.replace("-", " ").title()
        index_lines.append(f"- [{title}]({article})")
    
    (compiled_dir / "_index.md").write_text("\n".join(index_lines))
    context.log.info(f"Index updated: {len(articles)} articles")


@sensor(job_name="compile_raw_document")
def new_raw_file_sensor(context: SensorEvaluationContext):
    """
    Watches raw/ for new files.
    When you drop a document in, this fires the Compilation Crew automatically.
    """
    config = KnowledgeConfig.from_env()
    raw_dir = Path(config.raw_dir)
    
    # Track which files we've already processed
    processed = set(context.cursor.split(",")) if context.cursor else set()
    new_files = []
    
    for file_path in raw_dir.rglob("*"):
        if file_path.is_file() and str(file_path) not in processed:
            new_files.append(file_path)
    
    if new_files:
        processed.update(str(f) for f in new_files)
        yield RunRequest(
            run_key=str(new_files[0]),
            run_config={"ops": {"compile": {"config": {"file": str(new_files[0])}}}},
        )
        context.update_cursor(",".join(processed))
