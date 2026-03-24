import asyncio
from datetime import datetime
from dotenv import load_dotenv
from notifier import enviar_notificacion_telegram
from scraper_vuelos import procesar_rutas

load_dotenv()

async def main():
    print("🚀 Iniciando rastreo de vuelos programados...")
    
    # Hora UTC actual (8 AM EC = 13:00 UTC, 3 PM EC = 20:00 UTC, 8 PM EC = 01:00 UTC)
    hora_utc = datetime.utcnow().hour
    # Ventanas de reporte diario (Ecuador: 8 AM, 3 PM, 8 PM)
    # 12-13 UTC (8 AM), 19-20 UTC (3 PM), 00-01 UTC (8 PM)
    es_reporte_diario = (hora_utc in [12, 13, 19, 20, 0, 1])
    
    resultados = await procesar_rutas()
    if not resultados:
        print("No se obtuvieron resultados.")
        return
        
    vuelos_ganga = [r for r in resultados if r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']]
    
    # DECISIÓN DE TÍTULO Y CONTENIDO:
    if vuelos_ganga:
        # Prioridad absoluta a la Alerta de Precio si existen gangas
        titulo = "🚨 <b>PRECIOS MÁS BAJOS AHORA!</b> 🚨\n"
        frase_intro = "<i>Precios más bajos detectados en este momento:</i>\n\n"
        vuelos_a_mostrar = resultados if es_reporte_diario else vuelos_ganga
    elif es_reporte_diario:
        titulo = "🌅 <b>REPORTE DIARIO DE VUELOS</b>\n"
        frase_intro = "<i>Resumen general de todas tus rutas de hoy:</i>\n\n"
        vuelos_a_mostrar = resultados
    else:
        # Modo silencioso: no hay gangas ni es hora de reporte
        print(f"🤫 Modo silencioso a las {hora_utc}:00 UTC. No hay alertas críticas.")
        return

    mensaje_telegram = titulo + frase_intro

    for r in vuelos_a_mostrar:
        es_ganga = (r['precio'] <= r['alerta_manual'] or r['es_ganga_mat'])
        icono = "🚨" if es_ganga else "📍"
        mensaje_telegram += f"{icono} <b>{r['ruta']}</b>\n"
        
        for i, opc in enumerate(r['mejores']):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            # Info de DIR: 🚀 o ESC: 🛬 junto a la fecha (ya formateada como DD/MM/YY o N/F)
            tipo = "DIR: 🚀" if opc['tipo'] == "DIR" else "ESC: 🛬"
            mensaje_telegram += f"   {medal} <b>${opc['precio']} USD</b> - {opc['detalle']} ({tipo})\n"
        
        mensaje_telegram += f"   📊 Promedio Normal: ${r['mediana']} USD\n"
        mensaje_telegram += f"   🔗 <a href='{r['url']}'>Ver en Google Flights</a>\n\n"
        
    print(f"📩 Enviando mensaje a Telegram: {titulo.strip()}")
    enviar_notificacion_telegram(mensaje_telegram)

if __name__ == "__main__":
    asyncio.run(main())
