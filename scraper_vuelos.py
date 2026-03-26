import asyncio
import os
import csv
import re
import statistics
import requests
from io import StringIO
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def extrar_mejor_precio(page, origen, destino, fecha_inicio, fecha_fin):
    url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origen}%20on%20{fecha_inicio}%20through%20{fecha_fin}&hl=es-419"
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

        # Preparar rango de meses para asignar fechas
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

        for e in elementos:
            label = e.get('aria-label', '').lower()
            if any(x in label for x in ['dólar', 'dolar', 'usd', '$']):
                match = re.search(r'((?:us\$|\$)?\s*\d+(?:,\d+)?(?:\.\d+)?)\s*', label)
                if match:
                    txt = match.group(1).replace('US$', '').replace('$', '').replace(',', '').strip()
                    try:
                        precio = int(float(txt))
                        if precio > 10:
                            tipo = "DIR" if any(x in label for x in ["sin escalas", "directo"]) else "ESC"

                            # Intentar extraer fecha del aria-label directamente
                            # Google Flights incluye la fecha en el label: "15 de abril, $234"
                            fecha_corta = "N/F"
                            match_fecha = re.search(
                                r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
                                label
                            )
                            meses_es = {
                                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                            }
                            if match_fecha:
                                dia = int(match_fecha.group(1))
                                mes_nombre = match_fecha.group(2)
                                mes_num = meses_es.get(mes_nombre, '00')
                                # Determinar año: si el mes es menor al de inicio, es año siguiente
                                anio = y_ini if meses else "26"
                                if meses and int(mes_num) < m_ini:
                                    anio = str(int(y_ini) + 1)
                                fecha_corta = f"{dia:02d}/{mes_num}/{str(anio)[2:]}"
                            elif meses:
                                # Fallback: usar el día del texto del padre
                                parent_text = e.parent.get_text(separator=' ', strip=True) if e.parent else ""
                                match_day = re.search(r'^(\d{1,2})\b', parent_text)
                                if match_day:
                                    dia = int(match_day.group(1))
                                    if 1 <= dia <= 31:
                                        if dia < prev_dia and mes_idx < len(meses) - 1:
                                            mes_idx += 1
                                        prev_dia = dia
                                        m_act, y_act = meses[mes_idx]
                                        fecha_corta = f"{dia:02d}/{int(m_act):02d}/{str(y_act)[2:]}"

                            precios_validos.append((precio, fecha_corta, tipo))
                    except:
                        pass

        if precios_validos:
            precios_validos.sort(key=lambda x: x[0])
            mejores_3 = precios_validos[:3]
            mediana = statistics.median([p[0] for p in precios_validos])
            return {
                "mejores": [{"precio": p[0], "detalle": p[1], "tipo": p[2]} for p in mejores_3],
                "precio": mejores_3[0][0],
                "url": url,
                "mediana": int(mediana),
                "es_ganga_mat": (mejores_3[0][0] <= (mediana * 0.8))
            }
    except Exception as e:
        print(f"  ⚠️ Salto en {destino} por error: {e}")
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
                    "alerta": int(row.get("PRECIO ALERTA", 0))
                })
    except:
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
