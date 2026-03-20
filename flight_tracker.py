import asyncio
from datetime import datetime
from dotenv import load_dotenv
from notifier import enviar_notificacion_telegram
from scraper_vuelos import procesar_rutas

# Cargar variables de entorno desde el archivo .env
load_dotenv()

async def main():
    print("🚀 Iniciando rastreo de vuelos programados...")
    
    # Evaluar la hora actual en la máquina de GitHub (UTC)
    hora_actual_utc = datetime.utcnow().hour
    # Queremos reportes generales completos a las 8:00 AM (13 UTC) y 2:00 PM (19 UTC).
    # Las demás ejecuciones del día serán en modo "Silencioso" cazando gangas.
    es_reporte_diario = (hora_actual_utc in [13, 14, 19, 20])
    
    # 1. Scraping visual por todas las rutas
    resultados = await procesar_rutas()
    
    if not resultados:
        print("No se obtuvieron resultados de ninguna ruta.")
        return
        
    # Un vuelo es ganga si baja de tu Precio de Alerta (manual) O si es un 20% más barato que el promedio del mes entero
    vuelos_ganga = [r for r in resultados if r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']]
    
    if es_reporte_diario:
        mensaje_telegram = f"🌅 <b>REPORTE DIARIO DE VUELOS</b>\n"
        mensaje_telegram += f"<i>Resumen general de todas tus rutas de hoy:</i>\n\n"
        for r in resultados:
            es_ganga = (r['precio'] <= r['alerta_manual'] or r['es_ganga_mat'])
            if es_ganga:
                mensaje_telegram += f"🚨 <b>¡GANGA! {r['ruta']}</b>\n"
            else:
                mensaje_telegram += f"📍 <b>{r['ruta']}</b>\n"
            mensaje_telegram += f"   💵 <b>${r['precio']} USD</b> (Promedio Normal: ${r['mediana']} USD)\n"
            mensaje_telegram += f"   📅 {r['detalle']}\n"
            mensaje_telegram += f"   🔗 <a href='{r['url']}'>Ver Google Flights</a>\n\n"
            
        print("\n📩 Enviando Reporte Diario Total a Telegram...")
        enviar_notificacion_telegram(mensaje_telegram)
        
    else:
        # Modo Cazador de Gangas Silencioso
        if vuelos_ganga:
            mensaje_telegram = f"🚨 <b>¡ALERTA DE PRECIOS BAJOS!</b> 🚨\n"
            mensaje_telegram += f"<i>El radar detectó un desplome matemático en este vuelo ahora mismo:</i>\n\n"
            for r in vuelos_ganga:
                mensaje_telegram += f"📍 <b>{r['ruta']}</b>\n"
                mensaje_telegram += f"   🔥 <b>${r['precio']} USD</b> (Normalmente cuesta: ${r['mediana']} USD)\n"
                mensaje_telegram += f"   📅 {r['detalle']}\n"
                mensaje_telegram += f"   🔗 <a href='{r['url']}'>¡Reserva rápido aquí!</a>\n\n"
                
            print("\n📩 ¡Enviando ALERTA DE GANGA a Telegram!")
            enviar_notificacion_telegram(mensaje_telegram)
        else:
            print(f"\n🤫 Monitoreo silencioso a las {hora_actual_utc}:00 UTC.")
            print("Ningún vuelo presentó un descuento agresivo hoy. Se queda callado.")

if __name__ == "__main__":
    asyncio.run(main())
