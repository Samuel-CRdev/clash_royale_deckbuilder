# server.py
import os, json, logging
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
from api import update_cards_cache, fetch_player_by_tag, transform_player_to_schema
from storage import get_cards, get_meta, get_player, save_player, save_json, list_players
from prompt_builder import build_llm_payload
from ai_gemini import suggest_three_decks
from deck_postprocess import validate_cards, clamp_evolutions, average_elixir

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

HOME_HTML = """
<!doctype html>
<title>Clash Deck Builder</title>
<h1>Clash Deck Builder (Gemini)</h1>
<ul>
  <li><a href="/ui">Montar 3 decks</a></li>
  <li><a href="/admin">Admin (atualizar cartas, colar meta)</a></li>
  <li><a href="/import">Importar Player por TAG</a></li>
  <li><a href="/players">Listar players</a></li>
  <li><a href="/debug/files">Debug de arquivos</a></li>
</ul>
"""

UI_HTML = """
<!doctype html>
<title>Montar 3 decks</title>
<h2>Montar 3 decks</h2>
<form method="post" action="/build_decks_form">
  <label>Player:</label>
  <select name="player_id">
    {% for p in players %}
      <option value="{{p}}">{{p}}</option>
    {% endfor %}
  </select>
  <br><br>
  <label>Prompt:</label><br>
  <textarea name="prompt" rows="3" cols="60" placeholder="Ex.: quero 2.6 com P.E.K.K.A e Dark Prince"></textarea>
  <br><br>
  <button type="submit">Gerar</button>
</form>

{% if error %}
  <hr>
  <p style="color:#b00"><b>Erro:</b> {{ error }}</p>
{% endif %}

{% if result %}
  <hr>
  <h3>Resultado</h3>
  {% for i,deck in enumerate(result["decks"],1) %}
    <h4>Deck {{i}}</h4>
    <ul>
      {% for c in deck.get("cards", []) %}
        <li>{{c}}</li>
      {% endfor %}
    </ul>
    {% if deck.get("avg_elixir") is not none %}<p><b>Média de Elixir:</b> {{deck["avg_elixir"]}}</p>{% endif %}
    {% if deck.get("evolved_cards") %}<p><b>Evoluções (<=2):</b> {{", ".join(deck["evolved_cards"])}}</p>{% endif %}
    {% if deck.get("reasons") %}<p><b>Razões:</b> {{ deck["reasons"] }}</p>{% endif %}
    {% if deck.get("warnings") %}<p><b>Avisos:</b> {{ deck["warnings"] }}</p>{% endif %}
  {% endfor %}
{% endif %}
<p><a href="/">voltar</a></p>
"""

ADMIN_HTML = """
<!doctype html>
<title>Admin</title>
<h2>Admin</h2>

<form method="post" action="/update_cards_form">
  <button type="submit">Atualizar cartas (Supercell API)</button>
</form>

<hr>
<h3>Atualizar Meta</h3>
<form method="post" action="/update_meta_form">
  <p>Cole o JSON completo do meta (meta_snapshot.json):</p>
  <textarea name="meta" rows="14" cols="100" placeholder='{"period":"...","archetypes":[...]}'></textarea>
  <br><br>
  <button type="submit">Salvar meta</button>
</form>

<p><a href="/">voltar</a></p>
"""

IMPORT_HTML = """
<!doctype html>
<title>Importar Player</title>
<h2>Importar Player por TAG</h2>
<form method="post" action="/import">
  <label>ID local do player (ex: samuel):</label>
  <input name="player_id" value="samuel"/>
  <br><br>
  <label>Player TAG (ex: #ABCD123):</label>
  <input name="tag" placeholder="#ABCD123"/>
  <br><br>
  <button type="submit">Importar</button>
</form>
{% if msg %}
  <p><b>{{msg}}</b></p>
{% endif %}
<p><a href="/">voltar</a></p>
"""

def _require_api_key():
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY ausente no ambiente.")
    return api_key

def _prepare_decks_output(player_id, result):
    cards = get_cards() or []
    cards_idx = {c["name"]: c for c in cards if "name" in c}
    player = get_player(player_id) or {}
    evo_owned = [n for n, info in (player.get("cards_owned") or {}).items() if info.get("evolution")]

    decks = []
    for d in result.get("decks", []):
        raw = (d.get("cards") or [])[:8]
        fixed = validate_cards(raw, cards_idx)
        evos = clamp_evolutions(d.get("evolved_cards", []) or [], evo_owned, max_per_deck=2)
        avg = average_elixir(fixed, cards_idx)
        decks.append({
            "cards": fixed,
            "avg_elixir": avg,
            "evolved_cards": evos,
            "reasons": d.get("reasons", ""),
            "warnings": d.get("warnings", ""),
        })
    return { "decks": decks }

@app.route("/")
def home():
    return HOME_HTML

# ===== UI =====
@app.route("/ui")
def ui_form():
    return render_template_string(UI_HTML, players=list_players())

@app.route("/build_decks_form", methods=["POST"])
def build_decks_form():
    player_id = request.form.get("player_id","").strip().lower()
    prompt = request.form.get("prompt","").strip()
    if not player_id or not prompt:
        return render_template_string(UI_HTML, players=list_players(),
                                      error="player_id e prompt são obrigatórios")

    player = get_player(player_id)
    if not player:
        return render_template_string(UI_HTML, players=list_players(),
                                      error=f"player '{player_id}' não encontrado")

    if not player.get("cards_owned"):
        return render_template_string(UI_HTML, players=list_players(),
                                      error=f"player '{player_id}' sem cartas. Importe em /import.")

    cards = get_cards()
    meta = get_meta()
    if not cards:
        return render_template_string(UI_HTML, players=list_players(),
                                      error="Sem cards cache. Vá em /admin e clique 'Atualizar cartas'.")
    if not meta or not meta.get("archetypes"):
        return render_template_string(UI_HTML, players=list_players(),
                                      error="Sem meta. Vá em /admin e cole o meta.")

    payload = build_llm_payload(player, cards, meta, prompt, max_evos_per_deck=2)

    try:
        result = suggest_three_decks(payload)
    except Exception as e:
        logging.exception("Falha na IA")
        return render_template_string(UI_HTML, players=list_players(),
                                      error=f"IA falhou: {e}")

    out = _prepare_decks_output(player_id, result)
    return render_template_string(UI_HTML, players=list_players(), result=out)

@app.route("/admin")
def admin():
    return render_template_string(ADMIN_HTML)

@app.route("/update_cards_form", methods=["POST"])
def update_cards_form():
    api_key = _require_api_key()
    total = update_cards_cache(api_key)
    logging.info(f"[CARDS] Atualizados: {total}")
    return redirect(url_for('admin'))

@app.route("/update_meta_form", methods=["POST"])
def update_meta_form():
    text = request.form.get("meta","")
    try:
        meta = json.loads(text)
        save_json("data/meta_snapshot.json", meta)
        logging.info("[META] meta_snapshot.json salvo.")
        return redirect(url_for('admin'))
    except Exception as e:
        return f"JSON inválido: {e}", 400

# ===== Import robusto =====
@app.route("/import", methods=["GET","POST"])
def import_form():
    msg = None
    if request.method == "POST":
        api_key = _require_api_key()
        pid = (request.form.get("player_id","").strip() or "samuel").lower()
        tag = (request.form.get("tag","").strip() or "").upper()
        if not pid or not tag:
            msg = "player_id e tag são obrigatórios"
        else:
            try:
                raw = fetch_player_by_tag(api_key, tag)
                if not raw:
                    msg = "❌ Erro ao importar: verifique TAG e permissões de API (token/IP)."
                else:
                    doc = transform_player_to_schema(pid, raw)
                    # sanity check: cards_owned precisa existir
                    if not doc or not isinstance(doc, dict) or not doc.get("cards_owned"):
                        msg = "❌ Import retornou sem cartas. Verifique TAG e escopo da API."
                    else:
                        save_player(pid, doc)  # storage.save_json atômico por baixo
                        msg = f"✅ Player '{pid}' importado com {len(doc['cards_owned'])} cartas."
                        logging.info(f"[IMPORT] Player '{pid}' salvo.")
            except Exception as e:
                logging.exception("Falha no import")
                msg = f"❌ Erro inesperado ao importar: {e}"

    return render_template_string(IMPORT_HTML, msg=msg)

# ===== API endpoints =====
@app.route("/update_cards", methods=["POST"])
def update_cards():
    api_key = _require_api_key()
    total = update_cards_cache(api_key)
    return jsonify({"updated": total})

@app.route("/update_meta", methods=["POST"])
def update_meta():
    try:
        meta = request.get_json(force=True)
        save_json("data/meta_snapshot.json", meta)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.route("/players")
def players_list():
    return jsonify({"players": list_players()})

@app.route("/players/import_tag", methods=["POST"])
def players_import_tag():
    api_key = _require_api_key()
    data = request.get_json(force=True)
    pid = (data.get("player_id","").strip() or "samuel").lower()
    tag = (data.get("tag","").strip() or "").upper()
    if not pid or not tag:
        return jsonify({"ok": False, "error": "player_id e tag são obrigatórios"}), 400
    raw = fetch_player_by_tag(api_key, tag)
    if not raw:
        return jsonify({"ok": False, "error": "Falha ao buscar player na API Supercell"}), 502
    doc = transform_player_to_schema(pid, raw)
    if not doc or not doc.get("cards_owned"):
        return jsonify({"ok": False, "error": "Transform retornou sem cartas"}), 500
    save_player(pid, doc)
    return jsonify({"ok": True, "player_id": pid, "cards": len(doc["cards_owned"])})

@app.route("/players/add_card", methods=["POST"])
def players_add_card():
    data = request.get_json(force=True)
    pid = (data.get("player_id","").strip() or "").lower()
    name = data.get("name","").strip()
    level = int(data.get("level", 11))
    evolution = bool(data.get("evolution", False))
    player = get_player(pid)
    if not player:
        return jsonify({"ok": False, "error": "player não encontrado"}), 404
    if "cards_owned" not in player:
        player["cards_owned"] = {}
    player["cards_owned"][name] = {"level": level, "evolution": evolution}
    save_player(pid, player)
    return jsonify({"ok": True})

@app.route("/build_decks", methods=["POST"])
def build_decks():
    data = request.get_json(force=True)
    player_id = (data.get("player_id","").strip() or "").lower()
    prompt = (data.get("prompt","").strip() or "")
    if not player_id or not prompt:
        return jsonify({"ok": False, "error":"player_id e prompt são obrigatórios"}), 400

    player = get_player(player_id)
    cards = get_cards()
    meta = get_meta()
    if not player: return jsonify({"ok": False, "error":"player não encontrado"}), 404
    if not player.get("cards_owned"): return jsonify({"ok": False, "error":"player sem cartas. Importe em /import"}), 400
    if not cards: return jsonify({"ok": False, "error":"sem cards cache; chame /update_cards"}), 400
    if not meta or not meta.get("archetypes"): return jsonify({"ok": False, "error":"sem meta; POST /update_meta"}), 400

    payload = build_llm_payload(player, cards, meta, prompt, max_evos_per_deck=2)
    try:
        result = suggest_three_decks(payload)
    except Exception as e:
        logging.exception("Falha na IA")
        return jsonify({"ok": False, "error": str(e)}), 500

    out = _prepare_decks_output(player_id, result)
    return jsonify({"ok": True, **out})

# ===== Debug de arquivos no Render =====
@app.route("/debug/files")
def debug_files():
    try:
        players_dir = os.path.exists("data/players")
        files = []
        if players_dir:
            files = [f for f in os.listdir("data/players") if f.endswith(".json")]
        resp = {
            "players_dir_exists": players_dir,
            "players_files": files,
            "meta_exists": os.path.exists("data/meta_snapshot.json"),
            "cards_exists": os.path.exists("data/cards.json"),
        }
        return jsonify(resp)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
