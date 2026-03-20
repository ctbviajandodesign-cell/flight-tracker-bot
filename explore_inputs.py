import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Cargando Google Flights...")
        await page.goto("https://www.google.com/travel/flights?hl=es-419")
        await page.wait_for_timeout(4000)
        
        print("\n--- COMBOBOXES ---")
        locators = await page.get_by_role("combobox").all()
        for i, loc in enumerate(locators):
            try:
                name = await loc.get_attribute("aria-label")
                print(f"Combobox {i}: label='{name}'")
            except Exception as e:
                print(f"Combobox {i}: {e}")
                
        print("\n--- INPUTS ---")
        inputs = await page.locator("input").all()
        for i, loc in enumerate(inputs):
            try:
                name = await loc.get_attribute("aria-label")
                val = await loc.input_value()
                print(f"Input {i}: label='{name}' value='{val}'")
            except Exception as e:
                pass
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
