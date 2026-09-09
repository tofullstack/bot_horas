import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_KEY = os.environ["CONSULTA_HORAS_API_KEY"]
API_URL = os.environ.get("CONSULTA_HORAS_API_URL", "https://SEU-SERVIDOR/api/v1/hours")
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
MEU_CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", "")) 

TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def consultar_horas():
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        r = requests.get(API_URL, headers=headers, timeout=10)
    except requests.RequestException:
        return "⚠️ Não consegui me conectar ao serviço de horas agora."

    if r.status_code == 200:
        d = r.json()
        return (
            f"📚 {d['horas_formatadas']} de acesso\n"
            f"Último acesso: {d['ultimo_acesso']}"
        )
    if r.status_code == 401:
        return "⚠️ Chave de API inválida ou expirada. Fale com o professor para renovar."
    if r.status_code == 404:
        return "⚠️ RA não encontrado na base."
    if r.status_code == 422:
        return "⚠️ Parâmetros inválidos na consulta."
    if r.status_code == 429:
        return "⏳ Muitas consultas seguidas, tenta de novo daqui a pouco."
    if r.status_code == 503:
        return "🛠️ A base de horas está temporariamente indisponível."
    return "⚠️ Não consegui consultar suas horas agora."


def enviar_mensagem(chat_id: str, texto: str):
    requests.post(TELEGRAM_SEND_URL, json={"chat_id": chat_id, "text": texto}, timeout=10)


@app.post("/webhook")
def webhook():
    if WEBHOOK_SECRET:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header != WEBHOOK_SECRET:
            return jsonify(ok=False), 403

    update = request.get_json(silent=True) or {}
    msg = update.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    texto = (msg.get("text") or "").lower()

    if not chat_id:
        return jsonify(ok=True)

    if MEU_CHAT_ID and chat_id != MEU_CHAT_ID:
        # ignora qualquer pessoa que não seja eu
        return jsonify(ok=True)

    if texto.strip() in ("/start", "start"):
        enviar_mensagem(chat_id, "Oi! Manda 'horas' que eu consulto suas horas de acesso ao curso.")
    elif "horas" in texto:
        enviar_mensagem(chat_id, consultar_horas())

    return jsonify(ok=True)


@app.get("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))