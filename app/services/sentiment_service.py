import os
from openai import OpenAI

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def analyze_sentiment(text: str) -> dict:
    if not text or not text.strip():
        return {"label": "NEUTRAL", "urgency": "low"}
    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    "Išanalizuok šio kliento laiško toną ir skubumą. "
                    "Grąžink TIK JSON: {\"label\": \"POSITIVE|NEUTRAL|NEGATIVE\", \"urgency\": \"low|medium|high\"}\n\n"
                    f"Laiškas:\n{text[:1000]}"
                )
            }],
            temperature=0,
            max_tokens=30,
        )
        import json
        return json.loads(response.choices[0].message.content.strip())
    except Exception:
        return {"label": "NEUTRAL", "urgency": "low"}
