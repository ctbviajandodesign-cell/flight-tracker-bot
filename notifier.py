import os
import requests

def enviar_notificacion_telegram(mensaje_texto):
    """Envía un mensaje usando el bot de Telegram especificado en el .env"""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("⚠️ Advertencia: No se pueden enviar mensajes porque falta TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en .env")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje_texto,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Notificación de Telegram enviada exitosamente.")
        return True
    except Exception as e:
        print(f"❌ Error enviando mensaje por Telegram: {e}")
        return False
