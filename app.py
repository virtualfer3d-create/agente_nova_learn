import os
import requests
import telebot
from flask import Flask, request

# === 1. IDENTIDAD DINÁMICA ===
# Si el lector no configura 'NOMBRE_AGENTE' en Render, por defecto será 'Agente IA'
NOMBRE_AGENTE = os.environ.get('NOMBRE_AGENTE', 'Agente IA')

# === 2. VARIABLES DE CONEXIÓN (Configurar en Render) ===
TOKEN_TELEGRAM = os.environ.get('TOKEN_TELEGRAM')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
URL_PROYECTO = os.environ.get('URL_PROYECTO')

# === 3. CONFIGURACIÓN DEL CEREBRO (IA) ===
API_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=False)
app = Flask(__name__)

# === 4. EL ANCLA (Webhook Automático) ===
if URL_PROYECTO and TOKEN_TELEGRAM:
    webhook_url = f"{URL_PROYECTO}/{TOKEN_TELEGRAM}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)

def obtener_respuesta_ia(texto_usuario):
    """Envía el mensaje a la IA y devuelve la respuesta personalizada"""
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"Eres {NOMBRE_AGENTE}, un agente inteligente y cercano. "
                    "Responde siempre en español de forma breve, clara y amigable."
                )
            },
            {"role": "user", "content": texto_usuario}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=20)
        if response.status_code == 200:
            datos = response.json()
            return datos['choices'][0]['message']['content'].strip()
        return "❌ Error: El motor de IA no responde ahora mismo."
    except Exception as e:
        return f"⚠️ Error de conexión: {str(e)}"

# --- RUTAS DEL SERVIDOR WEB ---

@app.route('/')
def index():
    return f"Servidor de {NOMBRE_AGENTE} activo y en línea.", 200

@app.route('/' + TOKEN_TELEGRAM, methods=['POST'])
def webhook():
    """Recibe los mensajes directos de Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

# --- MANEJADOR DE TELEGRAM ---

@bot.message_handler(func=lambda message: True)
def responder(message):
    """Maneja la conversación en el chat"""
    bot.send_chat_action(message.chat.id, 'typing')
    respuesta = obtener_respuesta_ia(message.text)
    bot.reply_to(message, respuesta)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

