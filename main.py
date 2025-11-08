import requests

# 👉 Substitua isso pela sua própria chave da Supercell
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjIwNGRhNTljLWM2MGQtNDRjNy1iYWM5LTMxMDQ1Y2ZjYWM5OCIsImlhdCI6MTc2MTg3MTIwMSwic3ViIjoiZGV2ZWxvcGVyLzA0NGQ5ZTIzLTljMzYtMjJlYi1hMzkwLTEzOTdhZjc4YTVjYSIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyIxOTAuMTE1LjY2Ljk5Il0sInR5cGUiOiJjbGllbnQifV19.dxxWxOgs-fWrAlFKNFLbQgBxiYTywLCKMqmvSQ1iWS0bmZisRxjpfoP119ujuoqHacvnpOcZj0thSBdJnA09Ow"

# Tag do jogador (você encontra no Clash Royale — ex: #2PP ou #8YLUUQJ)
PLAYER_TAG = "2GJRJRQLG"

# Construindo a URL (note o %23 no lugar do #)
url = f"https://api.clashroyale.com/v1/players/%23{PLAYER_TAG}"

# Cabeçalhos obrigatórios (para autorização e formato de resposta)
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# Enviando a requisição
response = requests.get(url, headers=headers)

# Verificando o resultado
if response.status_code == 200:
    data = response.json()
    print("✅ Conexão bem-sucedida!")
    print("Nome:", data["name"])
    print("Nível:", data["expLevel"])
    print("Troféus:", data["trophies"])
else:
    print("❌ Erro ao conectar.")
    print("Status:", response.status_code)
    print(response.text)

