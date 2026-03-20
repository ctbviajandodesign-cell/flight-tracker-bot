import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import re

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://www.google.com/travel/flights?q=Flights%20to%20PTY%20from%20GYE%20on%202026-06-01%20through%202026-07-31&hl=es-419"
        print("Cargando URL directa con fechas...")
        await page.goto(url)
        await page.wait_for_timeout(4000)
        
        origen = await page.get_by_role("combobox", name="¿Desde dónde? ").input_value()
        destino = await page.get_by_role("combobox", name="¿A dónde quieres ir? ").input_value()
        salida = await page.get_by_placeholder("Salida").first.input_value()
        print(f"Buscando de: {origen} a {destino} ({salida})")
        
        print("\nAbriendo calendario...")
        await page.get_by_placeholder("Salida").first.click()
        await page.wait_for_timeout(3000)
        
        from bs4 import BeautifulSoup
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        elements = soup.find_all(lambda tag: tag.has_attr('aria-label') and tag.get('role') == 'button' and tag.text.strip().isdigit())
        
        if not elements:
            # Intentar con gridcell
            elements = soup.find_all(lambda tag: tag.has_attr('aria-label') and tag.get('role') == 'gridcell')
            
        precios = []
        for e in elements:
            label = e.get('aria-label')
            if label and ('dólar' in label.lower() or 'usd' in label.lower() or 'dolar' in label.lower()):
                print(f"Encontrado: {label}")
                # Extraer precio numérico
                match = re.search(r'(\d+)\s*dólar', label.lower())
                if match:
                    precios.append(int(match.group(1)))
                    
        if precios:
            print(f"\n✅ Total días con precios: {len(precios)}")
            print(f"💸 Precio más barato encontrado: ${min(precios)}")
        else:
            print("❌ No se encontraron precios en el calendario.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
