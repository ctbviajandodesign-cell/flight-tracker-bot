 1 import asyncio
    2 import os
    3 import httpx
    4 from datetime import datetime
    5 from dotenv import load_dotenv
    6 from notifier import enviar_notificacion_telegram
    7 from scraper_vuelos import procesar_rutas
    8
    9 load_dotenv()
   10
   11 async def guardar_en_supabase(resultados):
   12     url = os.getenv("SUPABASE_URL")
   13     key = os.getenv("SUPABASE_KEY")
   14     if not url or not key: return
   15     headers = {"apikey": key, "Authorization": f"Bearer {key}",
      "Content-Type": "application/json"}
   16     datos = []
   17     for r in resultados:
   18         datos.append({
   19             "ruta": r['ruta'], "precio": r['precio'],
   20             "es_ganga": (r['precio'] <= r['alerta_manual'] or
      r['es_ganga_mat']),
   21             "tipo_vuelo": r['mejores'][0]['tipo'] if r['mejores'] else
      "UNK"
   22         })
   23     try:
   24         async with httpx.AsyncClient(timeout=15.0) as client:
   25             await client.post(f"{url}/rest/v1/vuelos_historial",
      json=datos, headers=headers)
   26             print("✅ Supabase actualizado.")
   27     except:
   28         print("⚠️ Error base de datos.")
   29
   30 async def main():
   31     print("🚀 Iniciando rastreo...")
   32     hora_utc = datetime.utcnow().hour
   33     es_reporte_diario = (hora_utc in [12, 19, 1])
   34     
   35     try:
   36         resultados = await asyncio.wait_for(procesar_rutas(),
      timeout=1200)
   37     except:
   38         print("❌ Tiempo excedido.")
   39         return
   40
   41     if not resultados:
   42         print("Sin resultados.")
   43         return
   44
   45     await guardar_en_supabase(resultados)
   46     
   47     vuelos_ganga = [r for r in resultados if r['precio'] <=
      r['alerta_manual'] or r['es_ganga_mat']]
   48     if vuelos_ganga:
   49         titulo = "🚨 <b>¡GANGAS DETECTADAS!</b>\n\n"
   50         vuelos_a_mostrar = resultados if es_reporte_diario else
      vuelos_ganga
   51     elif es_reporte_diario:
   52         titulo = "🌅 <b>REPORTE DIARIO</b>\n\n"
   53         vuelos_a_mostrar = resultados
   54     else: return
   55
   56     mensaje = titulo
   57     for r in vuelos_a_mostrar:
   58         # Limpieza de caracteres que rompen HTML de Telegram
   59         ruta_limpia = r['ruta'].replace("<", "&lt;").replace(">", "&gt;")
   60         icono = "🚨" if (r['precio'] <= r['alerta_manual'] or
      r['es_ganga_mat']) else "📍"
   61         
   62         bloque = f"{icono} <b>{ruta_limpia}</b>\n"
   63         for i, opc in enumerate(r['mejores']):
   64             medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
   65             tipo = "🚀" if opc['tipo'] == "DIR" else "🛬"
   66             bloque += f"   {medal} ${opc['precio']} - {tipo}\n"
   67         
   68         url_l = r['url'].replace("&", "&amp;").replace("<",
      "&lt;").replace(">", "&gt;")
   69         bloque += f"   📊 Promedio: ${r['mediana']}\n"
   70         bloque += f"   🔗 <a href='{url_l}'>Ver en Google Flights</a>\n\n"
   71         mensaje += bloque
   72     
   73     enviar_notificacion_telegram(mensaje)
   74
   75 if __name__ == "__main__":
   76     asyncio.run(main())
