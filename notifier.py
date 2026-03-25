import os
import requests
from dotenv import load_dotenv

load_dotenv()

def enviar_notificacion_telegram(mensaje_texto):
    """Envía un mensaje usando el bot de Telegram. Si es muy largo, lo divide."""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("⚠️ Advertencia: No se pueden enviar mensajes porque falta TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en .env")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Límite de Telegram es 4096. Usamos 4000 para margen de seguridad.
    MAX_LENGTH = 4000

    # Dividir el mensaje en partes si supera el límite
    partes = [
        mensaje_texto[i:i + MAX_LENGTH]
        for i in range(0, len(mensaje_texto), MAX_LENGTH)
    ]

    for i, parte in enumerate(partes):
        texto_final = parte

        # Si hay más de una parte, añadimos indicador
        if len(partes) > 1:
            texto_final = f"<b>[Parte {i+1}/{len(partes)}]</b>\n\n{parte}"

        payload = {
            "chat_id": chat_id,
            "text": texto_final,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            print(f"✅ Parte {i+1}/{len(partes)} enviada exitosamente a Telegram.")
        except Exception as e:
            print(f"❌ Error enviando parte {i+1} de Telegram: {e}")
