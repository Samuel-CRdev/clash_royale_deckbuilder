# checa evos, elixir e etc
def normalize_log(name: str) -> str:
    return "The Log" if name.lower().strip() in {"log","the log"} else name

def validate_cards(deck_cards, cards_index):
    fixed = []
    seen = set()
    for n in deck_cards:
        nn = normalize_log(n)
        if nn in cards_index and nn not in seen:
            fixed.append(nn)
            seen.add(nn)
    return fixed[:8]  # garante 8 no máximo

def clamp_evolutions(evo_list, evolutions_owned, max_per_deck=2):
    if not evo_list: return []
    # mantem apenas evoluções que o player possui, limita a 2
    valid = [n for n in evo_list if n in evolutions_owned]
    return valid[:max_per_deck]

def average_elixir(deck_names, cards_index):
    if len(deck_names) != 8: return None
    total = sum(cards_index[n].get("elixirCost", 3) for n in deck_names)
    return round(total / 8.0, 2)
