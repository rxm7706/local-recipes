#!/usr/bin/env python3
"""Thin MCP JSON-RPC client for calling conda_forge_server.py tools from the shell."""
import json, subprocess, sys
from pathlib import Path

SERVER = Path(__file__).parent / "conda_forge_server.py"
PYTHON = sys.executable

def call(tool_name: str, **kwargs) -> dict:
    msgs = [
        {"jsonrpc": "2.0", "method": "initialize", "id": 1,
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "mcp_call", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "tools/call", "id": 2,
         "params": {"name": tool_name, "arguments": kwargs}},
    ]
    inp = "\n".join(json.dumps(m) for m in msgs) + "\n"
    proc = subprocess.run([PYTHON, SERVER], input=inp, capture_output=True, text=True, timeout=300)
    for line in proc.stdout.splitlines():
        try:
            obj = json.loads(line)
            if obj.get("id") == 2:
                if "error" in obj:
                    return {"error": obj["error"]}
                result = obj.get("result", {})
                content = result.get("content", [])
                if content:
                    text = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
                    try:
                        return json.loads(text)
                    except Exception:
                        return {"text": text}
                return result
        except Exception:
            pass
    return {"error": "no response", "stderr": proc.stderr[:500]}

if __name__ == "__main__":
    # AUD-CFE-012 is a trusted-operator wrapper by design: it grants nothing the
    # operator could not do by running conda_forge_server.py directly, so it adds
    # no privilege boundary. What it DID do was crash with a bare IndexError when
    # called with no arguments, and pass malformed JSON straight to a traceback.
    # The tools it reaches are themselves confined now (AUD-CFE-001/002/006).
    if len(sys.argv) < 2:
        print(
            f"usage: {Path(sys.argv[0]).name} <tool_name> ['{{\"arg\": \"value\"}}']\n"
            "  Calls a tool on conda_forge_server.py over stdio JSON-RPC.",
            file=sys.stderr,
        )
        sys.exit(2)
    tool = sys.argv[1]
    try:
        args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    except json.JSONDecodeError as exc:
        print(f"arguments must be a JSON object: {exc}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(args, dict):
        print(f"arguments must be a JSON object, got {type(args).__name__}",
              file=sys.stderr)
        sys.exit(2)
    result = call(tool, **args)
    print(json.dumps(result, indent=2))
    sys.exit(1 if isinstance(result, dict) and "error" in result else 0)
