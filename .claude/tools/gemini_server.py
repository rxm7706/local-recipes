#!/usr/bin/env python3
"""Gemini MCP Server — exposes Google Gemini as tools for Claude Code.

Requires: GEMINI_API_KEY environment variable
Model catalog: https://ai.google.dev/gemini-api/docs/models

gemini_chat works with any text/reasoning model below (default: gemini-flash-latest).
The *-latest rolling aliases auto-track the newest stable release, so the default
never goes stale.

[YYYY-MM] = release month (from each model's API version string). Alias lines show the
exact model they resolve to and the date that mapping was last verified; Google gives
2 weeks' notice before re-pointing a *-latest alias, so re-verify periodically.

Text & reasoning (usable via gemini_chat) — newest first:
  gemini-flash-latest      Alias -> gemini-3.5-flash (as of 2026-06-21). The default: fast, balanced, cheap.
  gemini-pro-latest        Alias -> gemini-2.5-pro (as of 2026-06-21; no 3.x Pro is GA yet). Hardest reasoning without pinning.
  gemini-3.5-flash         [2026-05] Newest stable Flash; top sustained agentic/coding performance. Production agents & coding.
  gemini-3.1-flash-lite    [2026-05] Frontier-class, lowest-cost Flash. High-frequency, latency/cost-sensitive tasks.
  gemini-3.1-pro-preview   [2026-01] Advanced reasoning + agentic/"vibe" coding (preview). Complex problem-solving, agents.
  gemini-3-flash-preview   [2025-12] Frontier-class performance at a fraction of the cost (preview). Competitive on a budget.
  gemini-2.5-flash-lite    [2025-07] Cheapest current option for simple, high-throughput calls.
  gemini-2.5-pro           [2025-06] Deep reasoning + coding (prior gen). Enterprise reasoning, sophisticated code generation.
  gemini-2.5-flash         [2025-06] Best price-performance (prior gen). Low-latency, high-volume work needing some reasoning.
  gemini-2.0-flash         [2025-02] DEPRECATED / shutting down — do not use for new work.

Specialized families (NOT for gemini_chat, which returns text only — listed for reference):
  Image:      gemini-3-pro-image (Nano Banana Pro, Gemini-3 gen, highest quality), gemini-3.1-flash-image (Nano Banana 2, fast/high-volume)
  Video:      veo-3.1-generate-preview (Veo 3.1, cinematic+audio), veo-3.1-lite-generate-preview (low-cost)
  Audio:      gemini-3.1-flash-tts-preview (speech synthesis), gemini-3.1-flash-live-preview [2026-03] (real-time voice / Live API)
  Embeddings: gemini-embedding-2 (multimodal semantic search / RAG)
  Agentic:    gemini-2.5-computer-use-preview-10-2025 [2025-10] (UI automation), deep-research-preview-04-2026 [2026-04] (multi-source research)

Cost controls (https://ai.google.dev/gemini-api/docs/batch-api):
  thinking_budget   gemini_chat / gemini_batch_submit param. 0 (default) disables billed
                    "thinking" tokens -> cheapest, fastest reply on Flash; -1 = dynamic
                    (use for hard reasoning, or Pro models which reject 0); >0 = fixed cap.
                    Verified ~60% fewer billed tokens at 0 vs dynamic on a reasoning prompt.
  Batch API         gemini_batch_submit + gemini_batch_get. ~50% cheaper than gemini_chat
                    for BULK, NON-URGENT prompts (async; target ~24h, 48h expiry). REQUIRES
                    a paid/billing-enabled project — free-tier keys return HTTP 400
                    FAILED_PRECONDITION. Use a concrete model ID (not a *-latest alias).
  Model choice      prefer Flash over Pro; use a *-lite model for simple high-volume calls.
"""
import json
import os
import urllib.request
import urllib.error
from fastmcp import FastMCP

# Prefer requests for more robust HTTP; fall back to the stdlib urllib (imported
# unconditionally above) when requests is not installed.
try:
    import requests
except ImportError:
    requests = None


mcp = FastMCP("gemini")

_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY")


def _post_requests(path: str, payload: dict, timeout: int = 60) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = f"{_BASE}/{path}?key={key}"
    assert requests is not None  # _post binds here only when requests is importable
    response = requests.post(
        url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout
    )
    response.raise_for_status()
    return response.json()

def _get_requests(path: str, timeout: int = 30) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = f"{_BASE}/{path}?key={key}"
    assert requests is not None  # _get binds here only when requests is importable
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()

def _post_urllib(path: str, payload: dict, timeout: int = 60) -> dict:
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

def _get_urllib(path: str, timeout: int = 30) -> dict:
    key = _api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    url = f"{_BASE}/{path}?key={key}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())

# Choose implementation based on availability
_post = _post_requests if requests else _post_urllib
_get = _get_requests if requests else _get_urllib


def _format_error(e: Exception) -> str:
    """Render a transport error uniformly across the requests and urllib paths."""
    if requests is not None and isinstance(e, requests.RequestException):
        resp = e.response
        if resp is not None:
            return f"Error: {resp.status_code} - {resp.text}"
        return f"Error: N/A - {e}"
    if isinstance(e, urllib.error.HTTPError):
        return f"Error: {e.code} - {e.read().decode()}"
    return f"An unexpected error occurred: {e}"


_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]


def _chat_contents(prompt: str, system_prompt: str) -> list:
    """Build the `contents` array, threading an optional system prompt as a priming turn."""
    contents = []
    if system_prompt:
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})
        contents.append({"role": "model", "parts": [{"text": "OK."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    return contents


def _generation_config(thinking_budget: int) -> dict:
    """generationConfig with a thinking-budget cost control.

    thinking_budget: 0 disables model "thinking" (cheapest/fastest; Flash only), -1 =
    dynamic/auto (model decides; required by Pro models, which reject 0), >0 = fixed
    thinking-token cap. Thinking tokens are billed, so 0 is the cheapest default
    (verified ~60% fewer billed tokens than dynamic on a reasoning prompt).
    """
    return {
        "temperature": 0.9,
        "topK": 1,
        "topP": 1,
        "maxOutputTokens": 2048,
        "stopSequences": [],
        "thinkingConfig": {"thinkingBudget": thinking_budget},
    }


def _extract_text(resp: dict) -> str | None:
    """Pull the first text part from a generateContent response, or None."""
    cands = resp.get("candidates") or []
    if cands:
        for part in cands[0].get("content", {}).get("parts", []):
            if "text" in part:
                return part["text"]
    return None


@mcp.tool()
def gemini_chat(
    prompt: str,
    model: str = "gemini-flash-latest",
    system_prompt: str = "",
    thinking_budget: int = 0,
) -> str:
    """Send a prompt to Google Gemini and return the text response.

    Args:
        prompt: The prompt to send to Gemini.
        model: The Gemini model to use (default "gemini-flash-latest"; e.g.
            "gemini-3.5-flash", "gemini-pro-latest"). See the module docstring for the catalog.
        system_prompt: An optional system prompt to guide the model's behavior.
        thinking_budget: Internal-reasoning token budget (cost control). 0 (default)
            disables billed "thinking" for the cheapest, fastest reply — best for routine
            chat on Flash models; -1 lets the model decide (use for hard reasoning, or for
            Pro models, which reject 0); >0 caps thinking at that many tokens.

    Returns:
        The text response from Gemini.
    """
    payload = {
        "contents": _chat_contents(prompt, system_prompt),
        "generationConfig": _generation_config(thinking_budget),
        "safetySettings": _SAFETY_SETTINGS,
    }
    try:
        resp = _post(f"models/{model}:generateContent", payload)
        text = _extract_text(resp)
        return text if text is not None else json.dumps(resp)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
def gemini_list_models() -> str:
    """List available Gemini models.

    Returns:
        A JSON string of available models.
    """
    try:
        resp = _get("models")
        return json.dumps(resp, indent=2)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
def gemini_get_model(model_name: str) -> str:
    """Get information about a specific Gemini model.

    Args:
        model_name: The name of the model to retrieve information for (e.g., "gemini-3.5-flash").

    Returns:
        A JSON string of the model's information.
    """
    try:
        resp = _get(f"models/{model_name}")
        return json.dumps(resp, indent=2)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
def gemini_batch_submit(
    prompts: list[str],
    model: str = "gemini-3.5-flash",
    system_prompt: str = "",
    thinking_budget: int = 0,
) -> str:
    """Submit many prompts as ONE asynchronous Batch API job — ~50% cheaper than gemini_chat.

    Use for BULK, NON-URGENT work (target turnaround ~24h, 48h hard expiry). This does NOT
    return answers directly: it returns a batch job name. Poll that name with
    gemini_batch_get to fetch results once the job reaches JOB_STATE_SUCCEEDED.

    REQUIRES A PAID / BILLING-ENABLED PROJECT. On a free-tier key the API returns
    HTTP 400 FAILED_PRECONDITION (sync gemini_chat still works on free tier). Pass a
    CONCRETE model ID — rolling "*-latest" aliases may be rejected for batch.

    Args:
        prompts: Independent prompts to run together in one batch.
        model: Concrete Gemini model ID (default "gemini-3.5-flash"; avoid *-latest aliases).
        system_prompt: Optional system instruction applied to every prompt.
        thinking_budget: Cost control, same as gemini_chat (0 = cheapest; -1 = dynamic; >0 cap).

    Returns:
        The batch job name (e.g. "batches/123...") with a hint to poll, or an error string.
    """
    if not prompts:
        return "Error: no prompts provided."
    gen_cfg = _generation_config(thinking_budget)
    inline = [
        {
            "request": {
                "contents": _chat_contents(p, system_prompt),
                "generationConfig": gen_cfg,
            },
            "metadata": {"key": f"req-{i}"},
        }
        for i, p in enumerate(prompts)
    ]
    payload = {
        "batch": {
            "display_name": "mcp-gemini-batch",
            "input_config": {"requests": {"requests": inline}},
        }
    }
    try:
        resp = _post(f"models/{model}:batchGenerateContent", payload)
        name = resp.get("name")
        if name:
            return f'Submitted batch job: {name}\nPoll it with gemini_batch_get("{name}").'
        return json.dumps(resp)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
def gemini_batch_get(batch_name: str) -> str:
    """Check a Batch API job and return its per-prompt results once complete.

    Args:
        batch_name: The job name from gemini_batch_submit (e.g. "batches/123...").

    Returns:
        The per-prompt text results when state is JOB_STATE_SUCCEEDED; the current state
        if still pending/running; a pointer to the result file for file-output jobs; or an
        error string.
    """
    try:
        resp = _get(batch_name)
    except Exception as e:
        return _format_error(e)
    state = (resp.get("metadata") or {}).get("state") or resp.get("state")
    if state and state != "JOB_STATE_SUCCEEDED":
        return f"Batch {batch_name} state: {state} (not ready — poll again later)."
    # Inline-input jobs return results inline; large/file jobs write a downloadable file.
    dest = resp.get("dest") or (resp.get("response") or {}).get("dest") or {}
    inlined = dest.get("inlinedResponses") or dest.get("inlined_responses") or []
    if not inlined:
        fname = dest.get("fileName") or dest.get("file_name")
        if fname:
            return (f"Batch {batch_name} SUCCEEDED; results are in file '{fname}' "
                    f"(fetch via the Files API — not auto-downloaded here).")
        return f"Batch {batch_name} state: {state or 'unknown'}; no inline results.\n{json.dumps(resp)[:500]}"
    lines = []
    for item in inlined:
        key = (item.get("metadata") or {}).get("key", "?")
        r = item.get("response") or {}
        err = item.get("error") or r.get("error")
        if err:
            lines.append(f"[{key}] ERROR: {json.dumps(err)[:200]}")
            continue
        text = _extract_text(r)
        lines.append(f"[{key}] {text if text is not None else json.dumps(r)[:200]}")
    stats = resp.get("batchStats") or {}
    failed = stats.get("failedRequestCount")
    header = f"Batch {batch_name} SUCCEEDED ({len(lines)} responses"
    header += f", {failed} failed):" if failed else "):"
    return header + "\n" + "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
