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
    await page.wait_for_timeout(3000)
    
    # Hacer clic en la flecha de Salida
    try:
        await page.get_by_placeholder("Salida").first.click()
        await page.wait_for_timeout(3000)
    except Exception as e:
        print("  ❌ No se pudo abrir el calendario.")
        return None

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')
    
    elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
    precios_validos = []
    
    # Aseguramos que tengan guiones por si el usuario usó / en Excel
    fecha_inicio = fecha_inicio.replace("/", "-")
    fecha_fin = fecha_fin.replace("/", "-")
    
    meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    m_ini = int(fecha_inicio.split("-")[1])
    y_ini = fecha_inicio.split("-")[0]
    m_fin = int(fecha_fin.split("-")[1])
    y_fin = fecha_fin.split("-")[0]
    
    meses_recorrido = [f"{meses_nombres[m_ini-1]} {y_ini}"]
    if m_ini != m_fin or y_ini != y_fin:
        meses_recorrido.append(f"{meses_nombres[m_fin-1]} {y_fin}")
        
    mes_actual_idx = 0
    prev_dia = -1
    
    for e in elementos:
        label = e.get('aria-label', '').lower()
        if ('dólar' in label or 'dolar' in label or 'usd' in label or 'us$' in label):
            match = re.search(r'((?:us\$|\$)?\s*\d+(?:,\d+)?(?:\.\d+)?)\s*(?:dólares|dolares|dólar|usd)?', label)
            if match:
                txt_precio = match.group(1).replace('US$', '').replace('$', '').replace(',', '').strip()
                try:
                    precio = int(float(txt_precio))
                    if precio > 10: 
                        parent_text = e.parent.get_text(separator=' ', strip=True) if e.parent else ""
                        match_day = re.search(r'^(\d+)', parent_text)
                        
                        if match_day:
                            dia = int(match_day.group(1))
                            if dia < prev_dia and mes_actual_idx < len(meses_recorrido) - 1:
                                mes_actual_idx += 1
                            prev_dia = dia
                            
                            str_mes = meses_recorrido[mes_actual_idx]
                            precios_validos.append((precio, f"Vuelo el {dia} de {str_mes}"))
                        else:
                            precios_validos.append((precio, "Día no determinado"))
                except Exception as ex:
                    pass
                    
    if precios_validos:
        # Extraemos solo los números para la matemática
        solo_precios = [p[0] for p in precios_validos]
        mediana = statistics.median(solo_precios) if solo_precios else 0
        
        precios_validos.sort(key=lambda x: x[0])
        mejor = precios_validos[0]
        
        # Consideramos GANGA matemática si es al menos un 20% más barato que el precio normal del mes
        es_ganga_matematica = (mejor[0] <= (mediana * 0.8))
        
        return {
            "precio": mejor[0],
            "detalle": mejor[1],
            "url": url,
            "mediana": int(mediana),
            "es_ganga_mat": es_ganga_matematica
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

async def procesar_rutas():
    resultados = []
    rutas = []
    
    try:
        import requests
        from io import StringIO
        
        url_csv = os.getenv("GOOGLE_SHEETS_URL", "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAIoIzvnw6Ph-llHN452AtSDRH2oc1CA3LS4MtfbcDQmBzXxbckBFiCk8DyDlIZHXSYR1ghETYUW_L/pub?output=csv")
        print(f"🌐 Descargando rutas desde Google Sheets...")
        
        response = requests.get(url_csv, allow_redirects=True)
        response.raise_for_status()
        
        texto_csv = response.text
        f = StringIO(texto_csv)
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        print(f"DEBUG - Headers encontrados: {headers}")
        
        for row in reader:
            origen = row.get("ORIGEN", row.get("Origen", "")).strip()
            destino = row.get("DESTINO", row.get("Destino", "")).strip()
            mes_inicio_raw = row.get("MES DE INICIO", row.get("Mes_Inicio", "")).strip()
            mes_fin_raw = row.get("MES DE FIN", row.get("Mes_Fin", "")).strip()
            
            str_alerta = row.get("PRECIO ALERTA", row.get("Precio_Alerta", "0")).strip()
            precio_alerta = int(str_alerta) if str_alerta.isdigit() else 0
            
            dias_paq_raw = row.get("Dias_del_Paquete", "").strip()
            dias_paquete = int(dias_paq_raw) if dias_paq_raw.isdigit() else None
            
            if origen and destino and mes_inicio_raw and mes_fin_raw:
                f_ini = format_date(mes_inicio_raw, "01")
                f_fin = format_date(mes_fin_raw, "28")
                if f_ini and f_fin:
                    rutas.append({
                        "origen": origen,
                        "destino": destino,
                        "inicio": f_ini, 
                        "fin": f_fin,
                        "alerta": precio_alerta,
                        "dias_paquete": dias_paquete
                    })
    except Exception as e:
        print(f"❌ Error leyendo Google Sheets: {e}")
        return []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Contexto persistente evita recargas innecesarias
        context = await browser.new_context()
        page = await context.new_page()
        
        for r in rutas:
            res = await extrar_mejor_precio(page, r["origen"], r["destino"], r["inicio"], r["fin"], r["dias_paquete"])
            if res:
                resultados.append({
                    "ruta": f"{r['origen']} ➡️ {r['destino']}",
                    "precio": res['precio'],
                    "detalle": res['detalle'],
                    "url": res['url'],
                    "alerta_manual": r['alerta'],
                    "mediana": res['mediana'],
                    "es_ganga_mat": res['es_ganga_mat']
                })
                print(f"  ✅ Encontrado: ${res['precio']} (Mediana: ${res['mediana']}) - {res['detalle'][:40]}")
            else:
                print(f"  ❌ Sin fechas encontradas.")
                
        await browser.close()
        
    return resultados

if __name__ == "__main__":
    asyncio.run(procesar_rutas())
