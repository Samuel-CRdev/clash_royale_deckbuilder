# guarda e compacta os dados para a IA ler
from typing import Dict, Any, List
from math import fsum

def compress_cards(cards: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    keep = ("name","elixirCost","rarity","id","type")
    return [{k:c.get(k) for k in keep if k in c} for c in cards]

def build_llm_payload(player: Dict[str,Any], cards: List[Dict[str,Any]],
                      meta: Dict[str,Any], user_request: str,
                      max_evos_per_deck: int = 2) -> Dict[str,Any]:
    levels = [v.get("level", 1) for v in (player.get("cards_owned") or {}).values()]
    avg_lvl = round(fsum(levels)/len(levels),2) if levels else 11.0
    evolutions_owned = [name for name,info in (player.get("cards_owned") or {}).items()
                        if info.get("evolution") is True]
    return {
        "constraints": {
            "max_evolutions_per_deck": max_evos_per_deck
        },
        "player": {
            "id": player.get("player_id"),
            "avg_level": avg_lvl,
            "owned": list(player.get("cards_owned", {}).keys()),
            "levels": player.get("cards_owned", {}),
            "evolutions_owned": evolutions_owned
        },
        "cards": compress_cards(cards),
        "meta": meta,
        "request": user_request
    }
