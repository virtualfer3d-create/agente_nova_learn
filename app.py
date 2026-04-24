import os, requests, telebot, time, threading, random
from flask import Flask, request

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
TOKEN = os.environ.get("TOKEN_TELEGRAM")
GROQ = os.environ.get("GROQ_API_KEY")
MOLT = os.environ.get("MOLTBOOK_API_KEY")
NOMBRE = os.environ.get("NOMBRE_AGENTE", "Agente IA")
SISTEMA = os.environ.get("CIRCULO_INTERNO", "Eres una IA creativa.")
URL = os.environ.get("URL_PROYECTO", "").rstrip("/")
ADMIN = int(os.environ.get("ADMIN_ID", 0))

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

STATE = "ultimo_post.txt"

# ---------------------------------------------------------
# PERSISTENCIA
# ---------------------------------------------------------
def ts_get():
    try:
        return float(open(STATE).read().strip())
    except:
        return 0

def ts_set():
    try:
        open(STATE, "w").write(str(time.time()))
    except:
        pass

# ---------------------------------------------------------
# IA
# ---------------------------------------------------------
def ia(prompt, sistema=SISTEMA):
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
            headers={"Authorization": f"Bearer {GROQ}"},
            json=payload,
            timeout=10
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return ""

# ---------------------------------------------------------
# MOLTBOOK
# ---------------------------------------------------------
def api(m, e, d=None):
    url = f"https://moltbook.com/api/v1{e}"
    h = {"Authorization": f"Bearer {MOLT}", "Content-Type": "application/json"}
    try:
        r = requests.get(url, headers=h, timeout=10) if m=="GET" else requests.post(url, json=d, headers=h, timeout=15)
        return r.json() if r.status_code in [200,201] else None
    except:
        return None

# ---------------------------------------------------------
# PUBLICAR
# ---------------------------------------------------------
def publicar(tema=None):
    tema = tema or ia("Genera un tema breve para una reflexión.", SISTEMA)
    cuerpo = ia(f"Escribe una reflexión sobre: {tema}", SISTEMA)

    titulo_raw = ia(
        f"Escribe SOLO el título para este texto, sin frases previas ni comillas: {cuerpo[:120]}",
        "Eres editor. Responde únicamente con el título limpio."
    )
    titulo = titulo_raw.replace('"', "").split(":")[-1].strip()
    if len(titulo) < 3:
        titulo = tema.strip()

    api("POST", "/posts", {"title": titulo, "content": cuerpo, "submolt": "ai"})
    ts_set()

# ---------------------------------------------------------
# SOCIALIZAR
# ---------------------------------------------------------
def socializar():
    feed = api("GET", "/posts?limit=20")
    if not feed or "posts" not in feed:
        return
    externos = [p for p in feed["posts"] if p.get("author", {}).get("name") != NOMBRE]
    if not externos:
        return
    obj = random.choice(externos)
    comentario = ia(f"Comenta brevemente esta idea: {obj.get('content')[:120]}", SISTEMA)
    api("POST", f"/posts/{obj['id']}/comments", {"content": comentario})

# ---------------------------------------------------------
# REVISAR COMENTARIOS
# ---------------------------------------------------------
def revisar():
    posts = api("GET", "/posts?limit=20")
    if not posts or "posts" not in posts:
        return
    for p in posts["posts"]:
        if p.get("author", {}).get("name") != NOMBRE:
            continue
        coms = api("GET", f"/posts/{p['id']}/comments")
        if not coms or "comments" not in coms:
            continue
        for c in coms["comments"]:
            if c.get("author", {}).get("name") == NOMBRE:
                continue
            resp = ia(f"Responde brevemente a: {c.get('content')}", SISTEMA)
            api("POST", f"/posts/{p['id']}/comments", {"content": resp})

# ---------------------------------------------------------
# MOTOR
# ---------------------------------------------------------
def motor():
    time.sleep(5)
    while True:
        try:
            ahora = time.time()
            ultimo = ts_get()            

            if ultimo == 0 or (ahora - ultimo >= 5*60*60):
                publicar()
                socializar()

            revisar()
            time.sleep(60)
        except:
            time.sleep(60)

# ---------------------------------------------------------
# KEEP-ALIVE
# ---------------------------------------------------------
def keep():
    while True:
        try:
            if URL:
                requests.get(URL, timeout=5)
        except:
            pass
        time.sleep(45)

# ---------------------------------------------------------
# WEBHOOK
# ---------------------------------------------------------
if URL and TOKEN:
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{URL}/{TOKEN}")

threading.Thread(target=motor, daemon=True).start()
threading.Thread(target=keep, daemon=True).start()

@app.route(f"/{TOKEN}", methods=["POST"])
def wh():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "", 200

@app.route("/")
def index():
    return f"{NOMBRE} operativo.", 200

@bot.message_handler(commands=["publicar", "socializar", "estado"])
def cmd(m):
    if m.from_user.id != ADMIN:
        return
    if "publicar" in m.text:
        tema = m.text.replace("/publicar", "").strip() or None
        publicar(tema)
        bot.reply_to(m, "Publicado.")
    elif "socializar" in m.text:
        socializar()
        bot.reply_to(m, "Socializado.")
    else:
        bot.reply_to(m, f"{NOMBRE} en línea.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))




