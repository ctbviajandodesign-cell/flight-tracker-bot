import asyncio
from playwright.async_api import async_playwright
import re

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Cargando Google Flights...")
        await page.goto("https://www.google.com/travel/flights?hl=es-419")
        await page.wait_for_timeout(3000)
        
        print("Llenando Origen y Destino...")
        origen_input = page.get_by_role("combobox", name="¿Desde dónde? ")
        await origen_input.clear()
        await origen_input.fill("GYE")
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Enter")
        
        destino_input = page.get_by_role("combobox", name="¿A dónde quieres ir? ")
        await destino_input.fill("PTY")
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Enter")
        
        print("Abriendo calendario...")
        salida_input = page.get_by_role("textbox", name="Salida")
        if await salida_input.count() > 0:
            await salida_input.first.click()
        else:
            await page.get_by_placeholder("Salida").first.click()
            
        await page.wait_for_timeout(3000)
        
        print("\n--- BUSCANDO PRECIOS EN EL CALENDARIO ---\n")
        # El calendario suele estar en 'div' con rol 'button' o texto directo.
        # Vamos a buscar todos los elementos que contengan texto como '$' o 'USD' 
        # o iterar los div que tengan aria-label.
        
        from bs4 import BeautifulSoup
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscamos divs que tengan atributos aria-label
        elements = soup.find_all(lambda tag: tag.has_attr('aria-label') and tag.get('role') == 'gridcell' or tag.get('role') == 'button')
        
        count = 0
        for e in elements:
            label = e.get('aria-label')
            if label and ('dólar' in label.lower() or 'dolar' in label.lower() or 'usd' in label.lower() or '$' in label):
                print(f"Día con precio -> {label}")
                count += 1
                if count > 10: # Mostrar solo los primeros 10
                    break
                    
        print(f"Total encontrados: {count}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
