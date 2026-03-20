import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

async def test_round_trip():
    origen = "GYE"
    destino = "PTY"
    # Supongamos que queremos un viaje de 6 dias. 
    # El truco es que en la URL le pasamos una fecha de IDA y una de REGRESO separadas por 6 días.
    # Google Flights automáticamente anclará la duración a 6 días en el calendario
    url = "https://www.google.com/travel/flights?q=Flights%20to%20PTY%20from%20GYE%20on%202026-06-01%20through%202026-06-07&hl=es-419"
    
    print(f"✈️ Prueba Round Trip: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Guardaremos un screenshot para ver si el DOM cargó el viaje redondo
        await page.screenshot(path="round_trip_initial.png")
        
        # Abriremos el calendario de IDA
        try:
            await page.get_by_placeholder("Salida").first.click()
            await page.wait_for_timeout(3000)
            await page.screenshot(path="round_trip_calendar.png")
            print("✅ Calendario abierto con éxito.")
        except Exception as e:
            print(f"❌ Error al abrir el calendario: {e}")
            
        # Analizaremos si los precios en el calendario dicen "viaje redondo" o cambian
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        elementos = soup.find_all(lambda tag: tag.has_attr('aria-label'))
        precios = []
        for e in elementos:
            label = e.get('aria-label', '').lower()
            if 'dólar' in label or 'usd' in label or 'us$' in label:
                match = re.search(r'((?:us\$|\$)?\s*\d+(?:,\d+)?(?:\.\d+)?)\s*(?:dólares|dolares|dólar|usd)?', label)
                if match:
                    precios.append(label)
                    
        print(f"Encontrados {len(precios)} precios en el calendario. Primeros 5:")
        for p in precios[:5]:
            print(p)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_round_trip())
