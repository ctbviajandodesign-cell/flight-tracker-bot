import os
import requests
import time
import re
from dotenv import load_dotenv

load_dotenv()

def limpiar_html(texto):
    """Limpia todos los tags HTML para fallback a texto plano"""
    texto = re.sub(r'<b>(.*?)</b>', r'\1', texto, flags=re.DOTALL)
    texto = re.sub(r'<i>(.*?)</i>', r'\1', texto, flags=re.DOTALL)
    texto = re.sub(r'<a href=["\'].*?["\']>(.*?)</a>', r'\1', texto, flags=re.DOTALL)
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = texto.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return texto

def dividir_mensaje(texto, max_len=3900):
    """Divide el mensaje en partes respetando bloques de rutas"""
    bloques = texto.split('\n\n')
    partes = []
    actual = ''
    for bloque in bloques:
        if not bloque.strip():
            continue
        if len(actual) + len(bloque) + 5 > max_len:
            if actual:
                partes.append(actual)
            actual = bloque + '\n\n'
        else:
            actual += bloque + '\n\n'
    if actual.strip():
        partes.append(actual)
    # Eliminar partes vacías
    return [p for p in partes if p.strip()]

def enviar_notificacion_telegram(mensaje_texto):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print('⚠️ Credenciales de Telegram faltantes.')
        return

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    partes = dividir_mensaje(mensaje_texto)

    for i, msg in enumerate(partes):
        if not msg.strip():
            continue
        texto = msg
        if len(partes) > 1:
            texto = f'<b>[ Parte {i+1} de {len(partes)} ]</b>\n\n' + msg

        # Intento 1: HTML completo
        payload = {
            'chat_id': chat_id,
            'text': texto,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                print(f'✅ Parte {i+1} enviada con formato HTML.')
                time.sleep(1.5)
                continue
            else:
                error_detail = resp.json().get('description', resp.text[:200])
                print(f'⚠️ HTML falló ({resp.status_code}): {error_detail}')
        except Exception as e:
            print(f'⚠️ Excepción en intento HTML: {e}')

        # Intento 2: Texto plano sin formato
        texto_plano = limpiar_html(texto)
        if len(partes) > 1:
            texto_plano = f'[ Parte {i+1} de {len(partes)} ]\n\n' + limpiar_html(msg)

        payload_plano = {
            'chat_id': chat_id,
            'text': texto_plano,
            'disable_web_page_preview': True
        }
        try:
            resp2 = requests.post(url, json=payload_plano, timeout=30)
            if resp2.status_code == 200:
                print(f'⚠️ Parte {i+1} enviada sin formato (fallback texto plano).')
            else:
                print(f'❌ Ambos intentos fallaron: {resp2.json().get("description", resp2.text[:200])}')
        except Exception as e2:
            print(f'❌ Error definitivo en Telegram: {e2}')

        time.sleep(1.5)
