To feed this conversation into a BMAD workflow (such as `bmad-spec`, `bmad-prd`, or `bmad-quick-dev`), you need to compress the intent into a clean, context-rich starting document.

Here is the conversation summarized as a **Raw Intent / Product Brief** formatted specifically for your BMAD Analyst or PM agent to ingest. You can save this as `intent.md` or drop it directly into your chat to kick off the planning phase.

---

# Project Intent: Open-Source PowerPoint Agent Skills

## 1. Goal (The "What")

Equip our AI agents (Claude Code, Cursor, Copilot) with the ability to read, modify, and generate Microsoft PowerPoint (`.pptx`) documents using exclusively MIT/Apache 2.0 licensed tools.

## 2. Business Context (The "Why")

The current known implementation (`document-skills/pptx` from `ComposioHQ/awesome-claude-skills`) is explicitly tagged with a `Proprietary` license by Anthropic. This creates a legal blocker that prevents us from modifying the code, embedding it in internal enterprise tools, or redistributing it commercially. We must replace this capability with open-source alternatives to remove legal risk and enable commercial viability.

## 3. Technical Constraints & Architecture Input

The BMAD **Architect** agent should evaluate and select from the following five validated, MIT-licensed open-source solutions based on our target deployment environment. We are shifting from standalone proprietary Markdown skills to Model Context Protocol (MCP) servers or permissive CLI drop-ins.

* **Option A (Python / Cross-Platform):** `Office-PowerPoint-MCP-Server` (GongRzhe). Uses `python-pptx` under the hood. Best for comprehensive XML-level slide generation, table formatting, and automatic font scaling via an MCP server.  Office-PowerPoint-MCP-Server

    Repository: [https://github.com/GongRzhe/Office-PowerPoint-MCP-Server](https://github.com/GongRzhe/Office-PowerPoint-MCP-Server)

    Note: The most complete OSS Python option; features 32 tools and automated font/layout scaling.  

* **Option B (Windows Native / Desktop):** `mcp-server-ppt` (trsdn). Uses Microsoft COM Interop via MCP. Best if the agent needs to drive the local PowerPoint GUI application live on a Windows desktop.  mcp-server-ppt

    Repository: [https://github.com/trsdn/mcp-server-ppt](https://github.com/trsdn/mcp-server-ppt)

    Note: Uses COM Interop to drive the local Windows PowerPoint application natively.
* **Option C (Drop-in IDE Skill):** `ppt-master` (hugohe3). A direct CLI/IDE skill folder. Best for immediate use in Cursor or Claude Code to generate decks from PDFs/docs with native animations.      
    Repository: [https://github.com/hugohe3/ppt-master](https://github.com/hugohe3/ppt-master)  
    Note: A direct, drop-in CLI skill specifically built for generating slides and audio scripts from source documents.
* **Option D (.NET Core):** `pptx-tools` (jongalloway). Best if we need surgical modifications (updating specific placeholders or existing Excel-backed charts) without breaking enterprise templates.  pptx-tools

    Repository: [https://github.com/jongalloway/pptx-tools](https://github.com/jongalloway/pptx-tools)

    Note: Built in .NET; optimized for extracting content and selectively updating placeholders/chart data.  
    
* **Option E (Node.js / SaaS):** MiniMax-AI `pptx-generator`. Uses `PptxGenJS`. Best for embedding in a commercial web app or Node environment, driven by a strict design system/color palette.  MiniMax-AI pptx-generator (Fork)

    Repository: [https://github.com/bruc3van/bruce-pptx-generator](https://github.com/bruc3van/bruce-pptx-generator)

    Note: This is the specific open-source fork (using pptxgenjs / Node) adapted from the MiniMax skills library to work universally with AI agents like Claude Code and OpenClaw.

## 4. Acceptance Criteria (For the QA / TEA Agent)

* **License Check:** The final integrated solution must contain exactly zero proprietary code (must be MIT or Apache 2.0).
* **Read Capability:** The agent can successfully ingest a `.pptx` file and extract the text content (e.g., using a tool like MarkItDown or python-pptx).
* **Write Capability:** The agent can successfully generate a new `.pptx` file or modify an existing one without corrupting the file structure.
* **Integration:** The solution successfully registers as a callable tool/skill within our chosen agent framework (via MCP or `.md` skill injection).
