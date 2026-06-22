from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.file import FileTools
from pathlib import Path
from ..lasuite.client import LaSuiteClient
from ..lasuite.sync import WikiSyncer
from ..config import KnowledgeConfig


def run_compilation_crew(raw_file_path: Path, config: KnowledgeConfig) -> None:
    """
    Compile a single raw document into the wiki.
    
    This is called by Dagster when a new file lands in raw/.
    
    Args:
        raw_file_path: Path to the new document in raw/
        config: Configuration (La Suite URL, API token, wiki paths)
    """

    # --- Tools ---
    # Agno provides built-in FileTools for reading/writing
    file_tools = FileTools(
        base_dir=Path.cwd(),
        read_file=True,
        write_file=True,
        list_files=True
    )

    # --- Agents (BMAD personas loaded from .md files) ---
    ingester = Agent(
        name="Knowledge Ingester",
        description=Path("agents/ingester.md").read_text() if Path("agents/ingester.md").exists() else "You extract key topics and structure from raw documents.",
        tools=[file_tools],
        model=Claude(id="claude-3-5-sonnet-20241022"),
        show_tool_calls=True,
    )

    compiler = Agent(
        name="Knowledge Compiler",
        description=Path("agents/compiler.md").read_text() if Path("agents/compiler.md").exists() else "You transform raw documents into structured wiki articles.",
        tools=[file_tools],
        model=Claude(id="claude-3-5-sonnet-20241022"),
        show_tool_calls=True,
    )

    linker = Agent(
        name="Knowledge Linker",
        description=Path("agents/linker.md").read_text() if Path("agents/linker.md").exists() else "You connect the new article to related existing wiki articles.",
        tools=[file_tools],
        model=Claude(id="claude-3-5-sonnet-20241022"),
        show_tool_calls=True,
    )

    # --- Execution (BMAD: sequential workflow) ---
    
    # 1. Ingest
    ingester_response = ingester.run(
        f"""
        Read the document at: {raw_file_path}
        
        Extract:
        1. The main topic (one sentence)
        2. Key concepts covered (bullet list)
        3. Suggested wiki article title
        4. Which compiled/ subfolder it belongs in (concepts/, how-to/, decisions/)
        
        Output a structured summary for the Compiler agent.
        """
    )

    # 2. Compile
    compiler_response = compiler.run(
        f"""
        Using the Ingester's summary: {ingester_response.content}
        
        Read the original raw document at {raw_file_path} and write 
        a wiki article to the compiled/ directory.
        
        Format:
        ```
        summary: <one sentence summary>
        tags: [tag1, tag2]
        
        # <Article Title>
        
        ## Overview
        
        ## Key Concepts
        
        ## How It Works
        
        ## Related Articles
        ```
        
        Save to: compiled/<subfolder>/<slug>.md
        Also update: compiled/_index.md with the new entry
        """
    )

    # 3. Link
    linker.run(
        f"""
        The compiler just wrote this article: {compiler_response.content}
        
        Read the newly compiled article and all existing articles in compiled/.
        
        Find articles that are related and update both the new article's 
        'Related Articles' section AND add a backlink in each related article.
        
        Only link articles that are genuinely related — don't create noise.
        """
    )

    # --- Sync to La Suite Docs ---
    client = LaSuiteClient(
        base_url=config.lasuite_url,
        api_token=config.lasuite_api_token,
    )
    syncer = WikiSyncer(client=client)
    syncer.sync_all(Path(config.compiled_dir))
