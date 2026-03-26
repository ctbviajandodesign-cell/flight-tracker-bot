import os
import requests
from dotenv import load_dotenv

load_dotenv()

def enviar_notificacion_telegram(mensaje_texto):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Credenciales de Telegram faltantes.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    MAX_LENGTH = 4000
    partes = [mensaje_texto[i:i + MAX_LENGTH] for i in range(0, len(mensaje_texto), MAX_LENGTH)]
    for i, parte in enumerate(partes):
        texto_final = parte
        if len(partes) > 1:
            texto_final = f"<b>[Parte {i+1}/{len(partes)}]</b>\n\n" + parte
        payload = {
            "chat_id": chat_id,
            "text": texto_final,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            response = requests.post(url, json=payload, timeout=20)
            response.raise_for_status()
            print(f"✅ Parte {i+1} enviada.")
        except Exception as e:
            print(f"❌ Error Telegram: {e}")
