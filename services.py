import os
import re
import json
import time
import requests
import sett
from datetime import datetime, timedelta

# =========================
# Zona horaria
# =========================
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# =========================
# PERSISTENCIA & PERFIL DEL LEAD
# =========================
LEADS = {}  # { number: {nombre, enganche, auto_a_cuenta, auto_objetivo, fecha_cita, prueba_manejo, fecha_prueba, pago, created_at, updated_at} }
LEADS_PATH = "leads.json"  # persistencia local opcional

def _now_tz():
    return datetime.now(ZoneInfo("America/Mexico_City")) if ZoneInfo else datetime.now()

def _iso(dt):
    if not dt: return None
    if isinstance(dt, str): return dt
    return dt.isoformat()

def load_leads():
    """Cárgalo al iniciar la app (en app.py)."""
    global LEADS
    if os.path.exists(LEADS_PATH):
        try:
            with open(LEADS_PATH, "r", encoding="utf-8") as f:
                LEADS = json.load(f)
        except Exception:
            LEADS = {}

def save_leads():
    try:
        with open(LEADS_PATH, "w", encoding="utf-8") as f:
            json.dump(LEADS, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_or_create_lead(number):
    lead = LEADS.get(number)
    if not lead:
        lead = {
            "nombre": None,
            "enganche": None,
            "auto_a_cuenta": None,
            "auto_objetivo": None,
            "fecha_cita": None,
            "prueba_manejo": False,
            "fecha_prueba": None,
            "pago": None,
            "created_at": _iso(_now_tz()),
            "updated_at": _iso(_now_tz()),
        }
        LEADS[number] = lead
        save_leads()
    return lead

def update_lead(number, **fields):
    lead = get_or_create_lead(number)
    for k, v in fields.items():
        if k in lead:
            if k in ("fecha_cita", "fecha_prueba"):
                lead[k] = _iso(v) if v else None
            else:
                lead[k] = v
    lead["updated_at"] = _iso(_now_tz())
    save_leads()
    return lead

def human_datetime(iso_str):
    if not iso_str: return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z",""))
        meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
        return f"{dt.day} de {meses[dt.month-1]} {dt.year} • {dt.strftime('%I:%M %p')}"
    except Exception:
        return iso_str

# =========================
# FICHA TÉCNICA GENÉRICA
# =========================
FICHA_TECNICA = {
    "motor": "4 cilindros 1.6–2.0L, inyección multipunto",
    "potencia": "115–180 hp (según versión)",
    "torque": "150–320 Nm (según versión)",
    "transmisión": "Manual 5/6 vel o Automática Tiptronic/DSG",
    "tracción": "Delantera (algunas versiones AWD en SUV)",
    "seguridad": "6 bolsas de aire, ABS, ESC, ISOFIX",
    "infotenimiento": "Pantalla 8–10\", App-Connect (CarPlay/Android Auto)",
    "consumo_promedio": "12–18 km/L (mixto, depende versión)",
    "garantía": "3 años o 60,000 km",
}

def ficha_str():
    lineas = [f"• {k.capitalize()}: {v}" for k, v in FICHA_TECNICA.items()]
    return "*Ficha técnica genérica*\n" + "\n".join(lineas)

# =========================
# MODELOS / CATÁLOGO
# =========================
MODELOS = {
    "SUV": [
        "TAIGUN 2025", "TAOS 2025", "TIGUAN 2025",
        "TERAMONT 2025", "CROSS SPORT 2025"
    ],
    "Compactos": [
        "POLO TRACK", "VIRTUS 2025", "JETTA 2025", "NUEVO GTI"
    ],
    "Camionetas": [
        "SAVEIRO 2025", "AMAROK 2024", "AMAROK 2025",
        "CADDY CARGO 2024", "CRAFTER PASAJEROS 2025", "CRAFTER CARGO 2025",
        "TRANSPORTE CHASIS", "TRANSPORTE CARGO"
    ]
}
MODELOS_FLAT = {m.lower(): m for cat in MODELOS.values() for m in cat}

def _es_categoria(msg):
    msg = msg.lower()
    if "suv" in msg: return "SUV"
    if "compacto" in msg or "compactos" in msg: return "Compactos"
    if "camioneta" in msg or "camionetas" in msg: return "Camionetas"
    return None

def _buscar_modelo_en_texto(msg):
    t = msg.lower()
    for canon_lower, canon in MODELOS_FLAT.items():
        clave = canon_lower.split()[0]
        if clave in t or canon_lower in t:
            return canon
    return None

# =========================
# FECHAS / CALENDARIO
# =========================
DIAS_ES = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
MESES_ES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]

def _now_mex():
    if ZoneInfo is not None:
        return datetime.now(ZoneInfo("America/Mexico_City"))
    return datetime.now()

def _proximos_5_sin_domingo():
    hoy = _now_mex().date()
    fechas = []
    d = 1
    while len(fechas) < 5:
        dt = hoy + timedelta(days=d)
        if dt.weekday() != 6:  # 6 = domingo
            fechas.append(dt)
        d += 1
    return fechas

def _formatear_fecha_es(d):
    return f"{d.day} de {MESES_ES[d.month-1]} ({DIAS_ES[d.weekday()]})"

# =========================
# HELPERS DE PARSEO
# =========================
NUM_RE = re.compile(r"(\d{1,3}(?:[.,]\d{3})*|\d+)(?:\s*(?:mxn|pesos|\$))?", re.IGNORECASE)

def parse_enganche(text):
    """Busca un monto en el mensaje. Convierte a entero MXN."""
    t = text.lower().replace(" mil", "000")
    m = NUM_RE.search(t)
    if not m:
        return None
    n = m.group(1).replace(".", "").replace(",", "")
    try:
        return int(n)
    except:
        return None

def parse_pago(text):
    t = text.lower()
    if "crédito" in t or "credito" in t or "financiamiento" in t:
        return "crédito"
    if "contado" in t or "cash" in t:
        return "contado"
    return None

def parse_nombre(text):
    t = text.strip()
    m = re.search(r"(me llamo|mi nombre es|soy)\s+(.+)", t, re.IGNORECASE)
    if m:
        name = m.group(2).strip()
        name = re.split(r"[.,;:!?]", name)[0].strip()
        if 3 <= len(name) <= 60 and not any(ch.isdigit() for ch in name):
            return name
    if 3 <= len(t) <= 60 and not any(ch.isdigit() for ch in t) and len(t.split()) >= 2:
        return t
    return None

def parse_nombre(text):
    t = text.strip()
    t = t.lower()
    if "me llamo" in t:
        arreglo = t.split()
        name = arreglo[2] + " " + arreglo[3]
        return name
    elif "soy" in t:
        arreglo = t.split()
        name = arreglo[1] + " " + arreglo[1]
        return name
    elif "mi nombre es" in t:
        arreglo = t.split()
        name = arreglo[3] + " " + arreglo[4]
        return name
    if 3 <= len(t) <= 60 and not any(ch.isdigit() for ch in t) and len(t.split()) >= 2:
        return t
    return None

def parse_auto_a_cuenta(text):
    t = text.lower()
    if any(x in t for x in ["auto a cuenta","tengo un auto","tomar a cuenta","a cuenta"]):
        return text.strip()
    if re.search(r"(?:\b[a-zA-Z]{3,}\b)\s+(?:19|20)\d{2}", t):
        return text.strip()
    return None

def parse_modelo(text):
    return _buscar_modelo_en_texto(text)

# =========================
# WHATSAPP HELPERS
# =========================
def obtener_Mensaje_whatsapp(message):
    if 'type' not in message:
        return 'mensaje no reconocido'

    typeMessage = message['type']
    if typeMessage == 'text':
        text = message['text']['body']
    elif typeMessage == 'button':
        text = message['button']['text']
    elif typeMessage == 'interactive' and message['interactive']['type'] == 'list_reply':
        text = message['interactive']['list_reply']['title']
    elif typeMessage == 'interactive' and message['interactive']['type'] == 'button_reply':
        text = message['interactive']['button_reply']['title']
    else:
        text = 'mensaje no procesado'
    return text

def enviar_Mensaje_whatsapp(data):
    try:
        whatsapp_token = sett.whatsapp_token
        whatsapp_url = sett.whatsapp_url
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + whatsapp_token
        }
        print("se envia ", data)
        response = requests.post(whatsapp_url, headers=headers, data=data)
        if response.status_code == 200:
            return 'mensaje enviado', 200
        else:
            return 'error al enviar mensaje', response.status_code
    except Exception as e:
        return e, 403

def text_Message(number, text):
    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "text",
        "text": {"body": text}
    })
    return data

def buttonReply_Message(number, options, body, footer, sedd, messageId):
    buttons = []
    for i, option in enumerate(options):
        buttons.append({
            "type": "reply",
            "reply": {"id": sedd + "_btn_" + str(i+1), "title": option}
        })

    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "footer": {"text": footer},
            "action": {"buttons": buttons}
        }
    })
    return data

def listReply_Message(number, options, body, footer, sedd, messageId):
    rows = []
    for i, option in enumerate(options):
        rows.append({"id": sedd + "_row_" + str(i+1), "title": option, "description": ""})

    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "footer": {"text": footer},
            "action": {
                "button": "Ver Opciones",
                "sections": [{"title": "Secciones", "rows": rows}]
            }
        }
    })
    return data

def document_Message(number, url, caption, filename):
    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "document",
        "document": {"link": url, "caption": caption, "filename": filename}
    })
    return data

def sticker_Message(number, sticker_id):
    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "sticker",
        "sticker": {"id": sticker_id}
    })
    return data

def get_media_id(media_name, media_type):
    media_id = ""
    if media_type == "sticker":
        media_id = sett.stickers.get(media_name, None)
    elif media_type == "image":
        media_id = sett.images.get(media_name, None)
    elif media_type == "video":
        media_id = sett.videos.get(media_name, None)
    elif media_type == "audio":
        media_id = sett.audio.get(media_name, None)
    return media_id

def replyReaction_Message(number, messageId, emoji):
    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "reaction",
        "reaction": {"message_id": messageId, "emoji": emoji}
    })
    return data

def replyText_Message(number, messageId, text):
    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "context": {"message_id": messageId},
        "type": "text",
        "text": {"body": text}
    })
    return data

def markRead_Message(messageId):
    data = json.dumps({
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": messageId
    })
    return data

# =========================
# NÚCLEO DEL CHATBOT
# =========================
def administrar_chatbot(text, number, messageId, name):
    text_orig = text.lower()
    out = []
    print("mensaje del usuario:", text_orig)

    # Marcar leído
    out.append(markRead_Message(messageId))
    time.sleep(1)

    # Obtener/crear ficha del lead
    lead = get_or_create_lead(number)

    # ---- CAPTURA PASIVA
    nombre = parse_nombre(text_orig)
    if nombre and not lead["nombre"]:
        update_lead(number, nombre=nombre)
        out.append(replyText_Message(number, messageId, f"¡Gracias, *{nombre}*! 😊"))

    eng = parse_enganche(text_orig)
    if eng and (not lead["enganche"] or eng != lead["enganche"]):
        update_lead(number, enganche=eng)
        out.append(replyText_Message(number, messageId, f"Perfecto, anoto tu *enganche* por ${eng:,.0f} MXN."))

    pago = parse_pago(text_orig)
    if pago and pago != lead["pago"]:
        update_lead(number, pago=pago)
        out.append(replyText_Message(number, messageId, f"Entendido, sería *{pago}*."))

    trade = parse_auto_a_cuenta(text_orig)
    if trade and not lead["auto_a_cuenta"]:
        update_lead(number, auto_a_cuenta=trade)
        out.append(replyText_Message(number, messageId, "¡Excelente! Anoto tu *auto a cuenta* para la valuación."))

    modelo_detect = parse_modelo(text_orig)
    if modelo_detect and modelo_detect != lead["auto_objetivo"]:
        update_lead(number, auto_objetivo=modelo_detect)
        out.append(replyText_Message(number, messageId, f"Excelente elección: *{modelo_detect}*."))

    # ---- INTENCIONES PRINCIPALES

    # Saludo / inicio
    if any(g in text for g in ["hola","buenas tardes","buenos dias","buenos días","buenas noches","buen dia","buen día","buena tarde","buena noche","menu","inicio","empezar"]):
        body = (f"¡Hola {lead['nombre']+' ' if lead['nombre'] else ''}👋! Soy *Volky* de *R&R Córdoba Autos*.\n"
                "¿Qué te gustaría hacer?")
        footer = "Asistente Virtual Volky"
        options = ["Ver autos disponibles","Cotizar un auto","Auto a cuenta","Ver ficha técnica","Agendar cita","Promociones"]
        out.append(replyReaction_Message(number, messageId, "🫡"))
        out.append(listReply_Message(number, options, body, footer, "sed_menu", messageId))

    # Mostrar autos disponibles (elige categoría)
    elif "autos disponibles" in text or "ver autos" in text:
        body = "Perfecto ✅ ¿Qué categoría te interesa?\n\n🚙 SUV\n🚗 Compactos\n🚘 Camionetas"
        footer = "Ventas R&R Córdoba"
        options = ["SUV","Compactos","Camionetas","Modelos"]
        out.append(listReply_Message(number, options, body, footer, "sed_cat", messageId))

    elif "modelo" in text or "modelos" in text:
        body = "Estos son los modelos disponibles ahora mismo:\n"
        for c in MODELOS.keys():
            body += f"\n - {c}:\n"
            for m in MODELOS[c]:
                body += f"    • {m}\n"
        body += "\nEscribe el *modelo* que te interesa"
        out.append(text_Message(number, body))

    elif _es_categoria(text):
        categoria = _es_categoria(text)
        modelos = MODELOS.get(categoria, [])
        footer = f"Ventas R&R Córdoba • {categoria}"
        if modelos:
            body = f"Estos son los *{categoria}* disponibles:\n\n" + "\n".join([f"• {m}" for m in modelos]) + "\n\n¿De cuál te gustaría más información?"
            out.append(listReply_Message(number, modelos[:10], body, footer, "sed_modelos", messageId))
        else:
            body = "Por ahora no tengo existencias en esa categoría. ¿Quieres revisar otra?"
            options = ["SUV","Compactos","Camionetas"]
            out.append(buttonReply_Message(number, options, body, footer, "sed_cat_retry", messageId))

    # El usuario menciona un modelo: ofrecer pasos
    elif modelo_detect:
        body = (f"¿Qué te gustaría hacer con *{modelo_detect}*?")
        footer = "Ventas R&R Córdoba"
        opciones = ["Ver ficha técnica","Lista de precios","Agendar prueba de manejo","Agendar cita"]
        out.append(listReply_Message(number, opciones, body, footer, "sed_modelo_accion", messageId))

    # FICHA TÉCNICA
    elif "ficha técnica" in text or "ver ficha técnica" in text or "ficha" in text:
        body = ficha_str()
        if lead["auto_objetivo"]:
            body = f"*Modelo:* {lead['auto_objetivo']}\n\n" + body
        out.append(text_Message(number, body))

    # Lista de precios (genérica)
    elif "lista de precios" in text or "ver lista de precios" in text or "precios" in text:
        body = ("Te comparto rangos estimados 💰:\n"
                "• Compactos: desde $300,000\n"
                "• SUV: desde $400,000\n"
                "• Camionetas: desde $900,000 (comerciales) y $600,000 (pickups)\n\n"
                "¿Quieres que cotice un *modelo y versión* específicos?")
        footer = "Ventas R&R Córdoba"
        options = ["Sí, cotizar modelo","Ver promociones","Agendar cita"]
        out.append(buttonReply_Message(number, options, body, footer, "sed_precios", messageId))

    # Promociones
    elif "promociones" in text or "ver promociones" in text:
        body = ("Ahora mismo tenemos:\n"
                "🎯 0% comisión por apertura\n"
                "🎯 Enganches desde el 10%\n"
                "🎯 Seguro gratis el primer año\n\n"
                "¿Prefieres *agendar una cita* o una *cotización por WhatsApp*?")
        footer = "Ventas R&R Córdoba"
        options = ["Agendar cita","Cotización por WhatsApp"]
        out.append(buttonReply_Message(number, options, body, footer, "sed_promo", messageId))

    # Cotización
    elif "cotizar un auto" in text or "cotizar" in text:
        body = ("Perfecto, para cotizar necesito:\n"
                "1️⃣ *Modelo* de interés\n"
                "2️⃣ ¿*Contado* o a *crédito*?\n"
                "3️⃣ Si es crédito, ¿cuánto darías de *enganche*?\n"
                "4️⃣ ¿Tienes *auto a cuenta*? (marca, modelo, año)")
        out.append(text_Message(number, body))

    # Prueba de manejo
    elif "prueba de manejo" in text or "agendar prueba de manejo" in text:
        update_lead(number, prueba_manejo=True)
        body = "¡Perfecto! Veamos disponibilidad para tu *prueba de manejo*."
        footer = "Ventas R&R Córdoba"
        options = ["Sí, agendar cita","Luego"]
        out.append(buttonReply_Message(number, options, body, footer, "sed_prueba", messageId))

    # Agendar cita (día)
    elif "sí, agendar cita" in text or "si, agendar cita" in text or "agendar cita" in text or "agenda" in text or "agendar" in text:
        body = "Elige el día que mejor te acomode:"
        footer = "Ventas R&R Córdoba"
        fechas = _proximos_5_sin_domingo()
        options = [f"📅 { _formatear_fecha_es(f) }" for f in fechas]
        out.append(listReply_Message(number, options, body, footer, "sed_cita_dia", messageId))

    # Usuario elige fecha (de la lista con 📅)
    elif any(mes in text for mes in MESES_ES) and "📅" in text_orig:
        fecha_elegida = text_orig.replace("📅", "").strip()
        out.append(replyText_Message(number, messageId, f"Anotado: *{fecha_elegida}* ✅"))
        body = "¿Qué horario prefieres?"
        footer = "Ventas R&R Córdoba"
        options = ["10:00 AM - 12:00 PM","12:30 PM - 3:00 PM","3:30 PM - 5:30 PM"]
        out.append(buttonReply_Message(number, options, body, footer, "sed_cita_hora", messageId))

    # Usuario elige hora
    elif any(h in text for h in ["10:00 am - 12:00 pm","12:30 pm - 3:00 pm","3:30 pm - 5:30 pm"]):
        hora_elegida = text_orig.upper()
        if lead.get("prueba_manejo"):
            update_lead(number, fecha_prueba=hora_elegida)
        else:
            update_lead(number, fecha_cita=hora_elegida)

        body = (f"¡Listo! 📌 Cita *{hora_elegida}* confirmada.\n\n"
                "Para dejarla agendada, por favor compárteme:\n"
                "• Tu *nombre completo*\n"
                "• *Modelo* de interés\n"
                "• ¿*Contado* o *crédito*? (si es crédito, ¿*enganche*?)\n"
                "• ¿Tienes *auto a cuenta*? (marca, modelo, año)")
        out.append(text_Message(number, body))

    # Confirmación y estado del lead
    elif any(k in text for k in ["estado","resumen","mi info","mis datos","status"]):
        lead = get_or_create_lead(number)
        eng_str = f"${lead['enganche']:,.0f} MXN" if lead['enganche'] else "—"  # <- evita anidar f-strings
        body = ("*Tu información hasta ahora:*\n"
                f"• Nombre: {lead['nombre'] or '—'}\n"
                f"• Pago: {lead['pago'] or '—'}\n"
                f"• Enganche: {eng_str}\n"
                f"• Auto a cuenta: {lead['auto_a_cuenta'] or '—'}\n"
                f"• Modelo objetivo: {lead['auto_objetivo'] or '—'}\n"
                f"• Cita: {lead['fecha_cita'] or '—'}\n"
                f"• Prueba de manejo: {'Sí' if lead['prueba_manejo'] else 'No'}\n"
                f"• Fecha de prueba: {lead['fecha_prueba'] or '—'}\n\n"
                "¿Deseas *agendar/ajustar cita*, *ver ficha técnica* o *finalizar cotización*?")
        footer = "R&R Córdoba"
        options = ["Agendar/ajustar cita","Ver ficha técnica","Finalizar cotización"]
        out.append(buttonReply_Message(number, options, body, footer, "sed_status", messageId))

    # Reiniciar conversación / limpiar lead
    elif any(k in text for k in ["reiniciar","empezar de nuevo","borrar datos","reset"]):
        LEADS.pop(number, None)
        save_leads()
        body = "He borrado tu información de este chat. Empezamos desde cero. ¿Qué te gustaría hacer?"
        footer = "R&R Córdoba"
        options = ["Ver autos disponibles","Cotizar un auto","Agendar cita"]
        out.append(buttonReply_Message(number, options, body, footer, "sed_reset", messageId))

    # Sí / No genéricos
    elif text.strip() in ("sí", "si"):
        body = "Perfecto ✅ ¿Qué categoría te interesa?\n\n🚙 SUV\n🚗 Compactos\n🚘 Camionetas"
        footer = "R&R Córdoba"
        options = ["SUV","Compactos","Camionetas"]
        out.append(listReply_Message(number, options, body, footer, "sed_cat", messageId))

    elif text.strip() == "no":
        body = "¡Entendido! Si más adelante necesitas información o una cotización, aquí estaré para ayudarte. 🙌"
        out.append(text_Message(number, body))

    # Fallback
    else:
        body = ("Puedo ayudarte a *ver modelos*, *cotizar*, *agendar cita* o mostrarte la *ficha técnica*.\n"
                "¿Qué deseas hacer?")
        footer = "Asistente Virtual Volky"
        options = ["Ver autos disponibles","Cotizar un auto","Agendar cita","Ver ficha técnica","Promociones","Estado"]
        out.append(buttonReply_Message(number, options, body, footer, "sed_fallback", messageId))

    # Enviar todos los mensajes encolados
    for item in out:
        enviar_Mensaje_whatsapp(item)

# =========================
# Utilidad prefijo México
# =========================
def replace_start(s):
    number = s[3:]
    if s.startswith("521"):
        return "52" + number
    else:
        return s
