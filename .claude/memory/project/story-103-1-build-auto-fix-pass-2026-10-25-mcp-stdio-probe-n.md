---
name: "story-103-1-build-auto-fix-pass-2026-10-25-mcp-stdio-probe-n"
description: "Story 103.1 build-auto fix pass (2026-10-25): mcp_stdio_probe now enforces wall-clock timeouts via selectors+os.read, a…"
metadata:
  type: project
---

Story 103.1 build-auto fix pass (2026-10-25): mcp_stdio_probe now enforces wall-clock timeouts via selectors+os.read, always tears down process groups (incl. Windows), matches JSON-RPC ids, redacts stderr concurrently; tests cover AC6–AC8 including preflight JSON AC7; coverage gate green.
