import asyncio
import os
import csv
import re
import statistics
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def extrar_mejor_precio(page, origen, destino, fecha_inicio, fecha_fin):
    url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origen}%20on%20{fecha_inicio}%20through%20{fecha_fin}&hl=es-419"
    print(f"✈️ Analizando: {origen} -> {destino}")
    try:
        await page.goto(url, wait_until="commit", timeout=35000)
        await page.wait_for_timeout(5000)
        try:
            await page.click('input[placeholder*="Salida"], [aria-label*="Salida"], .S9fT9c', timeout=8000)
            await page.wait_for_timeout(4000)
        except:
            pass

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
        precios_validos = []

        f_ini = fecha_inicio.replace("/", "-")
        m_ini = int(f_ini.split("-")[1])
        y_ini = f_ini.split("-")[0]

        f_fin = fecha_fin.replace("/", "-")
        m_fin = int(f_fin.split("-")[1])
        y_fin = f_fin.split("-")[0]

        meses = [(m_ini, y_ini), (m_fin, y_fin)] if m_ini != m_fin else [(m_ini, y_ini)]

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

                            parent_text = e.parent.get_text(separator=' ', strip=True) if e.parent else ""
                            match_day = re.search(r'^(\d+)', parent_text)

                            if match_day:
                                dia = int(match_day.group(1))
                                if dia < prev_dia and mes_idx < len(meses) - 1:
                                    mes_idx += 1
                                prev_dia = dia
                                m_act, y_act = meses[mes_idx]
                                fecha_corta = f"{dia:02d}/{int(m_act):02d}/{str(y_act)[2:]}"
                                precios_validos.append((precio, fecha_corta, tipo))
                            else:
                                precios_validos.append((precio, "N/F", tipo))
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

    except:
        pass

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
        except:
            res = None

        await context.close()
        return res

async def procesar_rutas():
    rutas_pendientes = []

    try:
        import requests
        from io import StringIO

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

    semaphore = asyncio.Semaphore(4)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [procesar_una_ruta(browser, r, semaphore) for r in rutas_pendientes]
        respuestas = await asyncio.gather(*tasks)
        await browser.close()

        return [r for r in respuestas if r]

if __name__ == "__main__":
    asyncio.run(procesar_rutas())
