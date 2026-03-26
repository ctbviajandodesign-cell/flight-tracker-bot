'use client';

import { useState, useEffect, useRef } from 'react';
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
  id: number; ruta: string; precio: number; mediana: number;
  fecha_vuelo: string; precio_alerta: number; es_ganga: boolean;
  tipo_vuelo: string; fecha: string; url_vuelo?: string;
};
type HistorialEntry = { fecha: string; precio: number; es_ganga: boolean };

function FreshnessIndicator({ fecha }: { fecha: string }) {
  const diffHrs = (Date.now() - new Date(fecha).getTime()) / 36e5 - 5;
  const fresh = diffHrs < 4;
  const stale = diffHrs > 12;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ${
      fresh ? 'bg-emerald-500/15 text-emerald-500' :
      stale ? 'bg-rose-500/15 text-rose-500' :
      'bg-amber-500/15 text-amber-500'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${fresh ? 'bg-emerald-500' : stale ? 'bg-rose-500' : 'bg-amber-500'}`}/>
      {new Date(new Date(fecha).getTime() - 5*3600000).toLocaleString('es-EC', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}
    </span>
  );
}

function MiniChart({ data }: { data: HistorialEntry[] }) {
  if (data.length < 2) return null;
  const prices = data.map(d => d.precio);
  const min = Math.min(...prices), max = Math.max(...prices);
  const range = max - min || 1;
  const w = 200, h = 40, pad = 4;
  const pts = data.slice(-15).map((d, i, arr) => {
    const x = pad + (i / (arr.length - 1)) * (w - pad * 2);
    const y = h - pad - ((d.precio - min) / range) * (h - pad * 2);
    return `${x},${y}`;
  }).join(' ');
  const last = data[data.length - 1];
  const prev = data[data.length - 2];
  const trend = last.precio < prev.precio ? 'down' : last.precio > prev.precio ? 'up' : 'flat';
  return (
    <div className="flex items-center gap-2 mt-2">
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="flex-shrink-0">
        <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="1.5"
          className={trend === 'down' ? 'text-emerald-400' : trend === 'up' ? 'text-rose-400' : 'text-slate-400'}
          strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
      <span className={`text-xs font-bold ${trend === 'down' ? 'text-emerald-400' : trend === 'up' ? 'text-rose-400' : 'text-slate-400'}`}>
        {trend === 'down' ? '↓ bajando' : trend === 'up' ? '↑ subiendo' : '→ estable'}
      </span>
    </div>
  );
}

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
  const [nuevoVuelo, setNuevoVuelo] = useState({ origen:'', destino:'', ida:'', vuelta:'', alerta:'', dias_paquete:'' });
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  const cargarRutas = async () => {
    try {
      setCargando(true);
      const [resRutas, resPrecios] = await Promise.all([fetch('/api/flights'), fetch('/api/prices')]);
      const dataRutas = await resRutas.json();
      const dataPrecios = await resPrecios.json();
      if (dataRutas.success) setRutas(dataRutas.flights);
      if (dataPrecios.success) {
        const mapa: Record<string, PrecioData> = {};
        for (const p of dataPrecios.precios) {
          const k = p.ruta.replace(' ➡️ ', ' -> ').replace('➡️', '->').trim();
          mapa[k] = p;
        }
        setPrecios(mapa);
        setHistorial(dataPrecios.historial || {});
      }
      setErrorSync('');
    } catch (e: any) { setErrorSync(e.message); }
    finally { setCargando(false); }
  };

  useEffect(() => { setMounted(true); cargarRutas(); }, []);

  const getPrecio = (o: string, d: string): PrecioData | null =>
    precios[`${o} -> ${d}`] || precios[`${o} ➡️ ${d}`] || null;

  const eliminarRuta = async (id: number) => {
    setRutas(rutas.filter(r => r.id !== id));
    await fetch(`/api/flights?id=${id}`, { method: 'DELETE' });
    cargarRutas();
  };

  const agregarRuta = async (e: React.FormEvent) => {
    e.preventDefault();
    const nueva = { id: Date.now(), ...nuevoVuelo, alerta: nuevoVuelo.alerta ? Number(nuevoVuelo.alerta) : '', dias_paquete: nuevoVuelo.dias_paquete ? Number(nuevoVuelo.dias_paquete) : '' };
    setRutas([...rutas, nueva]);
    setMostrarFormulario(false);
    setNuevoVuelo({ origen:'', destino:'', ida:'', vuelta:'', alerta:'', dias_paquete:'' });
    await fetch('/api/flights', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(nueva) });
    cargarRutas();
  };

  const parseFecha = (s: string) => {
    if (!s) return null;
    const p = s.split('-');
    return p.length === 2 ? new Date(+p[0], +p[1]-1, 1) : p.length === 3 ? new Date(+p[0], +p[1]-1, +p[2]) : null;
  };
  const fmtFecha = (d: Date | null, tipo: string) => !d ? '' : tipo === 'mes' ? format(d, 'yyyy-MM') : format(d, 'yyyy-MM-dd');

  const rutasPorDestino = rutas.reduce((acc: Record<string,any[]>, r) => { (acc[r.destino] = acc[r.destino]||[]).push(r); return acc; }, {});
  const rutasFiltradas = rutas.filter(r => { const t = filtro.toLowerCase(); return r.origen.toLowerCase().includes(t) || r.destino.toLowerCase().includes(t) || getCityName(r.origen).toLowerCase().includes(t) || getCityName(r.destino).toLowerCase().includes(t); });
  const totalGangas = rutas.filter(r => getPrecio(r.origen, r.destino)?.es_ganga).length;
  const ultimaActualizacion = Object.values(precios)[0]?.fecha;

  return (
    <div className="min-h-screen bg-background text-on-background font-sans pb-24 relative">

      {/* Fondo sutil */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-32 -right-32 w-96 h-96 bg-primary/8 rounded-full blur-3xl"/>
        <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-tertiary/6 rounded-full blur-3xl"/>
      </div>

      <div className="max-w-6xl mx-auto px-6 pt-10 relative z-10">

        {/* ── HEADER ── */}
        <header className="mb-8">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="material-symbols-outlined text-primary text-3xl">travel_explore</span>
                <h1 className="text-3xl font-black tracking-tight text-on-background">Monitor de Vuelos <span className="text-primary">CTB</span></h1>
              </div>
              <div className="flex flex-wrap items-center gap-3 mt-2">
                <span className="text-on-surface-variant text-sm">{rutas.length} rutas activas</span>
                {totalGangas > 0 && (
                  <span className="inline-flex items-center gap-1.5 bg-amber-500/15 text-amber-500 border border-amber-500/20 text-xs font-bold px-3 py-1 rounded-full">
                    🔥 {totalGangas} gangas detectadas
                  </span>
                )}
                {ultimaActualizacion && <FreshnessIndicator fecha={ultimaActualizacion}/>}
              </div>
              {errorSync && <p className="text-rose-400 mt-2 text-xs bg-rose-500/10 px-3 py-1.5 rounded-lg border border-rose-500/20">{errorSync}</p>}
            </div>
            <div className="flex items-center gap-3">
              {mounted && (
                <div className="flex bg-surface-container-low border border-outline-variant/20 rounded-xl p-1">
                  {(['light','dark','system'] as const).map(t => (
                    <button key={t} onClick={() => setTheme(t)} title={t}
                      className={`p-2 rounded-lg transition ${theme===t ? 'bg-primary/15 text-primary' : 'text-on-surface-variant hover:text-on-surface'}`}>
                      <span className="material-symbols-outlined text-[18px]">
                        {t==='light' ? 'light_mode' : t==='dark' ? 'dark_mode' : 'desktop_windows'}
                      </span>
                    </button>
                  ))}
                </div>
              )}
              <button onClick={() => setMostrarFormulario(!mostrarFormulario)}
                className="flex items-center gap-2 bg-primary text-white font-bold px-5 py-2.5 rounded-xl hover:bg-primary/90 transition shadow-lg shadow-primary/20">
                <span className="material-symbols-outlined text-[18px]">{mostrarFormulario ? 'close' : 'add'}</span>
                {mostrarFormulario ? 'Cancelar' : 'Nueva Ruta'}
              </button>
            </div>
          </div>
        </header>

        {/* ── FORMULARIO ── */}
        {mostrarFormulario && (
          <div className="mb-8 bg-surface-container-low border border-outline-variant/20 rounded-2xl p-6 shadow-xl">
            <h2 className="text-base font-bold text-primary flex items-center gap-2 mb-5">
              <span className="material-symbols-outlined text-[20px]">flight_takeoff</span>Agregar nueva ruta de monitoreo
            </h2>
            <form onSubmit={agregarRuta}>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                {[{label:'Origen',key:'origen',ph:'GYE'},{label:'Destino',key:'destino',ph:'MAD'}].map(f=>(
                  <div key={f.key}>
                    <label className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1.5">{f.label}</label>
                    <input required value={(nuevoVuelo as any)[f.key]}
                      onChange={e=>setNuevoVuelo({...nuevoVuelo,[f.key]:e.target.value.toUpperCase()})}
                      maxLength={3} placeholder={f.ph}
                      className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-3 py-2.5 text-sm font-bold uppercase outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 h-[42px]"/>
                  </div>
                ))}
                {(['ida','vuelta'] as const).map(k=>(
                  <div key={k}>
                    <label className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1.5">{k==='ida'?'Mes ida':'Mes vuelta'}</label>
                    <DatePicker selected={parseFecha((nuevoVuelo as any)[k])}
                      onChange={(d:Date|null)=>setNuevoVuelo({...nuevoVuelo,[k]:fmtFecha(d,'mes')})}
                      dateFormat="MM/yyyy" showMonthYearPicker locale={es} wrapperClassName="w-full"
                      placeholderText="MM/YYYY"
                      className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-primary h-[42px]"/>
                  </div>
                ))}
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1.5">Días viaje</label>
                  <input value={nuevoVuelo.dias_paquete} onChange={e=>setNuevoVuelo({...nuevoVuelo,dias_paquete:e.target.value})}
                    type="number" placeholder="6"
                    className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-primary h-[42px]"/>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1.5">Alerta $</label>
                  <input value={nuevoVuelo.alerta} onChange={e=>setNuevoVuelo({...nuevoVuelo,alerta:e.target.value})}
                    type="number" placeholder="350"
                    className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-primary h-[42px]"/>
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <button type="submit" className="flex items-center gap-2 bg-primary text-white font-bold px-6 py-2.5 rounded-xl hover:bg-primary/90 transition">
                  <span className="material-symbols-outlined text-[18px]">save</span>Guardar
                </button>
              </div>
            </form>
          </div>
        )}

        {/* ── NAVEGACIÓN ── */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex gap-1 bg-surface-container-low border border-outline-variant/20 rounded-xl p-1">
            <button onClick={()=>setVistaActiva('tarjetas')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${vistaActiva==='tarjetas' ? 'bg-primary text-white shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
              ✈️ Todas las rutas
            </button>
            <button onClick={()=>setVistaActiva('comparativa')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${vistaActiva==='comparativa' ? 'bg-primary text-white shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
              ⚖️ GYE vs UIO
            </button>
          </div>
          <div className="flex items-center gap-2">
            {vistaActiva==='tarjetas' && (
              <div className="relative">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">search</span>
                <input type="text" placeholder="Buscar destino..." value={filtro} onChange={e=>setFiltro(e.target.value)}
                  className="bg-surface-container-low border border-outline-variant/20 rounded-xl py-2 pl-9 pr-4 text-sm outline-none focus:border-primary w-48 transition-all focus:w-64"/>
              </div>
            )}
            <button onClick={cargarRutas} className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface-container-low border border-outline-variant/20 text-on-surface-variant hover:text-on-surface text-sm font-medium transition">
              <span className="material-symbols-outlined text-[16px]">refresh</span>
            </button>
          </div>
        </div>

        {/* ── CONTENIDO ── */}
        {cargando ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="w-12 h-12 border-2 border-primary/30 border-t-primary rounded-full animate-spin"/>
            <p className="text-on-surface-variant text-sm">Cargando precios en tiempo real...</p>
          </div>

        ) : vistaActiva==='comparativa' ? (
          <div className="space-y-3">
            {Object.entries(rutasPorDestino).map(([dest, rs]) => {
              const pGYE = getPrecio('GYE', dest), pUIO = getPrecio('UIO', dest);
              const barato = pGYE && pUIO ? (pGYE.precio <= pUIO.precio ? 'GYE' : 'UIO') : null;
              const hayGanga = pGYE?.es_ganga || pUIO?.es_ganga;
              return (
                <div key={dest} className="bg-surface-container-low border border-outline-variant/15 rounded-2xl overflow-hidden">
                  <div className={`px-5 py-3 flex items-center justify-between border-b border-outline-variant/10 ${hayGanga ? 'bg-amber-500/5' : ''}`}>
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-primary text-[18px]">location_on</span>
                      <span className="font-bold text-sm">{dest}</span>
                      <span className="text-on-surface-variant text-sm">— {getCityName(dest)}</span>
                    </div>
                    {hayGanga && <span className="text-[10px] font-bold text-amber-500 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">🔥 GANGA</span>}
                  </div>
                  <div className="grid grid-cols-2 divide-x divide-outline-variant/10">
                    {[{org:'GYE',p:pGYE},{org:'UIO',p:pUIO}].map(({org,p})=>(
                      <div key={org} className={`p-4 ${barato===org && p ? 'bg-emerald-500/5' : ''}`}>
                        <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-2">{org} → {dest}</p>
                        {p ? (
                          <>
                            <p className={`text-2xl font-black ${p.es_ganga ? 'text-amber-500' : barato===org ? 'text-emerald-500' : 'text-on-background'}`}>
                              ${p.precio.toLocaleString()} <span className="text-xs font-normal text-on-surface-variant">USD</span>
                            </p>
                            {p.fecha_vuelo && p.fecha_vuelo!=='N/D' && <p className="text-xs text-on-surface-variant mt-1">📅 {p.fecha_vuelo}</p>}
                            {p.mediana>0 && <p className="text-xs text-on-surface-variant">prom. ${p.mediana}</p>}
                            {barato===org && <p className="text-xs text-emerald-500 font-bold mt-1">✓ más económico</p>}
                          </>
                        ) : <p className="text-xs text-on-surface-variant/50 mt-4">sin datos</p>}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

        ) : rutasFiltradas.length===0 ? (
          <div className="text-center py-24">
            <span className="material-symbols-outlined text-5xl text-on-surface-variant/30 block mb-3">search_off</span>
            <p className="text-on-surface-variant">Sin resultados para "{filtro}"</p>
          </div>

        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {rutasFiltradas.map(ruta => {
              const p = getPrecio(ruta.origen, ruta.destino);
              const ganga = p?.es_ganga || false;
              const key = `${ruta.origen}-${ruta.destino}`;
              const hRuta = historial[`${ruta.origen} -> ${ruta.destino}`] || historial[`${ruta.origen} ➡️ ${ruta.destino}`] || [];
              const expanded = rutaDetalle === key;
              return (
                <div key={ruta.id} onClick={()=>setRutaDetalle(expanded ? null : key)}
                  className={`relative rounded-2xl border transition-all duration-200 cursor-pointer group overflow-hidden
                    ${ganga
                      ? 'border-amber-500/30 bg-gradient-to-br from-amber-500/5 to-surface-container-low hover:border-amber-500/50 hover:shadow-lg hover:shadow-amber-500/10'
                      : 'border-outline-variant/15 bg-surface-container-low hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5'
                    }`}>

                  {/* Stripe superior ganga */}
                  {ganga && <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber-400 to-orange-400"/>}

                  <div className="p-5">
                    {/* Cabecera ruta */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${ganga ? 'bg-amber-500/15' : 'bg-primary/10'}`}>
                          <span className={`material-symbols-outlined text-[18px] ${ganga ? 'text-amber-500' : 'text-primary'}`}>flight_takeoff</span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-black text-lg tracking-tight">{ruta.origen}</span>
                            <span className="text-on-surface-variant/40 text-sm">→</span>
                            <span className="font-black text-lg tracking-tight">{ruta.destino}</span>
                          </div>
                          <p className="text-[10px] text-on-surface-variant">{getCityName(ruta.origen)} → {getCityName(ruta.destino)}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {ganga && <span className="text-[9px] font-black text-amber-500 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full tracking-wider">🔥 GANGA</span>}
                        <button onClick={e=>{e.stopPropagation();eliminarRuta(ruta.id);}}
                          className="opacity-0 group-hover:opacity-100 text-on-surface-variant/40 hover:text-rose-400 transition p-1 rounded-lg hover:bg-rose-500/10">
                          <span className="material-symbols-outlined text-[16px]">delete</span>
                        </button>
                      </div>
                    </div>

                    {/* Precio */}
                    {p ? (
                      <div className={`rounded-xl p-4 mb-3 ${ganga ? 'bg-amber-500/8' : 'bg-surface-container'}`}>
                        <div className="flex items-end justify-between">
                          <div>
                            <p className={`text-[9px] uppercase tracking-widest font-bold mb-1 ${ganga ? 'text-amber-500/70' : 'text-on-surface-variant'}`}>mejor precio</p>
                            <p className={`text-3xl font-black leading-none ${ganga ? 'text-amber-700 dark:text-amber-400' : 'text-primary'}`}>
                              ${p.precio.toLocaleString()}
                              <span className="text-xs font-normal text-on-surface-variant ml-1">USD</span>
                            </p>
                            {p.fecha_vuelo && p.fecha_vuelo!=='N/D' && (
                              <p className="text-xs text-on-surface-variant mt-1.5 flex items-center gap-1">
                                <span className="material-symbols-outlined text-[12px]">calendar_today</span>
                                {p.fecha_vuelo}
                              </p>
                            )}
                          </div>
                          <div className="text-right">
                            {p.precio_alerta > 0 && (
                              <p className="text-[10px] text-on-surface-variant">🎯 alerta: ${p.precio_alerta}</p>
                            )}
                            {p.mediana > 0 && (
                              <p className="text-[10px] text-on-surface-variant">📊 prom: ${p.mediana}</p>
                            )}
                            <FreshnessIndicator fecha={p.fecha}/>
                          </div>
                        </div>
                        {hRuta.length > 1 && <MiniChart data={hRuta}/>}
                      </div>
                    ) : (
                      <div className="rounded-xl p-4 mb-3 bg-surface-container border border-dashed border-outline-variant/30">
                        <p className="text-xs text-on-surface-variant/50 text-center">⏳ Esperando consulta del bot...</p>
                      </div>
                    )}

                    {/* Fechas paquete */}
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="bg-surface-container rounded-lg px-3 py-2">
                        <p className="text-[9px] uppercase tracking-wider text-on-surface-variant font-bold mb-0.5">Salida</p>
                        <p className="font-semibold text-on-surface">{ruta.ida || '—'}</p>
                      </div>
                      <div className="bg-surface-container rounded-lg px-3 py-2">
                        <p className="text-[9px] uppercase tracking-wider text-on-surface-variant font-bold mb-0.5">Retorno</p>
                        <p className="font-semibold text-on-surface">{ruta.vuelta || '—'}</p>
                      </div>
                    </div>

                    {/* Tags */}
                    <div className="flex items-center justify-between mt-3">
                      <div className="flex gap-1.5">
                        {ruta.dias_paquete && (
                          <span className="text-[9px] font-bold text-tertiary bg-tertiary/10 px-2 py-0.5 rounded-full">{ruta.dias_paquete}d paquete</span>
                        )}
                        {p?.tipo_vuelo && p.tipo_vuelo!=='N/D' && (
                          <span className="text-[9px] font-bold text-on-surface-variant bg-surface-container px-2 py-0.5 rounded-full">
                            {p.tipo_vuelo==='DIR' ? '✈ directo' : '🛬 escala'}
                          </span>
                        )}
                      </div>
                      {p?.url_vuelo && (
                        <a href={p.url_vuelo} target="_blank" rel="noopener noreferrer"
                          onClick={e=>e.stopPropagation()}
                          className="text-[10px] text-on-surface-variant/40 hover:text-primary transition flex items-center gap-1">
                          <span className="material-symbols-outlined text-[12px]">open_in_new</span>
                          Google Flights
                        </a>
                      )}
                    </div>

                    {/* Historial expandido */}
                    {expanded && hRuta.length > 1 && (
                      <div className="mt-3 pt-3 border-t border-outline-variant/10" onClick={e=>e.stopPropagation()}>
                        <p className="text-[9px] uppercase tracking-widest text-on-surface-variant font-bold mb-2">Historial de precios</p>
                        <div className="flex items-end gap-0.5 h-14">
                          {hRuta.slice(-20).map((h,i) => {
                            const mx = Math.max(...hRuta.map((x:HistorialEntry)=>x.precio));
                            const mn = Math.min(...hRuta.map((x:HistorialEntry)=>x.precio));
                            const alt = Math.max(8, Math.round(((h.precio-mn)/(mx-mn||1))*44)+8);
                            return (
                              <div key={i} title={`$${h.precio}`} className="flex-1 flex items-end">
                                <div className={`w-full rounded-sm transition-all ${h.es_ganga ? 'bg-amber-400' : 'bg-primary/50'}`} style={{height:`${alt}px`}}/>
                              </div>
                            );
                          })}
                        </div>
                        <div className="flex justify-between mt-1">
                          <span className="text-[9px] text-on-surface-variant">min ${Math.min(...hRuta.map((x:HistorialEntry)=>x.precio))}</span>
                          <span className="text-[9px] text-on-surface-variant">{hRuta.length} registros</span>
                          <span className="text-[9px] text-on-surface-variant">max ${Math.max(...hRuta.map((x:HistorialEntry)=>x.precio))}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
