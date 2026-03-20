import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Cargando URL directa...")
        # Pasamos la consulta en texto libre en la URL
        await page.goto("https://www.google.com/travel/flights?q=Flights%20to%20PTY%20from%20GYE%20on%202026-06-01%20through%202026-07-31&hl=es-419")
        await page.wait_for_timeout(5000)
        
        origen = await page.get_by_role("combobox", name="¿Desde dónde? ").input_value()
        destino = await page.get_by_role("combobox", name="¿A dónde quieres ir? ").input_value()
        print(f"Origen cargado: {origen}")
        print(f"Destino cargado: {destino}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
