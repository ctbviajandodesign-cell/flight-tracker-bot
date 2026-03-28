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
    ahora_utc = datetime.utcnow()
    ahora_ec = datetime.utcnow().replace(hour=(datetime.utcnow().hour - 5) % 24)
    hora_utc = ahora_utc.hour
    fecha_hora = ahora_utc.strftime('%d/%m/%Y')

    print("🚀 Iniciando rastreo inteligente...")

    # 12 UTC = 7:47 AM Ecuador → GENERAL
    # 15 UTC = 10:47 AM Ecuador → SOLO GANGAS
    # 20 UTC = 3:10 PM Ecuador  → GENERAL
    # 21 UTC = 4:45 PM Ecuador  → SOLO GANGAS
    es_reporte_diario = (hora_utc in [12, 13, 20, 21])

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

    if es_reporte_diario and vuelos_ganga:
        titulo = (
            f"🌐 <b>REPORTE DIARIO CTB</b> — {fecha_hora}\n"
            f"🚨 <b>¡{len(vuelos_ganga)} gangas detectadas!</b>\n"
            f"📊 {len(resultados)} rutas analizadas\n\n"
        )
        vuelos_a_mostrar = resultados
    elif es_reporte_diario:
        titulo = (
            f"🌐 <b>REPORTE DIARIO CTB</b> — {fecha_hora}\n"
            f"📊 {len(resultados)} rutas analizadas — sin gangas por ahora\n\n"
        )
        vuelos_a_mostrar = resultados
    elif vuelos_ganga:
        titulo = (
            f"🚨 <b>¡ALERTA DE GANGAS!</b> — {fecha_hora}\n"
            f"🔥 <b>{len(vuelos_ganga)} oportunidades detectadas</b>\n\n"
        )
        vuelos_a_mostrar = vuelos_ganga
    else:
        return

    mensaje = titulo

    if es_reporte_diario:
        # REPORTE GENERAL — una línea por ruta, compacto
        for r in vuelos_a_mostrar:
            ruta_l = r['ruta'].replace("<", "&lt;").replace(">", "&gt;")
            es_ganga = r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual']
            icono = "🔥" if es_ganga else "✈️"
            mejor = r['mejores'][0] if r['mejores'] else None
            precio_txt = f"<b>${r['precio']}</b>" if mejor else "—"
            fecha_txt = mejor['detalle'] if mejor and mejor['detalle'] != 'N/D' else ""
            tipo_txt = " 🚀" if mejor and mejor['tipo'] == "DIR" else " 🛬" if mejor and mejor['tipo'] == "ESC" else ""
            ganga_txt = " <i>← GANGA</i>" if es_ganga else ""
            linea = f"{icono} {ruta_l} — {precio_txt} USD{tipo_txt}{ganga_txt}"
            if fecha_txt:
                linea += f" · {fecha_txt}"
            linea += "\n"
            mensaje += linea

        # Separador y gangas con detalle al final
        if vuelos_ganga:
            mensaje += "\n🚨 <b>DETALLE GANGAS:</b>\n"
            for r in vuelos_ganga:
                es_ganga = r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual']
                if not es_ganga:
                    continue
                ruta_l = r['ruta'].replace("<", "&lt;").replace(">", "&gt;")
                url_l = r['url'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                mejor = r['mejores'][0] if r['mejores'] else None
                fecha_txt = mejor['detalle'] if mejor and mejor['detalle'] != 'N/D' else "—"
                tipo_txt = " 🚀 Directo" if mejor and mejor['tipo'] == "DIR" else " 🛬 Escala" if mejor and mejor['tipo'] == "ESC" else ""
                mensaje += (
                    f"🔥 <b>{ruta_l}</b>\n"
                    f"   💰 <b>${r['precio']} USD</b>{tipo_txt} · {fecha_txt}\n"
                    f"   🎯 Alerta: ${r['alerta_manual']} | 📊 Prom: ${r['mediana']}\n"
                    f"   🔗 <a href=\"{url_l}\">Ver en Google Flights</a>\n"
                )
    else:
        # ALERTA GANGAS — detalle completo solo de gangas
        for r in vuelos_a_mostrar:
            es_ganga = r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual']
            ruta_l = r['ruta'].replace("<", "&lt;").replace(">", "&gt;")
            url_l = r['url'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            mejor = r['mejores'][0] if r['mejores'] else None
            fecha_txt = mejor['detalle'] if mejor and mejor['detalle'] != 'N/D' else "—"
            tipo_txt = " 🚀 Directo" if mejor and mejor['tipo'] == "DIR" else " 🛬 Escala" if mejor and mejor['tipo'] == "ESC" else ""
            mensaje += (
                f"🔥 <b>{ruta_l}</b>\n"
                f"   💰 <b>${r['precio']} USD</b>{tipo_txt} · {fecha_txt}\n"
                f"   🎯 Alerta: ${r['alerta_manual']} | 📊 Prom: ${r['mediana']}\n"
                f"   🔗 <a href=\"{url_l}\">Ver en Google Flights</a>\n"
                f"─────────────────\n"
            )

    enviar_notificacion_telegram(mensaje)


if __name__ == "__main__":
    asyncio.run(main())
