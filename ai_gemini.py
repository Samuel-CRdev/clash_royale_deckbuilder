# ai_gemini.py
# chama o gemini, e retorna o JSON com o deck (tolerante a respostas sem Part.text)
import os, json, re
import google.generativeai as genai
from typing import Dict, Any, Optional

MODEL_DEFAULT = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"

INSTRUCTIONS = """
You are a Clash Royale deck planner. INPUT is a JSON with:
- constraints: { max_evolutions_per_deck: 2 }
- player: owned cards, levels, evolutions_owned (subset of owned)
- cards: game cards {name, elixirCost, type, rarity, id}
- meta: curated archetypes from the last ~4 months
- request: natural language preferences (style, must-haves, target elixir)

Return 3 suggested decks. Each deck must include:
- 8 card names (real names in INPUT.cards or INPUT.meta)
- average elixir (number)
- up to 2 evolved cards (subset of player.evolutions_owned)
- short 'reasons' and optional 'warnings'

If strict JSON is difficult, you may return text, but structure should be clear.
Do not refuse; do your best with available data.
"""

# -------- helpers --------

def _extract_text(resp) -> str:
    """
    Extrai conteúdo textual de diferentes formatos de resposta do Gemini.
    Não depende de resp.text (que quebra quando finish_reason != STOP).
    """
    if not resp:
        return ""
    # 1) caminho feliz
    try:
        if getattr(resp, "text", None):
            return resp.text
    except Exception:
        pass

    # 2) partes nos candidatos
    try:
        if getattr(resp, "candidates", None):
            chunks = []
            for c in resp.candidates:
                # se houver bloqueio/safety, ainda tentamos capturar feedback
                if getattr(c, "content", None) and getattr(c.content, "parts", None):
                    for p in c.content.parts:
                        # part.text
                        if hasattr(p, "text") and isinstance(p.text, str):
                            chunks.append(p.text)
                        # part.inline_data (ignoramos binários)
                        # part.function_call (não esperamos aqui)
                # também podemos ler finish_reason para logs
            if chunks:
                return "\n".join(chunks).strip()
    except Exception:
        pass

    # 3) prompt_feedback (às vezes traz motivo do bloqueio)
    try:
        fb = getattr(resp, "prompt_feedback", None)
        if fb:
            # concatena quaisquer mensagens conhecidas
            s = []
            if getattr(fb, "block_reason", None):
                s.append(f"block_reason={fb.block_reason}")
            if getattr(fb, "safety_ratings", None):
                s.append(f"safety_ratings={fb.safety_ratings}")
            if s:
                return " | ".join(s)
    except Exception:
        pass

    return ""


def _try_parse_first_json(text: str) -> Optional[dict]:
    """
    Tenta achar o primeiro bloco {...} JSON válido dentro do texto.
    Se falhar, retorna None.
    """
    if not text:
        return None

    # tentativa simples: pegar o maior bloco de chaves balanceadas
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start:end+1]
        try:
            return json.loads(snippet)
        except Exception:
            pass

    # fallback: regex gulosa que tenta capturar blocos JSON
    candidates = re.findall(r"\{(?:[^{}]|(?R))*\}", text, flags=re.DOTALL)
    for snip in candidates:
        try:
            return json.loads(snip)
        except Exception:
            continue
    return None


def _fallback_from_text(text: str) -> Dict[str, Any]:
    """
    Se não houver JSON parseável, devolve um fallback com o texto nas 'reasons'.
    Garante estrutura para a UI.
    """
    return {
        "decks": [
            {
                "cards": [],
                "avg_elixir": 0,
                "evolved_cards": [],
                "reasons": text.strip()[:4000],  # evita texto gigante
                "warnings": "Fallback: resposta não-JSON do modelo."
            }
        ]
    }


def _safety_settings_block_none():
    # Desbloqueia filtros para evitar finish_reason por safety em conteúdo inofensivo.
    # (Mantemos responsabilidade do lado do usuário).
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    return {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUAL: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }


# -------- main --------

def suggest_three_decks(payload: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model_name = os.getenv("GEMINI_MODEL") or MODEL_DEFAULT
    model = genai.GenerativeModel(model_name)

    # payload pode ficar muito grande: para reduzir riscos, criamos uma versão compacta
    # - cards: apenas campos essenciais
    cards = payload.get("cards", [])
    small_cards = [
        {k: v for k, v in c.items() if k in ("name", "elixirCost", "type", "rarity")}
        for c in cards
        if isinstance(c, dict)
    ]
    slim_payload = dict(payload)
    slim_payload["cards"] = small_cards

    full_prompt = (
        INSTRUCTIONS
        + "\n\n--- INPUT ---\n"
        + json.dumps(slim_payload, ensure_ascii=False)
        + "\n--- END INPUT ---\n"
        + "Return 3 decks. Prefer JSON if possible."
    )

    # 2 tentativas: a 2ª mais conservadora (menos tokens/temperatura)
    attempts = [
        dict(temperature=0.4, max_output_tokens=1200),
        dict(temperature=0.2, max_output_tokens=800),
    ]

    text = ""
    last_err = None
    for cfg in attempts:
        try:
            resp = model.generate_content(
                full_prompt,
                generation_config=cfg,
                safety_settings=_safety_settings_block_none(),
            )
            text = _extract_text(resp)
            if text and text.strip():
                break
            # se chegou aqui, a resposta não trouxe texto aproveitável
            last_err = ValueError("Empty response or no text parts.")
        except Exception as e:
            last_err = e

    if not text.strip():
        raise RuntimeError(f"Gemini generation failed (no text): {last_err}")

    # tenta parsear JSON; se não conseguir, retorna fallback com 'reasons'
    parsed = _try_parse_first_json(text)
    if not parsed:
        return _fallback_from_text(text)

    # garante que sempre tenhamos 'decks' (e no máximo 3) para a UI
    decks = parsed.get("decks", [])
    if not isinstance(decks, list):
        return _fallback_from_text(text)
    if len(decks) > 3:
        decks = decks[:3]
    while len(decks) < 3:
        decks.append({
            "cards": [],
            "avg_elixir": 0,
            "evolved_cards": [],
            "reasons": "fallback deck (AI returned fewer than 3)",
            "warnings": ""
        })
    parsed["decks"] = decks
    return parsed
