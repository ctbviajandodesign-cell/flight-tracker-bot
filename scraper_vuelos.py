 1 import asyncio
     2 import os
     3 import csv
     4 import re
     5 import statistics
     6 from playwright.async_api import async_playwright
     7 from bs4 import BeautifulSoup
     8
     9 async def extrar_mejor_precio(page, origen, destino, fecha_inicio,
       fecha_fin):
    10     url =
       f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20from
       %20{origen}%20on%20{fecha_inicio}%20through%20{fecha_fin}&hl=es-419"
    11     print(f"✈️ Analizando: {origen} -> {destino}")
    12     
    13     try:
    14         # Cargamos rápido con domcontentloaded
    15         await page.goto(url, wait_until="commit", timeout=35000)
    16         await page.wait_for_timeout(5000)
    17         
    18         try:
    19             # Intento de abrir calendario para cargar precios
    20             await page.click('input[placeholder*="Salida"],
       [aria-label*="Salida"], .S9fT9c', timeout=8000)
    21             await page.wait_for_timeout(4000)
    22         except: pass
    23         
    24         html = await page.content()
    25         soup = BeautifulSoup(html, 'html.parser')
    26         elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
    27         precios_validos = []
    28
    29         # Lógica de fechas (Día/Mes/Año)
    30         f_ini = fecha_inicio.replace("/", "-")
    31         m_ini = int(f_ini.split("-")[1])
    32         y_ini = f_ini.split("-")[0]
    33         f_fin = fecha_fin.replace("/", "-")
    34         m_fin = int(f_fin.split("-")[1])
    35         y_fin = f_fin.split("-")[0]
    36         meses = [(m_ini, y_ini), (m_fin, y_fin)] if m_ini != m_fin else
       [(m_ini, y_ini)]
    37
    38         mes_idx, prev_dia = 0, -1
    39         for e in elementos:
    40             label = e.get('aria-label', '').lower()
    41             if any(x in label for x in ['dólar', 'dolar', 'usd', '$']):
    42                 match =
       re.search(r'((?:us\$|\$)?\s*\d+(?:,\d+)?(?:\.\d+)?)\s*', label)
    43                 if match:
    44                     txt = match.group(1).replace('US$', '').replace('$',
       '').replace(',', '').strip()
    45                     try:
    46                         precio = int(float(txt))
    47                         if precio > 10:
    48                             tipo = "DIR" if any(x in label for x in ["sin
       escalas", "directo"]) else "ESC"
    49                             parent_text = e.parent.get_text(separator='
       ', strip=True) if e.parent else ""
    50                             match_day = re.search(r'^(\d+)', parent_text)
    51                             if match_day:
    52                                 dia = int(match_day.group(1))
    53                                 if dia < prev_dia and mes_idx <
       len(meses) - 1: mes_idx += 1
    54                                 prev_dia = dia
    55                                 m_act, y_act = meses[mes_idx]
    56                                 fecha_corta =
       f"{dia:02d}/{int(m_act):02d}/{str(y_act)[2:]}"
    57                                 precios_validos.append((precio,
       fecha_corta, tipo))
    58                             else:
    59                                 precios_validos.append((precio, "N/F",
       tipo))
    60                     except: pass
    61
    62         if precios_validos:
    63             precios_validos.sort(key=lambda x: x[0])
    64             mejores_3 = precios_validos[:3]
    65             mediana = statistics.median([p[0] for p in precios_validos])
    66             return {
    67                 "mejores": [{"precio": p[0], "detalle": p[1], "tipo":
       p[2]} for p in mejores_3],
    68                 "precio": mejores_3[0][0], "url": url, "mediana":
       int(mediana),
    69                 "es_ganga_mat": (mejores_3[0][0] <= (mediana * 0.8))
    70             }
    71     except Exception as e:
    72         print(f"  ⚠️ Error en {destino}: {e}")
    73     return None
    74
    75 async def procesar_una_ruta(browser, r, semaphore):
    76     async with semaphore:
    77         context = await browser.new_context()
    78         page = await context.new_page()
    79         try:
    80             # LÍMITE DE 100 SEGUNDOS POR VUELO
    81             res = await asyncio.wait_for(extrar_mejor_precio(page,
       r["origen"], r["destino"], r["inicio"], r["fin"]), timeout=100)
    82             if res:
    83                 res["ruta"] = f"{r['origen']} -> {r['destino']}"
    84                 res["alerta_manual"] = r['alerta']
    85         except:
    86             print(f"  🛑 Tiempo agotado para {r['destino']}")
    87             res = None
    88         await context.close()
    89         return res
    90
    91 async def procesar_rutas():
    92     rutas_pendientes = []
    93     try:
    94         import requests
    95         from io import StringIO
    96         url_csv = os.getenv("GOOGLE_SHEETS_URL", "")
    97         response = requests.get(url_csv, timeout=15)
    98         f = StringIO(response.text)
    99         reader = csv.DictReader(f)
   100         for row in reader:
   101             if row.get("ORIGEN") and row.get("DESTINO"):
   102                 rutas_pendientes.append({
   103                     "origen": row["ORIGEN"], "destino": row["DESTINO"],
   104                     "inicio": row["MES DE INICIO"].replace("/", "-"),
   105                     "fin": row["MES DE FIN"].replace("/", "-"),
   106                     "alerta": int(row.get("PRECIO ALERTA", 0))
   107                 })
   108     except: return []
   109
   110     # PARALELISMO DE 4 VENTANAS
   111     semaphore = asyncio.Semaphore(4)
   112     async with async_playwright() as p:
   113         browser = await p.chromium.launch(headless=True)
   114         tasks = [procesar_una_ruta(browser, r, semaphore) for r in
       rutas_pendientes]
   115         respuestas = await asyncio.gather(*tasks)
   116         await browser.close()
   117         return [r for r in respuestas if r]
