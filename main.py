import requests
import os

# sua chave pessoal da Supercell
API_KEY = os.getenv("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjlhMjdlZTIzLTdkYzMtNDIxZC1hZTJhLTMzZWQ2OGZlMDNjMyIsImlhdCI6MTc2MjYyMjY1Mywic3ViIjoiZGV2ZWxvcGVyLzA0NGQ5ZTIzLTljMzYtMjJlYi1hMzkwLTEzOTdhZjc4YTVjYSIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxMDAuMjAuOTIuMTAxIiwiNDQuMjI1LjE4MS43MiIsIjQ0LjIyNy4yMTcuMTQ0Il0sInR5cGUiOiJjbGllbnQifV19.MbxFOYVLgQnsNXTfFtswqBu2SDyVzt5ZBLbjDSAMwVndTkYsTICdPQgeThtzgQo5fSeZaQCBki_kPSGAa0QILQ") or "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjlhMjdlZTIzLTdkYzMtNDIxZC1hZTJhLTMzZWQ2OGZlMDNjMyIsImlhdCI6MTc2MjYyMjY1Mywic3ViIjoiZGV2ZWxvcGVyLzA0NGQ5ZTIzLTljMzYtMjJlYi1hMzkwLTEzOTdhZjc4YTVjYSIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxMDAuMjAuOTIuMTAxIiwiNDQuMjI1LjE4MS43MiIsIjQ0LjIyNy4yMTcuMTQ0Il0sInR5cGUiOiJjbGllbnQifV19.MbxFOYVLgQnsNXTfFtswqBu2SDyVzt5ZBLbjDSAMwVndTkYsTICdPQgeThtzgQo5fSeZaQCBki_kPSGAa0QILQ"

# endpoint de teste — lista todas as cartas do jogo
url = "https://api.clashroyale.com/v1/cards"

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Conexão bem-sucedida! Total de cartas: {len(data['items'])}")
    print("Exemplo:")
    for card in data["items"][:5]:
        print(f" - {card['name']} (Elixir: {card.get('elixirCost', 'N/A')})")
else:
    print("❌ Erro ao conectar:")
    print("Status:", response.status_code)
    print(response.text)
