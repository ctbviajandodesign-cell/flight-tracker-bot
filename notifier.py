import os
import requests
import time
from dotenv import load_dotenv
import re

load_dotenv()

def enviar_notificacion_telegram(mensaje_texto):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Credenciales de Telegram faltantes.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    bloques = mensaje_texto.split("\n\n")
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
            texto = f"<b>[ Parte {i+1} de {len(mensajes_a_enviar)} ]</b>\n\n" + msg

        payload = {
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 400:
                # Fallback: limpiar HTML y reenviar
                texto_plano = re.sub(r'<[^>]+>', '', texto)
                texto_plano = texto_plano.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                payload_plano = {
                    "chat_id": chat_id,
                    "text": texto_plano,
                    "disable_web_page_preview": True
                }
                response = requests.post(url, json=payload_plano, timeout=30)
                print(f"⚠️ Parte {i+1} enviada sin formato (HTML falló)")
            else:
                response.raise_for_status()
                print(f"✅ Parte {i+1} enviada con formato.")
            time.sleep(1.5)
        except Exception as e:
            print(f"❌ Error en Telegram: {e}")
            if hasattr(response, 'text'):
                print(f"   Respuesta: {response.text[:300]}")
