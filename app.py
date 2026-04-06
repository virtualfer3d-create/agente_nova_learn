import os
import telebot
from groq import Groq
from flask import Flask, request

# Configuración de variables de entorno
TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_KEY = os.environ.get('GROQ_API_KEY')

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)
app = Flask(__name__)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "¡Hola! Soy tu nuevo Agente IA creado con el Método Nova. ¿En qué puedo ayudarte?")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": message.text}],
            model="llama3-8b-8192",
        )
        response = chat_completion.choices[0].message.content
        bot.reply_to(message, response)
    except Exception:
        bot.reply_to(message, "Ups, algo ha fallado. Revisa tus claves en Render.")

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    return "Bot de Tutorial Operativo", 200

# BLOQUE FINAL OBLIGATORIO PARA RENDER + GUNICORN (PUERTO 10000)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

