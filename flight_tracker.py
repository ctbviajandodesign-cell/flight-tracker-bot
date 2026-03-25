import asyncio
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv
from notifier import enviar_notificacion_telegram
from scraper_vuelos import procesar_rutas

load_dotenv()

async def guardar_en_supabase(resultados):
    """Guarda los resultados en la tabla vuelos_historial de Supabase."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("⚠️ Supabase no configurado (falta URL o KEY). Saltando guardado.")
        return

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    datos_a_guardar = []
    for r in resultados:
        # Preparamos la fila para la base de datos
        datos_a_guardar.append({
            "ruta": r['ruta'],
            "precio": r['precio'],
            "es_ganga": (r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']),
            "tipo_vuelo": r['mejores'][0]['tipo'] if r['mejores'] else "UNK"
        })

    if not datos_a_guardar:
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{url}/rest/v1/vuelos_historial", json=datos_a_guardar, headers=headers)
            if response.status_code in [200, 201]:
                print(f"✅ Historial guardado en Supabase ({len(datos_a_guardar)} filas).")
            else:
                print(f"❌ Error al guardar en Supabase: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Fallo crítico al conectar con Supabase: {e}")

async def main():
    print("🚀 Iniciando rastreo inteligente...")
    hora_utc = datetime.utcnow().hour

    # Reportes programados (Ecuador: 8am, 3pm, 9pm)
    es_reporte_diario = (hora_utc in [12, 19, 1])

    resultados = await procesar_rutas()
    if not resultados:
        print("No se obtuvieron resultados.")
        return

    # GUARDADO EN HISTORIAL: Intentamos guardar todo lo que encontramos
    await guardar_en_supabase(resultados)

    vuelos_ganga = [
        r for r in resultados
        if r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']
    ]

    if vuelos_ganga:
        titulo = "🚨 <b>PRECIOS MÁS BAJOS AHORA!</b> 🚨\n"
        frase_intro = "<i>Precios más bajos detectados en este momento:</i>\n\n"
        vuelos_a_mostrar = resultados if es_reporte_diario else vuelos_ganga
    elif es_reporte_diario:
        titulo = "🌅 <b>REPORTE DIARIO DE VUELOS</b>\n"
        frase_intro = "<i>Resumen general de todas tus rutas de hoy:</i>\n\n"
        vuelos_a_mostrar = resultados
    else:
        return

    mensaje_telegram = titulo + frase_intro

    for r in vuelos_a_mostrar:
        es_ganga = (r['precio'] <= r['alerta_manual'] or r['es_ganga_mat'])
        icono = "🚨" if es_ganga else "📍"
        mensaje_telegram += f"{icono} <b>{r['ruta']}</b>\n"

        for i, opc in enumerate(r['mejores']):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"

            # LÓGICA DE ICONOS: Solo se muestran si se detectan
            if opc['tipo'] == "DIR":
                info_vuelo = "(DIR: 🚀)"
            elif opc['tipo'] == "ESC":
                info_vuelo = "(ESC: 🛬)"
            else:
                info_vuelo = ""  # Quitamos el círculo amarillo

            mensaje_telegram += f"   {medal} <b>${opc['precio']} USD</b> - {opc['detalle']} {info_vuelo}\n"

        mensaje_telegram += f"   📊 Promedio Normal: ${r['mediana']} USD\n"
        mensaje_telegram += f"   🔗 <a href='{r['url']}'>Ver en Google Flights</a>\n\n"

    enviar_notificacion_telegram(mensaje_telegram)

if __name__ == "__main__":
    asyncio.run(main())
