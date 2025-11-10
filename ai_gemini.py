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

def suggest_three_decks(payload: Dict[str,Any]) -> Dict[str,Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model_name = os.getenv("GEMINI_MODEL") or MODEL_DEFAULT
    model = genai.GenerativeModel(model_name)

    # Structured output (schema) para garantir 3 decks com 8 cartas e até 2 evoluções
    schema = {
      "type": "object",
      "properties": {
        "decks": {
          "type": "array",
          "minItems": 3, "maxItems": 3,
          "items": {
            "type": "object",
            "properties": {
              "cards": {
                "type": "array",
                "minItems": 8, "maxItems": 8,
                "items": { "type": "string" }
              },
              "avg_elixir": { "type": "number" },
              "evolved_cards": {
                "type": "array",
                "items": { "type": "string" }
              },
              "reasons": { "type": "string" },
              "warnings": { "type": "string" }
            },
            "required": ["cards"]
          }
        }
      },
      "required": ["decks"]
    }

    resp = model.generate_content(
        contents=[
            {"role":"user","parts":[INSTRUCTIONS]},
            {"role":"user","parts":[json.dumps(payload, ensure_ascii=False)]}
        ],
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 800,
            "response_mime_type": "application/json",
            "response_schema": schema
        }
    )

    if not resp or not resp.text:
        raise RuntimeError("Empty response from Gemini")
    return json.loads(resp.text)
