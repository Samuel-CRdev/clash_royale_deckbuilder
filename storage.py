# codigo onde é guardado json com cartas, players, o meta
import json, os, glob

def load_json(path, default=None):
    if not os.path.exists(path): return default
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=2)

def get_cards(): return load_json("data/cards.json", default=[])
def get_meta():  return load_json("data/meta_snapshot.json", default={"period":"", "archetypes":[]})

def list_players():
    os.makedirs("data/players", exist_ok=True)
    files = sorted(glob.glob("data/players/*.json"))
    return [os.path.splitext(os.path.basename(p))[0] for p in files]

def get_player(pid): return load_json(f"data/players/{pid}.json", default=None)

def save_player(pid, data):
    data["player_id"] = pid
    save_json(f"data/players/{pid}.json", data)

def delete_player(pid):
    p = f"data/players/{pid}.json"
    if os.path.exists(p): os.remove(p); return True
    return False
