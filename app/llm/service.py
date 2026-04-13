import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")

async def review_chunk(chunk: dict) -> tuple:
    valid_lines = list(chunk["position_map"].keys())

    prompt = f"""You are a senior software engineer reviewing a pull request.

File: {chunk['filename']}
Language: {chunk['language']}

Here is the diff:
<diff>
{chunk['patch']}
</diff>

IMPORTANT: You can ONLY reference these line numbers in your findings: {valid_lines}
Do not reference any line number outside this list. If an issue exists on a line not in this list, skip it.

Return ONLY a valid JSON array with no markdown, no explanation, no backticks.
Each item must follow this exact structure:
[{{
  "line": <must be one of {valid_lines}>,
  "severity": "error" | "warning" | "style",
  "category": "logic" | "security" | "performance" | "style",
  "message": "<what the issue is>",
  "suggestion": "<how to fix it>"
}}]

If there are no issues on the valid lines, return an empty array: []
"""

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        response.raise_for_status()
        data = response.json()

    raw = data["choices"][0]["message"]["content"]

    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)

    print(f"Tokens — in: {tokens_in} out: {tokens_out}")

    findings = parse_findings(raw)
    return findings, tokens_in, tokens_out


def parse_findings(raw: str) -> list:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception as e:
        print(f"Failed to parse LLM response: {e}")
        print(f"Raw response: {raw}")
        return []