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

async def esperar_resultados(page, destino):
    """
    Espera activamente hasta que aparezcan resultados reales de vuelos.
    Los resultados reales tienen clases específicas de Google Flights (jJSFMe, YMlIz, etc.)
    o texto con formato de precio USD en el body visible.
    """
    print(f"  ⏳ Esperando resultados reales para {destino}...")

    # Intentar hasta 4 veces con scroll progresivo
    for intento in range(4):
        await page.wait_for_timeout(4000)

        # Scroll progresivo para forzar carga lazy
        await page.evaluate(f"window.scrollTo(0, {300 * (intento + 1)})")

        # Verificar si hay precios reales en el texto visible de la página
        try:
            contenido = await page.evaluate("""() => {
                // Buscar elementos que contengan precios reales (no del formulario)
                // Los resultados de vuelos están en listas/tablas, no en el header
                const body = document.body.innerText;
                const matches = body.match(/\\$\\s*\\d{2,4}|US\\$\\s*\\d{2,4}|\\d{2,4}\\s*USD/g);
                return matches ? matches.slice(0, 5) : [];
            }""")

            if contenido and len(contenido) >= 3:
                print(f"  ✅ Resultados confirmados para {destino}: {contenido[:3]}")
                return True
        except:
            pass

        print(f"  🔄 Intento {intento + 1}/4 para {destino} — aún cargando...")

    print(f"  ❌ Sin resultados tras 4 intentos para {destino}")
    return False


async def extrar_mejor_precio(page, origen, destino, fecha_inicio, fecha_fin):
    url = f"https://www.google.com/travel/flights?q=Flights+to+{destino}+from+{origen}+on+{fecha_inicio}+through+{fecha_fin}&hl=es-419&curr=USD"
    print(f"  ✈️  {origen} ➡️  {destino} | {fecha_inicio} → {fecha_fin}")

    try:
        await page.wait_for_timeout(random.randint(1000, 2500))
        await page.goto(url, wait_until="networkidle", timeout=45000)

        hay_resultados = await esperar_resultados(page, destino)
        if not hay_resultados:
            return None

        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Verificar bloqueo real
        bloqueado = False
        for tag in soup.find_all(['h1', 'h2', 'p']):
            texto = tag.get_text().lower()
            if 'unusual traffic' in texto or 'not a robot' in texto or 'verify you' in texto:
                bloqueado = True
                break
        if bloqueado:
            print(f"  🚫 Bloqueo real para {destino}")
            return None

        precios_validos = []

        # Estrategia 1: buscar por aria-label con precio
        elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
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
            match_precio = re.search(r'(?:us\$|\$|usd)\s*(\d+(?:[.,]\d+)?)', label)
            if not match_precio:
                # También buscar patrón "123 dólares" o "123 USD"
                match_precio = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:dólar|dolar|usd)', label)
            if match_precio:
                txt = match_precio.group(1).replace(',', '').replace('.', '')
                try:
                    precio = int(txt)
                    if 30 < precio < 15000:
                        tipo = "DIR" if any(x in label for x in ["sin escala", "directo", "nonstop"]) else "ESC"
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
                        else:
                            precios_validos.append((precio, "N/F", tipo))
                except:
                    pass

        # Estrategia 2: si aria-label no dio nada, buscar precios en texto visible del DOM
        if not precios_validos:
            print(f"  🔍 aria-label vacío para {destino}, intentando extracción por texto...")
            all_text = soup.get_text(separator='\n')
            matches = re.findall(r'(?:US\$|\$)\s*(\d{2,4})', all_text)
            for m in matches:
                try:
                    precio = int(m)
                    if 30 < precio < 15000:
                        precios_validos.append((precio, "N/F", "ESC"))
                except:
                    pass

        if precios_validos:
            precios_validos.sort(key=lambda x: x[0])
            # Eliminar duplicados de precio
            vistos = set()
            unicos = []
            for p in precios_validos:
                if p[0] not in vistos:
                    vistos.add(p[0])
                    unicos.append(p)
            mejores_3 = unicos[:3]
            mediana = statistics.median([p[0] for p in unicos])
            print(f"  💰 {len(unicos)} precios únicos para {destino}. Mejor: ${mejores_3[0][0]}")
            return {
                "mejores": [{"precio": p[0], "detalle": p[1], "tipo": p[2]} for p in mejores_3],
                "precio": mejores_3[0][0],
                "url": url,
                "mediana": int(mediana),
                "es_ganga_mat": (mejores_3[0][0] <= (mediana * 0.8))
            }
        else:
            print(f"  ❌ Sin precios extraíbles para {destino}")
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
                timeout=90
            )
            if res:
                res["ruta"] = f"{r['origen']} ➡️ {r['destino']}"
                res["alerta_manual"] = r['alerta']
        except asyncio.TimeoutError:
            print(f"  🛑 Timeout (90s) para {r['destino']}")
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
        print(f"✅ Google Sheets OK (HTTP {response.status_code})")
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

        print(f"📊 {len(rutas_pendientes)} rutas cargadas.")

    except Exception as e:
        print(f"❌ Error cargando rutas: {type(e).__name__}: {e}")
        return []

    if not rutas_pendientes:
        print("⚠️ Lista de rutas vacía.")
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
