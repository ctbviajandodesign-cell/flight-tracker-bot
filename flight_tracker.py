import asyncio
import os
import httpx
import statistics
from datetime import datetime, timedelta
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
            or r.get('ganga_sesion', False)
        )
        datos.append({
            "ruta": r['ruta'],
            "precio": r['precio'],
            "mediana": r.get('mediana_historica') or r.get('mediana', 0),
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


async def contar_gangas_hoy(ruta):
    """Cuenta cuántas veces fue ganga esta ruta hoy en Supabase."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return 0
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        today = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')  # hora Ecuador
        ruta_encoded = quote(ruta, safe='')
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{url}/rest/v1/vuelos_historial?ruta=eq.{ruta_encoded}&es_ganga=eq.true&fecha=gte.{today}T00:00:00&select=ruta",
                headers=headers
            )
            if resp.status_code == 200:
                return len(resp.json())
    except Exception as e:
        print(f"⚠️ Error racha ({ruta}): {e}")
    return 0


async def obtener_resumen_dia():
    """Obtiene las mejores gangas del día desde Supabase."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return []
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        today = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')  # hora Ecuador
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{url}/rest/v1/vuelos_historial?es_ganga=eq.true&fecha=gte.{today}T00:00:00&order=precio.asc&select=ruta,precio,mediana,precio_alerta",
                headers=headers
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"⚠️ Error resumen día: {e}")
    return []


async def obtener_stats_dia():
    """Obtiene rutas monitoreadas hoy y precio más bajo del día desde Supabase."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return 0, None
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        today = (datetime.utcnow() - timedelta(hours=5)).strftime('%Y-%m-%d')
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{url}/rest/v1/vuelos_historial?fecha=gte.{today}T00:00:00&order=precio.asc&select=ruta,precio",
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                rutas_unicas = len(set(r['ruta'] for r in data))
                mejor = data[0] if data else None
                return rutas_unicas, mejor
    except Exception as e:
        print(f"⚠️ Error stats día: {e}")
    return 0, None


async def analizar_gangas_historicas(resultados):
    """Para rutas sin alerta manual, detecta gangas comparando con historial de Supabase."""
    rutas_sin_alerta = [r for r in resultados if r['alerta_manual'] == 0]
    if not rutas_sin_alerta:
        return

    tasks = [obtener_precios_historicos(r['ruta']) for r in rutas_sin_alerta]
    historiales = await asyncio.gather(*tasks)

    for r, historico in zip(rutas_sin_alerta, historiales):
        # Tendencia: historico viene ordenado más reciente primero
        if len(historico) >= 2:
            if r['precio'] < historico[0] and historico[0] <= historico[1]:
                r['tendencia'] = 'bajando'
            elif r['precio'] > historico[0]:
                r['tendencia'] = 'subiendo'
            else:
                r['tendencia'] = ''
        else:
            r['tendencia'] = ''

        if len(historico) >= 30:
            mediana_hist = statistics.median(historico)
            bajada_pct = int((1 - r['precio'] / mediana_hist) * 100)
            if bajada_pct >= 15:
                r['ganga_historica'] = True
                r['ganga_sesion'] = False
                r['mediana_historica'] = int(mediana_hist)
                r['bajada_pct'] = bajada_pct
                print(f"  📉 Ganga histórica detectada: {r['ruta']} — {bajada_pct}% bajo promedio")
            else:
                r['ganga_historica'] = False
                r['ganga_sesion'] = False
        else:
            r['ganga_historica'] = False
            if r.get('es_ganga_mat', False):
                r['ganga_sesion'] = True
                print(f"  📊 Ganga de mercado detectada: {r['ruta']} ({len(historico)} registros aún)")
            else:
                r['ganga_sesion'] = False
                print(f"  ℹ️ {r['ruta']}: solo {len(historico)} registros, sin ganga de mercado")


async def main():
    ahora_ec = datetime.utcnow() - timedelta(hours=5)
    fecha_hora = ahora_ec.strftime('%d/%m/%Y')

    print("🚀 Iniciando rastreo inteligente...")

    run_type = os.getenv("RUN_TYPE", "gangas")
    es_reporte_diario = (run_type == "general")

    # ── RESUMEN DEL DÍA ──────────────────────────────────────
    if run_type == "resumen":
        gangas_hoy = await obtener_resumen_dia()
        if not gangas_hoy:
            rutas_vistas, mejor_precio = await obtener_stats_dia()
            msg = f"🌙 <b>Resumen del día</b> — {fecha_hora}\n"
            if rutas_vistas > 0:
                msg += f"📊 {rutas_vistas} rutas monitoreadas hoy\n"
                if mejor_precio:
                    ruta_l = mejor_precio['ruta'].replace("<", "&lt;").replace(">", "&gt;")
                    msg += f"✈️ Precio más bajo visto: <b>{ruta_l}</b> — <b>${mejor_precio['precio']} USD</b>\n"
            msg += f"💤 Sin gangas detectadas hoy"
            enviar_notificacion_telegram(msg)
            return
        # Deduplicar por ruta, quedar con la de menor precio
        vistas = {}
        for g in gangas_hoy:
            ruta = g['ruta']
            if ruta not in vistas or g['precio'] < vistas[ruta]['precio']:
                vistas[ruta] = g
        top = sorted(vistas.values(), key=lambda x: x['precio'])[:3]
        lineas = ""
        for i, g in enumerate(top, 1):
            ruta_l = g['ruta'].replace("<", "&lt;").replace(">", "&gt;")
            if g.get('precio_alerta') and g['precio_alerta'] > 0:
                ref = f"🎯 alerta ${g['precio_alerta']}"
            elif g.get('mediana') and g['mediana'] > 0:
                pct = int((1 - g['precio'] / g['mediana']) * 100)
                ref = f"📉 -{pct}% del promedio"
            else:
                ref = ""
            lineas += f"{i}. {ruta_l} — <b>${g['precio']} USD</b>"
            if ref:
                lineas += f" · {ref}"
            lineas += "\n"
        enviar_notificacion_telegram(
            f"🌙 <b>Resumen del día</b> — {fecha_hora}\n"
            f"🔥 Mejores gangas de hoy:\n\n{lineas}"
        )
        return

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

    # Criterio de ganga: alerta manual O bajada histórica >= 15% O ganga de mercado
    vuelos_ganga = [
        r for r in resultados
        if (r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual'])
        or r.get('ganga_historica', False)
        or r.get('ganga_sesion', False)
    ]

    # Definir qué mostrar y con qué título
    if es_reporte_diario and vuelos_ganga:
        titulo = (
            f"🌐 <b>REPORTE DIARIO</b> — {fecha_hora}\n"
            f"🚨 <b>{len(vuelos_ganga)} gangas detectadas</b> de {len(resultados)} rutas\n\n"
        )
        vuelos_a_mostrar = resultados
    elif es_reporte_diario:
        titulo = (
            f"🌐 <b>REPORTE DIARIO</b> — {fecha_hora}\n"
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
        # Pre-cargar rachas para todas las gangas del día
        rachas = {}
        if vuelos_ganga:
            tareas_racha = [contar_gangas_hoy(r['ruta']) for r in vuelos_ganga]
            conteos = await asyncio.gather(*tareas_racha)
            rachas = {r['ruta']: c for r, c in zip(vuelos_ganga, conteos)}

        for r in vuelos_a_mostrar:
            ruta_l = r['ruta'].replace("<", "&lt;").replace(">", "&gt;")
            es_ganga_manual = r['alerta_manual'] > 0 and r['precio'] <= r['alerta_manual']
            es_ganga = es_ganga_manual or r.get('ganga_historica', False) or r.get('ganga_sesion', False)
            if es_ganga:
                icono = "🔥🔥" if rachas.get(r['ruta'], 0) >= 2 else "🔥"
            else:
                icono = "✈️"
            mejor = r['mejores'][0] if r.get('mejores') else None
            fecha_txt = mejor['detalle'] if mejor and mejor['detalle'] != 'N/D' else ""
            tipo_txt = " 🚀" if mejor and mejor['tipo'] == "DIR" else " 🛬" if mejor and mejor['tipo'] == "ESC" else ""
            if r.get('ganga_historica'):
                ganga_txt = f" <i>← -{r['bajada_pct']}% Hist.</i>"
            elif r.get('ganga_sesion'):
                ganga_txt = " <i>← mercado actual</i>"
            else:
                ganga_txt = ""
            tendencia = r.get('tendencia', '')
            tendencia_txt = " 📉" if tendencia == 'bajando' else " 📈" if tendencia == 'subiendo' else ""
            linea = f"{icono} {ruta_l} — <b>${r['precio']}</b> USD{tipo_txt}{tendencia_txt}{ganga_txt}"
            if fecha_txt:
                linea += f" · {fecha_txt}"
            linea += "\n"
            mensaje += linea

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
            elif r.get('ganga_historica'):
                referencia = f"📉 {r['bajada_pct']}% bajo promedio histórico (${r['mediana_historica']})"
            else:
                referencia = f"📊 20% bajo el precio de mercado actual"
            tendencia = r.get('tendencia', '')
            tendencia_txt = " · 📉 en bajada" if tendencia == 'bajando' else " · 📈 en subida" if tendencia == 'subiendo' else ""
            mensaje += (
                f"🔥 <b>{ruta_l}</b>\n"
                f"   💰 <b>${r['precio']} USD</b>{tipo_txt}\n"
                f"   📅 {fecha_txt}{tendencia_txt}\n"
                f"   {referencia}\n"
                f"   🔗 <a href=\"{url_l}\">Ver en Google Flights</a>\n"
                f"─────────────────\n"
            )

    enviar_notificacion_telegram(mensaje)


if __name__ == "__main__":
    asyncio.run(main())
