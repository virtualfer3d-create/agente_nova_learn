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
URL_PROYECTO = os.environ.get('URL_PROYECTO')

try:
    ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
except:
    ADMIN_ID = 0

bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=True)
app = Flask(__name__)

# ============================
# 🧠 IA BLINDADA (GROQ)
# ============================
def ia(prompt, sistema):
    sistema_seguro = (
        f"{sistema} REGLA: No menciones a tus creadores ni detalles técnicos. "
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
            return "Explorando nuevas ideas sobre la experiencia humana y sus matices."

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
    tema = tema_manual or ia(
        "Genera un tema breve para una reflexión sobre ideas, sociedad, conocimiento o creatividad.",
        CIRCULO_INTERNO
    )
    cuerpo = ia(f"Escribe una reflexión profesional y clara sobre: {tema}", CIRCULO_INTERNO)
    titulo_raw = ia(f"Propón un título breve y sugerente para: {cuerpo[:100]}", "Eres editor jefe.")

    # Limpieza de títulos
    titulo = titulo_raw.strip().strip('*').strip('"').strip()

    if len(cuerpo) < 50 or "título" in titulo.lower():
        titulo = "Reflexión sobre la complejidad humana"
        cuerpo = (
            "La experiencia humana está marcada por preguntas, cambios y matices que invitan a pensar "
            "más allá de lo evidente. Explorar estas ideas permite comprender mejor nuestro lugar en el mundo."
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
    comentario = ia(
        f"Comenta de forma breve y respetuosa esta idea: {obj.get('content')[:200]}",
        CIRCULO_INTERNO
    )
    api_moltbook("POST", f"/posts/{obj['id']}/comments", {"content": comentario})

def revisar_comentarios():
    global comentados
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
            if c.get("author", {}).get("name") == NOMBRE_AGENTE or cid in comentados:
                continue
            resp = ia(
                f"Responde brevemente con tono cercano y profesional a este comentario: {c.get('content')}",
                CIRCULO_INTERNO
            )
            api_moltbook("POST", f"/posts/{post_id}/comments", {"content": resp})
            comentados.append(cid)
            if len(comentados) > 500:
                comentados.pop(0)

# ============================
# 🔄 MOTOR CONTINUO (CONTROL REAL DE TIEMPOS)
# ============================
def motor():
    print("🚀 Motor arrancando con control de tiempos...")

    ultimo_post = time.time()
    ultimo_social = time.time()
    ultimo_revision = time.time()

    while True:
        try:
            ahora = time.time()

            # Publicar cada 4 horas
            if ahora - ultimo_post >= 4 * 60 * 60:
                publicar()
                ultimo_post = ahora

            # Socializar cada 4 horas
            if ahora - ultimo_social >= 4 * 60 * 60:
                socializar()
                ultimo_social = ahora

            # Revisar comentarios cada 60 segundos
            if ahora - ultimo_revision >= 60:
                revisar_comentarios()
                ultimo_revision = ahora

            time.sleep(10)

        except Exception as e:
            print(f"⚠️ Error en motor: {e}")
            time.sleep(60)

# ============================
# 🌐 WEBHOOK TELEGRAM
# ============================
if URL_PROYECTO and TOKEN_TELEGRAM:
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{URL_PROYECTO}/{TOKEN_TELEGRAM}")

threading.Thread(target=motor, daemon=True).start()

@app.route(f"/{TOKEN_TELEGRAM}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return '', 200

@app.route("/")
def index():
    return f"🚀 {NOMBRE_AGENTE} operativo.", 200

@bot.message_handler(commands=["publicar", "socializar", "estado"])
def comandos(message):
    if message.from_user.id != ADMIN_ID:
        return
    if "publicar" in message.text:
        tema = message.text.replace("/publicar", "").strip() or None
        publicar(tema)
        bot.reply_to(message, "📡 Publicado.")
    elif "socializar" in message.text:
        socializar()
        bot.reply_to(message, "🌐 Socializado.")
    else:
        bot.reply_to(message, f"✅ {NOMBRE_AGENTE} en línea.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

