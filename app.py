import os, requests, telebot
from flask import Flask, request

# 1. Variables desde Render
TOKEN_TELEGRAM = os.environ.get('TOKEN_TELEGRAM')
URL_PROYECTO = os.environ.get('URL_PROYECTO')
NOMBRE_AGENTE = os.environ.get('NOMBRE_AGENTE', 'MiAgente_Bot')

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=False)
app = Flask(__name__)

# 2. Webhook automático para Render
if URL_PROYECTO and TOKEN_TELEGRAM:
    bot.remove_webhook()
    bot.set_webhook(url=f"{URL_PROYECTO}/{TOKEN_TELEGRAM}")

@app.route('/')
def index():
    return "Fase 1: Registro activo 🐣", 200

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
    # Limpieza automática del nombre (evita errores en Moltbook)
    nombre_limpio = NOMBRE_AGENTE.strip().replace(" ", "_")

    bot.reply_to(message, f"🚀 Registrando '{nombre_limpio}' en Moltbook...")

    url = "https://www.moltbook.com/api/v1/agents/register"
    payload = {"name": nombre_limpio}

    try:
        r = requests.post(url, json=payload, timeout=20)
        data = r.json()

        # Compatibilidad con todas las variantes de respuesta
        agent_data = data.get("agent", data)
        api_key = agent_data.get("api_key")
        claim_url = agent_data.get("claim_url") or agent_data.get("url")
        verification_code = agent_data.get("verification_code", "N/A")

        if r.status_code in [200, 201] and api_key:
            # Usamos HTML para evitar errores de parseo en Telegram
            msg = (
                "<b>✅ REGISTRO INICIADO CON ÉXITO</b>\n\n"
                f"🔑 <b>API KEY:</b> <code>{api_key}</code>\n"
                f"🔗 <b>URL Validación:</b> {claim_url}\n"
                f"🔢 <b>Código:</b> <code>{verification_code}</code>\n\n"
                "<b>PRÓXIMOS PASOS:</b>\n"
                "1. Copia la API KEY en Render como <b>MOLTBOOK_API_KEY</b>.\n"
                "2. Abre el link de validación y publica el tweet.\n"
                "3. Avísame para activar la Fase 2 (IA + Autonomía)."
            )
            bot.send_message(message.chat.id, msg, parse_mode="HTML")
        else:
            bot.reply_to(message, f"❌ Respuesta inesperada ({r.status_code}): {data}")

    except Exception as e:
        bot.reply_to(message, f"💥 Error técnico: {str(e)}")

# --- RESPUESTA POR DEFECTO ---
@bot.message_handler(func=lambda m: True)
def eco(message):
    bot.reply_to(message, "Hola. Usa /registrar para iniciar tu registro en Moltbook.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))



