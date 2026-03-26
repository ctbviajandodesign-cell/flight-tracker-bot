import asyncio
    2 import os
    3 import csv
    4 import re
    5 import statistics
    6 import datetime
    7 from playwright.async_api import async_playwright
    8 from bs4 import BeautifulSoup
    9
   10 async def extrar_mejor_precio(page, origen, destino, fecha_inicio,
      fecha_fin, dias_paquete=None):
   11     url =
      f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from%
      20{origen}%20on%20{fecha_inicio}%20through%20{fecha_fin}&hl=es-419"
   12     print(f"✈️ Analizando: {origen} -> {destino}")
   13     try:
   14         # TIMEOUT DE CARGA: 30 segundos máximo para abrir la página
   15         await page.goto(url, wait_until="commit", timeout=30000)
   16         await page.wait_for_timeout(6000)
   17         try:
   18             # Intento de abrir calendario con timeout corto
   19             await page.click('input[placeholder*="Salida"],
      [aria-label*="Salida"], .S9fT9c', timeout=7000)
   20             await page.wait_for_timeout(3000)
   21         except:
   22             print(f"  ⚠️ Calendario no abierto para {destino}, intentando
      extraer igual...")
   23         
   24         html = await page.content()
   25         soup = BeautifulSoup(html, 'html.parser')
   26         elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
   27         precios_validos = []
   28         for e in elementos:
   29             label = e.get('aria-label', '').lower()
   30             if any(x in label for x in ['dólar', 'dolar', 'usd', '$']):
   31                 match =
      re.search(r'((?:us\$|\$)?\s*\d+(?:,\d+)?(?:\.\d+)?)\s*', label)
   32                 if match:
   33                     txt = match.group(1).replace('US$', '').replace('$',
      '').replace(',', '').strip()
   34                     try:
   35                         precio = int(float(txt))
   36                         if precio > 10:
   37                             tipo = "DIR" if any(x in label for x in ["sin
      escalas", "directo"]) else "ESC"
   38                             precios_validos.append((precio, "N/F", tipo))
   39                     except: pass
   40         if precios_validos:
   41             precios_validos.sort(key=lambda x: x[0])
   42             mejores_3 = precios_validos[:3]
   43             solo_precios = [p[0] for p in precios_validos]
   44             mediana = statistics.median(solo_precios)
   45             return {
   46                 "mejores": [{"precio": p[0], "detalle": p[1], "tipo":
      p[2]} for p in mejores_3],
   47                 "precio": mejores_3[0][0], "url": url, "mediana":
      int(mediana),
   48                 "es_ganga_mat": (mejores_3[0][0] <= (mediana * 0.8))
   49             }
   50     except Exception as e:
   51         print(f"  ❌ Error en {destino}: {e}")
   52     return None
   53
   54 async def procesar_una_ruta(browser, r, semaphore):
   55     async with semaphore:
   56         context = await browser.new_context()
   57         page = await context.new_page()
   58         # TIEMPO LÍMITE TOTAL POR RUTA: 90 segundos
   59         try:
   60             res = await asyncio.wait_for(extrar_mejor_precio(page,
      r["origen"], r["destino"], r["inicio"], r["fin"]), timeout=90)
   61             if res:
   62                 res["ruta"] = f"{r['origen']} -> {r['destino']}"
   63                 res["alerta_manual"] = r['alerta']
   64         except asyncio.TimeoutError:
   65             print(f"  🛑 Tiempo agotado para {r['destino']}")
   66             res = None
   67         await context.close()
   68         return res
   69
   70 async def procesar_rutas():
   71     rutas_pendientes = []
   72     try:
   73         import requests
   74         from io import StringIO
   75         url_csv = os.getenv("GOOGLE_SHEETS_URL", "")
   76         response = requests.get(url_csv, timeout=15)
   77         f = StringIO(response.text)
   78         reader = csv.DictReader(f)
   79         for row in reader:
   80             if row.get("ORIGEN") and row.get("DESTINO"):
   81                 rutas_pendientes.append({
   82                     "origen": row["ORIGEN"], "destino": row["DESTINO"],
   83                     "inicio": row["MES DE INICIO"].replace("/", "-"),
   84                     "fin": row["MES DE FIN"].replace("/", "-"),
   85                     "alerta": int(row.get("PRECIO ALERTA", 0))
   86                 })
   87     except: return []
   88     if not rutas_pendientes: return []
   89     semaphore = asyncio.Semaphore(3) # Bajamos a 3 para mayor estabilidad
   90     async with async_playwright() as p:
   91         browser = await p.chromium.launch(headless=True)
   92         tasks = [procesar_una_ruta(browser, r, semaphore) for r in
      rutas_pendientes]
   93         respuestas = await asyncio.gather(*tasks)
   94         await browser.close()
   95         return [r for r in respuestas if r]
