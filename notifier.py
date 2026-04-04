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

def dividir_mensaje(texto, max_len=3800):
    """
    Divide el mensaje en partes respetando líneas completas.
    Calcula dinámicamente cuántas partes necesita según el contenido real.
    """
    if len(texto) <= max_len:
        return [texto]

    # Dividir por líneas para no cortar a mitad de una ruta
    lineas = texto.split('\n')
    partes = []
    actual = ''

    for linea in lineas:
        # Si agregar esta línea excede el límite, cerrar parte actual
        if len(actual) + len(linea) + 1 > max_len:
            if actual.strip():
                partes.append(actual.strip())
            actual = linea + '\n'
        else:
            actual += linea + '\n'

    if actual.strip():
        partes.append(actual.strip())

    total = len(partes)
    print(f"📨 Mensaje: {len(texto):,} chars → {total} parte(s) de ~{max_len:,} chars c/u")
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
                try:
                    error_detail = resp.json().get('description', resp.text[:200])
                except Exception:
                    error_detail = resp.text[:200]
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
