import requests
import sett
import json
import time
from datetime import datetime, timedelta

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
        clave = canon_lower.split()[0]  # ej. "po", "virtus", "taigun", "taos", "tiguan", "teramont", "sport", "saveiro", "amarok", "caddy", "crafter", "transporte", "jetta", "gti"
        if clave in t or canon_lower in t:
            return canon
    return None


try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

DIAS_ES = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
MESES_ES = ["enero","febrero","marzo","abril","mayo","junio",
            "julio","agosto","septiembre","octubre","noviembre","diciembre"]

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
        if dt.weekday() != 6:
            fechas.append(dt)
        d += 1
    return fechas

def _formatear_fecha_es(d):
    return f"{d.day} de {MESES_ES[d.month-1]} ({DIAS_ES[d.weekday()]})"


def obtener_Mensaje_whatsapp(message):
    if 'type' not in message :
        text = 'mensaje no reconocido'
        return text

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
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + whatsapp_token}
        print("se envia ", data)
        response = requests.post(whatsapp_url, 
                                 headers=headers, 
                                 data=data)
        
        if response.status_code == 200:
            return 'mensaje enviado', 200
        else:
            return 'error al enviar mensaje', response.status_code
    except Exception as e:
        return e,403
    
def text_Message(number,text):
    data = json.dumps(
            {
                "messaging_product": "whatsapp",    
                "recipient_type": "individual",
                "to": number,
                "type": "text",
                "text": {
                    "body": text
                }
            }
    )
    return data

def buttonReply_Message(number, options, body, footer, sedd,messageId):
    buttons = []
    for i, option in enumerate(options):
        buttons.append(
            {
                "type": "reply",
                "reply": {
                    "id": sedd + "_btn_" + str(i+1),
                    "title": option
                }
            }
        )

    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body
                },
                "footer": {
                    "text": footer
                },
                "action": {
                    "buttons": buttons
                }
            }
        }
    )
    return data

def listReply_Message(number, options, body, footer, sedd,messageId):
    rows = []
    for i, option in enumerate(options):
        rows.append(
            {
                "id": sedd + "_row_" + str(i+1),
                "title": option,
                "description": ""
            }
        )

    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": body
                },
                "footer": {
                    "text": footer
                },
                "action": {
                    "button": "Ver Opciones",
                    "sections": [
                        {
                            "title": "Secciones",
                            "rows": rows
                        }
                    ]
                }
            }
        }
    )
    return data

def document_Message(number, url, caption, filename):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "document",
            "document": {
                "link": url,
                "caption": caption,
                "filename": filename
            }
        }
    )
    return data

def sticker_Message(number, sticker_id):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "sticker",
            "sticker": {
                "id": sticker_id
            }
        }
    )
    return data

def get_media_id(media_name , media_type):
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
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "reaction",
            "reaction": {
                "message_id": messageId,
                "emoji": emoji
            }
        }
    )
    return data

def replyText_Message(number, messageId, text):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "context": { "message_id": messageId },
            "type": "text",
            "text": {
                "body": text
            }
        }
    )
    return data

def markRead_Message(messageId):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id":  messageId
        }
    )
    return data

def administrar_chatbot(text, number, messageId, name):
    text = text.lower()
    list = []
    print("mensaje del usuario: ", text)

    markRead = markRead_Message(messageId)
    list.append(markRead)
    time.sleep(2)

    # Saludo inicial
    """
    if "hola" in text:
        body = f"¡Hola {name if name else ''}! 👋 Bienvenido a *R&R Cordoba Autos*. Soy Volky, seré tu asesor virtual y estoy aquí para ayudarte a encontrar tu próximo auto 🚗✨.\n\n¿Cuál es tu nombre completo para poder atenderte mejor?"
        footer = "Asistente Virtual Volky"
        options = ["Quiero ver autos disponibles", "Tengo un auto para tomar a cuenta", "Quiero cotizar un auto"]
        replyButtonData = buttonReply_Message(number, options, body, footer, "sed1",messageId)
        list.append(replyReaction_Message(number, messageId, "🚗"))
        list.append(replyButtonData)
        
    if "hola" in text or "buenas tardes" in text or "buenos dias" in text or "buenas noches" in text or "buen dia" in text or "buena tarde" in text or "buena noche" in text:
        body = "¡Hola! 👋 Bienvenido a R&R Cordoba. ¿Cómo podemos ayudarte hoy?"
        footer = "Asistente Virtual Volky"
        options = ["✅ Servicios", "📅 Agendar cita"]

        replyButtonData = buttonReply_Message(number, options, body, footer, "sed1",messageId)
        replyReaction = replyReaction_Message(number, messageId, "🫡")
        list.append(replyReaction)
        list.append(replyButtonData)
    """
    if "hola" in text or "buenas tardes" in text or "buenos dias" in text or "buenas noches" in text or "buen dia" in text or "buena tarde" in text or "buena noche" in text:
        body = f"¡Hola! 👋 Bienvenido a *R&R Cordoba Autos*. Soy Volky, seré tu asesor virtual y estoy aquí para ayudarte a encontrar tu próximo auto 🚗."
        footer = "Asistente Virtual Volky"
        options = ["Ver autos disponibles", "Auto a cuenta", "Cotizar un auto"]
        
        listReplyData =listReply_Message(number, options, body, footer, "sed2",messageId)
        replyReaction = replyReaction_Message(number, messageId, "🫡")
        list.append(replyReaction)
        list.append(listReplyData)

    # Mostrar autos disponibles (elige categoría)
    elif "autos disponibles" in text or "ver autos" in text:
        body = "Perfecto ✅ Tenemos varias opciones. ¿Qué categoría te interesa?\n\n🚙 SUV\n🚗 Compactos\n🚘 Camionetas"
        footer = "Ventas R&R Cordoba"
        options = ["SUV", "Compactos", "Camionetas"]
        listReplyData = listReply_Message(number, options, body, footer, "sed2", messageId)
        list.append(listReplyData)

    # Preguntar si tiene auto para tomar a cuenta
    elif "tengo un auto para tomar a cuenta" in text or "auto a cuenta" in text:
        body = ("¡Excelente! Podemos tomar tu auto como parte del pago.\n\n"
                "📍 ¿Qué *marca, modelo y año* es tu auto?\n"
                "📸 Si cuentas con *fotos*, compártelas y agilizamos la valuación.")
        textMessage = text_Message(number, body)
        list.append(textMessage)

    # Cotización de auto
    elif "cotizar un auto" in text or "cotizar" in text:
        body = ("Claro, dime por favor:\n"
                "1️⃣ *Modelo* que te interesa.\n"
                "2️⃣ ¿Compra de *contado* o a *crédito*?\n"
                "3️⃣ Si es a crédito, ¿cuánto consideras de *enganche*?")
        textMessage = text_Message(number, body)
        list.append(textMessage)
    
    elif _es_categoria(text):
        categoria = _es_categoria(text)
        modelos = MODELOS.get(categoria, [])
        footer = f"Ventas R&R Cordoba • {categoria}"
        if modelos:
            body = f"Estos son los *{categoria}* disponibles ahora mismo:\n\n" + "\n".join([f"• {m}" for m in modelos]) + \
                   "\n\n¿De cuál te gustaría más información?"
            # Como lista de selección rápida (hasta 10). Si hay más de 10, enviar en dos tandas.
            opciones = modelos[:10]
            listReplyData = listReply_Message(number, opciones, body, footer, "sed3", messageId)
            list.append(listReplyData)
        else:
            body = "Por ahora no tengo existencias en esa categoría. ¿Quieres revisar otra?"
            options = ["SUV", "Compactos", "Camionetas"]
            replyButtonData = buttonReply_Message(number, options, body, footer, "sed3b", messageId)
            list.append(replyButtonData)
    
    elif "modelos" in text or "modelo" in text:
        footer = f"Ventas R&R Cordoba"
        body = f"Estos son los modelos disponibles ahora mismo:\n"
        modelos = []
        for c in MODELOS.keys():
            body += f"\n - {c}:"
            for m in MODELOS[c]:
                body += f"\n    • {m}"
                modelos.append(m)       
            body += f"\n"

        body += "\n¿De cuál te gustaría más información?"
        # Como lista de selección rápida (hasta 10). Si hay más de 10, enviar en dos tandas.
        opciones = modelos[:10]
        listReplyData = listReply_Message(number, opciones, body, footer, "sed3", messageId)
        list.append(listReplyData)

    # --- El usuario menciona un modelo específico: ofrecer pasos siguientes ---
    elif _buscar_modelo_en_texto(text):
        modelo = _buscar_modelo_en_texto(text)
        body = (f"Excelente elección: *{modelo}* ✅\n\n"
                "¿Qué te gustaría hacer ahora?")
        footer = "Ventas R&R Cordoba"
        opciones = ["Ver lista de precios","Agendar prueba de manejo"]
        listReplyData = listReply_Message(number, opciones, body, footer, "sed4", messageId)
        list.append(listReplyData)

    # Lista de precios (genérica; aquí puedes inyectar tus precios reales)
    elif "lista de precios" in text or "ver lista de precios" in text:
        body = ("Claro, te comparto rangos estimados 💰 (pueden variar por versión y paquetes):\n"
                "• Compactos: desde $300,000\n"
                "• SUV: desde $400,000\n"
                "• Camionetas: desde $300,000 (comerciales) y $600,000 (pickups)\n\n"
                "¿Quieres que cotice un *modelo y versión* específicos?")
        footer = "Ventas R&R Cordoba"
        options = ["Sí, cotizar modelo", "No, ver promociones"]
        replyButtonData = buttonReply_Message(number, options, body, footer, "sed4a", messageId)
        list.append(replyButtonData)

    # Promociones
    elif "promociones" in text or "ver promociones" in text:
        body = ("Ahora mismo tenemos:\n"
                "🎯 0% comisión por apertura\n"
                "🎯 Enganches desde el 10%\n"
                "🎯 Seguro gratis el primer año\n\n"
                "¿Deseas *agendar una cita* para ver el auto en persona o prefieres una *cotización por WhatsApp*?")
        footer = "Ventas R&R Cordoba"
        options = ["Sí, agendar cita", "Cotización por WhatsApp"]
        replyButtonData = buttonReply_Message(number, options, body, footer, "sed4b", messageId)
        list.append(replyButtonData)

    # Financiamiento
    elif "financiamiento" in text or "opciones de financiamiento" in text:
        body = ("Podemos financiar tu auto con mensualidades accesibles.\n\n"
                "💵 ¿Cuánto podrías dar de *enganche*?\n"
                "📅 ¿A cuántos *meses* te gustaría financiarlo? (12, 24, 36, 48, 60)")
        textMessage = text_Message(number, body)
        list.append(textMessage)

    # Agendar prueba de manejo (deriva a la agenda)
    elif "prueba de manejo" in text or "agendar prueba de manejo" in text:
        body = "¡Perfecto! Agendemos tu *prueba de manejo*. ¿Te parece si vemos disponibilidad?"
        footer = "Ventas R&R Cordoba"
        options = ["Sí, agendar cita", "Luego"]
        replyButtonData = buttonReply_Message(number, options, body, footer, "sed4c", messageId)
        list.append(replyButtonData)

    # Agendar cita (mostrar próximas 5 fechas sin domingo)
    elif "sí, agendar cita" in text:
        body = "Perfecto 😎. Elige el día que mejor te acomode para visitarnos:"
        footer = "Ventas R&R Cordoba"

        fechas = _proximos_5_sin_domingo()
        options = [f"📅 { _formatear_fecha_es(f) }" for f in fechas]

        listReplyData = listReply_Message(number, options, body, footer, "sed5", messageId)
        list.append(listReplyData)

    elif any(mes in text for mes in MESES_ES) and "📅" in text:
        fecha_elegida = text.replace("📅", "").strip()

        body = (f"Anotado: *{fecha_elegida}* ✅\n\n"
                "¿Qué horario prefieres?")
        footer = "Ventas R&R Cordoba"
        options = ["09:30 AM", "12:00 PM", "2:00 PM", "4:00 PM"]

        replyButtonData = buttonReply_Message(number, options, body, footer, "sed6", messageId)
        list.append(replyButtonData)

    # Cuando el usuario elige la hora, confirmamos y pedimos datos básicos
    elif any(h in text for h in ["09:30 am","12:00 pm","2:00 pm","4:00 pm"]):
        hora_elegida = text.upper()
        body = (f"¡Listo! 📌 Cita *{hora_elegida}* confirmada.\n\n"
                "Para dejarla agendada, por favor compárteme:\n"
                "• Tu *nombre completo*\n"
                "• *Modelo* del auto que te interesa\n"
                "• ¿Vienes *de contado* o *a crédito*? (Si es a crédito, ¿cuánto consideras de *enganche*?)\n"
                "• ¿Tienes *auto a cuenta*? (marca, modelo, año)")
        textMessage = text_Message(number, body)
        list.append(textMessage)

    elif text.strip() == "sí":
        # Llevar al flujo de autos disponibles
        body = "Perfecto ✅ ¿Qué categoría te interesa?\n\n🚙 SUV\n🚗 Compactos (sedanes/hatchback)\n🚘 Camionetas (pickups y comerciales)"
        footer = "Ventas R&R Cordoba"
        options = ["SUV", "Compactos", "Camionetas"]
        listReplyData = listReply_Message(number, options, body, footer, "sed2", messageId)
        list.append(listReplyData)

    elif text.strip() == "no":
        body = "¡Entendido! Si más adelante necesitas información o una cotización, aquí estaré para ayudarte. 🙌"
        textMessage = text_Message(number, body)
        list.append(textMessage)
    else:
        body = ("No cuento con esa información exacta, pero puedo ayudarte a *agendar una cita* "
                "o brindarte *detalles de los modelos disponibles* en la agencia. "
                "¿Quieres que te ayude a encontrar tu próximo auto?")
        footer = "Asistente Virtual *Volky*"
        options = ["Sí", "No"]
        replyButtonData = buttonReply_Message(number, options, body, footer, "sedX", messageId)
        list.append(replyButtonData)


    for item in list:
        enviar_Mensaje_whatsapp(item)


#al parecer para mexico, whatsapp agrega 521 como prefijo en lugar de 52,
# este codigo soluciona ese inconveniente.
def replace_start(s):
    number = s[3:]
    if s.startswith("521"):
        return "52" + number
    elif s.startswith("549"):
        return "54" + number
    else:
        return s
        

