import asyncio
import os
import csv
import re
import requests
from io import StringIO
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def extrar_mejor_precio(page, origen, destino, fecha_inicio, fecha_fin):
    url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origen}%20on%20{fecha_inicio}%20through%20{fecha_fin}&hl=es-419"
    print(f"✈️ {origen} -> {destino}")
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

        print(f"\n===== TODOS los aria-label con dígitos para {destino} =====")
        count = 0
        for e in elementos:
            label = e.get('aria-label', '')
            if re.search(r'\d{2,}', label):
                print(f"  [{count}] {label[:150]}")
                count += 1
            if count >= 30:
                break
        print(f"===== FIN ({count} labels) =====\n")

    except Exception as e:
        print(f"  ❌ Error: {e}")
    return None

async def procesar_una_ruta(browser, r, semaphore):
    async with semaphore:
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await asyncio.wait_for(
                extrar_mejor_precio(page, r["origen"], r["destino"], r["inicio"], r["fin"]),
                timeout=100
            )
        except:
            pass
        await context.close()
        return None

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
    except Exception as e:
        print(f"❌ Error sheets: {e}")
        return []

    # Solo procesar GYE->PEI para el debug
    rutas_pendientes = [r for r in rutas_pendientes if r["destino"] == "PEI"][:1]
    print(f"📊 Procesando solo: {rutas_pendientes}")

    semaphore = asyncio.Semaphore(1)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [procesar_una_ruta(browser, r, semaphore) for r in rutas_pendientes]
        await asyncio.gather(*tasks)
        await browser.close()
    return []

if __name__ == "__main__":
    asyncio.run(procesar_rutas())
