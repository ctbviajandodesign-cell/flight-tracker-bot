import asyncio
     2 import os
     3 import csv
     4 import re
     5 import statistics
     6 import datetime
     7 from datetime import timedelta
     8 from playwright.async_api import async_playwright
     9 from bs4 import BeautifulSoup
    10
    11 async def extrar_mejor_precio(page, origen, destino, fecha_inicio,
       fecha_fin, dias_paquete=None):
    12     if dias_paquete:
    13         d_ini = datetime.datetime.strptime(fecha_inicio, "%Y-%m-%d")
    14         d_ret = d_ini + timedelta(days=int(dias_paquete))
    15         url_ret = d_ret.strftime("%Y-%m-%d")
    16         url =
       f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20fro
       m%20{origen}%20on%20{fecha_inicio}%20through%20{url_ret}&hl=es-419"
    17     else:
    18         url =
       f"https://www.google.com/travel/flights?q=Flights%20to%20{destino}%20fro
       m%20{origen}%20on%20{fecha_inicio}%20through%20{fecha_fin}&hl=es-419"
    19
    20     print(f"✈️ Buscando: {origen} ➡️ {destino} (Iniciando en
       {fecha_inicio})")
    21
    22     await page.goto(url, wait_until="networkidle")
    23     await page.wait_for_timeout(5000)
    24
    25     try:
    26         # Intento 1: Selector por placeholder o etiqueta común
    27         await page.click('input[placeholder*="Salida"],
       input[aria-label*="Salida"], .S9fT9c', timeout=8000)
    28         await page.wait_for_timeout(4000)
    29     except Exception:
    30         # Intento 2: Selector alternativo por rol de diálogo
    31         try:
    32             await page.click('[data-placeholder="Salida"],
       [aria-haspopup="dialog"]', timeout=5000)
    33             await page.wait_for_timeout(4000)
    34         except:
    35             print(f"  ❌ No se pudo abrir el calendario para {origen} ->
       {destino}.")
    36             return None
    37
    38     html = await page.content()
    39     soup = BeautifulSoup(html, 'html.parser')
    40     elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
    41     precios_validos = []
    42
    43     fecha_inicio = fecha_inicio.replace("/", "-")
    44     fecha_fin = fecha_fin.replace("/", "-")
    45
    46     m_ini = int(fecha_inicio.split("-")[1])
    47     y_ini = fecha_inicio.split("-")[0]
    48     m_fin = int(fecha_fin.split("-")[1])
    49     y_fin = fecha_fin.split("-")[0]
    50
    51     meses_recorrido = [(m_ini, y_ini)]
    52     if m_ini != m_fin or y_ini != y_fin:
    53         meses_recorrido.append((m_fin, y_fin))
    54
    55     mes_actual_idx = 0
    56     prev_dia = -1
    57
    58     for e in elementos:
    59         label = e.get('aria-label', '').lower()
    60         if ('dólar' in label or 'dolar' in label or 'usd' in label or
       'us$' in label):
    61             match =
       re.search(r'((?:us\$|\$)?\s*\d+(?:,\d+)?(?:\.\d+)?)\s*(?:dólares|dolar|u
       sd)?', label)
    62             if match:
    63                 txt_precio = match.group(1).replace('US$',
       '').replace('$', '').replace(',', '').strip()
    64                 try:
    65                     precio = int(float(txt_precio))
    66                     if precio > 10:
    67                         if any(x in label for x in ["sin escalas",
       "directo", "nonstop"]):
    68                             tipo_vuelo = "DIR"
    69                         elif any(x in label for x in ["escala",
       "parada", "stop"]):
    70                             tipo_vuelo = "ESC"
    71                         else:
    72                             tipo_vuelo = "UNK"
    73
    74                         parent_text = e.parent.get_text(separator=' ',
       strip=True) if e.parent else ""
    75                         match_day = re.search(r'^(\d+)', parent_text)
    76
    77                         if match_day:
    78                             dia = int(match_day.group(1))
    79                             if dia < prev_dia and mes_actual_idx <
       len(meses_recorrido) - 1:
    80                                 mes_actual_idx += 1
    81                             prev_dia = dia
    82                             m_actual, y_actual =
       meses_recorrido[mes_actual_idx]
    83                             fecha_corta =
       f"{dia:02d}/{int(m_actual):02d}/{str(y_actual)[2:]}"
    84                             precios_validos.append((precio, fecha_corta,
       tipo_vuelo))
    85                         else:
    86                             precios_validos.append((precio, "N/F",
       tipo_vuelo))
    87                 except:
    88                     pass
    89
    90     if precios_validos:
    91         solo_precios = [p[0] for p in precios_validos]
    92         mediana = statistics.median(solo_precios) if solo_precios else 0
    93         precios_validos.sort(key=lambda x: x[0])
    94         mejores_3 = precios_validos[:3]
    95
    96         return {
    97             "mejores": [{"precio": p[0], "detalle": p[1], "tipo": p[2]}
       for p in mejores_3],
    98             "precio": mejores_3[0][0],
    99             "url": url,
   100             "mediana": int(mediana),
   101             "es_ganga_mat": (mejores_3[0][0] <= (mediana * 0.8))
   102         }
   103
   104     return None
   105
   106 def format_date(date_str, fallback_day):
   107     date_str = date_str.replace("/", "-")
   108     parts = date_str.split("-")
   109     if len(parts) == 2:
   110         return f"{parts[0]}-{parts[1]}-{fallback_day}"
   111     elif len(parts) == 3:
   112         if len(parts[0]) == 4: return date_str
   113         elif len(parts[2]) == 4: return
       f"{parts[2]}-{parts[1]}-{parts[0]}"
   114     return None
   115
   116 async def procesar_una_ruta(browser, r, semaphore):
   117     async with semaphore:
   118         context = await browser.new_context()
   119         page = await context.new_page()
   120         try:
   121             res = await extrar_mejor_precio(page, r["origen"],
       r["destino"], r["inicio"], r["fin"], r["dias_paquete"])
   122             await context.close()
   123             if res:
   124                 return {
   125                     "ruta": f"{r['origen']} ➡️ {r['destino']}",
   126                     "mejores": res['mejores'],
   127                     "precio": res['precio'],
   128                     "url": res['url'],
   129                     "alerta_manual": r['alerta'],
   130                     "mediana": res['mediana'],
   131                     "es_ganga_mat": res['es_ganga_mat']
   132                 }
   133         except Exception as e:
   134             print(f"❌ Error procesando {r['origen']}->{r['destino']}:
       {e}")
   135             await context.close()
   136         return None
   137
   138 async def procesar_rutas():
   139     rutas_pendientes = []
   140     try:
   141         import requests
   142         from io import StringIO
   143         url_csv = os.getenv("GOOGLE_SHEETS_URL", "")
   144         if not url_csv: return []
   145         response = requests.get(url_csv)
   146         f = StringIO(response.text)
   147         reader = csv.DictReader(f)
   148         for row in reader:
   149             origen = row.get("ORIGEN", "").strip()
   150             destino = row.get("DESTINO", "").strip()
   151             mes_ini = row.get("MES DE INICIO", "").strip()
   152             mes_fin = row.get("MES DE FIN", "").strip()
   153             str_alerta = row.get("PRECIO ALERTA", "0").strip()
   154             alerta = int(str_alerta) if str_alerta.isdigit() else 0
   155             paquete = row.get("Dias_del_Paquete", "").strip()
   156             paquete = int(paquete) if paquete.isdigit() else None
   157             if origen and destino:
   158                 rutas_pendientes.append({
   159                     "origen": origen, "destino": destino,
   160                     "inicio": format_date(mes_ini, "01"),
   161                     "fin": format_date(mes_fin, "28"),
   162                     "alerta": alerta, "dias_paquete": paquete
   163                 })
   164     except Exception as e:
   165         print(f"❌ Error cargando rutas: {e}")
   166         return []
   167
   168     if not rutas_pendientes: return []
   169
   170     semaphore = asyncio.Semaphore(4)
   171     async with async_playwright() as p:
   172         browser = await p.chromium.launch(headless=True)
   173         tasks = [procesar_una_ruta(browser, r, semaphore) for r in
       rutas_pendientes]
   174         respuestas = await asyncio.gather(*tasks)
   175         resultados = [r for r in respuestas if r is not None]
   176         await browser.close()
   177     return resultados
   178
   179 if __name__ == "__main__":
   180     asyncio.run(procesar_rutas())
