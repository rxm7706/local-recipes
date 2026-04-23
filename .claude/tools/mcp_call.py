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
    tool = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    result = call(tool, **args)
    print(json.dumps(result, indent=2))
