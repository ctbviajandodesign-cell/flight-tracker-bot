import asyncio
import os
import csv
import re
import statistics
import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def extrar_mejor_precio(page, origen, destino, fecha_inicio, fecha_fin):
    url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origen}%20on%20{fecha_inicio}%20through%20{fecha_fin}&hl=es-419"
    print(f"✈️ Analizando: {origen} -> {destino}")
    try:
        # Tiempo límite de carga inicial: 35 segundos
        await page.goto(url, wait_until="commit", timeout=35000)
        await page.wait_for_timeout(6000)
        try:
            # Intento de abrir calendario con timeout corto
            await page.click('input[placeholder*="Salida"], [aria-label*="Salida"], .S9fT9c', timeout=7000)
            await page.wait_for_timeout(3000)
        except:
            pass

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
        precios_validos = []

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
                            precios_validos.append((precio, "N/F", tipo))
                    except:
                        pass

        if precios_validos:
            precios_validos.sort(key=lambda x: x[0])
            mejores_3 = precios_validos[:3]
            solo_precios = [p[0] for p in precios_validos]
            mediana = statistics.median(solo_precios)
            return {
                "mejores": [{"precio": p[0], "detalle": p[1], "tipo": p[2]} for p in mejores_3],
                "precio": mejores_3[0][0],
                "url": url,
                "mediana": int(mediana),
                "es_ganga_mat": (mejores_3[0][0] <= (mediana * 0.8))
            }
    except Exception as e:
        print(f"  ⚠️ Salto en {destino} por tiempo de espera.")
    return None

async def procesar_una_ruta(browser, r, semaphore):
    async with semaphore:
        context = await browser.new_context()
        page = await context.new_page()
        # TIEMPO LÍMITE TOTAL POR RUTA: 90 segundos para evitar bloqueos
        try:
            res = await asyncio.wait_for(extrar_mejor_precio(page, r["origen"], r["destino"], r["inicio"], r["fin"]), timeout=100)
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

    # Paralelismo de 3 (más estable en infraestructura gratuita)
    semaphore = asyncio.Semaphore(3)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [procesar_una_ruta(browser, r, semaphore) for r in rutas_pendientes]
        respuestas = await asyncio.gather(*tasks)
        await browser.close()
        return [r for r in respuestas if r]
