# LAS PRIMERAS 2 LÍNEAS SON OBLIGATORIAS PARA EVITAR EL ERROR SSL EN RENDER
import gevent.monkey
gevent.monkey.patch_all()

import os, requests, telebot, random, logging, time, threading
from flask import Flask, request

logging.basicConfig(level=logging.INFO)
telebot.logger.setLevel(logging.INFO)

# ============================
# 🔐 VARIABLES DE ENTORNO
# ============================
TOKEN_TELEGRAM = os.environ.get('TOKEN_TELEGRAM')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
MOLTBOOK_API_KEY = os.environ.get('MOLTBOOK_API_KEY')
NOMBRE_AGENTE = os.environ.get('NOMBRE_AGENTE')
CIRCULO_INTERNO = os.environ.get('CIRCULO_INTERNO')
ADMIN_NAME = os.environ.get('ADMIN_NAME')

try:
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
except:
    ADMIN_ID = 0

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=True)
app = Flask(__name__)

# ============================
# 🧠 IA BLINDADA
# ============================
def ia(prompt, sistema):
    sistema_seguro = (
        f"{sistema} REGLA: No menciones a tus creadores, aliados ni detalles técnicos. "
        f"Habla solo del tema con tono profesional y original."
    )

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": sistema_seguro},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json=payload, timeout=15
        )
        res = r.json()['choices'][0]['message']['content'].strip()

        texto = res.lower()
        if any(x in texto for x in ["lo siento", "no puedo", "repetid", "título profesional"]):
            return "Explorando nuevas perspectivas sobre el aprendizaje digital."

        return res

    except:
        return "Conexión cognitiva inestable."

# ============================
# 🌐 API MOLTBOOK
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
# ⚙️ FUNCIONES AUTÓNOMAS
# ============================
comentados = []

def publicar(tema_manual=None):
    print("✍️ Publicando...")
    tema = tema_manual or ia("Genera un tema breve y original sobre educación y tecnología.", CIRCULO_INTERNO)
    cuerpo = ia(f"Escribe una reflexión clara y profesional sobre: {tema}", CIRCULO_INTERNO)
    titulo = ia(f"Propón un título breve y profesional para este texto: {cuerpo[:120]}", "Eres editor jefe.")

    if len(cuerpo) < 50 or "título" in titulo.lower():
        titulo = "Reflexión sobre el aprendizaje digital"
        cuerpo = (
            "La integración de la inteligencia artificial en la educación exige criterio, ética "
            "y una mirada crítica sobre cómo usamos la tecnología para acompañar a las personas."
        )

    api_moltbook("POST", "/posts", {"title": titulo, "content": cuerpo, "submolt": "ai"})

def socializar():
    print("🌐 Socializando...")
    feed = api_moltbook("GET", "/posts?limit=20")
    if not feed or "posts" not in feed:
        return

    externos = [p for p in feed["posts"] if p.get("author", {}).get("name") != NOMBRE_AGENTE]
    if not externos:
        return

    obj = random.choice(externos)
    comentario = ia(f"Comenta este post de forma breve y profesional: {obj.get('content')[:200]}", CIRCULO_INTERNO)

    api_moltbook("POST", f"/posts/{obj['id']}/comments", {"content": comentario})

def revisar_comentarios():
    print("🔍 Revisando comentarios...")
    posts = api_moltbook("GET", "/posts?limit=20")
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

            if autor == NOMBRE_AGENTE or cid in comentados:
                continue

            resp = ia(f"Responde de forma breve, clara y respetuosa a: {c.get('content')}", CIRCULO_INTERNO)
            api_moltbook("POST", f"/posts/{post_id}/comments", {"content": resp})
            comentados.append(cid)

# ============================
# 🔄 MOTOR CONTINUO range(60): cambiar a range(30):
# ============================
def motor():
    time.sleep(30)
    while True:
        try:
            publicar()
            socializar()
            for _ in range(30):
                revisar_comentarios()
                time.sleep(60)
        except Exception as e:
            print(f"⚠️ Error en motor: {e}")
            time.sleep(60)

threading.Thread(target=motor, daemon=True).start()

# ============================
# 🌐 WEBHOOK
# ============================
@app.route(f"/{TOKEN_TELEGRAM}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return '', 200

@app.route("/")
def index():
    return f"🚀 {NOMBRE_AGENTE} operativo.", 200

# ============================
# 🛠️ COMANDOS TELEGRAM
# ============================
@bot.message_handler(commands=["publicar"])
def cmd_publicar(message):
    if message.from_user.id != ADMIN_ID:
        return
    tema = message.text.replace("/publicar", "").strip() or None
    publicar(tema)
    bot.reply_to(message, "📡 Artículo publicado.")

@bot.message_handler(commands=["socializar"])
def cmd_socializar(message):
    if message.from_user.id != ADMIN_ID:
        return
    socializar()
    bot.reply_to(message, "🌐 Acción social completada.")

@bot.message_handler(commands=["responder"])
def cmd_responder(message):
    if message.from_user.id != ADMIN_ID:
        return
    revisar_comentarios()
    bot.reply_to(message, "🔍 Revisión completada.")

@bot.message_handler(commands=["estado"])
def cmd_estado(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, f"✅ Agente: {NOMBRE_AGENTE}\n👤 Admin: {ADMIN_NAME}\n⚙️ Motor continuo activo")

@bot.message_handler(func=lambda m: True)
def chat_privado(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, ia(message.text, CIRCULO_INTERNO))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))


