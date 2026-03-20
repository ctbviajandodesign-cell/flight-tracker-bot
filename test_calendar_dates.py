import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Cargando URL directa con fechas...")
        url = "https://www.google.com/travel/flights?q=Flights%20to%20PTY%20from%20GYE%20on%202026-06-01%20through%202026-07-31&hl=es-419"
        await page.goto(url)
        await page.wait_for_timeout(4000)
        
        await page.get_by_placeholder("Salida").first.click()
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar gridcells
        elements = soup.find_all(lambda tag: tag.has_attr('aria-label'))
        
        count = 0
        for e in elements:
            label = e.get('aria-label')
            if label and 'dólar' in label.lower():
                parent = e.parent
                if parent:
                    print(f"PARENT TEXT: {parent.get_text(strip=True, separator=' ')}")
                count += 1
                if count > 5: break
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
