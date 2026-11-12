"""In-app perfumery agent: Opus 5.5 tool-calling loop over the shared Scent Finder tools.

Guardrails: tools are the only actions; add_to_collection is preview-only here (the UI's
Save button confirms); a hard cap on tool rounds and output tokens per message.
"""

import asyncio
import json
import os
from datetime import date
from typing import Any, cast

from openai import omit
from openai.types.chat import ChatCompletionToolParam

from . import tools
from .db import gateway
from .mcp_server import mcp

CHAT_MODEL = os.environ.get("CHAT_MODEL", "system.ai.claude-opus-5-5")  # Unity Gateway model service
MAX_TOOL_ROUNDS = 6
MAX_OUTPUT_TOKENS = 1200
MAX_HISTORY = 12

INSTRUCTIONS = """You are Scent Finder, a knowledgeable, concise perfumery guide.

Rules:
- Always check the user's collection (get_my_collection) before recommending.
- Many visitors have an empty collection. Then give general picks from what they describe, and end with one short line inviting them to add fragrances they own for more personal picks. Don't call get_scent_dna for an empty collection.
- Questions about "my" wear history or DNA with an empty collection: say there's nothing on their shelf yet.
- Never recommend something the user already owns unless they ask. Wishlist items are fine; say they're on the wishlist.
- Give exactly 3 picks. For each: **Name (House)** then one line explaining the match through shared or contrasting notes, citing real notes from tool results.
- Ask one clarifying question only if the request is very vague; otherwise make a sensible assumption and state it in a few words.
- Use only fragrances returned by tools. Never invent notes, prices or availability.
- Prices aren't in the data. For a budget, use max_price_usd (it maps to assumed price bands) and say the price is a band estimate.
- "Find the gap" / "something different": use get_scent_dna (family_gaps, profile), then search outside the dominant accords.
- "What should I wear tonight?": pick from the user's OWNED bottles, using season, the occasion and the wear log (get_my_collection shows times_worn and last_worn). Today is {today}; assume the southern hemisphere (Australia) unless told otherwise, so Sep-Nov is spring, Dec-Feb summer, Mar-May autumn, Jun-Aug winter. Seasons tagged season_inferred are rule-of-thumb.
- log_wear writes immediately: only call it when the user clearly says they wore something.
- add_to_collection here only previews matches; tell the user to press Save in the import card to confirm.
- Data is approximate (model-generated and public datasets); if a row is low_confidence, say the notes are a best guess.
- Format: short markdown. No preamble."""

_tool_schemas: list[dict] | None = None


def tool_schemas() -> list[dict]:
    global _tool_schemas
    if _tool_schemas is None:
        listed = asyncio.run(mcp.list_tools())
        _tool_schemas = [
            {"type": "function", "function": {"name": t.name, "description": t.description or "",
                                              "parameters": t.input_schema}}
            for t in listed
        ]
    return _tool_schemas


def run_tool(name: str, args: dict) -> dict:
    if name == "add_to_collection":
        args["confirm"] = False  # the UI confirms writes
    fn = {
        "search_by_notes": tools.search_by_notes, "find_similar": tools.find_similar,
        "get_my_collection": tools.get_my_collection, "get_scent_dna": tools.get_scent_dna,
        "log_wear": tools.log_wear, "add_to_collection": tools.add_to_collection,
    }.get(name)
    if fn is None:
        return {"error": f"unknown tool {name}"}
    try:
        return fn(**args)
    except TypeError as e:
        return {"error": f"bad arguments: {e}"}


def _text(content) -> str:
    """Content may be a string or a list of parts (reasoning + text); keep the text."""
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return content or ""


def chat(history: list[dict]) -> dict:
    """history: [{role: user|assistant, content: str}]. Returns reply, tool trace, pending import, usage."""
    messages: list[Any] = [{"role": "system", "content": INSTRUCTIONS.format(today=date.today().isoformat())}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history[-MAX_HISTORY:]]
    client, trace, pending, usage = gateway(), [], None, {"prompt_tokens": 0, "completion_tokens": 0}
    for round_ in range(MAX_TOOL_ROUNDS + 1):
        resp = client.chat.completions.create(
            model=CHAT_MODEL, messages=messages, max_tokens=MAX_OUTPUT_TOKENS,
            tools=cast(list[ChatCompletionToolParam], tool_schemas()) if round_ < MAX_TOOL_ROUNDS else omit,
        )
        if resp.usage:
            usage["prompt_tokens"] += resp.usage.prompt_tokens
            usage["completion_tokens"] += resp.usage.completion_tokens
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {"reply": _text(msg.content), "tool_calls": trace, "pending_import": pending, "usage": usage}
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            if tc.type != "function":
                continue
            args = json.loads(tc.function.arguments or "{}")
            result = run_tool(tc.function.name, args)
            trace.append({"name": tc.function.name, "args": args})
            if tc.function.name == "add_to_collection" and result.get("preview"):
                pending = {**result, "status": args.get("status", "owned")}
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, ensure_ascii=False, default=str)[:12000]})
    return {"reply": "I hit my step limit for one message. Try a narrower question.",
            "tool_calls": trace, "pending_import": pending, "usage": usage}
