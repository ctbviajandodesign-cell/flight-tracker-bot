import asyncio
from datetime import datetime
from dotenv import load_dotenv
from notifier import enviar_notificacion_telegram
from scraper_vuelos import procesar_rutas

load_dotenv()

async def main():
    print("🚀 Iniciando rastreo inteligente...")
    hora_utc = datetime.utcnow().hour
    # Reportes: 8 AM EC (13 UTC), 3 PM EC (20 UTC), 9 PM EC (02 UTC)
    es_reporte_diario = (hora_utc in [12, 13, 19, 20, 1, 2])
    
    resultados = await procesar_rutas()
    if not resultados: return
        
    vuelos_ganga = [r for r in resultados if r['precio'] <= r['alerta_manual'] or r['es_ganga_mat']]
    
    if vuelos_ganga:
        titulo = "🚨 <b>PRECIOS MÁS BAJOS AHORA!</b> 🚨\n"
        frase_intro = "<i>¡Oportunidades únicas detectadas por el radar!</i>\n\n"
        vuelos_a_mostrar = resultados if es_reporte_diario else vuelos_ganga
    elif es_reporte_diario:
        titulo = "🌅 <b>REPORTE DIARIO DE VUELOS</b>\n"
        frase_intro = "<i>Resumen general de tus rutas (Precios normales):</i>\n\n"
        vuelos_a_mostrar = resultados
    else:
        print(f"🤫 Modo silencioso a las {hora_utc} UTC.")
        return

    mensaje_telegram = titulo + frase_intro

    for r in vuelos_a_mostrar:
        es_ganga = (r['precio'] <= r['alerta_manual'] or r['es_ganga_mat'])
        icono = "🚨" if es_ganga else "📍"
        mensaje_telegram += f"{icono} <b>{r['ruta']}</b>\n"
        
        for i, opc in enumerate(r['mejores']):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            # DETECCIÓN DE EMOJI
            if opc['tipo'] == "DIR":
                info_vuelo = "(DIR: 🚀)"
            elif opc['tipo'] == "ESC":
                info_vuelo = "(ESC: 🛬)"
            else:
                info_vuelo = "" # No mostramos nada si no hay info segura
                
            mensaje_telegram += f"   {medal} <b>${opc['precio']} USD</b> - {opc['detalle']} {info_vuelo}\n"
        
        mensaje_telegram += f"   📊 Promedio Normal: ${r['mediana']} USD\n"
        mensaje_telegram += f"   🔗 <a href='{r['url']}'>Ver en Google Flights</a>\n\n"
        
    enviar_notificacion_telegram(mensaje_telegram)

if __name__ == "__main__":
    asyncio.run(main())
