import asyncio
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv
from notifier import enviar_notificacion_telegram
from scraper_vuelos import procesar_rutas

load_dotenv()

async def guardar_en_supabase(resultados):
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    datos = []
    for r in resultados:
        datos.append({
            "ruta": r['ruta'],
            "precio": r['precio'],
            "es_ganga": (r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']),
            "tipo_vuelo": r['mejores'][0]['tipo'] if r['mejores'] else "UNK"
        })
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(f"{url}/rest/v1/vuelos_historial", json=datos, headers=headers)
            print("✅ Supabase actualizado.")
    except:
        print("⚠️ Error base de datos.")

async def main():
    print("🚀 Iniciando rastreo...")
    hora_utc = datetime.utcnow().hour
    es_reporte_diario = (hora_utc in [12, 19, 1])

    try:
        resultados = await asyncio.wait_for(procesar_rutas(), timeout=1200)
    except:
        print("❌ Tiempo excedido.")
        return

    if not resultados:
        print("Sin resultados.")
        return

    await guardar_en_supabase(resultados)

    vuelos_ganga = [r for r in resultados if r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']]
    if vuelos_ganga:
        titulo = "🚨 <b>¡GANGAS DETECTADAS!</b>\n\n"
        vuelos_a_mostrar = resultados if es_reporte_diario else vuelos_ganga
    elif es_reporte_diario:
        titulo = "🌅 <b>REPORTE DIARIO</b>\n\n"
        vuelos_a_mostrar = resultados
    else:
        return

    mensaje = titulo
    for r in vuelos_a_mostrar:
        ruta_limpia = r['ruta'].replace("<", "&lt;").replace(">", "&gt;")
        icono = "🚨" if (r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']) else "📍"

        bloque = f"{icono} <b>{ruta_limpia}</b>\n"
        for i, opc in enumerate(r['mejores']):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            tipo = "🚀" if opc['tipo'] == "DIR" else "🛬"
            bloque += f"   {medal} ${opc['precio']} - {tipo}\n"

        url_l = r['url'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        bloque += f"   📊 Promedio: ${r['mediana']}\n"
        bloque += f"   🔗 <a href='{url_l}'>Ver en Google Flights</a>\n\n"
        mensaje += bloque

    enviar_notificacion_telegram(mensaje)

if __name__ == "__main__":
    asyncio.run(main())
