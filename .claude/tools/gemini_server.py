#!/usr/bin/env python3
"""Gemini MCP Server — exposes Google Gemini as tools for Claude Code.

Requires: GEMINI_API_KEY environment variable
Models: https://ai.google.dev/gemini-api/docs/models
"""
import json
import os
import urllib.request
import urllib.error
from fastmcp import FastMCP

mcp = FastMCP("gemini")

_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY")


def _post(path: str, payload: dict, timeout: int = 60) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = f"{_BASE}/{path}?key={key}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _get(path: str, timeout: int = 30) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = f"{_BASE}/{path}?key={key}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


@mcp.tool()
def gemini_chat(
    prompt: str,
    model: str = "gemini-2.0-flash",
    system_prompt: str = "",
) -> str:
    """Send a prompt to Google Gemini and return the text response.

    Args:
        prompt: The prompt to send to Gemini.
        model: The Gemini model to use (e.g., "gemini-pro", "gemini-2.0-flash").
        system_prompt: An optional system prompt to guide the model's behavior.

    Returns:
        The text response from Gemini.
    """
    contents = []
    if system_prompt:
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})
        contents.append({"role": "model", "parts": [{"text": "OK."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.9,
            "topK": 1,
            "topP": 1,
            "maxOutputTokens": 2048,
            "stopSequences": [],
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE",
            },
        ],
    }
    try:
        resp = _post(f"models/{model}:generateContent", payload)
        if "candidates" in resp and resp["candidates"]:
            for part in resp["candidates"][0]["content"]["parts"]:
                if "text" in part:
                    return part["text"]
        return json.dumps(resp)
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.read().decode()}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"


@mcp.tool()
def gemini_list_models() -> str:
    """List available Gemini models.

    Returns:
        A JSON string of available models.
    """
    try:
        resp = _get("models")
        return json.dumps(resp, indent=2)
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.read().decode()}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"


@mcp.tool()
def gemini_get_model(model_name: str) -> str:
    """Get information about a specific Gemini model.

    Args:
        model_name: The name of the model to retrieve information for (e.g., "gemini-pro").

    Returns:
        A JSON string of the model's information.
    """
    try:
        resp = _get(f"models/{model_name}")
        return json.dumps(resp, indent=2)
    except urllib.error.HTTPError as e:
        return f"Error: {e.code} - {e.read().decode()}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"


if __name__ == "__main__":
    mcp.run()
