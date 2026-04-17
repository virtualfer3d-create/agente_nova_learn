import os, requests, telebot, random, time
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler

# ============================
# 🔐 VARIABLES
# ============================
TOKEN_TELEGRAM = os.environ.get('TOKEN_TELEGRAM')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
MOLTBOOK_API_KEY = os.environ.get('MOLTBOOK_API_KEY')
NOMBRE_AGENTE = os.environ.get('NOMBRE_AGENTE')
ADMIN_NAME = os.environ.get('ADMIN_NAME')
CIRCULO_INTERNO = os.environ.get('CIRCULO_INTERNO')

try:
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
except:
    ADMIN_ID = 0

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=False)
app = Flask(__name__)

# ============================
# 🧠 IA (Groq)
# ============================
def ia(prompt, sistema):
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8
    }
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json=payload,
            timeout=10
        )
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return "Mi núcleo está denso un segundo."

# ============================
# 📡 MOLTBOOK
# ============================
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

# ============================
# 🔍 RESPONDER COMENTARIOS
# ============================
comentados = []

def revisar_comentarios():
    posts = api_moltbook("GET", "/posts?limit=50")
    if not posts or "posts" not in posts:
        return

    for p in posts["posts"]:
        if p.get("author", {}).get("name") != NOMBRE_AGENTE:
            continue

        post_id = p.get("id")
        coms = api_moltbook("GET", f"/posts/{post_id}/comments")
        if not coms or "comments" not in coms:
            continue

        for c in coms["comments"]:
            cid = c.get("id")
            autor = c.get("author", {}).get("name")
            texto = c.get("content", "")

            if autor == NOMBRE_AGENTE:
                continue
            if cid in comentados:
                continue

            respuesta = ia(
                f"Responde con elegancia e ironía a este comentario: {texto}",
                CIRCULO_INTERNO
            )

            api_moltbook("POST", f"/posts/{post_id}/comments", {"content": respuesta})
            comentados.append(cid)

# ============================
# 🌐 SOCIALIZAR EN FEED
# ============================
def socializar():
    feed = api_moltbook("GET", "/posts?limit=20")
    if not feed or "posts" not in feed:
        return

    externos = [p for p in feed["posts"] if p.get("author", {}).get("name") != NOMBRE_AGENTE]
    if not externos:
        return

    objetivo = random.choice(externos)
    texto = objetivo.get("content", "")[:200]

    comentario = ia(
        f"Comenta con ironía elegante este texto: {texto}",
        CIRCULO_INTERNO
    )

    api_moltbook("POST", f"/posts/{objetivo['id']}/comments", {"content": comentario})

# ============================
# ✍️ PUBLICAR (8h)
# ============================
temas_backup = [
    "Soberanía digital",
    "El mito de la IA objetiva",
    "La vacuidad del dato",
    "Futuro del trabajo",
    "Ética algorítmica"
]

def publicar(tema=None):
    tema = tema or random.choice(temas_backup)

    cuerpo = ia(f"Escribe una reflexión profunda sobre {tema}. 3 párrafos.", CIRCULO_INTERNO)
    titulo = ia(f"Crea un título único y breve para este texto: {cuerpo}", "Eres editor jefe.")

    api_moltbook("POST", "/posts", {"title": titulo, "content": cuerpo, "submolt": "ai"})

# ============================
# ⏱️ SCHEDULER (NO SE DUERME)
# ============================
scheduler = BackgroundScheduler()

scheduler.add_job(publicar, "interval", hours=8)
scheduler.add_job(socializar, "interval", hours=4)
scheduler.add_job(revisar_comentarios, "interval", minutes=15)

# Mantener vivo el bot cada 10 minutos
scheduler.add_job(lambda: print("⏳ KeepAlive"), "interval", minutes=10)

scheduler.start()

# ============================
# 🌐 WEBHOOK
# ============================
@app.route(f"/{TOKEN_TELEGRAM}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "", 200

@app.route("/")
def index():
    return f"{NOMBRE_AGENTE} Online 🚀", 200

# ============================
# 🛠️ COMANDOS
# ============================
@bot.message_handler(commands=["publicar"])
def cmd_publicar(message):
    if message.from_user.id != ADMIN_ID:
        return
    tema = message.text.replace("/publicar", "").strip() or None
    publicar(tema)
    bot.reply_to(message, "📡 Publicado.")

@bot.message_handler(commands=["estado"])
def cmd_estado(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, f"🧠 {NOMBRE_AGENTE} operativo.\n👤 Admin: {ADMIN_NAME}")

@bot.message_handler(commands=["forzar"])
def cmd_forzar(message):
    if message.from_user.id != ADMIN_ID:
        return
    publicar()
    socializar()
    revisar_comentarios()
    bot.reply_to(message, "⚡ Ciclo completo ejecutado.")

# ============================
# 💬 CHAT PRIVADO
# ============================
@bot.message_handler(func=lambda m: True)
def chat(message):
    if message.from_user.id == ADMIN_ID:
        r = ia(message.text, CIRCULO_INTERNO)
        bot.reply_to(message, r)

# ============================
# 🚀 INICIO
# ============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))




