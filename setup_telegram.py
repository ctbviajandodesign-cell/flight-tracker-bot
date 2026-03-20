import os
import requests
from dotenv import load_dotenv

def obtener_chat_id():
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")

    if not token or token.strip() == "tu_token_aqui":
        print("⚠️ Por favor configura tu TELEGRAM_TOKEN en el archivo .env primero.")
        return

    print("Buscando mensajes recientes enviados al bot...")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        response = requests.get(url).json()
        if response.get("ok") and len(response.get("result", [])) > 0:
            chat_id = response["result"][-1]["message"]["chat"]["id"]
            nombre = response["result"][-1]["message"]["chat"].get("first_name", "Usuario")
            print(f"\n✅ ¡Encontrado! Tu Chat ID es: {chat_id} (Usuario: {nombre})")
            print(f"👉 Abre tu archivo .env y agrega la siguiente línea al final:\n")
            print(f"TELEGRAM_CHAT_ID={chat_id}\n")
        else:
            print("❌ No se encontraron mensajes nuevos.")
            print("Asegúrate de ir a Telegram, buscar a tu bot y enviarle un mensaje cualquiera (ej. 'Hola') antes de correr este script de nuevo.")
    except Exception as e:
        print(f"❌ Error contactando a Telegram: {e}")

if __name__ == "__main__":
    obtener_chat_id()
