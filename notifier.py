import os
import requests
import time
from dotenv import load_dotenv
import re

load_dotenv()

def limpiar_html(texto):
    texto = re.sub(r'<b>(.*?)</b>', r'\1', texto)
    texto = re.sub(r"<a href='.*?'>(.*?)</a>", r'\1', texto)
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = texto.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return texto

def enviar_notificacion_telegram(mensaje_texto):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Credenciales de Telegram faltantes.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    mensaje_limpio = limpiar_html(mensaje_texto)

    bloques = mensaje_limpio.split("\n\n")
    mensajes_a_enviar = []
    mensaje_actual = ""

    for bloque in bloques:
        if not bloque.strip():
            continue
        if len(mensaje_actual) + len(bloque) + 5 > 3900:
            mensajes_a_enviar.append(mensaje_actual)
            mensaje_actual = bloque + "\n\n"
        else:
            mensaje_actual += bloque + "\n\n"

    if mensaje_actual:
        mensajes_a_enviar.append(mensaje_actual)

    for i, msg in enumerate(mensajes_a_enviar):
        texto = msg
        if len(mensajes_a_enviar) > 1:
            texto = f"[Parte {i+1}/{len(mensajes_a_enviar)}]\n\n" + msg

        payload = {
            "chat_id": chat_id,
            "text": texto,
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            print(f"✅ Parte {i+1} enviada.")
            time.sleep(1.5)
        except Exception as e:
            print(f"❌ Error en Telegram: {e}")
            print(f"   Respuesta: {response.text[:300]}")
