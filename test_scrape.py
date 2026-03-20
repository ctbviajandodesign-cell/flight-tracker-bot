import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Cargando Google Flights...")
        await page.goto("https://www.google.com/travel/flights?hl=es-419")
        await page.wait_for_timeout(3000)
        
        print("Llenando Origen...")
        origen_input = page.get_by_role("combobox", name="¿Desde dónde? ")
        await origen_input.clear()
        await origen_input.fill("GYE")
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Enter")
        
        print("Llenando Destino...")
        destino_input = page.get_by_role("combobox", name="¿A dónde quieres ir? ")
        await destino_input.fill("PTY")
        await page.wait_for_timeout(1000)
        await page.keyboard.press("Enter")
        
        print("Haciendo clic en la fecha de Salida...")
        salida_input = page.get_by_role("textbox", name="Salida")
        if await salida_input.count() > 0:
            await salida_input.first.click()
        else:
            print("No se encontró el input de salida por role, probando placeholder...")
            await page.get_by_placeholder("Salida").first.click()
            
        await page.wait_for_timeout(3000)
        
        print("Tomando screenshot del calendario...")
        await page.screenshot(path="calendario.png", full_page=True)
        
        html = await page.content()
        with open("calendario_dom.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Todo guardado.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
