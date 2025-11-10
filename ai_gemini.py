# ai_gemini.py — versão simplificada e tolerante
import os, json, re
import google.generativeai as genai
from typing import Dict, Any

MODEL_DEFAULT = "gemini-2.0-flash"

INSTRUCTIONS = """
You are a Clash Royale deck planner.
Input is JSON with: player (owned cards, levels, evolutions), cards (with elixir and type), meta (top archetypes).
Your task: Suggest 3 viable decks of 8 cards each, with average elixir and up to 2 evolved cards.
Output: JSON ONLY, with:
{
  "decks": [
    {
      "cards": ["Card1","Card2","Card3","Card4","Card5","Card6","Card7","Card8"],
      "avg_elixir": 3.4,
      "evolved_cards": ["CardA","CardB"],
      "reasons": "short reasoning why deck works"
    },
    {...}, {...}
  ]
}
"""

def _try_parse_json(text: str):
    """Extrai JSON mesmo que venha junto de texto."""
    try:
        return json.loads(text)
    except:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
    return {"decks": []}

def suggest_three_decks(payload: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL") or MODEL_DEFAULT
    model = genai.GenerativeModel(model_name)

    try:
        resp = model.generate_content(
            contents=[
                {"role": "user", "parts": [INSTRUCTIONS]},
                {"role": "user", "parts": [json.dumps(payload, ensure_ascii=False)]}
            ],
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 1200,
                "response_mime_type": "application/json"
            }
        )

        text = ""
        if hasattr(resp, "text") and resp.text:
            text = resp.text
        elif hasattr(resp, "candidates"):
            for c in resp.candidates:
                if c.content and hasattr(c.content, "parts"):
                    for p in c.content.parts:
                        if hasattr(p, "text") and p.text:
                            text += p.text

        if not text.strip():
            raise RuntimeError("Empty response from Gemini")

        data = _try_parse_json(text)

    except Exception as e:
        raise RuntimeError(f"Gemini generation failed: {e}")

    decks = data.get("decks", [])
    if len(decks) < 3:
        while len(decks) < 3:
            decks.append({
                "cards": [],
                "avg_elixir": 0,
                "evolved_cards": [],
                "reasons": "fallback (AI returned fewer decks)"
            })
    return {"decks": decks[:3]}
