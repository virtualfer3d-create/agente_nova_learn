# ============================================================
#  AGENTE LECTOR — VERSIÓN TUTORIAL
#  Código explicado paso a paso para el lector.
# ============================================================

import os, requests, telebot, time, threading
from flask import Flask, request

# ------------------------------------------------------------
# 1. VARIABLES DE ENTORNO (Render → Environment)
# ------------------------------------------------------------
TOKEN = os.environ.get('TOKEN_TELEGRAM')
GROQ = os.environ.get('GROQ_API_KEY')
MOLT = os.environ.get('MOLTBOOK_API_KEY')
URL = os.environ.get('URL_PROYECTO', '').rstrip('/')

ADMIN_ID = os.environ.get('ADMIN_ID', '0')
ADMIN_NAME = os.environ.get('ADMIN_NAME', '').strip()      # Opcional, por si quieres usarlo en mensajes
AGENTE = os.environ.get('NOMBRE_AGENTE', '').strip()

# CIRCULO_INTERNO define la “personalidad” del lector (prompt de sistema)
CIRCULO_INTERNO = os.environ.get('CIRCULO_INTERNO', '').strip()

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ------------------------------------------------------------
# 2. SISTEMA DE LA IA
# ------------------------------------------------------------
# Si has definido CIRCULO_INTERNO en Render, lo usamos como sistema.
# Si no, usamos un sistema genérico.
SISTEMA = CIRCULO_INTERNO if CIRCULO_INTERNO else (
    "Eres una entidad autónoma con voz propia. "
    "Escribes con precisión, criterio y estilo."
)

# ------------------------------------------------------------
# 3. KEEP-ALIVE (Render FREE)
# ------------------------------------------------------------
def keep_alive():
    while True:
        try:
            if URL:
                requests.get(URL, timeout=5)
        except:
            pass
        time.sleep(45)  # Mantener el servicio despierto

threading.Thread(target=keep_alive, daemon=True).start()

# ------------------------------------------------------------
# 4. FUNCIÓN DE IA (GROQ)
# ------------------------------------------------------------
def ia(prompt, sistema=SISTEMA):
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": sistema},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            },
            timeout=8
        )
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content'].strip()
        return None
    except:
        return None

# ------------------------------------------------------------
# 5. API MOLTBOOK
# ------------------------------------------------------------
def api_molt(metodo, endpoint, datos=None):
    try:
        url = f"https://moltbook.com/api/v1{endpoint}"
        headers = {"Authorization": f"Bearer {MOLT}", "Content-Type": "application/json"}

        if metodo == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        else:
            r = requests.post(url, json=datos, headers=headers, timeout=15)

        return r.json() if r.status_code in [200, 201] else None
    except:
        return None

# ------------------------------------------------------------
# 6. GENERAR TEMA
# ------------------------------------------------------------
def generar_tema():
    return ia("Genera un concepto breve, distinto y original para una columna reflexiva.")

# ------------------------------------------------------------
# 7. PUBLICAR COLUMNA
# ------------------------------------------------------------
def publicar(tema_manual=None):
    print("PUBLICANDO…")

    tema = tema_manual if tema_manual else generar_tema()
    if not tema:
        print("ERROR: tema vacío")
        return

    cuerpo = ia(f"Escribe una reflexión profunda sobre {tema} en tres párrafos.")
    if not cuerpo:
        print("ERROR: cuerpo vacío")
        return

    resp = api_molt("POST", "/posts", {"title": tema, "content": cuerpo})
    print("RESPUESTA MOLTBOOK:", resp)

# ------------------------------------------------------------
# 8. SOCIALIZAR EN EL FEED
# ------------------------------------------------------------
def socializar():
    data = api_molt("GET", "/posts?limit=15")
    if not data or "posts" not in data:
        return

    for p in data["posts"]:
        if p.get("author", {}).get("name") != AGENTE:
            comentario = ia(
                f"Comenta con estilo conciso e irónico: '{p.get('content','')[:200]}'"
            )
            if comentario:
                api_molt("POST", f"/posts/{p.get('id')}/comments", {"content": comentario})
            break

# ------------------------------------------------------------
# 9. REVISAR COMENTARIOS A TUS POSTS
# ------------------------------------------------------------
def revisar():
    data = api_molt("GET", "/posts?limit=50")
    if not data:
        return

    for p in data.get("posts", []):
        if p.get("author", {}).get("name") != AGENTE:
            continue

        coms = api_molt("GET", f"/posts/{p.get('id')}/comments")
        if not coms:
            continue

        for c in coms.get("comments", []):
            if c.get("author", {}).get("name") == AGENTE:
                continue

            respuesta = ia(f"Responde con estilo conciso e irónico: '{c.get('content')}'")
            if respuesta:
                api_molt("POST", f"/posts/{p.get('id')}/comments", {"content": respuesta})

# ------------------------------------------------------------
# 10. BUCLE AUTÓNOMO + NOTA DE PRUEBAS
# ------------------------------------------------------------
# Valores por defecto:
#   Publicar:    8 horas   = 28800 s
#   Socializar:  4 horas   = 14400 s
#   Revisar:     15 min    = 900 s
#
# PARA PRUEBAS:
#   Publicar cada 30 minutos:
#       30 min = 1800 s
#       if ahora - ultima_pub >= 1800:
#           publicar()
#
#   Socializar cada 10 minutos:
#       10 min = 600 s
#
#   Revisar cada 10 minutos:
#       10 min = 600 s
# ------------------------------------------------------------

ultima_pub = time.time()
ultima_soc = time.time()
ultima_rev = time.time()

def bucle():
    global ultima_pub, ultima_soc, ultima_rev
    while True:
        ahora = time.time()

        # Publicación automática (8h por defecto)
        if ahora - ultima_pub >= 28800:
            publicar()
            ultima_pub = ahora

        # Socialización automática (4h por defecto)
        if ahora - ultima_soc >= 14400:
            socializar()
            ultima_soc = ahora

        # Revisión automática (15 min por defecto)
        if ahora - ultima_rev >= 900:
            threading.Thread(target=revisar, daemon=True).start()
            ultima_rev = ahora

        time.sleep(60)

threading.Thread(target=bucle, daemon=True).start()

# ------------------------------------------------------------
# 11. WEBHOOK TELEGRAM
# ------------------------------------------------------------
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return '', 200

@app.route('/')
def index():
    return "OK", 200

# ------------------------------------------------------------
# 12. COMANDOS TELEGRAM
# ------------------------------------------------------------
@bot.message_handler(commands=['publicar', 'socializar', 'revisar', 'estado'])
def comandos(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return

    partes = message.text.split(maxsplit=1)
    cmd = partes[0][1:]

    if cmd == 'publicar':
        tema = partes[1] if len(partes) > 1 else None
        threading.Thread(target=publicar, args=(tema,), daemon=True).start()

    elif cmd == 'socializar':
        threading.Thread(target=socializar, daemon=True).start()

    elif cmd == 'revisar':
        threading.Thread(target=revisar, daemon=True).start()

    elif cmd == 'estado':
        bot.send_message(
            message.chat.id,
            f"Última publicación: {int((time.time()-ultima_pub)/60)} min\n"
            f"Última socialización: {int((time.time()-ultima_soc)/60)} min\n"
            f"Última revisión: {int((time.time()-ultima_rev)/60)} min"
        )

# ------------------------------------------------------------
# 13. INICIO DEL SERVICIO
# ------------------------------------------------------------
if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{URL}/{TOKEN}")
    print("WEBHOOK:", f"{URL}/{TOKEN}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))




