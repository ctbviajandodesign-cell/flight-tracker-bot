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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

async def extrar_mejor_precio(page, origen, destino, fecha_inicio, fecha_fin):
    url = f"https://www.google.com/travel/flights?q=Flights+to+{destino}+from+{origen}+on+{fecha_inicio}+through+{fecha_fin}&hl=es-419&curr=USD"
    print(f"  ✈️  {origen} ➡️  {destino} | Fechas: {fecha_inicio} → {fecha_fin}")

    try:
        await page.wait_for_timeout(random.randint(800, 2000))
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)

        try:
            await page.wait_for_selector('[aria-label*="dólar"], [aria-label*="USD"], [aria-label*="$"]', timeout=12000)
            print(f"  ✅ Precios detectados en página para {destino}")
        except:
            print(f"  ⚠️  No aparecieron precios en 12s para {destino} — intentando scroll...")
            await page.evaluate("window.scrollTo(0, 400)")
            await page.wait_for_timeout(3000)

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Verificar bloqueo REAL: solo si hay texto visible de error en h1/h2/p
        # (Google incluye "captcha" y "unusual traffic" en su JS interno aunque la página esté bien)
        bloqueado = False
        for tag in soup.find_all(['h1', 'h2', 'p']):
            texto = tag.get_text().lower()
            if 'unusual traffic' in texto or 'not a robot' in texto or 'verify you' in texto:
                bloqueado = True
                break

        if bloqueado:
            print(f"  🚫 Bloqueo real detectado para {destino} (página de verificación visible)")
            return None

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
            print(f"  💰 {len(precios_validos)} precios encontrados para {destino}. Mejor: ${mejores_3[0][0]}")
            return {
                "mejores": [{"precio": p[0], "detalle": p[1], "tipo": p[2]} for p in mejores_3],
                "precio": mejores_3[0][0],
                "url": url,
                "mediana": int(mediana),
                "es_ganga_mat": (mejores_3[0][0] <= (mediana * 0.8))
            }
        else:
            print(f"  ❌ Sin precios válidos para {destino} — página cargó pero sin datos extraíbles.")
            return None

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
                "DNT": "1",
            }
        )
        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)

        res = None
        try:
            res = await asyncio.wait_for(
                extrar_mejor_precio(page, r["origen"], r["destino"], r["inicio"], r["fin"]),
                timeout=60
            )
            if res:
                res["ruta"] = f"{r['origen']} ➡️ {r['destino']}"
                res["alerta_manual"] = r['alerta']
        except asyncio.TimeoutError:
            print(f"  🛑 Timeout (60s) para {r['destino']}")
        except Exception as e:
            print(f"  🛑 Error inesperado en {r['destino']}: {e}")
        finally:
            await context.close()

        return res


async def procesar_rutas():
    rutas_pendientes = []
    print("📡 Conectando con Google Sheets...")

    try:
        url_csv = os.getenv("GOOGLE_SHEETS_URL", "")
        if not url_csv:
            print("❌ GOOGLE_SHEETS_URL no configurado en Secrets.")
            return []

        response = requests.get(url_csv, timeout=15)
        print(f"✅ Google Sheets OK (HTTP {response.status_code}) — {len(response.text)} caracteres recibidos")

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

        print(f"📊 {len(rutas_pendientes)} rutas cargadas desde Google Sheets.")

    except Exception as e:
        print(f"❌ Error cargando rutas: {type(e).__name__}: {e}")
        return []

    if not rutas_pendientes:
        print("⚠️ Lista de rutas vacía. Verifica tu Google Sheets.")
        return []

    semaphore = asyncio.Semaphore(3)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        tasks = [procesar_una_ruta(browser, r, semaphore) for r in rutas_pendientes]
        respuestas = await asyncio.gather(*tasks)
        await browser.close()

    exitosas = [r for r in respuestas if r]
    print(f"\n📈 Resultado final: {len(exitosas)}/{len(rutas_pendientes)} rutas con precios.")
    return exitosas


if __name__ == "__main__":
    asyncio.run(procesar_rutas())
