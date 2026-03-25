import asyncio
import os
import csv
import re
import statistics
import datetime
from datetime import timedelta
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def extrar_mejor_precio(page, origen, destino, fecha_inicio, fecha_fin, dias_paquete=None):
    if dias_paquete:
        d_ini = datetime.datetime.strptime(fecha_inicio, "%Y-%m-%d")
        d_ret = d_ini + timedelta(days=int(dias_paquete))
        url_ret = d_ret.strftime("%Y-%m-%d")
        url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origen}%20on%20{fecha_inicio}%20through%20{url_ret}&hl=es-419"
    else:
        url = f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%20{origen}%20on%20{fecha_inicio}%20through%20{fecha_fin}&hl=es-419"

    print(f"✈️ Buscando: {origen} ➡️ {destino} (Iniciando en {fecha_inicio})")

    await page.goto(url, wait_until="networkidle")
    await page.wait_for_timeout(5000)

    try:
        # Intento 1
        await page.click('input[placeholder*="Salida"], input[aria-label*="Salida"], .S9fT9c', timeout=8000)
        await page.wait_for_timeout(4000)
    except Exception:
        try:
            # Intento 2
            await page.click('[data-placeholder="Salida"], [aria-haspopup="dialog"]', timeout=5000)
            await page.wait_for_timeout(4000)
        except:
            print(f"  ❌ No se pudo abrir el calendario para {origen} -> {destino}.")
            return None

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')
    elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
    precios_validos = []

    fecha_inicio = fecha_inicio.replace("/", "-")
    fecha_fin = fecha_fin.replace("/", "-")

    m_ini = int(fecha_inicio.split("-")[1])
    y_ini = fecha_inicio.split("-")[0]
    m_fin = int(fecha_fin.split("-")[1])
    y_fin = fecha_fin.split("-")[0]

    meses_recorrido = [(m_ini, y_ini)]
    if m_ini != m_fin or y_ini != y_fin:
        meses_recorrido.append((m_fin, y_fin))

    mes_actual_idx = 0
    prev_dia = -1

    for e in elementos:
        label = e.get('aria-label', '').lower()
        if ('dólar' in label or 'dolar' in label or 'usd' in label or 'us$' in label):
            match = re.search(r'((?:us\$|\$)?\s*\d+(?:,\d+)?(?:\.\d+)?)\s*(?:dólares|dolar|usd)?', label)
            if match:
                txt_precio = match.group(1).replace('US$', '').replace('$', '').replace(',', '').strip()
                try:
                    precio = int(float(txt_precio))
                    if precio > 10:
                        if any(x in label for x in ["sin escalas", "directo", "nonstop"]):
                            tipo_vuelo = "DIR"
                        elif any(x in label for x in ["escala", "parada", "stop"]):
                            tipo_vuelo = "ESC"
                        else:
                            tipo_vuelo = "UNK"

                        parent_text = e.parent.get_text(separator=' ', strip=True) if e.parent else ""
                        match_day = re.search(r'^(\d+)', parent_text)

                        if match_day:
                            dia = int(match_day.group(1))
                            if dia < prev_dia and mes_actual_idx < len(meses_recorrido) - 1:
                                mes_actual_idx += 1
                            prev_dia = dia
                            m_actual, y_actual = meses_recorrido[mes_actual_idx]
                            fecha_corta = f"{dia:02d}/{int(m_actual):02d}/{str(y_actual)[2:]}"
                            precios_validos.append((precio, fecha_corta, tipo_vuelo))
                        else:
                            precios_validos.append((precio, "N/F", tipo_vuelo))
                except:
                    pass

    if precios_validos:
        solo_precios = [p[0] for p in precios_validos]
        mediana = statistics.median(solo_precios) if solo_precios else 0
        precios_validos.sort(key=lambda x: x[0])
        mejores_3 = precios_validos[:3]

        return {
            "mejores": [{"precio": p[0], "detalle": p[1], "tipo": p[2]} for p in mejores_3],
            "precio": mejores_3[0][0],
            "url": url,
            "mediana": int(mediana),
            "es_ganga_mat": (mejores_3[0][0] <= (mediana * 0.8))
        }

    return None

def format_date(date_str, fallback_day):
    date_str = date_str.replace("/", "-")
    parts = date_str.split("-")

    if len(parts) == 2:
        return f"{parts[0]}-{parts[1]}-{fallback_day}"
    elif len(parts) == 3:
        if len(parts[0]) == 4:
            return date_str
        elif len(parts[2]) == 4:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"

    return None

async def procesar_una_ruta(browser, r, semaphore):
    async with semaphore:
        context = await browser.new_context()
        page = await context.new_page()

        try:
            res = await extrar_mejor_precio(page, r["origen"], r["destino"], r["inicio"], r["fin"], r["dias_paquete"])
            await context.close()

            if res:
                return {
                    "ruta": f"{r['origen']} ➡️ {r['destino']}",
                    "mejores": res['mejores'],
                    "precio": res['precio'],
                    "url": res['url'],
                    "alerta_manual": r['alerta'],
                    "mediana": res['mediana'],
                    "es_ganga_mat": res['es_ganga_mat']
                }

        except Exception as e:
            print(f"❌ Error procesando {r['origen']}->{r['destino']}: {e}")
            await context.close()

        return None

async def procesar_rutas():
    rutas_pendientes = []

    try:
        import requests
        from io import StringIO

        url_csv = os.getenv("GOOGLE_SHEETS_URL", "")
        if not url_csv:
            return []

        response = requests.get(url_csv)
        f = StringIO(response.text)
        reader = csv.DictReader(f)

        for row in reader:
            origen = row.get("ORIGEN", "").strip()
            destino = row.get("DESTINO", "").strip()
            mes_ini = row.get("MES DE INICIO", "").strip()
            mes_fin = row.get("MES DE FIN", "").strip()
            str_alerta = row.get("PRECIO ALERTA", "0").strip()
            alerta = int(str_alerta) if str_alerta.isdigit() else 0
            paquete = row.get("Dias_del_Paquete", "").strip()
            paquete = int(paquete) if paquete.isdigit() else None

            if origen and destino:
                rutas_pendientes.append({
                    "origen": origen,
                    "destino": destino,
                    "inicio": format_date(mes_ini, "01"),
                    "fin": format_date(mes_fin, "28"),
                    "alerta": alerta,
                    "dias_paquete": paquete
                })

    except Exception as e:
        print(f"❌ Error cargando rutas: {e}")
        return []

    if not rutas_pendientes:
        return []

    semaphore = asyncio.Semaphore(4)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [procesar_una_ruta(browser, r, semaphore) for r in rutas_pendientes]
        respuestas = await asyncio.gather(*tasks)
        resultados = [r for r in respuestas if r is not None]
        await browser.close()

    return resultados

if __name__ == "__main__":
    asyncio.run(procesar_rutas())
