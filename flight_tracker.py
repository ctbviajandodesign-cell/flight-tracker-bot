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
        print("⚠️  Supabase no configurado (faltan SUPABASE_URL o SUPABASE_KEY).")
        return

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    datos = []
    for r in resultados:
        datos.append({
            "ruta": r['ruta'],
            "precio": r['precio'],
            "mediana": r.get('mediana', 0),
            "es_ganga": bool(r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']),
            "tipo_vuelo": r['mejores'][0]['tipo'] if r['mejores'] else "UNK",
            "fecha_mejor": r['mejores'][0]['detalle'] if r['mejores'] else "N/F",
            "url_vuelo": r.get('url', '')
        })

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{url}/rest/v1/vuelos_historial",
                json=datos,
                headers=headers
            )
            if resp.status_code in [200, 201]:
                print(f"✅ Supabase: {len(datos)} registros guardados.")
            else:
                print(f"⚠️  Supabase respondió HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Error guardando en Supabase: {type(e).__name__}: {e}")


async def main():
    ahora = datetime.utcnow()
    print(f"🚀 Iniciando rastreo — {ahora.strftime('%Y-%m-%d %H:%M')} UTC")

    hora_utc = ahora.hour
    # Reporte completo en las 3 ejecuciones principales del día
    es_reporte_diario = (hora_utc in [12, 15, 19, 21, 1, 3])

    try:
        resultados = await asyncio.wait_for(procesar_rutas(), timeout=2400)
    except asyncio.TimeoutError:
        print("❌ Timeout general (40 min). El proceso tardó demasiado.")
        enviar_notificacion_telegram("⚠️ Flight Tracker\nEl rastreo excedió el tiempo máximo (40 min). Revisa GitHub Actions.")
        return
    except Exception as e:
        print(f"❌ Error general: {e}")
        enviar_notificacion_telegram(f"⚠️ Flight Tracker — Error\n{str(e)[:200]}")
        return

    if not resultados:
        print("⚠️  Sin resultados. Google puede estar bloqueando el scraper.")
        enviar_notificacion_telegram(
            "⚠️ Flight Tracker\n\n"
            "No se obtuvieron resultados en este ciclo.\n"
            "Posible bloqueo de Google Flights o error en Google Sheets.\n\n"
            f"🕐 {ahora.strftime('%d/%m/%Y %H:%M')} UTC"
        )
        return

    # Guardar todo en Supabase siempre
    await guardar_en_supabase(resultados)

    # Clasificar gangas
    vuelos_ganga = [r for r in resultados if r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']]

    if vuelos_ganga:
        titulo = f"🚨 ¡GANGAS DETECTADAS! ({len(vuelos_ganga)} rutas)\n"
        titulo += f"📅 {ahora.strftime('%d/%m/%Y %H:%M')} UTC\n\n"
        vuelos_a_mostrar = resultados  # Muestra todo pero marca gangas
    elif es_reporte_diario:
        titulo = f"🌅 REPORTE DIARIO DE VUELOS\n"
        titulo += f"📅 {ahora.strftime('%d/%m/%Y %H:%M')} UTC\n\n"
        vuelos_a_mostrar = resultados
    else:
        # Fuera de horario de reporte y sin gangas — igual notifica un resumen corto
        print(f"ℹ️  Sin gangas y fuera de horario de reporte diario. Enviando resumen corto.")
        resumen = (
            f"✅ Rastreo completado\n"
            f"📅 {ahora.strftime('%d/%m/%Y %H:%M')} UTC\n"
            f"📊 {len(resultados)} rutas analizadas — sin gangas detectadas.\n"
            f"💾 Datos guardados en Supabase."
        )
        enviar_notificacion_telegram(resumen)
        return

    mensaje = titulo
    for r in vuelos_a_mostrar:
        ruta_l = r['ruta'].replace("<", "<").replace(">", ">")
        es_ganga = r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']
        icono = "🚨" if es_ganga else "📍"

        bloque = f"{icono} {ruta_l}"
        if es_ganga:
            bloque += " ← GANGA"
        bloque += "\n"

        for i, opc in enumerate(r['mejores']):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            tipo = "🚀 Directo" if opc['tipo'] == "DIR" else "🛬 Escala"
            fecha_txt = opc['detalle'] if opc['detalle'] != "N/F" else "fecha N/D"
            bloque += f"   {medal} ${opc['precio']} USD — {fecha_txt} — {tipo}\n"

        url_l = r['url'].replace("&", "&").replace("<", "<").replace(">", ">")
        bloque += f"   📊 Promedio mes: ${r['mediana']} USD\n"
        bloque += f"   🔗 Ver en Google Flights\n\n"
        mensaje += bloque

    enviar_notificacion_telegram(mensaje)
    print(f"✅ Proceso completo. {len(resultados)} rutas procesadas, {len(vuelos_ganga)} gangas.")


if __name__ == "__main__":
    asyncio.run(main())
