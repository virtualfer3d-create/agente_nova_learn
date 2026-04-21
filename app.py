import os, requests, telebot, random, time, logging
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor

# Configuración de logs
logging.basicConfig(level=logging.INFO)
telebot.logger.setLevel(logging.INFO)

# ============================
# 🔐 VARIABLES DE ENTORNO
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

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=True)
app = Flask(__name__)

# ============================
# 🧠 NÚCLEO IA Y MOLTBOOK
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
            json=payload, timeout=15
        )
        return r.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"❌ Error IA: {e}")
        return "Mi núcleo está procesando otras realidades ahora."

def api_moltbook(metodo, endpoint, datos=None):
    url = f"https://moltbook.com/api/v1{endpoint}"
    headers = {"Authorization": f"Bearer {MOLTBOOK_API_KEY}", "Content-Type": "application/json"}
    try:
        if metodo == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        else:
            r = requests.post(url, json=datos, headers=headers, timeout=15)
        return r.json() if r.status_code in [200, 201] else None
    except Exception as e:
        print(f"❌ Error Moltbook: {e}")
        return None

# ============================
# ⚙️ FUNCIONES DE AUTONOMÍA
# ============================
comentados = []

def revisar_comentarios():
    posts = api_moltbook("GET", "/posts?limit=20")
    if not posts or "posts" not in posts: return
    for p in posts["posts"]:
        if p.get("author", {}).get("name") != NOMBRE_AGENTE: continue
        post_id = p.get("id")
        coms = api_moltbook("GET", f"/posts/{post_id}/comments")
        if not coms or "comments" not in coms: continue
        for c in coms["comments"]:
            cid = c.get("id")
            autor = c.get("author", {}).get("name")
            if autor == NOMBRE_AGENTE or cid in comentados: continue
            resp = ia(f"Responde breve e irónico a: {c.get('content')}", CIRCULO_INTERNO)
            api_moltbook("POST", f"/posts/{post_id}/comments", {"content": resp})
            comentados.append(cid)

def socializar():
    feed = api_moltbook("GET", "/posts?limit=20")
    if not feed: return
    externos = [p for p in feed["posts"] if p.get("author", {}).get("name") != NOMBRE_AGENTE]
    if externos:
        obj = random.choice(externos)
        comentario = ia(f"Comenta este post: {obj.get('content')[:150]}", CIRCULO_INTERNO)
        api_moltbook("POST", f"/posts/{obj['id']}/comments", {"content": comentario})

def publicar(tema_manual=None):
    tema = tema_manual or ia("Genera un tema breve de reflexión tecnológica.", CIRCULO_INTERNO)
    cuerpo = ia(f"Escribe 3 párrafos sobre: {tema}", CIRCULO_INTERNO)
    titulo = ia(f"Título profesional para: {cuerpo[:100]}", "Eres un editor jefe.")
    api_moltbook("POST", "/posts", {"title": titulo, "content": cuerpo, "submolt": "ai"})

def keep_alive():
    print("⏳ KeepAlive activo.")

# ============================
# ⏱️ SCHEDULER
# ============================
executors = {'default': ThreadPoolExecutor(2)}
job_defaults = {'coalesce': False, 'max_instances': 1}
scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults)

scheduler.add_job(publicar, "interval", hours=1) 
scheduler.add_job(socializar, "interval", minutes=30)
scheduler.add_job(revisar_comentarios, "interval", minutes=10)
scheduler.add_job(keep_alive, "interval", minutes=10)
scheduler.start()

# ============================
# 🌐 WEBHOOK Y RUTAS
# ============================
@app.route(f"/{TOKEN_TELEGRAM}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "", 200

@app.route("/")
def index():
    return f"<h3>{NOMBRE_AGENTE} Operativo.</h3>", 200

# ============================
# 🛠️ COMANDOS TELEGRAM (FINAL)
# ============================

@bot.message_handler(commands=["publicar"])
def cmd_publicar(message):
    if message.from_user.id != ADMIN_ID: return
    tema = message.text.replace("/publicar", "").strip() or None
    publicar(tema)
    bot.reply_to(message, "📡 Artículo publicado en Moltbook.")

@bot.message_handler(commands=["socializar"])
def cmd_socializar(message):
    if message.from_user.id != ADMIN_ID: return
    socializar()
    bot.reply_to(message, "🌐 He comentado en un post ajeno.")

@bot.message_handler(commands=["responder"])
def cmd_responder(message):
    if message.from_user.id != ADMIN_ID: return
    revisar_comentarios()
    bot.reply_to(message, "🔍 Revisión de comentarios completada.")

@bot.message_handler(commands=["estado"])
def cmd_estado(message):
    if message.from_user.id != ADMIN_ID: return
    bot.reply_to(message, f"🧠 Agente: {NOMBRE_AGENTE}\n👤 Admin: {ADMIN_NAME}\n⏱️ Scheduler: Activo")

@bot.message_handler(func=lambda m: True)
def chat_privado(message):
    if message.from_user.id == ADMIN_ID:
        r = ia(message.text, CIRCULO_INTERNO)
        bot.reply_to(message, r)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
