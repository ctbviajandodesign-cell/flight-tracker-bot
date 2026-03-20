import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navegando a Google Flights...")
        # Forzamos idioma y región a español latinoamericano para un HTML constante
        await page.goto("https://www.google.com/travel/flights?hl=es-419")
        # Esperamos a que cargue el JavaScript
        await page.wait_for_timeout(5000)
        
        html = await page.content()
        with open("flights_dom.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("DOM guardado en flights_dom.html")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
