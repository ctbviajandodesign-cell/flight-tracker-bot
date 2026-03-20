import asyncio
from dotenv import load_dotenv
from notifier import enviar_notificacion_telegram
from scraper_vuelos import procesar_rutas

# Cargar variables de entorno desde el archivo .env
load_dotenv()

async def main():
    print("🚀 Iniciando rastreo de vuelos programados...")
    
    # 1. Scraping visual por todas las rutas
    resultados = await procesar_rutas()
    
    # 2. Formatear resultados
    if not resultados:
        print("No se obtuvieron resultados de ninguna ruta.")
        return
        
    mensaje_telegram = f"✈️ <b>Reporte de Vuelos Baratos</b>\n"
    mensaje_telegram += f"🔍 <i>Buscando el mejor precio en todo el intervalo...</i>\n\n"
    
    for r in resultados:
        mensaje_telegram += f"📍 <b>{r['ruta']}</b>\n"
        mensaje_telegram += f"   💵 <b>${r['precio']} USD</b> - {r['detalle']}\n"
        mensaje_telegram += f"   🔗 <a href='{r['url']}'>Ver calendario en Google Flights</a>\n\n"
        
    print("\n📩 Enviando resultados a Telegram...")
    # 3. Enviar al notificador
    enviar_notificacion_telegram(mensaje_telegram)

if __name__ == "__main__":
    asyncio.run(main())
