import asyncio
import os
import csv
import re
import statistics
import requests
from calendar import monthrange
from datetime import datetime
from io import StringIO
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

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
        await page.wait_for_timeout(6000)
        try:
            await page.click('input[placeholder*="Salida"], [aria-label*="Salida"], .S9fT9c', timeout=7000)
            await page.wait_for_timeout(3000)
        except:
            pass

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


async def procesar_una_ruta(browser, r, semaphore):
    async with semaphore:
        context = await browser.new_context()
        page = await context.new_page()
        try:
            res = await asyncio.wait_for(
                extrar_mejor_precio(page, r["origen"], r["destino"], r["inicio"], r["fin"]),
                timeout=100
            )
            if res:
                res["ruta"] = f"{r['origen']} -> {r['destino']}"
                res["alerta_manual"] = r['alerta']
        except asyncio.TimeoutError:
            print(f"  🛑 Tiempo agotado para {r['destino']}")
            res = None
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
            if row.get("ORIGEN") and row.get("DESTINO"):
                rutas_pendientes.append({
                    "origen": row["ORIGEN"],
                    "destino": row["DESTINO"],
                    "inicio": row["MES DE INICIO"].replace("/", "-"),
                    "fin": row["MES DE FIN"].replace("/", "-"),
                    "alerta": int(row.get("Precio_Alerta") or row.get("PRECIO ALERTA") or 0),
                    "pais_destino": row.get("PAIS_DESTINO", "")
                })
    except Exception as e:
        print(f"❌ Error cargando rutas: {e}")
        return []

    if not rutas_pendientes:
        return []

    semaphore = asyncio.Semaphore(3)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [procesar_una_ruta(browser, r, semaphore) for r in rutas_pendientes]
        respuestas = await asyncio.gather(*tasks)
        await browser.close()
        return [r for r in respuestas if r]

if __name__ == "__main__":
    asyncio.run(procesar_rutas())
