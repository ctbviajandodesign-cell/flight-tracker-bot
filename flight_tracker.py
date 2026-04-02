import asyncio
import os
import httpx
import statistics
from datetime import datetime
from urllib.parse import quote
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
        es_ganga = bool(
            (r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual'])
            or r.get('ganga_historica', False)
        )
        datos.append({
            "ruta": r['ruta'],
            "precio": r['precio'],
            "mediana": r.get('mediana', 0),
            "fecha_vuelo": r['mejores'][0]['detalle'] if r.get('mejores') else "N/D",
            "precio_alerta": r.get('alerta_manual', 0),
            "es_ganga": es_ganga,
            "tipo_vuelo": r['mejores'][0]['tipo'] if r.get('mejores') and r['mejores'][0]['tipo'] else "N/D"
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


async def obtener_precios_historicos(ruta):
    """Obtiene los últimos 30 precios de una ruta desde Supabase."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return []
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    try:
        ruta_encoded = quote(ruta, safe='')
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{url}/rest/v1/vuelos_historial?ruta=eq.{ruta_encoded}&order=fecha.desc&limit=30&select=precio",
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                return [row['precio'] for row in data if row.get('precio')]
    except Exception as e:
        print(f"⚠️ Error historial Supabase ({ruta}): {e}")
    return []


async def analizar_gangas_historicas(resultados):
    """Para rutas sin alerta manual, detecta gangas comparando con historial de Supabase."""
    rutas_sin_alerta = [r for r in resultados if r['alerta_manual'] == 0]
    if not rutas_sin_alerta:
        return

    tasks = [obtener_precios_historicos(r['ruta']) for r in rutas_sin_alerta]
    historiales = await asyncio.gather(*tasks)

    for r, historico in zip(rutas_sin_alerta, historiales):
        if len(historico) >= 30:
            mediana_hist = statistics.median(historico)
            bajada_pct = int((1 - r['precio'] / mediana_hist) * 100)
            if bajada_pct >= 15:
                r['ganga_historica'] = True
                r['mediana_historica'] = int(mediana_hist)
                r['bajada_pct'] = bajada_pct
                print(f"  📉 Ganga histórica detectada: {r['ruta']} — {bajada_pct}% bajo promedio")
            else:
                r['ganga_historica'] = False
        else:
            r['ganga_historica'] = False
            print(f"  ℹ️ {r['ruta']}: solo {len(historico)} registros (mínimo 30 para análisis histórico)")


async def main():
    ahora_utc = datetime.utcnow()
    fecha_hora = ahora_utc.strftime('%d/%m/%Y')

    print("🚀 Iniciando rastreo inteligente...")

    run_type = os.getenv("RUN_TYPE", "gangas")
    es_reporte_diario = (run_type == "general")

    try:
        resultados = await asyncio.wait_for(procesar_rutas(), timeout=2400)
    except asyncio.TimeoutError:
        print("❌ Tiempo excedido (40 min).")
        return
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return

    if not resultados:
        print("Sin resultados.")
        return

    # Analizar gangas históricas antes de guardar (así es_ganga queda correcto en Supabase)
    await analizar_gangas_historicas(resultados)

    await guardar_en_supabase(resultados)

    # Criterio de ganga: alerta manual O bajada histórica >= 15%
    vuelos_ganga = [
        r for r in resultados
        if (r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual'])
        or r.get('ganga_historica', False)
    ]

    # Definir qué mostrar y con qué título
    if es_reporte_diario and vuelos_ganga:
        titulo = (
            f"🌐 <b>REPORTE DIARIO CTB</b> — {fecha_hora}\n"
            f"🚨 <b>{len(vuelos_ganga)} gangas detectadas</b> de {len(resultados)} rutas\n\n"
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
            f"🚨 <b>ALERTA DE GANGAS</b> — {fecha_hora}\n"
            f"🔥 <b>{len(vuelos_ganga)} oportunidades detectadas</b>\n\n"
        )
        vuelos_a_mostrar = vuelos_ganga
    else:
        mensaje_vacio = (
            f"✅ <b>Bot activo</b> — {fecha_hora}\n"
            f"📊 {len(resultados)} rutas analizadas\n"
            f"💤 Sin gangas en este momento\n"
            f"<i>Próxima consulta en horario programado</i>"
        )
        enviar_notificacion_telegram(mensaje_vacio)
        return

    mensaje = titulo

    if es_reporte_diario:
        # ── REPORTE GENERAL ─────────────────────────────────
        for r in vuelos_a_mostrar:
            ruta_l = r['ruta'].replace("<", "&lt;").replace(">", "&gt;")
            es_ganga_manual = r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual']
            es_ganga = es_ganga_manual or r.get('ganga_historica', False)
            icono = "🔥" if es_ganga else "✈️"
            mejor = r['mejores'][0] if r.get('mejores') else None
            fecha_txt = mejor['detalle'] if mejor and mejor['detalle'] != 'N/D' else ""
            tipo_txt = " 🚀" if mejor and mejor['tipo'] == "DIR" else " 🛬" if mejor and mejor['tipo'] == "ESC" else ""
            if es_ganga_manual:
                ganga_txt = " <i>← GANGA</i>"
            elif r.get('ganga_historica'):
                ganga_txt = f" <i>← -{r['bajada_pct']}% histórico</i>"
            else:
                ganga_txt = ""
            linea = f"{icono} {ruta_l} — <b>${r['precio']}</b> USD{tipo_txt}{ganga_txt}"
            if fecha_txt:
                linea += f" · {fecha_txt}"
            linea += "\n"
            mensaje += linea

        # Detalle de gangas al final
        if vuelos_ganga:
            mensaje += "\n🚨 <b>DETALLE GANGAS:</b>\n"
            for r in vuelos_ganga:
                ruta_l = r['ruta'].replace("<", "&lt;").replace(">", "&gt;")
                url_l = r['url'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                mejor = r['mejores'][0] if r.get('mejores') else None
                fecha_txt = mejor['detalle'] if mejor and mejor['detalle'] != 'N/D' else "—"
                tipo_txt = " 🚀 Directo" if mejor and mejor['tipo'] == "DIR" else " 🛬 Escala" if mejor and mejor['tipo'] == "ESC" else ""
                es_ganga_manual = r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual']
                if es_ganga_manual:
                    referencia = f"🎯 Alerta: ${r['alerta_manual']} | 📊 Prom: ${r['mediana']}"
                else:
                    referencia = f"📉 {r['bajada_pct']}% bajo promedio histórico (${r['mediana_historica']})"
                mensaje += (
                    f"🔥 <b>{ruta_l}</b>\n"
                    f"   💰 <b>${r['precio']} USD</b>{tipo_txt} · {fecha_txt}\n"
                    f"   {referencia}\n"
                    f"   🔗 <a href=\"{url_l}\">Ver en Google Flights</a>\n"
                )
    else:
        # ── ALERTA GANGAS ────────────────────────────────────
        for r in vuelos_a_mostrar:
            ruta_l = r['ruta'].replace("<", "&lt;").replace(">", "&gt;")
            url_l = r['url'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            mejor = r['mejores'][0] if r.get('mejores') else None
            fecha_txt = mejor['detalle'] if mejor and mejor['detalle'] != 'N/D' else "—"
            tipo_txt = " 🚀 Directo" if mejor and mejor['tipo'] == "DIR" else " 🛬 Escala" if mejor and mejor['tipo'] == "ESC" else ""
            es_ganga_manual = r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual']
            if es_ganga_manual:
                referencia = f"🎯 Alerta: ${r['alerta_manual']} | 📊 Prom: ${r['mediana']}"
            else:
                referencia = f"📉 {r['bajada_pct']}% bajo promedio histórico (${r['mediana_historica']})"
            mensaje += (
                f"🔥 <b>{ruta_l}</b>\n"
                f"   💰 <b>${r['precio']} USD</b>{tipo_txt} · {fecha_txt}\n"
                f"   {referencia}\n"
                f"   🔗 <a href=\"{url_l}\">Ver en Google Flights</a>\n"
                f"─────────────────\n"
            )

    enviar_notificacion_telegram(mensaje)


if __name__ == "__main__":
    asyncio.run(main())
