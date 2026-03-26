import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

def enviar_notificacion_telegram(mensaje_texto):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Credenciales de Telegram faltantes.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Dividimos por bloques de vuelos (separados por \n\n)
    bloques = mensaje_texto.split("\n\n")
    mensajes_a_enviar = []
    mensaje_actual = ""

    for bloque in bloques:
        if not bloque.strip():
            continue
        # Si añadir este bloque supera el límite de Telegram (4096), guardamos el actual y empezamos uno nuevo
        if len(mensaje_actual) + len(bloque) + 2 > 3800:
            mensajes_a_enviar.append(mensaje_actual)
            mensaje_actual = bloque + "\n\n"
        else:
            mensaje_actual += bloque + "\n\n"
    
    if mensaje_actual:
        mensajes_a_enviar.append(mensaje_actual)

    for i, msg in enumerate(mensajes_a_enviar):
        texto = msg
        if len(mensajes_a_enviar) > 1:
            texto = f"<b>[Parte {i+1}/{len(mensajes_a_enviar)}]</b>\n\n" + msg
        
        payload = {
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 400:
                print(f"❌ Error 400 en Parte {i+1}. Intentando enviar sin HTML...")
                payload["parse_mode"] = ""
                response = requests.post(url, json=payload, timeout=30)
            
            response.raise_for_status()
            print(f"✅ Parte {i+1}/{len(mensajes_a_enviar)} enviada.")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error crítico Telegram: {e}")
