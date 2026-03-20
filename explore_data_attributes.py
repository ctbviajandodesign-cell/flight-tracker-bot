import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.google.com/travel/flights?q=Flights%20to%20PTY%20from%20GYE%20on%202026-06-01%20through%202026-07-31&hl=es-419"
        await page.goto(url)
        await page.wait_for_timeout(4000)
        
        await page.get_by_placeholder("Salida").first.click()
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        elements = soup.find_all(lambda tag: tag.has_attr('aria-label') and tag.get('role') == 'button')
        if not elements:
            elements = soup.find_all(lambda tag: tag.has_attr('aria-label'))
            
        count = 0
        for e in elements:
            label = e.get('aria-label', '').lower()
            if 'dólar' in label or 'usd' in label:
                print(f"\n--- ELEMENTO {count} ---")
                print(f"Item attrs: {e.attrs}")
                if e.parent:
                    print(f"Parent attrs: {e.parent.attrs}")
                    if e.parent.parent:
                        print(f"Grandparent attrs: {e.parent.parent.attrs}")
                count += 1
                if count > 2: break
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
