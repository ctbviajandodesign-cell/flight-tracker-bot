'use client';

import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const IATA_MAP: Record = {
  GYE: "Guayaquil", UIO: "Quito", CUE: "Cuenca",
  BOG: "Bogotá", MDE: "Medellín", PTY: "Panamá",
  MIA: "Miami", NYC: "Nueva York", MAD: "Madrid",
  BCN: "Barcelona", LIM: "Lima", SCL: "Santiago",
  EZE: "Buenos Aires", MEX: "Ciudad de México",
  CUN: "Cancún", MCO: "Orlando", LAX: "Los Ángeles",
  GIG: "Río de Janeiro", CUR: "Curazao", PUJ: "Punta Cana",
  PEI: "Pereira", IST: "Estambul", ADZ: "San Andrés", CTG: "Cartagena",
};

const getCityName = (code: string) => IATA_MAP[code.toUpperCase()] || "Internacional";

type PrecioData = {
  id: number;
  ruta: string;
  precio: number;
  mediana: number;
  fecha_vuelo: string;
  precio_alerta: number;
  es_ganga: boolean;
  tipo_vuelo: string;
  fecha: string;
};

type HistorialEntry = { fecha: string; precio: number; es_ganga: boolean };

export default function Dashboard() {
  const [rutas, setRutas] = useState([]);
  const [precios, setPrecios] = useState>({});
  const [historial, setHistorial] = useState>({});
  const [cargando, setCargando] = useState(true);
  const [errorSync, setErrorSync] = useState('');
  const [filtro, setFiltro] = useState('');
  const [vistaActiva, setVistaActiva] = useState<'tarjetas' | 'comparativa'>('tarjetas');
  const [rutaDetalle, setRutaDetalle] = useState(null);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [nuevoVuelo, setNuevoVuelo] = useState({ origen: '', destino: '', ida: '', vuelta: '', alerta: '', dias_paquete: '' });
  const [tipoFecha, setTipoFecha] = useState<'mes' | 'exacta'>('mes');
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  const cargarRutas = async () => {
    try {
      setCargando(true);
      const [resRutas, resPrecios] = await Promise.all([
        fetch('/api/flights'),
        fetch('/api/prices'),
      ]);
      const dataRutas = await resRutas.json();
      const dataPrecios = await resPrecios.json();

      if (dataRutas.success) setRutas(dataRutas.flights);
      if (dataPrecios.success) {
        const mapaPrecios: Record = {};
        for (const p of dataPrecios.precios) {
          // Normalizar la clave de ruta
          const clave = p.ruta.replace(' ➡️ ', ' -> ').replace('➡️', '->').trim();
          mapaPrecios[clave] = p;
        }
        setPrecios(mapaPrecios);
        setHistorial(dataPrecios.historial || {});
      }
      setErrorSync('');
    } catch (e: any) {
      setErrorSync(e.message);
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => { setMounted(true); cargarRutas(); }, []);

  const getPrecioRuta = (origen: string, destino: string): PrecioData | null => {
    const clave1 = `${origen} -> ${destino}`;
    const clave2 = `${origen} ➡️ ${destino}`;
    return precios[clave1] || precios[clave2] || null;
  };

  const eliminarRuta = async (id: number) => {
    try {
      setRutas(rutas.filter(r => r.id !== id));
      await fetch(`/api/flights?id=${id}`, { method: 'DELETE' });
      cargarRutas();
    } catch (e: any) {
      setErrorSync('Error eliminando: ' + e.message);
      cargarRutas();
    }
  };

  const agregarRuta = async (e: React.FormEvent) => {
    e.preventDefault();
    const tempId = Date.now();
    const nuevaRuta = { id: tempId, ...nuevoVuelo, alerta: nuevoVuelo.alerta ? Number(nuevoVuelo.alerta) : '', dias_paquete: nuevoVuelo.dias_paquete ? Number(nuevoVuelo.dias_paquete) : '' };
    setRutas([...rutas, nuevaRuta]);
    setMostrarFormulario(false);
    setNuevoVuelo({ origen: '', destino: '', ida: '', vuelta: '', alerta: '', dias_paquete: '' });
    try {
      await fetch('/api/flights', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(nuevaRuta) });
      cargarRutas();
    } catch (e: any) {
      setErrorSync('Error agregando: ' + e.message);
      cargarRutas();
    }
  };

  const parseDateString = (dateStr: string, tipo: 'mes' | 'exacta') => {
    if (!dateStr) return null;
    const parts = dateStr.split('-');
    if (parts.length === 2) return new Date(Number(parts[0]), Number(parts[1]) - 1, 1);
    if (parts.length === 3) return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return null;
  };

  const formatDateObj = (date: Date | null, tipo: 'mes' | 'exacta') => {
    if (!date) return '';
    return tipo === 'mes' ? format(date, 'yyyy-MM') : format(date, 'yyyy-MM-dd');
  };

  // Agrupar rutas por destino para vista comparativa GYE vs UIO
  const rutasPorDestino = rutas.reduce((acc: Record, ruta) => {
    if (!acc[ruta.destino]) acc[ruta.destino] = [];
    acc[ruta.destino].push(ruta);
    return acc;
  }, {});

  const rutasFiltradas = rutas.filter(ruta => {
    const term = filtro.toLowerCase();
    return ruta.origen.toLowerCase().includes(term) ||
      ruta.destino.toLowerCase().includes(term) ||
      getCityName(ruta.origen).toLowerCase().includes(term) ||
      getCityName(ruta.destino).toLowerCase().includes(term);
  });

  const totalGangas = rutas.filter(r => getPrecioRuta(r.origen, r.destino)?.es_ganga).length;

  return (
    

      

      


      


        {/* HEADER */}
        

          

            

            <h1 className="...">Monitor de Vuelos CTB</h1>
            

            


              {rutas.length} rutas monitoreadas
              {totalGangas > 0 && 🚨 {totalGangas} gangas activas}
            


            {errorSync && 

{errorSync}

}
          

          

            {mounted && (
              

                 setTheme('light')} className={`p-2 rounded-lg flex items-center justify-center transition ${theme === 'light' ? 'bg-surface text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
                  light_mode
                
                 setTheme('dark')} className={`p-2 rounded-lg flex items-center justify-center transition ${theme === 'dark' ? 'bg-surface text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
                  dark_mode
                
                 setTheme('system')} className={`p-2 rounded-lg flex items-center justify-center transition ${theme === 'system' ? 'bg-surface text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
                  desktop_windows
                
              

            )}
             setMostrarFormulario(!mostrarFormulario)}
              className="bg-primary text-surface-container-lowest px-6 py-3 rounded-xl font-bold shadow-[0_0_20px_rgba(143,245,255,0.2)] hover:brightness-110 flex items-center gap-2 transition whitespace-nowrap">
              {mostrarFormulario ? "close" : "add"}
              {mostrarFormulario ? "Cancelar" : "Agregar Ruta"}
            
          

        


        {/* TABS VISTA */}
        

           setVistaActiva('tarjetas')}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition ${vistaActiva === 'tarjetas' ? 'bg-primary text-on-primary' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'}`}>
            📋 Todas las rutas
          
           setVistaActiva('comparativa')}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition ${vistaActiva === 'comparativa' ? 'bg-primary text-on-primary' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'}`}>
            ⚖️ GYE vs UIO por destino
          
          
            refresh Actualizar
          
        


        {/* BUSCADOR */}
        {!mostrarFormulario && vistaActiva === 'tarjetas' && rutas.length > 0 && (
          

            search
             setFiltro(e.target.value)}
              className="w-full bg-surface-container-low text-on-surface border border-outline-variant/20 rounded-full py-3 pl-12 pr-4 outline-none focus:border-primary shadow-sm transition-all text-sm font-medium" />
            {filtro &&  setFiltro('')} className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant">
              close
            }
          

        )}

        {/* FORMULARIO AGREGAR */}
        {mostrarFormulario && (
          

            

              flight_takeoffNueva ruta
            

            

              {[
                { label: 'Origen', key: 'origen', placeholder: 'GYE', upper: true },
                { label: 'Destino', key: 'destino', placeholder: 'MAD', upper: true },
              ].map(f => (
                

                  {f.label}
                   setNuevoVuelo({ ...nuevoVuelo, [f.key]: f.upper ? e.target.value.toUpperCase() : e.target.value })}
                    maxLength={3} placeholder={f.placeholder}
                    className="bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary uppercase h-[46px]" />
                

              ))}
              {(['ida', 'vuelta'] as const).map(k => (
                

                  {k === 'ida' ? 'Mes Ida' : 'Mes Vuelta'}
                   setNuevoVuelo({ ...nuevoVuelo, [k]: formatDateObj(d, tipoFecha) })}
                    dateFormat="MM/yyyy" showMonthYearPicker locale={es} wrapperClassName="w-full"
                    placeholderText="Mes / Año"
                    className="w-full bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary h-[46px]" />
                

              ))}
              

                Días Viaje
                 setNuevoVuelo({ ...nuevoVuelo, dias_paquete: e.target.value })}
                  type="number" placeholder="Ej: 6"
                  className="bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary h-[46px]" />
              

              

                Alerta $
                 setNuevoVuelo({ ...nuevoVuelo, alerta: e.target.value })}
                  type="number" placeholder="Opcional"
                  className="bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary h-[46px]" />
              

            

            

              
                saveGuardar Ruta
              
            

          

        )}

        {/* LOADING */}
        {cargando ? (
          

            cloud_sync
            

Cargando precios en tiempo real...


          


        /* VISTA COMPARATIVA GYE vs UIO */
        ) : vistaActiva === 'comparativa' ? (
          

            {Object.entries(rutasPorDestino).map(([destino, rutasDestino]) => {
              const rutaGYE = rutasDestino.find(r => r.origen === 'GYE');
              const rutaUIO = rutasDestino.find(r => r.origen === 'UIO');
              const precioGYE = rutaGYE ? getPrecioRuta('GYE', destino) : null;
              const precioUIO = rutaUIO ? getPrecioRuta('UIO', destino) : null;
              if (!rutaGYE && !rutaUIO) return null;
              const masBarato = precioGYE && precioUIO ? (precioGYE.precio <= precioUIO.precio ? 'GYE' : 'UIO') : null;
              return (
                

                  

                    flight_land
                    
{destino} — {getCityName(destino)}

                    {precioGYE?.es_ganga || precioUIO?.es_ganga ? 🚨 GANGA : null}
                  

                  

                    {[{ origen: 'GYE', precio: precioGYE }, { origen: 'UIO', precio: precioUIO }].map(({ origen, precio }) => (
                      

                        

{origen} → {destino}


                        {precio ? (
                          <>
                            


                              ${precio.precio} USD
                            


                            {precio.fecha_vuelo && precio.fecha_vuelo !== 'N/D' && (
                              

📅 {precio.fecha_vuelo}


                            )}
                            {precio.mediana > 0 && 

📊 Prom: ${precio.mediana}

}
                            {masBarato === origen && 

✅ Más barato

}
                          
                        ) : 

Sin datos aún

}
                      

                    ))}
                  

                

              );
            })}
          


        /* VISTA TARJETAS */
        ) : rutasFiltradas.length === 0 ? (
          

            search_off
            

No se encontraron rutas.


          

        ) : (
          

            {rutasFiltradas.map(ruta => {
              const precio = getPrecioRuta(ruta.origen, ruta.destino);
              const esGanga = precio?.es_ganga || false;
              const historialRuta = historial[`${ruta.origen} -> ${ruta.destino}`] || historial[`${ruta.origen} ➡️ ${ruta.destino}`] || [];
              return (
                
 setRutaDetalle(rutaDetalle === `${ruta.origen}-${ruta.destino}` ? null : `${ruta.origen}-${ruta.destino}`)}>

                  {esGanga && (
                    

                      🚨 GANGA
                    

                  )}

                   { e.stopPropagation(); eliminarRuta(ruta.id); }}
                    className="absolute top-6 right-6 text-outline-variant hover:text-error transition opacity-0 group-hover:opacity-100">
                    delete
                  

                  

                    

                      flight_takeoff
                    

                    

                      

                        

                          {ruta.origen}
                          {getCityName(ruta.origen)}
                        

                        →
                        

                          {ruta.destino}
                          {getCityName(ruta.destino)}
                        

                      

                    

                  


                  {/* PRECIO ACTUAL */}
                  {precio ? (
                    

                      

                        

                          

Mejor precio actual


                          


                            ${precio.precio} USD
                          


                          {precio.fecha_vuelo && precio.fecha_vuelo !== 'N/D' && (
                            

📅 Salida: {precio.fecha_vuelo}


                          )}
                        

                        

                          {precio.mediana > 0 && 

📊 Prom: ${precio.mediana}

}
                          {precio.precio_alerta > 0 && 

🎯 Alerta: ${precio.precio_alerta}

}
                          


                            {new Date(precio.fecha).toLocaleString('es-EC', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                          


                        

                      

                    

                  ) : (
                    

                      

⏳ Esperando primera consulta del bot...


                    

                  )}

                  {/* MINI HISTORIAL */}
                  {rutaDetalle === `${ruta.origen}-${ruta.destino}` && historialRuta.length > 1 && (
                    
 e.stopPropagation()}>
                      

Historial de precios


                      

                        {historialRuta.slice(0, 20).reverse().map((h, i) => {
                          const maxP = Math.max(...historialRuta.map(x => x.precio));
                          const minP = Math.min(...historialRuta.map(x => x.precio));
                          const rango = maxP - minP || 1;
                          const altura = Math.max(10, Math.round(((h.precio - minP) / rango) * 48) + 8);
                          return (
                            

                              

                            

                          );
                        })}
                      

                      

                        Más antiguo
                        Más reciente
                      

                      


                        Min: ${Math.min(...historialRuta.map(x => x.precio))} | 
                        Max: ${Math.max(...historialRuta.map(x => x.precio))} | 
                        {historialRuta.length} registros
                      


                    

                  )}

                  {/* FECHAS Y PAQUETE */}
                  

                    {ruta.dias_paquete && (
                      

                        Paquete {ruta.dias_paquete} Días
                      

                    )}
                    

                      

Salida / Mes


                      


                        calendar_today{ruta.ida}
                      


                    

                    

                      

Retorno / Mes


                      


                        calendar_today{ruta.vuelta}
                      


                    

                  


                  {precio && historialRuta.length > 1 && (
                    


                      {rutaDetalle === `${ruta.origen}-${ruta.destino}` ? '▲ Ocultar historial' : '▼ Ver historial de precios'}
                    


                  )}
                

              );
            })}
          

        )}
      

    

  );
}
