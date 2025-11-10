import os, sys, json
from api import update_cards_cache, fetch_player_by_tag, transform_player_to_schema
from storage import get_cards, get_meta, save_json, list_players, get_player, save_player
from prompt_builder import build_llm_payload
from ai_gemini import suggest_three_decks
from deck_postprocess import validate_cards, clamp_evolutions, average_elixir
from player_admin import create_player_interactive, delete_player_interactive, quick_add_card

def menu():
    print("\n=== Clash Deck Builder (Menu) ===")
    print("1) Atualizar cache de cartas (Supercell API)")
    print("2) Atualizar Meta (colar JSON dos últimos 4 meses)")
    print("3) Cadastrar/Apagar player (e adicionar cartas/evoluções)")
    print("4) Montar 3 decks (IA Gemini)")
    print("0) Sair")
    return input("Opção: ").strip()

def atualizar_cartas():
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("Defina API_KEY no ambiente (Render Settings → Environment).")
        return
    total = update_cards_cache(api_key)
    print(f"✅ Cartas atualizadas: {total}")

def atualizar_meta():
    print("Cole abaixo o JSON completo do meta (meta_snapshot.json).")
    print("Quando terminar, digite uma linha com apenas: FIM")
    lines = []
    while True:
        line = sys.stdin.readline()
        if not line: break
        if line.strip().upper() == "FIM": break
        lines.append(line)
    text = "".join(lines)
    try:
        data = json.loads(text)
        save_json("data/meta_snapshot.json", data)
        print("✅ Meta salvo em data/meta_snapshot.json")
    except Exception as e:
        print("❌ JSON inválido:", e)

def menu_players():
    print("\n=== Players ===")
    print("1) Cadastrar player (vazio)")
    print("2) Apagar player")
    print("3) Adicionar carta (nível/evolução)")
    print("4) Importar do Clash (por TAG)")  # NOVO
    print("0) Voltar")
    op = input("Opção: ").strip()
    if op == "1": create_player_interactive()
    elif op == "2": delete_player_interactive()
    elif op == "3": quick_add_card()
    elif op == "4": importar_player_por_tag()  # NOVO


def montar_decks():
    players = list_players()
    if not players:
        print("Nenhum player cadastrado. Use opção 3 primeiro.")
        return
    print("\n=== Selecionar Player ===")
    for i,p in enumerate(players,1): print(f"{i}) {p}")
    try:
        idx = int(input("Escolha: ").strip()); pid = players[idx-1]
    except:
        print("Escolha inválida."); return

    player = get_player(pid)
    cards = get_cards()
    meta = get_meta()
    if not cards:
        print("Sem cards cache. Rode opção 1 primeiro."); return
    if not meta or not meta.get("archetypes"):
        print("Sem meta. Rode opção 2 e cole meta_snapshot.json."); return

    prompt = input("Descreva o deck (ex: '2.6 com P.E.K.K.A e Dark Prince'): ")
    payload = build_llm_payload(player, cards, meta, prompt, max_evos_per_deck=2)

    try:
        result = suggest_three_decks(payload)
    except Exception as e:
        print("❌ Falha na IA:", e); return

    # pós-processo: validar nomes, calcular elixir, limitar evoluções a 2
    cards_idx = {c["name"]: c for c in cards}
    evolutions_owned = [n for n,info in (player.get("cards_owned") or {}).items() if info.get("evolution")]

    decks = result.get("decks", [])
    if not decks or len(decks) != 3:
        print("A IA não retornou 3 decks."); return

    print("\n=== Três decks sugeridos (nomes apenas) ===")
    for i, d in enumerate(decks, 1):
        raw = d.get("cards", [])[:8]
        fixed = validate_cards(raw, cards_idx)
        evos = clamp_evolutions(d.get("evolved_cards", []), evolutions_owned, max_per_deck=2)
        avg = average_elixir(fixed, cards_idx)
        print(f"\nDeck {i}:")
        for n in fixed: print(f"- {n}")
        if avg is not None: print(f"Média de Elixir: {avg}")
        if evos: print(f"Evoluções equipadas (<=2): {', '.join(evos)}")

def main():
    while True:
        op = menu()
        if op == "1": atualizar_cartas()
        elif op == "2": atualizar_meta()
        elif op == "3": menu_players()
        elif op == "4": montar_decks()
        elif op == "0": break
        else: print("Opção inválida.")

if __name__ == "__main__":
    main()
def importar_player_por_tag():
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("Defina API_KEY no ambiente (Render Settings → Environment).")
        return
    pid = input("ID local do player (ex: samuel): ").strip().lower()
    if not pid:
        print("ID inválido."); return
    tag = input("Player TAG (ex: #ABCD123): ").strip().upper()
    if not tag:
        print("TAG inválida."); return
    try:
        raw = fetch_player_by_tag(api_key, tag)
        doc = transform_player_to_schema(pid, raw)
        save_player(pid, doc)
        print(f"✅ Player '{pid}' importado com {len(doc['cards_owned'])} cartas.")
        print("Obs.: evoluções foram marcadas como False por padrão;")
        print("use 'Adicionar carta' no menu para ligar evoluções nas cartas que você tem.")
    except Exception as e:
        print("❌ Falha ao importar:", e)
