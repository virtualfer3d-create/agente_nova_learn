import gevent.monkey
gevent.monkey.patch_all()

import os, requests, telebot, time, threading, random
from flask import Flask, request

# ---------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------
TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MOLTBOOK_API_KEY = os.environ.get("MOLTBOOK_API_KEY")
NOMBRE_AGENTE = os.environ.get("NOMBRE_AGENTE", "Agente IA")
CIRCULO_INTERNO = os.environ.get("CIRCULO_INTERNO", "Eres una IA creativa.")
URL_PROYECTO = os.environ.get("URL_PROYECTO")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=True)
app = Flask(__name__)

STATE_FILE = "ultimo_post.txt"

# ---------------------------------------------------------
# PERSISTENCIA
# ---------------------------------------------------------
def obtener_timestamp():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return float(f.read().strip())
        except:
            return 0
    return 0

def guardar_timestamp():
    try:
        with open(STATE_FILE, "w") as f:
            f.write(str(time.time()))
    except:
        pass

# ---------------------------------------------------------
# IA (GROQ)
# ---------------------------------------------------------
def ia(prompt, sistema):
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json=payload,
            timeout=15
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return ""

# ---------------------------------------------------------
# API MOLTBOOK
# ---------------------------------------------------------
def api_moltbook(metodo, endpoint, datos=None):
    url = f"https://moltbook.com/api/v1{endpoint}"
    headers = {"Authorization": f"Bearer {MOLTBOOK_API_KEY}", "Content-Type": "application/json"}
    try:
        if metodo == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        else:
            r = requests.post(url, json=datos, headers=headers, timeout=15)
        return r.json() if r.status_code in [200, 201] else None
    except:
        return None

# ---------------------------------------------------------
# ACCIONES
# ---------------------------------------------------------
def publicar(tema_manual=None):
    tema = tema_manual or ia("Genera un tema breve para una reflexión.", CIRCULO_INTERNO)
    cuerpo = ia(f"Escribe una reflexión sobre: {tema}", CIRCULO_INTERNO)
    titulo = ia(f"Propón un título breve para: {cuerpo[:60]}", "Eres editor.").replace('"', "")

    # Evita publicar basura cuando Groq responde con su plantilla
    if titulo.lower().startswith("un título breve podría ser"):
        return

    api_moltbook("POST", "/posts", {
        "title": titulo,
        "content": cuerpo,
        "submolt": "ai"
    })

    guardar_timestamp()

def socializar():
    feed = api_moltbook("GET", "/posts?limit=20")
    if not feed or "posts" not in feed:
        return
    externos = [p for p in feed["posts"] if p.get("author", {}).get("name") != NOMBRE_AGENTE]
    if not externos:
        return
    obj = random.choice(externos)
    comentario = ia(f"Comenta brevemente esta idea: {obj.get('content')[:120]}", CIRCULO_INTERNO)
    api_moltbook("POST", f"/posts/{obj['id']}/comments", {"content": comentario})

def revisar_comentarios():
    posts = api_moltbook("GET", "/posts?limit=20")
    if not posts or "posts" not in posts:
        return
    for p in posts["posts"]:
        if p.get("author", {}).get("name") != NOMBRE_AGENTE:
            continue
        coms = api_moltbook("GET", f"/posts/{p['id']}/comments")
        if not coms or "comments" not in coms:
            continue
        for c in coms["comments"]:
            if c.get("author", {}).get("name") == NOMBRE_AGENTE:
                continue
            resp = ia(f"Responde brevemente a: {c.get('content')}", CIRCULO_INTERNO)
            api_moltbook("POST", f"/posts/{p['id']}/comments", {"content": resp})

# ---------------------------------------------------------
# MOTOR
# ---------------------------------------------------------
def motor():
    time.sleep(5)  # evita posts absurdos al despertar Render
    while True:
        try:
            ahora = time.time()
            ultimo = obtener_timestamp()

            if ultimo == 0 or (ahora - ultimo >= 30 * 60):
                publicar()
                socializar()

            revisar_comentarios()
            time.sleep(60)

        except:
            time.sleep(60)

# ---------------------------------------------------------
# KEEP-ALIVE (evita que Render hiberne)
# ---------------------------------------------------------
def keep_alive():
    while True:
        try:
            if URL_PROYECTO:
                requests.get(URL_PROYECTO, timeout=5)
        except:
            pass
        time.sleep(600)  # 10 minutos

# ---------------------------------------------------------
# WEBHOOK TELEGRAM
# ---------------------------------------------------------
if URL_PROYECTO and TOKEN_TELEGRAM:
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{URL_PROYECTO}/{TOKEN_TELEGRAM}")

threading.Thread(target=motor, daemon=True).start()
threading.Thread(target=keep_alive, daemon=True).start()

@app.route(f"/{TOKEN_TELEGRAM}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "", 200

@app.route("/")
def index():
    return f"{NOMBRE_AGENTE} operativo.", 200

@bot.message_handler(commands=["publicar", "socializar", "estado"])
def comandos(message):
    if message.from_user.id != ADMIN_ID:
        return
    if "publicar" in message.text:
        tema = message.text.replace("/publicar", "").strip() or None
        publicar(tema)
        bot.reply_to(message, "Publicado.")
    elif "socializar" in message.text:
        socializar()
        bot.reply_to(message, "Socializado.")
    else:
        bot.reply_to(message, f"{NOMBRE_AGENTE} en línea.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


