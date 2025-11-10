# cadastra/apaga players
from storage import save_player, delete_player, get_player

def create_player_interactive():
    pid = input("ID do player (ex: samuel): ").strip().lower()
    if not pid:
        print("ID inválido."); return
    data = {"cards_owned": {}, "preferences": {"bans": [], "must_have": []}}
    save_player(pid, data)
    print(f"Player '{pid}' criado em data/players/{pid}.json")

def delete_player_interactive():
    pid = input("ID do player para apagar: ").strip().lower()
    if not pid:
        print("ID inválido."); return
    ok = delete_player(pid)
    print("Apagado." if ok else "Player não encontrado.")

def quick_add_card():
    pid = input("ID do player: ").strip().lower()
    pl = get_player(pid)
    if not pl:
        print("Player não encontrado."); return
    name = input("Nome EXATO da carta (em inglês): ").strip()
    try:
        lvl = int(input("Nível da carta (ex: 12): ").strip())
    except:
        lvl = 11
    evo = input("Esta carta tem evolução habilitada para este player? (s/n): ").strip().lower() == "s"
    pl.setdefault("cards_owned", {})[name] = {"level": lvl, "evolution": evo}
    save_player(pid, pl)
    print(f"Carta '{name}' nível {lvl} (evo={evo}) adicionada a {pid}.")
