# chama o gemini, e retorna o JSON com o deck
import os, json
import google.generativeai as genai
from typing import Dict, Any

MODEL_DEFAULT = "gemini-2.5-flash"

INSTRUCTIONS = """
You are a Clash Royale deck planner. INPUT is a JSON with:
- constraints: { max_evolutions_per_deck: 2 }
- player: owned cards, levels, evolutions_owned (subset of owned)
- cards: game cards {name, elixirCost, type, rarity, id}
- meta: curated archetypes from the last ~4 months
- request: natural language preferences (style, must-haves, target elixir)

OUTPUT must be STRICT JSON with exactly 3 decks:
{
  "decks": [
    {
      "cards": ["Card1","Card2","Card3","Card4","Card5","Card6","Card7","Card8"],
      "avg_elixir": 3.4,
      "evolved_cards": ["CardA","CardB"],   // <= 2, subset of player.evolutions_owned and of 'cards'
      "reasons": "concise explanation (fit to meta, player's levels, request)",
      "warnings": "optional"
    },
    { ... },
    { ... }
  ]
}

Rules:
- Use ONLY real Clash Royale card names present in INPUT.cards or INPUT.meta.
- Prefer cards the player OWNS; if not owned, justify in 'warnings' and suggest nearest owned alternative in 'reasons'.
- Exactly 3 decks; each deck must have exactly 8 unique cards.
- Respect constraints.max_evolutions_per_deck (<=2) and only use evolutions from player.evolutions_owned.
- Consider the request (e.g., target elixir, must-haves) and current meta.
- No extra text outside the JSON.
"""

def suggest_three_decks(payload: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model_name = os.getenv("GEMINI_MODEL") or MODEL_DEFAULT
    model = genai.GenerativeModel(model_name)

    # Schema mais permissivo (sem minItems/maxItems)
    schema = {
        "type": "object",
        "properties": {
            "decks": {"type": "array"}
        }
    }

    try:
        resp = model.generate_content(
            contents=[
                {"role": "user", "parts": [INSTRUCTIONS]},
                {"role": "user", "parts": [json.dumps(payload, ensure_ascii=False)]}
            ],
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 1200,
                "response_mime_type": "application/json",
                "response_schema": schema
            }
        )

        # tenta extrair texto ou JSON
        text = ""
        if hasattr(resp, "text") and resp.text:
            text = resp.text
        elif hasattr(resp, "candidates") and resp.candidates:
            for c in resp.candidates:
                if c.content and hasattr(c.content, "parts"):
                    for p in c.content.parts:
                        if hasattr(p, "text"):
                            text += p.text

        if not text.strip():
            raise RuntimeError("Empty or no-match response from Gemini")

        data = json.loads(text)

    except Exception as e:
        raise RuntimeError(f"Gemini generation failed: {e}")

    # garantir que existam exatamente 3 decks
    decks = data.get("decks", [])
    if len(decks) > 3:
        decks = decks[:3]
    elif len(decks) < 3:
        while len(decks) < 3:
            decks.append({
                "cards": [],
                "avg_elixir": 0,
                "evolved_cards": [],
                "reasons": "fallback deck (AI returned fewer than 3)",
                "warnings": ""
            })
    data["decks"] = decks

    return data
