'use client';

import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const IATA_MAP: Record<string, string> = {
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
  const [rutas, setRutas] = useState<any[]>([]);
  const [precios, setPrecios] = useState<Record<string, PrecioData>>({});
  const [historial, setHistorial] = useState<Record<string, HistorialEntry[]>>({});
  const [cargando, setCargando] = useState(true);
  const [errorSync, setErrorSync] = useState('');
  const [filtro, setFiltro] = useState('');
  const [vistaActiva, setVistaActiva] = useState<'tarjetas' | 'comparativa'>('tarjetas');
  const [rutaDetalle, setRutaDetalle] = useState<string | null>(null);
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
        const mapaPrecios: Record<string, PrecioData> = {};
        for (const p of dataPrecios.precios) {
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
    const nuevaRuta = {
      id: tempId, ...nuevoVuelo,
      alerta: nuevoVuelo.alerta ? Number(nuevoVuelo.alerta) : '',
      dias_paquete: nuevoVuelo.dias_paquete ? Number(nuevoVuelo.dias_paquete) : ''
    };
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

  const rutasPorDestino = rutas.reduce((acc: Record<string, any[]>, ruta) => {
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
    <div className="min-h-screen bg-background text-on-background relative overflow-hidden font-sans transition-colors duration-300 pb-20">
      <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-primary/5 rounded-full blur-[120px] pointer-events-none z-0"></div>
      <div className="absolute bottom-[-10%] left-[20%] w-[40%] h-[40%] bg-secondary/5 rounded-full blur-[120px] pointer-events-none z-0"></div>

      <div className="max-w-5xl mx-auto p-8 relative z-10 pt-16">

        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 border-b border-outline-variant/20 pb-6 gap-6">
          <div>
            <h1 className="text-4xl font-extrabold bg-gradient-to-r from-primary to-primary-container bg-clip-text text-transparent mb-2">
              Monitor de Vuelos CTB
            </h1>
            <p className="text-on-surface-variant text-sm">
              {rutas.length} rutas monitoreadas
              {totalGangas > 0 && (
                <span className="ml-2 bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full text-xs font-bold">
                  🚨 {totalGangas} gangas activas
                </span>
              )}
            </p>
            {Object.values(precios).length > 0 && (
              <p className="text-on-surface-variant text-xs mt-1">
                🕐 Última actualización: {new Date(new Date(Object.values(precios)[0].fecha).getTime() - 5 * 60 * 60 * 1000).toLocaleString('es-EC', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
              </p>
            )}
            {errorSync && <p className="text-error mt-2 text-xs font-bold bg-error/10 p-2 rounded">{errorSync}</p>}
          </div>
          <div className="flex flex-col md:flex-row items-center gap-4">
            {mounted && (
              <div className="flex bg-surface-container-low border border-outline-variant/20 rounded-xl p-1 shadow-sm">
                <button onClick={() => setTheme('light')} className={`p-2 rounded-lg flex items-center justify-center transition ${theme === 'light' ? 'bg-surface text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
                  <span className="material-symbols-outlined text-[20px]">light_mode</span>
                </button>
                <button onClick={() => setTheme('dark')} className={`p-2 rounded-lg flex items-center justify-center transition ${theme === 'dark' ? 'bg-surface text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
                  <span className="material-symbols-outlined text-[20px]">dark_mode</span>
                </button>
                <button onClick={() => setTheme('system')} className={`p-2 rounded-lg flex items-center justify-center transition ${theme === 'system' ? 'bg-surface text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
                  <span className="material-symbols-outlined text-[20px]">desktop_windows</span>
                </button>
              </div>
            )}
            <button
              onClick={() => setMostrarFormulario(!mostrarFormulario)}
              className="bg-primary text-surface-container-lowest px-6 py-3 rounded-xl font-bold shadow-[0_0_20px_rgba(143,245,255,0.2)] hover:brightness-110 flex items-center gap-2 transition whitespace-nowrap">
              <span className="material-symbols-outlined font-bold text-xl">{mostrarFormulario ? "close" : "add"}</span>
              {mostrarFormulario ? "Cancelar" : "Agregar Ruta"}
            </button>
          </div>
        </header>

        <div className="flex gap-2 mb-6">
          <button onClick={() => setVistaActiva('tarjetas')}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition ${vistaActiva === 'tarjetas' ? 'bg-primary text-on-primary' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'}`}>
            📋 Todas las rutas
          </button>
          <button onClick={() => setVistaActiva('comparativa')}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition ${vistaActiva === 'comparativa' ? 'bg-primary text-on-primary' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'}`}>
            ⚖️ GYE vs UIO
          </button>
          <button onClick={cargarRutas} className="ml-auto px-4 py-2 rounded-lg text-sm font-bold bg-surface-container-low text-on-surface-variant hover:bg-surface-container transition flex items-center gap-1">
            <span className="material-symbols-outlined text-[16px]">refresh</span> Actualizar
          </button>
        </div>

        {!mostrarFormulario && vistaActiva === 'tarjetas' && rutas.length > 0 && (
          <div className="mb-6 relative max-w-md">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">search</span>
            <input type="text" placeholder="Buscar por código o ciudad..." value={filtro}
              onChange={e => setFiltro(e.target.value)}
              className="w-full bg-surface-container-low text-on-surface border border-outline-variant/20 rounded-full py-3 pl-12 pr-4 outline-none focus:border-primary shadow-sm transition-all text-sm font-medium" />
            {filtro && (
              <button onClick={() => setFiltro('')} className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant">
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            )}
          </div>
        )}

        {mostrarFormulario && (
          <form onSubmit={agregarRuta} className="bg-surface-container-low border border-outline-variant/10 p-6 rounded-2xl mb-10 shadow-xl animate-in fade-in slide-in-from-top-4">
            <h2 className="text-xl font-bold text-primary flex items-center gap-2 mb-6">
              <span className="material-symbols-outlined">flight_takeoff</span>Nueva ruta
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
              <div className="flex flex-col">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant mb-2 font-bold">Origen</label>
                <input required value={nuevoVuelo.origen}
                  onChange={e => setNuevoVuelo({ ...nuevoVuelo, origen: e.target.value.toUpperCase() })}
                  maxLength={3} placeholder="GYE"
                  className="bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary uppercase h-[46px]" />
              </div>
              <div className="flex flex-col">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant mb-2 font-bold">Destino</label>
                <input required value={nuevoVuelo.destino}
                  onChange={e => setNuevoVuelo({ ...nuevoVuelo, destino: e.target.value.toUpperCase() })}
                  maxLength={3} placeholder="MAD"
                  className="bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary uppercase h-[46px]" />
              </div>
              <div className="flex flex-col relative">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant mb-2 font-bold">Mes Ida</label>
                <DatePicker
                  selected={parseDateString(nuevoVuelo.ida, tipoFecha)}
                  onChange={(d: Date | null) => setNuevoVuelo({ ...nuevoVuelo, ida: formatDateObj(d, tipoFecha) })}
                  dateFormat="MM/yyyy" showMonthYearPicker locale={es} wrapperClassName="w-full"
                  placeholderText="Mes / Año"
                  className="w-full bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary h-[46px]" />
              </div>
              <div className="flex flex-col relative">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant mb-2 font-bold">Mes Vuelta</label>
                <DatePicker
                  selected={parseDateString(nuevoVuelo.vuelta, tipoFecha)}
                  onChange={(d: Date | null) => setNuevoVuelo({ ...nuevoVuelo, vuelta: formatDateObj(d, tipoFecha) })}
                  dateFormat="MM/yyyy" showMonthYearPicker locale={es} wrapperClassName="w-full"
                  placeholderText="Mes / Año"
                  className="w-full bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary h-[46px]" />
              </div>
              <div className="flex flex-col">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant mb-2 font-bold">Días Viaje</label>
                <input value={nuevoVuelo.dias_paquete}
                  onChange={e => setNuevoVuelo({ ...nuevoVuelo, dias_paquete: e.target.value })}
                  type="number" placeholder="Ej: 6"
                  className="bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary h-[46px]" />
              </div>
              <div className="flex flex-col">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant mb-2 font-bold">Alerta $</label>
                <input value={nuevoVuelo.alerta}
                  onChange={e => setNuevoVuelo({ ...nuevoVuelo, alerta: e.target.value })}
                  type="number" placeholder="Opcional"
                  className="bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary h-[46px]" />
              </div>
            </div>
            <div className="mt-6 flex justify-end">
              <button type="submit" className="bg-gradient-to-r from-primary to-primary-container text-on-primary font-bold px-8 py-3 rounded-lg hover:brightness-110 flex items-center gap-2 transition shadow-md">
                <span className="material-symbols-outlined">save</span>Guardar Ruta
              </button>
            </div>
          </form>
        )}

        {cargando ? (
          <div className="text-center py-20 bg-surface-container-low rounded-2xl border border-outline-variant/10">
            <span className="material-symbols-outlined text-6xl text-primary animate-pulse mb-4">cloud_sync</span>
            <p className="text-primary text-lg font-bold">Cargando precios en tiempo real...</p>
          </div>

        ) : vistaActiva === 'comparativa' ? (
          <div className="space-y-4">
            {Object.entries(rutasPorDestino).map(([destino, rutasDestino]) => {
              const rutaGYE = rutasDestino.find((r: any) => r.origen === 'GYE');
              const rutaUIO = rutasDestino.find((r: any) => r.origen === 'UIO');
              const precioGYE = rutaGYE ? getPrecioRuta('GYE', destino) : null;
              const precioUIO = rutaUIO ? getPrecioRuta('UIO', destino) : null;
              if (!rutaGYE && !rutaUIO) return null;
              const masBarato = precioGYE && precioUIO ? (precioGYE.precio <= precioUIO.precio ? 'GYE' : 'UIO') : null;
              return (
                <div key={destino} className="bg-surface-container-low border border-outline-variant/10 rounded-2xl p-5">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="material-symbols-outlined text-primary">flight_land</span>
                    <h3 className="text-lg font-bold">{destino} — {getCityName(destino)}</h3>
                    {(precioGYE?.es_ganga || precioUIO?.es_ganga) && (
                      <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full text-xs font-bold">🚨 GANGA</span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    {[{ origen: 'GYE', precio: precioGYE }, { origen: 'UIO', precio: precioUIO }].map(({ origen, precio }) => (
                      <div key={origen} className={`p-4 rounded-xl border ${precio?.es_ganga ? 'border-red-500/40 bg-red-500/5' : masBarato === origen ? 'border-green-500/40 bg-green-500/5' : 'border-outline-variant/10 bg-surface-container'}`}>
                        <p className="text-xs font-bold text-on-surface-variant uppercase mb-2">{origen} → {destino}</p>
                        {precio ? (
                          <>
                            <p className={`text-2xl font-extrabold ${precio.es_ganga ? 'text-red-400' : masBarato === origen ? 'text-green-400' : 'text-on-background'}`}>
                              ${precio.precio} <span className="text-sm font-normal text-on-surface-variant">USD</span>
                            </p>
                            {precio.fecha_vuelo && precio.fecha_vuelo !== 'N/D' && (
                              <p className="text-xs text-on-surface-variant mt-1">📅 {precio.fecha_vuelo}</p>
                            )}
                            {precio.mediana > 0 && <p className="text-xs text-on-surface-variant">📊 Prom: ${precio.mediana}</p>}
                            {masBarato === origen && <p className="text-xs text-green-400 font-bold mt-1">✅ Más barato</p>}
                          </>
                        ) : (
                          <p className="text-sm text-on-surface-variant">Sin datos aún</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

        ) : rutasFiltradas.length === 0 ? (
          <div className="text-center py-20 bg-surface-container-low rounded-2xl border border-outline-variant/10">
            <span className="material-symbols-outlined text-6xl text-outline-variant mb-4">search_off</span>
            <p className="text-on-surface-variant">No se encontraron rutas.</p>
          </div>

        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {rutasFiltradas.map(ruta => {
              const precio = getPrecioRuta(ruta.origen, ruta.destino);
              const esGanga = precio?.es_ganga || false;
              const claveHistorial1 = `${ruta.origen} -> ${ruta.destino}`;
              const claveHistorial2 = `${ruta.origen} ➡️ ${ruta.destino}`;
              const historialRuta = historial[claveHistorial1] || historial[claveHistorial2] || [];
              const rutaKey = `${ruta.origen}-${ruta.destino}`;
              return (
                <div key={ruta.id}
                  className={`border transition-all rounded-2xl p-6 relative group shadow-sm cursor-pointer ${esGanga ? 'bg-red-950/30 border-red-500/40 hover:border-red-500/60' : 'bg-surface-container-low border-outline-variant/10 hover:border-outline-variant/30'}`}
                  onClick={() => setRutaDetalle(rutaDetalle === rutaKey ? null : rutaKey)}>

                  {esGanga && (
                    <div className="absolute -top-3 left-6 bg-red-500 text-white text-[10px] uppercase font-bold px-3 py-1 rounded-full shadow animate-pulse">
                      🚨 GANGA
                    </div>
                  )}

                  <button onClick={e => { e.stopPropagation(); eliminarRuta(ruta.id); }}
                    className="absolute top-6 right-6 text-outline-variant hover:text-error transition opacity-0 group-hover:opacity-100">
                    <span className="material-symbols-outlined">delete</span>
                  </button>

                  <div className="flex items-center gap-4 mb-4">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center border ${esGanga ? 'bg-red-500/20 border-red-500/40 text-red-400' : 'bg-surface-container-highest border-outline-variant/20 text-primary'}`}>
                      <span className="material-symbols-outlined font-light text-2xl">flight_takeoff</span>
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold tracking-tight text-on-background flex items-center gap-3">
                        <div className="flex flex-col items-start leading-none">
                          <span>{ruta.origen}</span>
                          <span className="text-[9px] text-on-surface-variant font-medium uppercase tracking-wider mt-1.5">{getCityName(ruta.origen)}</span>
                        </div>
                        <span className="text-outline-variant/50 font-light text-xl pb-3">→</span>
                        <div className="flex flex-col items-start leading-none">
                          <span>{ruta.destino}</span>
                          <span className="text-[9px] text-on-surface-variant font-medium uppercase tracking-wider mt-1.5">{getCityName(ruta.destino)}</span>
                        </div>
                      </h3>
                    </div>
                  </div>

                  {precio ? (
                    <div className={`p-4 rounded-xl mb-4 ${esGanga ? 'bg-red-500/10 border border-red-500/20' : 'bg-surface-container border border-outline-variant/10'}`}>
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-1">Mejor precio actual</p>
                          <p className={`text-3xl font-extrabold ${esGanga ? 'text-red-400' : 'text-primary'}`}>
                            ${precio.precio} <span className="text-sm font-normal text-on-surface-variant">USD</span>
                          </p>
                          {precio.fecha_vuelo && precio.fecha_vuelo !== 'N/D' && (
                            <p className="text-xs text-on-surface-variant mt-1">📅 Salida: {precio.fecha_vuelo}</p>
                          )}
                        </div>
                        <div className="text-right">
                          {precio.mediana > 0 && <p className="text-xs text-on-surface-variant">📊 Prom: ${precio.mediana}</p>}
                          {precio.precio_alerta > 0 && <p className="text-xs text-on-surface-variant">🎯 Alerta: ${precio.precio_alerta}</p>}
                          <p className="text-[10px] text-on-surface-variant mt-1">
                            {new Date(precio.fecha).toLocaleString('es-EC', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl mb-4 bg-surface-container border border-outline-variant/10">
                      <p className="text-xs text-on-surface-variant">⏳ Esperando primera consulta del bot...</p>
                    </div>
                  )}

                  {rutaDetalle === rutaKey && historialRuta.length > 1 && (
                    <div className="mt-2 p-3 bg-surface-container rounded-xl border border-outline-variant/10" onClick={e => e.stopPropagation()}>
                      <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-3">Historial de precios</p>
                      <div className="flex items-end gap-1 h-16">
                        {historialRuta.slice(0, 20).reverse().map((h, i) => {
                          const maxP = Math.max(...historialRuta.map((x: HistorialEntry) => x.precio));
                          const minP = Math.min(...historialRuta.map((x: HistorialEntry) => x.precio));
                          const rango = maxP - minP || 1;
                          const altura = Math.max(10, Math.round(((h.precio - minP) / rango) * 48) + 8);
                          return (
                            <div key={i} className="flex flex-col items-center flex-1 gap-1" title={`$${h.precio}`}>
                              <div className={`w-full rounded-sm ${h.es_ganga ? 'bg-red-400' : 'bg-primary/60'}`} style={{ height: `${altura}px` }}></div>
                            </div>
                          );
                        })}
                      </div>
                      <p className="text-[10px] text-on-surface-variant mt-2 text-center">
                        Min: <strong>${Math.min(...historialRuta.map((x: HistorialEntry) => x.precio))}</strong> |
                        Max: <strong>${Math.max(...historialRuta.map((x: HistorialEntry) => x.precio))}</strong> |
                        {historialRuta.length} registros
                      </p>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4 bg-surface-container p-4 rounded-xl border border-outline-variant/10 relative mt-2">
                    {ruta.dias_paquete && (
                      <div className="absolute -top-3 right-4 bg-secondary text-surface-container-lowest text-[10px] uppercase font-bold px-3 py-1 rounded-full shadow-sm">
                        Paquete {ruta.dias_paquete} Días
                      </div>
                    )}
                    <div>
                      <p className="text-[10px] uppercase tracking-widest text-on-surface-variant mb-1 font-bold">Salida / Mes</p>
                      <p className="font-medium flex items-center gap-1 text-on-surface text-sm">
                        <span className="material-symbols-outlined text-[16px] text-tertiary">calendar_today</span>{ruta.ida}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-widest text-on-surface-variant mb-1 font-bold">Retorno / Mes</p>
                      <p className="font-medium flex items-center gap-1 text-on-surface text-sm">
                        <span className="material-symbols-outlined text-[16px] text-tertiary">calendar_today</span>{ruta.vuelta}
                      </p>
                    </div>
                  </div>

                  {precio && historialRuta.length > 1 && (
                    <p className="text-[10px] text-on-surface-variant text-center mt-3">
                      {rutaDetalle === rutaKey ? '▲ Ocultar historial' : '▼ Ver historial de precios'}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
