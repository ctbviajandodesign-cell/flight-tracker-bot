import asyncio
import os
import csv
import re
import statistics
import requests
import random
from io import StringIO
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

async def extrar_mejor_precio(page, origen, destino, fecha_inicio, fecha_fin):
    url = f"https://www.google.com/travel/flights?q=Flights+to+{destino}+from+{origen}+on+{fecha_inicio}+through+{fecha_fin}&hl=es-419&curr=USD"
    print(f"  ✈️  {origen} ➡️  {destino}")

    try:
        await page.wait_for_timeout(random.randint(800, 2000))
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)

        try:
            await page.wait_for_selector('[aria-label*="dólar"], [aria-label*="USD"], [aria-label*="$"]', timeout=12000)
        except:
            await page.evaluate("window.scrollTo(0, 400)")
            await page.wait_for_timeout(3000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # DEBUG: imprimir TODOS los aria-label que contengan números
        # para ver el formato real que usa Google ahora
        elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
        print(f"\n===== DEBUG aria-labels con números para {destino} (primeros 20) =====")
        count = 0
        for e in elementos:
            label = e.get('aria-label', '')
            if re.search(r'\d{2,}', label):  # labels con números de 2+ dígitos
                print(f"  LABEL: {label[:120]}")
                count += 1
                if count >= 20:
                    break
        print(f"===== FIN DEBUG ({count} labels mostrados) =====\n")

        return None  # No procesar, solo diagnosticar

    except Exception as e:
        print(f"  ❌ Excepción en {destino}: {type(e).__name__}: {e}")
        return None


async def procesar_una_ruta(browser, r, semaphore):
    async with semaphore:
        ua = random.choice(USER_AGENTS)
        context = await browser.new_context(
            user_agent=ua,
            viewport={"width": 1280, "height": 800},
            locale="es-419",
            timezone_id="America/Guayaquil",
            extra_http_headers={
                "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        res = None
        try:
            res = await asyncio.wait_for(
                extrar_mejor_precio(page, r["origen"], r["destino"], r["inicio"], r["fin"]),
                timeout=60
            )
        except asyncio.TimeoutError:
            print(f"  🛑 Timeout para {r['destino']}")
        except Exception as e:
            print(f"  🛑 Error en {r['destino']}: {e}")
        finally:
            await context.close()
        return res


async def procesar_rutas():
    rutas_pendientes = []
    print("📡 Conectando con Google Sheets...")

    try:
        url_csv = os.getenv("GOOGLE_SHEETS_URL", "")
        if not url_csv:
            print("❌ GOOGLE_SHEETS_URL no configurado.")
            return []

        response = requests.get(url_csv, timeout=15)
        f = StringIO(response.text)
        reader = csv.DictReader(f)

        for row in reader:
            r = {k.upper().strip(): v.strip() for k, v in row.items()}
            origen = r.get("ORIGEN", "")
            destino = r.get("DESTINO", "")
            if origen and destino:
                rutas_pendientes.append({
                    "origen": origen,
                    "destino": destino,
                    "inicio": r.get("MES DE INICIO", "").replace("/", "-"),
                    "fin": r.get("MES DE FIN", "").replace("/", "-"),
                    "alerta": int(r.get("PRECIO ALERTA", 0) or 0)
                })

        print(f"📊 {len(rutas_pendientes)} rutas. Solo procesando las primeras 2 para debug.")
        rutas_pendientes = rutas_pendientes[:2]  # SOLO 2 RUTAS para no desperdiciar tiempo

    except Exception as e:
        print(f"❌ Error: {e}")
        return []

    semaphore = asyncio.Semaphore(1)  # Una a la vez para logs limpios

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"]
        )
        tasks = [procesar_una_ruta(browser, r, semaphore) for r in rutas_pendientes]
        await asyncio.gather(*tasks)
        await browser.close()

    return []

if __name__ == "__main__":
    asyncio.run(procesar_rutas())
