"""Natural-language search via Vertex AI Gemini.

Auth picks itself up automatically:
  - locally: Application Default Credentials (`gcloud auth application-default login`)
  - on Cloud Run: the service account attached to the service

No API key, no env var, no secret.toml.
"""
from __future__ import annotations

import os
from typing import Any

try:
    from google import genai
    from google.genai import types
    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False


PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or "project-cc7ed957-d1e3-4c3f-8b5"
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1"
MODEL = "gemini-2.5-flash"


FILTER_AGENTS_FN = {
    "name": "filter_agents",
    "description": (
        "Filter ERC-8004 agents in the BigQuery dataset by structured criteria. "
        "Leave fields the user did not mention as null. "
        "Owner addresses are 42-char hex like 0xabc…. Scores are 0-100. "
        "Defaults to apply: 'trustworthy'/'reputable'/'verified' → "
        "min_unique_clients=3; 'high reputation'/'top' → min_avg_score=80; "
        "'payable' → x402_only=true; 'functional'/'has endpoint' → has_services=true."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "agent_id": {"type": "INTEGER",
                         "description": "Exact agent_id when the user gives one."},
            "owner": {"type": "STRING",
                      "description": "Owner wallet address (0x… 42 chars)."},
            "name_contains": {"type": "STRING",
                              "description": "Case-insensitive substring of the agent name."},
            "description_contains": {"type": "STRING",
                                     "description": "Case-insensitive substring of the description."},
            "min_unique_clients": {"type": "INTEGER",
                                   "description": "Minimum distinct reviewers."},
            "min_avg_score": {"type": "NUMBER",
                              "description": "Minimum average reputation score (0-100)."},
            "x402_only": {"type": "BOOLEAN",
                          "description": "Restrict to x402Support=true cards."},
            "has_services": {"type": "BOOLEAN",
                             "description": "Restrict to cards with non-empty services[]."},
            "limit": {"type": "INTEGER",
                      "description": "Max rows. Default 50."},
        },
    },
}

SYSTEM_INSTRUCTION = (
    "You parse natural-language search requests for an ERC-8004 agent explorer "
    "and call the `filter_agents` function exactly once with the smallest set "
    "of fields the user actually asked for. Do not invent filters. "
    "Substring filters must be lowercase."
)


_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
    return _client


def available() -> bool:
    """True when the SDK is installed. Auth is checked lazily on first call."""
    return _HAS_GENAI


def parse_query(user_text: str) -> dict[str, Any] | None:
    """Use Gemini function-calling to extract a filter dict from user_text.
    Returns None if Gemini didn't emit a function call (e.g. the request was
    too vague). Raises on auth/network errors so the caller can surface them."""
    if not _HAS_GENAI:
        return None

    client = _get_client()
    resp = client.models.generate_content(
        model=MODEL,
        contents=user_text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[types.Tool(function_declarations=[FILTER_AGENTS_FN])],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="ANY",
                    allowed_function_names=["filter_agents"],
                )
            ),
            temperature=0,
        ),
    )

    for cand in resp.candidates or []:
        for part in cand.content.parts or []:
            if part.function_call and part.function_call.name == "filter_agents":
                return dict(part.function_call.args or {})
    return None
