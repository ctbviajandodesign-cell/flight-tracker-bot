import asyncio
import os
import csv
import re
import random
import statistics
import requests
from calendar import monthrange
from datetime import datetime
from io import StringIO
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# Rotación de user-agents para evitar bloqueo de Google
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

def _normalizar_rango(inicio, fin):
    """
    Expande fechas sueltas a rango completo del mes.
    Acepta YYYY-MM o YYYY-MM-DD. Si fin está vacío o igual al inicio,
    cubre todo el mes de inicio. Devuelve (ini, fin) en YYYY-MM-DD.
    """
    inicio = (inicio or "").strip().replace("/", "-")
    fin    = (fin    or "").strip().replace("/", "-")

    def expandir(f, ultimo=False):
        partes = f.split("-")
        if len(partes) >= 2:
            y, m = int(partes[0]), int(partes[1])
            if len(partes) == 2:          # solo YYYY-MM → expandir
                dia = monthrange(y, m)[1] if ultimo else 1
                return f"{y:04d}-{m:02d}-{dia:02d}"
        return f                           # ya tiene día completo

    f_ini = expandir(inicio, ultimo=False)

    if not fin or fin == inicio or fin == f_ini:
        # Sin fin o igual → cubrir el mes completo del inicio
        y, m = int(f_ini.split("-")[0]), int(f_ini.split("-")[1])
        f_fin = f"{y:04d}-{m:02d}-{monthrange(y, m)[1]:02d}"
    else:
        f_fin = expandir(fin, ultimo=True)

    return f_ini, f_fin


# Parche: aeropuertos que Google confunde por código corto
_NOMBRES_AEROPUERTO = {
    "PEI": "Pereira Colombia",
    "EZE": "Aeropuerto Internacional Ministro Pistarini EZE Buenos Aires",
}
# Parche: cap de precio máximo por aeropuerto (origen o destino)
_PRECIO_MAX_AEROPUERTO = {
    "PEI": 800,
    "EZE": 1800,
}

async def extrar_mejor_precio(page, origen, destino, fecha_inicio, fecha_fin):
    fecha_inicio, fecha_fin = _normalizar_rango(fecha_inicio, fecha_fin)
    origen_q  = _NOMBRES_AEROPUERTO.get(origen.upper(),  origen).replace(" ", "%20")
    destino_q = _NOMBRES_AEROPUERTO.get(destino.upper(), destino).replace(" ", "%20")
    precio_max = max(
        _PRECIO_MAX_AEROPUERTO.get(origen.upper(),  0),
        _PRECIO_MAX_AEROPUERTO.get(destino.upper(), 0),
    )
    url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino_q}%20from%20{origen_q}%20on%20{fecha_inicio}%20through%20{fecha_fin}&hl=es-419"
    print(f"✈️ Analizando: {origen} -> {destino}")
    try:
        await page.goto(url, wait_until="commit", timeout=35000)
        # Espera inteligente: espera a que Google termine sus requests AJAX (precios cargados)
        # Si tarda más de 6s (Google sigue cargando cosas), continúa igual con 3s de fallback
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except:
            await page.wait_for_timeout(5000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
        precios_validos = []

        f_ini = fecha_inicio.replace("/", "-")
        f_fin = fecha_fin.replace("/", "-")
        try:
            m_ini = int(f_ini.split("-")[1])
            y_ini = f_ini.split("-")[0]
            m_fin = int(f_fin.split("-")[1])
            y_fin = f_fin.split("-")[0]
            meses = [(m_ini, y_ini), (m_fin, y_fin)] if m_ini != m_fin else [(m_ini, y_ini)]
        except:
            meses = []

        mes_idx, prev_dia = 0, -1

        meses_es = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }

        for e in elementos:
            label = e.get('aria-label', '').lower()

            tiene_precio = any(x in label for x in [
                'dólar', 'dolar', 'dólares', 'usd', '$', 'dólares estadounidenses'
            ])
            if not tiene_precio:
                continue

            match = re.search(r'(\d[\d,\.]*)\s*(?:dólar|dolar|dólares|usd)', label)
            if not match:
                match = re.search(r'(?:us\$|\$)\s*(\d[\d,\.]*)', label)
            if not match:
                continue

            txt = match.group(1).replace(',', '').replace('.', '').strip()
            try:
                precio = int(txt)
            except:
                continue

            if precio <= 10:
                continue
            if precio_max > 0 and precio > precio_max:
                continue

            # Tipo: solo marcar si hay certeza, sino dejar vacío
            if any(x in label for x in ["sin escala", "sin escalas", "directo", "nonstop", "vuelo directo"]):
                tipo = "DIR"
            elif any(x in label for x in ["escala", "escalas", "parada", "conexión", "con escala"]):
                tipo = "ESC"
            else:
                tipo = ""

            # Extraer fecha del aria-label
            fecha_corta = "N/D"
            match_fecha = re.search(
                r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?:\s+de\s+(\d{4}))?',
                label
            )
            if match_fecha:
                dia = int(match_fecha.group(1))
                mes_nombre = match_fecha.group(2)
                mes_num = meses_es.get(mes_nombre, '00')
                anio = match_fecha.group(3) if match_fecha.group(3) else (y_ini if meses else str(datetime.now().year))
                fecha_corta = f"{dia:02d}/{mes_num}/{str(anio)[2:]}"
            elif meses:
                parent_text = e.parent.get_text(separator=' ', strip=True) if e.parent else ""
                match_day = re.search(r'\b(\d{1,2})\b', parent_text)
                if match_day:
                    dia = int(match_day.group(1))
                    if 1 <= dia <= 31:
                        if dia < prev_dia and mes_idx < len(meses) - 1:
                            mes_idx += 1
                        prev_dia = dia
                        m_act, y_act = meses[mes_idx]
                        fecha_corta = f"{dia:02d}/{int(m_act):02d}/{str(y_act)[2:]}"

            precios_validos.append((precio, fecha_corta, tipo))

        if not precios_validos:
            print(f"  ❌ Sin precios para {destino}")
            return None

        precios_validos.sort(key=lambda x: x[0])
        vistos = set()
        unicos = []
        for p in precios_validos:
            clave = (p[0], p[1])
            if clave not in vistos:
                vistos.add(clave)
                unicos.append(p)

        mejores_3 = unicos[:3]
        mediana = statistics.median([p[0] for p in unicos])
        print(f"  💰 {len(unicos)} precios únicos para {destino}. Mejor: ${mejores_3[0][0]} ({mejores_3[0][1]})")

        return {
            "mejores": [{"precio": p[0], "detalle": p[1], "tipo": p[2]} for p in mejores_3],
            "precio": mejores_3[0][0],
            "url": url,
            "mediana": int(mediana),
            "es_ganga_mat": (mejores_3[0][0] <= (mediana * 0.8))
        }

    except Exception as e:
        print(f"  ⚠️ Salto en {destino}: {e}")
    return None


async def _crear_contexto_stealth(browser):
    """Crea un contexto de navegador con técnicas anti-detección."""
    ua = random.choice(_USER_AGENTS)
    context = await browser.new_context(
        user_agent=ua,
        viewport={"width": 1920, "height": 1080},
        locale="es-419",
        extra_http_headers={
            "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        },
    )
    # Ocultar firma de automatización que Google detecta
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['es-419', 'es', 'en']});
        window.chrome = {runtime: {}};
        delete window.__playwright;
        delete window.__pwInitScripts;
    """)
    return context


async def procesar_una_ruta(browser, r):
    context = await _crear_contexto_stealth(browser)
    page = await context.new_page()
    res = None
    try:
        res = await asyncio.wait_for(
            extrar_mejor_precio(page, r["origen"], r["destino"], r["inicio"], r["fin"]),
            timeout=90
        )
        if res:
            res["ruta"] = f"{r['origen']} -> {r['destino']}"
            res["alerta_manual"] = r['alerta']
    except asyncio.TimeoutError:
        print(f"  🛑 Tiempo agotado para {r['destino']}")
    finally:
        await context.close()
    return res


async def procesar_rutas():
    rutas_pendientes = []
    try:
        url_csv = os.getenv("GOOGLE_SHEETS_URL", "")
        response = requests.get(url_csv, timeout=15)
        f = StringIO(response.text)
        reader = csv.DictReader(f)
        for row in reader:
            origen  = (row.get("ORIGEN")  or "").strip()
            destino = (row.get("DESTINO") or "").strip()
            inicio  = (row.get("MES DE INICIO") or "").strip().replace("/", "-")
            if not origen or not destino or not inicio:
                # Sin origen, destino o mes de inicio → fila incompleta, se salta
                continue
            rutas_pendientes.append({
                "origen": origen,
                "destino": destino,
                "inicio": inicio,
                "fin": (row.get("MES DE FIN") or "").strip().replace("/", "-"),
                "alerta": int(str(row.get("Precio_Alerta") or row.get("PRECIO ALERTA") or "0").strip() or "0"),
                "pais_destino": row.get("PAIS_DESTINO", "")
            })
    except Exception as e:
        print(f"❌ Error cargando rutas: {e}")
        return [], 0

    if not rutas_pendientes:
        return [], 0

    print(f"📋 {len(rutas_pendientes)} rutas — procesando una a la vez para evitar bloqueo de Google")

    async with async_playwright() as p:
        # Headless nuevo modo: menos detectable que el clásico
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--headless=new",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        exitosas = []
        for i, r in enumerate(rutas_pendientes):
            res = await procesar_una_ruta(browser, r)
            if res:
                exitosas.append(res)
            # Delay entre rutas (excepto después de la última) para no triggear rate-limiting
            # 10-18s es suficiente: el stealth oculta la firma de bot, el delay solo evita rate-limit
            if i < len(rutas_pendientes) - 1:
                delay = random.randint(10, 18)
                print(f"  ⏳ Esperando {delay}s antes de la siguiente ruta...")
                await asyncio.sleep(delay)
        await browser.close()

        fallidas = len(rutas_pendientes) - len(exitosas)
        print(f"📊 Rutas procesadas: {len(exitosas)} exitosas, {fallidas} sin precios de {len(rutas_pendientes)} totales")
        return exitosas, len(rutas_pendientes)

if __name__ == "__main__":
    asyncio.run(procesar_rutas())
