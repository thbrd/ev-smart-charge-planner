"""Optional OpenAI candidate selection. AI never receives actuator access."""

from __future__ import annotations

import json
from typing import Any

from aiohttp import ClientError
from homeassistant.helpers.aiohttp_client import async_get_clientsession


async def choose_candidate(hass: Any, api_key: str, model: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not api_key or not candidates:
        return None
    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": "Kies uitsluitend een bestaande kandidaat. Antwoord alleen JSON met chosen_candidate en reason."}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": json.dumps(candidates, ensure_ascii=False)}],
            },
        ],
    }
    session = async_get_clientsession(hass)
    try:
        async with session.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        ) as response:
            if response.status != 200:
                return None
            data = await response.json()
    except (ClientError, TimeoutError):
        return None

    text = data.get("output_text", "")
    if not text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("text"):
                    text += content["text"]
    try:
        result = json.loads(text[text.find("{") : text.rfind("}") + 1])
    except (ValueError, TypeError):
        return None
    valid_ids = {candidate["id"] for candidate in candidates}
    if result.get("chosen_candidate") not in valid_ids:
        return None
    return {"chosen_candidate": result["chosen_candidate"], "reason": str(result.get("reason", "AI koos een bestaande kandidaat."))[:500]}
