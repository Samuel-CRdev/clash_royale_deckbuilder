# codigo para baixar e atualizar cache de cartas da supercell
import os, requests, json

BASE_URL = "https://api.clashroyale.com/v1"

def fetch_cards(api_key: str):
    headers = {"Accept": "application/json", "Authorization": f"Bearer {api_key}"}
    r = requests.get(f"{BASE_URL}/cards", headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["items"]

def update_cards_cache(api_key: str, path="data/cards.json"):
    cards = fetch_cards(api_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    return len(cards)
# api.py (adicione abaixo do que já existe)
import urllib.parse

def fetch_player_by_tag(api_key: str, player_tag: str):
    """
    Busca o perfil do jogador (inclui cartas e níveis).
    player_tag pode vir como '#ABCD123'; a API exige o %23 no lugar do #.
    """
    headers = {"Accept": "application/json", "Authorization": f"Bearer {api_key}"}
    tag_encoded = urllib.parse.quote(player_tag.strip().upper())  # converte # -> %23
    url = f"{BASE_URL}/players/{tag_encoded}"
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def transform_player_to_schema(player_id: str, raw_player: dict) -> dict:
    """
    Transforma o JSON da API (raw) no formato do nosso players/<id>.json.
    A API retorna raw_player['cards'] com: name, level, maxLevel, count, etc.
    Evoluções não vêm de forma padronizada – deixamos 'evolution': False
    e você marca depois nas cartas que realmente têm evolução habilitada.
    """
    cards_owned = {}
    for c in raw_player.get("cards", []):
        name = c.get("name")
        if not name:
            continue
        level = c.get("level", 1)
        cards_owned[name] = {
            "level": level,
            "evolution": False  # ajuste manual depois, se quiser
        }
    return {
        "player_id": player_id,
        "cards_owned": cards_owned,
        "preferences": {"bans": [], "must_have": []}
    }
