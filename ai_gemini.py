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

OUTPUT should SUGGEST 3 decks with reasoning, even if not strict JSON.
Each deck includes:
- 8 card names
- average elixir
- up to 2 evolved cards
- short explanation and optional warning
"""

def suggest_three_decks(payload: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model_name = os.getenv("GEMINI_MODEL") or MODEL_DEFAULT
    model = genai.GenerativeModel(model_name)

    # prompt completo
    full_prompt = (
        INSTRUCTIONS
        + "\n\nHere is the player and context data:\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    try:
        # chamada sem schema (modo livre)
        resp = model.generate_content(
            full_prompt,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 1500
            }
        )

        # extrai texto bruto
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

        # tenta converter o trecho JSON, se existir
        try:
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end != -1:
                snippet = text[json_start:json_end + 1]
                data = json.loads(snippet)
            else:
                raise ValueError("No JSON detected")
        except Exception:
            # fallback em caso de resposta não-JSON
            data = {
                "decks": [
                    {
                        "cards": [],
                        "avg_elixir": 0,
                        "evolved_cards": [],
                        "reasons": text.strip(),
                        "warnings": ""
                    }
                ]
            }

    except Exception as e:
        raise RuntimeError(f"Gemini generation failed: {e}")

    # garante 3 decks no retorno
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
