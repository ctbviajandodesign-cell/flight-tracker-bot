import os
    2 import requests
    3 from dotenv import load_dotenv
    4
    5 load_dotenv()
    6
    7 def enviar_notificacion_telegram(mensaje_texto):
    8     token = os.getenv("TELEGRAM_TOKEN")
    9     chat_id = os.getenv("TELEGRAM_CHAT_ID")
   10     if not token or not chat_id:
   11         print("⚠️ Credenciales de Telegram faltantes.")
   12         return
   13     url = f"https://api.telegram.org/bot{token}/sendMessage"
   14     MAX_LENGTH = 4000
   15     partes = [mensaje_texto[i:i + MAX_LENGTH] for i in range(0,
      len(mensaje_texto), MAX_LENGTH)]
   16     for i, parte in enumerate(partes):
   17         texto_final = parte
   18         if len(partes) > 1:
   19             texto_final = f"<b>[Parte {i+1}/{len(partes)}]</b>\n\n" +
      parte
   20         payload = {
   21             "chat_id": chat_id,
   22             "text": texto_final,
   23             "parse_mode": "HTML",
   24             "disable_web_page_preview": True
   25         }
   26         try:
   27             response = requests.post(url, json=payload, timeout=20)
   28             response.raise_for_status()
   29             print(f"✅ Parte {i+1} enviada.")
   30         except Exception as e:
   31             print(f"❌ Error Telegram: {e}")
