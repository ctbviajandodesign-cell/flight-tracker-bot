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
        print("⚠️ Supabase no configurado.")
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
            "fecha_vuelo": r['mejores'][0]['detalle'] if r['mejores'] else "N/D",
            "precio_alerta": r.get('alerta_manual', 0),
            "es_ganga": bool(r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']),
            "tipo_vuelo": r['mejores'][0]['tipo'] if r['mejores'][0]['tipo'] else "N/D"
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
                print(f"⚠️ Supabase HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Error Supabase: {e}")

async def main():
    print("🚀 Iniciando rastreo inteligente...")
    hora_utc = datetime.utcnow().hour

    # 12 UTC = 7:47 AM Ecuador → GENERAL
    # 15 UTC = 10:47 AM Ecuador → SOLO GANGAS
    # 20 UTC = 3:10 PM Ecuador  → GENERAL
    # 21 UTC = 4:45 PM Ecuador  → SOLO GANGAS
    es_reporte_diario = (hora_utc in [12, 20])

    try:
        resultados = await asyncio.wait_for(procesar_rutas(), timeout=2400)
    except:
        print("❌ Tiempo excedido.")
        return

    if not resultados:
        print("Sin resultados.")
        return

    await guardar_en_supabase(resultados)

    vuelos_ganga = [r for r in resultados if r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']]
vuelos_ganga = [r for r in resultados if r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']]

if es_reporte_diario and vuelos_ganga:
    titulo = "🌅 <b>REPORTE DIARIO</b> — 🚨 <b>¡Hay gangas!</b>\n\n"
    vuelos_a_mostrar = resultados
elif es_reporte_diario:
    titulo = "🌅 <b>REPORTE DIARIO</b>\n\n"
    vuelos_a_mostrar = resultados
elif vuelos_ganga:
    titulo = "🚨 <b>¡GANGAS DETECTADAS!</b>\n\n"
    vuelos_a_mostrar = vuelos_ganga
else:
    return

    mensaje = titulo
    for r in vuelos_a_mostrar:
        ruta_l = r['ruta'].replace("<", "<").replace(">", ">")
        icono = "🚨" if (r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']) else "📍"
        bloque = f"{icono} {ruta_l}\n"
        for i, opc in enumerate(r['mejores']):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            if opc['tipo'] == "DIR":
                tipo_txt = " — 🚀 Directo"
            elif opc['tipo'] == "ESC":
                tipo_txt = " — 🛬 Escala"
            else:
                tipo_txt = ""
            bloque += f"   {medal} ${opc['precio']} USD — {opc['detalle']}{tipo_txt}\n"
        url_l = r['url'].replace("&", "&").replace("<", "<").replace(">", ">")
        bloque += f"   📊 Promedio mes: ${r['mediana']} USD\n"
        bloque += f"   🔗 Ver en Google Flights\n\n"
        mensaje += bloque

    enviar_notificacion_telegram(mensaje)

if __name__ == "__main__":
    asyncio.run(main())
