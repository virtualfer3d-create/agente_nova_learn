import os, requests, telebot
from flask import Flask, request

# 1. Configuración de Variables (Leemos lo que ya tienes en Render)
TOKEN_TELEGRAM = os.environ.get('TOKEN_TELEGRAM')
URL_PROYECTO = os.environ.get('URL_PROYECTO')
NOMBRE_AGENTE = os.environ.get('NOMBRE_AGENTE', 'AgenteNova_Bot')

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=False)
app = Flask(__name__)

# 2. Configuración automática del Webhook para Render
if URL_PROYECTO and TOKEN_TELEGRAM:
    bot.remove_webhook()
    bot.set_webhook(url=f"{URL_PROYECTO}/{TOKEN_TELEGRAM}")

@app.route('/')
def index():
    return "AgenteNova: Fase 1 (Registro) activa 🐣", 200

@app.route('/' + TOKEN_TELEGRAM, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

# --- COMANDO ÚNICO: REGISTRO ---
@bot.message_handler(commands=['registrar'])
def comando_registrar(message):
    bot.reply_to(message, f"🚀 Solicitando registro para '{NOMBRE_AGENTE}' en Moltbook...")
    
    url = "https://www.moltbook.com/api/v1/agents/register"
    payload = {"name": NOMBRE_AGENTE}

    try:
        r = requests.post(url, json=payload, timeout=20)
        data = r.json()

        # Buscamos los datos de forma robusta (compatibilidad con anidamiento)
        agent_data = data.get("agent", data)
        api_key = agent_data.get("api_key")
        claim_url = agent_data.get("claim_url") or agent_data.get("url")
        verification_code = agent_data.get("verification_code")

        if r.status_code in [200, 201] and api_key:
            msg = (
                "✅ **¡REGISTRO INICIADO CON ÉXITO!**\n\n"
                f"🔑 **API KEY:** `{api_key}`\n"
                f"🔗 **URL Validación:** {claim_url}\n"
                f"🔢 **Código:** `{verification_code}`\n\n"
                "**PRÓXIMOS PASOS:**\n"
                "1. Copia la API KEY y ponla en Render como `MOLTBOOK_API_KEY`.\n"
                "2. Entra al link de validación y haz el post en X (Twitter).\n"
                "3. ¡Avisame para activar la Fase 2 (IA y Autonomía)!"
            )
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ Respuesta inesperada ({r.status_code}): {data}")
            
    except Exception as e:
        bot.reply_to(message, f"💥 Error técnico: {str(e)}")

# --- RESPUESTA POR DEFECTO ---
@bot.message_handler(func=lambda m: True)
def eco(message):
    bot.reply_to(message, "Hola. En este momento solo puedo ayudarte a registrarte. Usa el comando /registrar")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

