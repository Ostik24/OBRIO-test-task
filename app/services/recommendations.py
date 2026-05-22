import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

_client = None

def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


def generate_llm_recommendations(themes_data: dict, top_bigrams: list[tuple[str, int]]) -> list[str]:
    if not themes_data:
        return []

    themes_summary = "\n".join(
        f"- **{name}** ({data['count']} reviews). Example: \"{data['examples'][0]['review']}\""
        for name, data in sorted(themes_data.items(), key=lambda x: -x[1]["count"])
    )

    bigrams_summary = ", ".join(f'"{b}"' for b, _ in top_bigrams[:10])

    prompt = f"""You are analyzing negative App Store reviews for a product team.

## Top complaint themes:
{themes_summary}

## Common phrases in negative reviews:
{bigrams_summary}

Generate 3-5 specific, actionable recommendations for the product team. Each must be:
- Concrete (not vague like "improve UX" — say WHAT to improve and HOW)
- Tied to actual complaints from the data above
- One sentence

Return only the numbered list. No preamble, no closing remarks."""

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    return [
        line.strip()
        for line in text.split("\n")
        if line.strip() and line.strip()[0].isdigit()
    ]
