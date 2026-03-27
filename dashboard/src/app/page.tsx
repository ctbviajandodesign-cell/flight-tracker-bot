'use client';

import { useState, useEffect, useRef } from 'react';
import { useTheme } from 'next-themes';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const IATA_MAP: Record<string, string> = {
  GYE:"Guayaquil", UIO:"Quito", CUE:"Cuenca",
  BOG:"Bogotá", MDE:"Medellín", PTY:"Panamá",
  MIA:"Miami", NYC:"Nueva York", MAD:"Madrid",
  BCN:"Barcelona", LIM:"Lima", SCL:"Santiago",
  EZE:"Buenos Aires", MEX:"Ciudad de México",
  CUN:"Cancún", MCO:"Orlando", LAX:"Los Ángeles",
  GIG:"Río de Janeiro", CUR:"Curazao", PUJ:"Punta Cana",
  PEI:"Pereira", IST:"Estambul", ADZ:"San Andrés", CTG:"Cartagena",
};

const REGIONES: Record<string, string[]> = {
  "🏝️ Caribe":    ["PTY","CTG","PUJ","CUR","ADZ"],
  "🌎 Sudamérica": ["MDE","LIM","SCL","EZE","GIG","PEI","BOG"],
  "🌍 Europa":     ["MAD","BCN","IST"],
  "🇺🇸 USA":       ["MIA","MCO","LAX","NYC"],
  "🇲🇽 México":    ["MEX","CUN"],
};

const getCityName = (c: string) => IATA_MAP[c.toUpperCase()] || "Internacional";
const toEC = (f: string) => new Date(new Date(f).getTime() - 5*3600000);
const fmtEC = (f: string) => toEC(f).toLocaleString('es-EC',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
const getRegion = (d: string) => Object.entries(REGIONES).find(([,c])=>c.includes(d))?.[0] || "🌐 Otros";

type PrecioData = {
  id:number; ruta:string; precio:number; mediana:number;
  fecha_vuelo:string; precio_alerta:number; es_ganga:boolean;
  tipo_vuelo:string; fecha:string; url_vuelo?:string;
};
type HistorialEntry = {fecha:string; precio:number; es_ganga:boolean};
type Vista = 'todas' | 'gangas' | 'comparativa';

function FreshBadge({fecha}:{fecha:string}) {
  const hrs = (Date.now()-new Date(fecha).getTime())/3600000-5;
  const cfg = hrs<4
    ? {cls:'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/20', dot:'bg-emerald-500', lbl:'reciente'}
    : hrs<12
    ? {cls:'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/20', dot:'bg-amber-500', lbl:'hace horas'}
    : {cls:'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/20', dot:'bg-rose-500', lbl:'desact.'};
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${cfg.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`}/>
      <span className="hidden sm:inline">{fmtEC(fecha)} · </span>{cfg.lbl}
    </span>
  );
}

function Sparkline({data, ganga}:{data:HistorialEntry[], ganga:boolean}) {
  const [tip, setTip] = useState<number|null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  if (data.length < 2) return null;
  const slice = data.slice(-15);
  const prices = slice.map(d=>d.precio);
  const mn = Math.min(...prices), mx = Math.max(...prices), rng = mx-mn||1;
  const W=220, H=48, p=6;
  const pts = slice.map((d,i)=>({
    x: p+(i/(slice.length-1))*(W-p*2),
    y: H-p-((d.precio-mn)/rng)*(H-p*2),
    ...d
  }));
  const poly = pts.map(q=>`${q.x},${q.y}`).join(' ');
  const last = slice[slice.length-1], prev = slice[slice.length-2];
  const trend = last.precio<prev.precio?'down':last.precio>prev.precio?'up':'flat';
  const col = trend==='down'?'#059669':trend==='up'?'#dc2626':'#64748b';
  const tipPt = tip!==null ? pts[tip] : null;
  return (
    <div className="mt-2">
      <div className="relative">
        <svg ref={svgRef} width="100%" viewBox={`0 0 ${W} ${H}`}
          className="overflow-visible cursor-crosshair max-w-full"
          onMouseMove={e=>{
            const r=svgRef.current?.getBoundingClientRect();
            if(!r)return;
            const mx2=((e.clientX-r.left)/r.width)*W;
            let best=0;
            pts.forEach((q,i)=>{if(Math.abs(q.x-mx2)<Math.abs(pts[best].x-mx2))best=i;});
            setTip(best);
          }}
          onMouseLeave={()=>setTip(null)}>
          <defs>
            <linearGradient id={`sg${ganga?1:0}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={col} stopOpacity="0.2"/>
              <stop offset="100%" stopColor={col} stopOpacity="0"/>
            </linearGradient>
          </defs>
          <polygon points={`${pts[0].x},${H} ${poly} ${pts[pts.length-1].x},${H}`} fill={`url(#sg${ganga?1:0})`}/>
          <polyline points={poly} fill="none" stroke={col} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          {pts.map((q,i)=>q.es_ganga&&<circle key={i} cx={q.x} cy={q.y} r="3" fill="#f59e0b" stroke="white" strokeWidth="1"/>)}
          {tipPt&&<>
            <line x1={tipPt.x} y1={p} x2={tipPt.x} y2={H-p} stroke={col} strokeWidth="1" strokeDasharray="3,2" opacity="0.5"/>
            <circle cx={tipPt.x} cy={tipPt.y} r="3.5" fill={col} stroke="white" strokeWidth="1.5"/>
          </>}
        </svg>
        {tipPt&&(
          <div className="absolute z-30 pointer-events-none bg-surface-container-lowest border border-outline-variant/40 rounded-lg px-2.5 py-1.5 shadow-xl text-xs"
            style={{bottom:'110%', left:`clamp(0px, calc(${(tipPt.x/W)*100}% - 40px), calc(100% - 80px))`}}>
            <p className="font-black">${tipPt.precio.toLocaleString()}</p>
            <p className="text-on-surface-variant text-[10px]">{fmtEC(tipPt.fecha)}</p>
            {tipPt.es_ganga&&<p className="text-amber-500 text-[10px]">🔥 ganga</p>}
          </div>
        )}
      </div>
      <div className="flex justify-between mt-0.5">
        <span className="text-[9px] text-on-surface-variant/50">${mn.toLocaleString()}</span>
        <span className="text-[9px] font-bold" style={{color:col}}>
          {trend==='down'?'↓ bajando':trend==='up'?'↑ subiendo':'→ estable'}
        </span>
        <span className="text-[9px] text-on-surface-variant/50">${mx.toLocaleString()}</span>
      </div>
    </div>
  );
}

function RutaCard({ruta,precio,hist,expanded,onExpand,onDelete}:{
  ruta:any; precio:PrecioData|null; hist:HistorialEntry[];
  expanded:boolean; onExpand:()=>void; onDelete:()=>void;
}) {
  const ganga = precio?.es_ganga||false;
  return (
    <div onClick={onExpand}
      className={`relative rounded-2xl border transition-all duration-200 cursor-pointer group overflow-hidden
        ${ganga
          ?'border-amber-500/30 bg-surface-container-low hover:border-amber-500/50 hover:shadow-lg hover:shadow-amber-500/8'
          :'border-outline-variant/15 bg-surface-container-low hover:border-primary/25 hover:shadow-lg'
        }`}>
      {ganga&&<div className="absolute top-0 inset-x-0 h-0.5 bg-gradient-to-r from-amber-400 to-orange-400"/>}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${ganga?'bg-amber-500/15':'bg-primary/10'}`}>
              <span className={`material-symbols-outlined text-[16px] ${ganga?'text-amber-700 dark:text-amber-400':'text-primary'}`}>flight_takeoff</span>
            </div>
            <div>
              <div className="flex items-center gap-1.5 font-black text-sm">
                <span>{ruta.origen}</span>
                <span className="text-on-surface-variant/30 font-light">→</span>
                <span>{ruta.destino}</span>
                {ganga&&<span className="text-[9px] font-black text-amber-700 dark:text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded-full">🔥</span>}
              </div>
              <p className="text-[10px] text-on-surface-variant">{getCityName(ruta.origen)} → {getCityName(ruta.destino)}</p>
            </div>
          </div>
          <button onClick={e=>{e.stopPropagation();onDelete();}}
            className="opacity-0 group-hover:opacity-100 text-on-surface-variant/30 hover:text-rose-400 transition p-1 rounded-lg hover:bg-rose-500/10">
            <span className="material-symbols-outlined text-[14px]">delete</span>
          </button>
        </div>

        {precio?(
          <div className={`rounded-xl p-3 mb-3 ${ganga?'bg-amber-500/8 border border-amber-500/15':'bg-surface-container border border-outline-variant/10'}`}>
            <div className="flex items-start justify-between">
              <div>
                <p className={`text-2xl font-black leading-none ${ganga?'text-amber-700 dark:text-amber-400':'text-primary'}`}>
                  ${precio.precio.toLocaleString()}
                  <span className="text-xs font-normal text-on-surface-variant ml-1">USD</span>
                </p>
                {precio.fecha_vuelo&&precio.fecha_vuelo!=='N/D'&&(
                  <p className="text-[10px] text-on-surface-variant mt-1 flex items-center gap-1">
                    <span className="material-symbols-outlined text-[11px]">calendar_today</span>
                    {precio.fecha_vuelo}
                  </p>
                )}
              </div>
              <div className="text-right space-y-0.5">
                {precio.precio_alerta>0&&<p className="text-[10px] text-on-surface-variant">🎯 ${precio.precio_alerta}</p>}
                {precio.mediana>0&&<p className="text-[10px] text-on-surface-variant">≈ ${precio.mediana}</p>}
              </div>
            </div>
            <Sparkline data={hist} ganga={ganga}/>
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-outline-variant/10">
              <FreshBadge fecha={precio.fecha}/>
              {(precio.url_vuelo||ruta.origen)&&(
                <a
                  href={precio.url_vuelo||`https://www.google.com/travel/flights?q=Flights+to+${ruta.destino}+from+${ruta.origen}&hl=es-419&curr=USD`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={e=>e.stopPropagation()}
                  onTouchEnd={e=>e.stopPropagation()}
                  className="flex items-center gap-0.5 text-[10px] text-on-surface-variant hover:text-primary transition underline underline-offset-2 decoration-dotted">
                  <span className="material-symbols-outlined text-[10px]">open_in_new</span>
                  Ver en Google Flights
                </a>
              )}
            </div>
          </div>
        ):(
          <div className="rounded-xl p-4 mb-3 bg-surface-container border border-dashed border-outline-variant/20 text-center">
            <p className="text-xs text-on-surface-variant/40">⏳ Esperando consulta del bot...</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-1.5 mb-2">
          {[{l:'Salida',v:ruta.ida},{l:'Retorno',v:ruta.vuelta}].map(f=>(
            <div key={f.l} className="bg-surface-container rounded-lg px-2.5 py-1.5">
              <p className="text-[9px] uppercase tracking-wider text-on-surface-variant font-bold">{f.l}</p>
              <p className="text-xs font-semibold">{f.v||'—'}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-1">
          {ruta.dias_paquete&&<span className="text-[9px] font-bold text-tertiary bg-tertiary/10 border border-tertiary/15 px-2 py-0.5 rounded-full">{ruta.dias_paquete}d</span>}
          {precio?.tipo_vuelo&&precio.tipo_vuelo!=='N/D'&&(
            <span className="text-[9px] text-on-surface-variant bg-surface-container border border-outline-variant/15 px-2 py-0.5 rounded-full">
              {precio.tipo_vuelo==='DIR'?'✈ directo':'🛬 escala'}
            </span>
          )}
          {ganga&&<span className="text-[9px] font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/15 px-2 py-0.5 rounded-full">✓ bajo alerta</span>}
        </div>

        {expanded&&hist.length>1&&(
          <div className="mt-3 pt-3 border-t border-outline-variant/10" onClick={e=>e.stopPropagation()}>
            <p className="text-[9px] uppercase tracking-widest text-on-surface-variant/50 font-bold mb-2">Historial</p>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {hist.slice().reverse().map((h,i)=>(
                <div key={i} className={`flex justify-between px-2.5 py-1 rounded-lg text-xs ${h.es_ganga?'bg-amber-500/8':'bg-surface-container'}`}>
                  <span className="text-on-surface-variant">{fmtEC(h.fecha)}</span>
                  <span className={`font-bold ${h.es_ganga?'text-amber-700 dark:text-amber-400':'text-on-surface'}`}>
                    ${h.precio.toLocaleString()} {h.es_ganga&&'🔥'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        {hist.length>1&&(
          <p className="text-[9px] text-on-surface-variant/30 text-center mt-2">
            {expanded?'▲ cerrar':`▼ historial (${hist.length})`}
          </p>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [rutas, setRutas] = useState<any[]>([]);
  const [precios, setPrecios] = useState<Record<string,PrecioData>>({});
  const [historial, setHistorial] = useState<Record<string,HistorialEntry[]>>({});
  const [cargando, setCargando] = useState(true);
  const [errorSync, setErrorSync] = useState('');
  const [vista, setVista] = useState<Vista>('todas');
  const [filtroRegion, setFiltroRegion] = useState<string|null>(null);
  const [filtroOrigen, setFiltroOrigen] = useState<string|null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [expandido, setExpandido] = useState<string|null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [nuevoVuelo, setNuevoVuelo] = useState({origen:'',destino:'',ida:'',vuelta:'',alerta:'',dias_paquete:''});
  const [tipoFecha, setTipoFecha] = useState<'mes'|'exacta'>('mes');
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  const cargar = async () => {
    try {
      setCargando(true);
      const [r1,r2] = await Promise.all([fetch('/api/flights'),fetch('/api/prices')]);
      const d1=await r1.json(), d2=await r2.json();
      if (d1.success) setRutas(d1.flights);
      if (d2.success) {
        const m:Record<string,PrecioData>={};
        for (const p of d2.precios) {
          const k = p.ruta.replace(/\s*➡️\s*/g,' -> ').replace(/\s*→\s*/g,' -> ').trim();
          m[k]=p;
        }
        setPrecios(m);
        setHistorial(d2.historial||{});
      }
      setErrorSync('');
    } catch(e:any) { setErrorSync(e.message); }
    finally { setCargando(false); }
  };

  useEffect(()=>{setMounted(true);cargar();},[]);

  const getPrecio = (o:string,d:string) => precios[`${o} -> ${d}`]||precios[`${o} ➡️ ${d}`]||null;
  const getHist = (o:string,d:string) => historial[`${o} -> ${d}`]||historial[`${o} ➡️ ${d}`]||[];

  const eliminar = async (id:number) => {
    setRutas(rutas.filter(r=>r.id!==id));
    await fetch(`/api/flights?id=${id}`,{method:'DELETE'});
    cargar();
  };

  const agregar = async (e:React.FormEvent) => {
    e.preventDefault();
    const nueva={id:Date.now(),...nuevoVuelo,
      alerta:nuevoVuelo.alerta?Number(nuevoVuelo.alerta):'',
      dias_paquete:nuevoVuelo.dias_paquete?Number(nuevoVuelo.dias_paquete):''};
    setRutas([...rutas,nueva]);
    setMostrarForm(false);
    setNuevoVuelo({origen:'',destino:'',ida:'',vuelta:'',alerta:'',dias_paquete:''});
    await fetch('/api/flights',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(nueva)});
    cargar();
  };

  const parseFecha = (s:string) => {
    if(!s)return null;
    const p=s.split('-');
    return p.length===2?new Date(+p[0],+p[1]-1,1):p.length===3?new Date(+p[0],+p[1]-1,+p[2]):null;
  };
  const fmtFecha = (d:Date|null,t:string) => !d?'':t==='mes'?format(d,'yyyy-MM'):format(d,'yyyy-MM-dd');

  const rutasPorDestino = rutas.reduce((acc:Record<string,any[]>,r)=>{
    (acc[r.destino]=acc[r.destino]||[]).push(r);return acc;
  },{});

  const rutasFiltradas = rutas.filter(r=>{
    const p=getPrecio(r.origen,r.destino);
    if(vista==='gangas'&&!p?.es_ganga)return false;
    if(filtroRegion&&!(REGIONES[filtroRegion]||[]).includes(r.destino))return false;
    if(filtroOrigen&&r.origen!==filtroOrigen)return false;
    if(busqueda){
      const t=busqueda.toLowerCase();
      return r.origen.toLowerCase().includes(t)||r.destino.toLowerCase().includes(t)||
        getCityName(r.origen).toLowerCase().includes(t)||getCityName(r.destino).toLowerCase().includes(t);
    }
    return true;
  });

  const totalGangas = rutas.filter(r=>getPrecio(r.origen,r.destino)?.es_ganga).length;
  const ultimaAct = Object.values(precios).sort((a,b)=>new Date(b.fecha).getTime()-new Date(a.fecha).getTime())[0]?.fecha;

  return (
    <div className="min-h-screen bg-background text-on-background font-sans overflow-x-hidden">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary/5 rounded-full blur-3xl"/>
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-tertiary/4 rounded-full blur-3xl"/>
      </div>

      {/* ── TOP BAR ── */}
      <header className="sticky top-0 z-40 bg-background/90 backdrop-blur-xl border-b border-outline-variant/15 w-full">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 h-14 flex items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-2 flex-shrink-0">
            <img src="/logo_marcka.svg" alt="Marcka" className="h-4 w-auto hidden dark:block"/>
            <img src="/logo_marcka_dark.svg" alt="Marcka" className="h-4 w-auto dark:hidden"/>
          </div>

          {/* Tabs — desktop only */}
          <div className="hidden md:flex gap-1 bg-surface-container-low border border-outline-variant/15 rounded-xl p-1">
            {([
              {id:'todas',label:'✈️ Todas las rutas'},
              {id:'gangas',label:`🔥 Gangas (${totalGangas})`},
              {id:'comparativa',label:'⚖️ GYE vs UIO'},
            ] as const).map(t=>(
              <button key={t.id} onClick={()=>setVista(t.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition whitespace-nowrap
                  ${vista===t.id?'bg-primary text-white shadow-sm':'text-on-surface-variant hover:text-on-surface'}`}>
                {t.label}
              </button>
            ))}
          </div>

          {/* Buscador desktop */}
          <div className="relative flex-1 max-w-xs hidden md:block">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[15px]">search</span>
            <input value={busqueda} onChange={e=>setBusqueda(e.target.value)}
              placeholder="Buscar destino..."
              className="w-full bg-surface-container-low border border-outline-variant/20 rounded-xl py-2 pl-8 pr-3 text-xs outline-none focus:border-primary transition"/>
          </div>

          <div className="flex items-center gap-1.5 ml-auto">
            {ultimaAct&&<FreshBadge fecha={ultimaAct}/>}
            <button onClick={cargar} className="p-2 rounded-xl bg-surface-container-low border border-outline-variant/20 text-on-surface-variant hover:text-primary transition">
              <span className="material-symbols-outlined text-[18px]">refresh</span>
            </button>
            {mounted&&(
              <div className="hidden sm:flex bg-surface-container-low border border-outline-variant/20 rounded-xl p-0.5">
                {(['light','dark','system'] as const).map(t=>(
                  <button key={t} onClick={()=>setTheme(t)}
                    className={`p-1.5 rounded-lg transition ${theme===t?'bg-primary/15 text-primary':'text-on-surface-variant hover:text-on-surface'}`}>
                    <span className="material-symbols-outlined text-[15px]">
                      {t==='light'?'light_mode':t==='dark'?'dark_mode':'desktop_windows'}
                    </span>
                  </button>
                ))}
              </div>
            )}
            <button onClick={()=>setMostrarForm(!mostrarForm)}
              className="flex items-center gap-1.5 bg-primary text-white font-bold px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm hover:bg-primary/90 transition shadow-md shadow-primary/20">
              <span className="material-symbols-outlined text-[16px] sm:text-[18px]">{mostrarForm?'close':'add'}</span>
              <span className="hidden sm:block">{mostrarForm?'Cancelar':'Nueva Ruta'}</span>
            </button>
          </div>
        </div>

        {/* Buscador móvil */}
        <div className="md:hidden px-3 pb-2">
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[16px]">search</span>
            <input value={busqueda} onChange={e=>setBusqueda(e.target.value)}
              placeholder="Buscar destino o ciudad..."
              className="w-full bg-surface-container-low border border-outline-variant/20 rounded-xl py-2.5 pl-9 pr-8 text-sm outline-none focus:border-primary transition"/>
            {busqueda&&<button onClick={()=>setBusqueda('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant">
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>}
          </div>
        </div>
      </header>

      {/* ── FORMULARIO ── */}
      {mostrarForm&&(
        <div className="border-b border-outline-variant/15 bg-surface-container-low">
          <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4">
            <form onSubmit={agregar}>
              {/* Toggle mes / día exacto */}
              <div className="flex gap-1 bg-surface-container border border-outline-variant/20 rounded-xl p-1 w-fit mb-3">
                <button type="button" onClick={()=>setTipoFecha('mes')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${tipoFecha==='mes'?'bg-primary text-white':'text-on-surface-variant hover:text-on-surface'}`}>
                  📅 Mes entero
                </button>
                <button type="button" onClick={()=>setTipoFecha('exacta')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${tipoFecha==='exacta'?'bg-primary text-white':'text-on-surface-variant hover:text-on-surface'}`}>
                  🗓️ Día exacto
                </button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                {[{l:'Origen',k:'origen',ph:'GYE'},{l:'Destino',k:'destino',ph:'MAD'}].map(f=>(
                  <div key={f.k}>
                    <label className="text-[9px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1">{f.l}</label>
                    <input required value={(nuevoVuelo as any)[f.k]}
                      onChange={e=>setNuevoVuelo({...nuevoVuelo,[f.k]:e.target.value.toUpperCase()})}
                      maxLength={3} placeholder={f.ph}
                      className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-2.5 py-2 text-sm font-bold uppercase outline-none focus:border-primary h-[38px]"/>
                  </div>
                ))}
                {(['ida','vuelta'] as const).map(k=>(
                  <div key={k}>
                    <label className="text-[9px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1">
                      {k==='ida'?'Fecha ida':'Fecha vuelta'}
                    </label>
                    <DatePicker
                      selected={parseFecha((nuevoVuelo as any)[k])}
                      onChange={(d:Date|null)=>setNuevoVuelo({...nuevoVuelo,[k]:fmtFecha(d,tipoFecha)})}
                      dateFormat={tipoFecha==='mes'?'MM/yyyy':'dd/MM/yyyy'}
                      showMonthYearPicker={tipoFecha==='mes'}
                      locale={es}
                      wrapperClassName="w-full"
                      placeholderText={tipoFecha==='mes'?'MM/YYYY':'DD/MM/YYYY'}
                      className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-2.5 py-2 text-xs outline-none focus:border-primary h-[38px]"/>
                  </div>
                ))}
                <div>
                  <label className="text-[9px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1">Días</label>
                  <input value={nuevoVuelo.dias_paquete} onChange={e=>setNuevoVuelo({...nuevoVuelo,dias_paquete:e.target.value})}
                    type="number" placeholder="6"
                    className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-2.5 py-2 text-sm outline-none focus:border-primary h-[38px]"/>
                </div>
                <div>
                  <label className="text-[9px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1">Alerta $</label>
                  <input value={nuevoVuelo.alerta} onChange={e=>setNuevoVuelo({...nuevoVuelo,alerta:e.target.value})}
                    type="number" placeholder="350"
                    className="w-full bg-surface-container border border-outline-variant/30 rounded-lg px-2.5 py-2 text-sm outline-none focus:border-primary h-[38px]"/>
                </div>
              </div>
              <div className="mt-3 flex justify-end">
                <button type="submit" className="flex items-center gap-1.5 bg-primary text-white font-bold px-5 py-2 rounded-xl text-xs hover:bg-primary/90 transition">
                  <span className="material-symbols-outlined text-[16px]">save</span>Guardar ruta
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── LAYOUT PRINCIPAL ── */}
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 flex gap-5 relative z-10">

        {/* SIDEBAR DESKTOP */}
        <aside className="hidden md:block w-52 flex-shrink-0">
          <div className="sticky top-20 space-y-3">
            <div className="bg-surface-container-low border border-outline-variant/15 rounded-2xl p-4 space-y-2">
              <p className="text-[9px] uppercase tracking-widest text-on-surface-variant font-bold">Resumen</p>
              <div className="flex justify-between text-xs"><span className="text-on-surface-variant">Rutas</span><span className="font-bold">{rutas.length}</span></div>
              <div className="flex justify-between text-xs"><span className="text-on-surface-variant">Gangas</span><span className="font-bold text-amber-700 dark:text-amber-400">{totalGangas}</span></div>
              <div className="flex justify-between text-xs"><span className="text-on-surface-variant">Mostrando</span><span className="font-bold text-primary">{rutasFiltradas.length}</span></div>
            </div>
            <div className="bg-surface-container-low border border-outline-variant/15 rounded-2xl p-4">
              <p className="text-[9px] uppercase tracking-widest text-on-surface-variant font-bold mb-3">Origen</p>
              <div className="space-y-1">
                {[{id:null,label:'Todos'},{id:'GYE',label:'✈ Guayaquil'},{id:'UIO',label:'✈ Quito'}].map(o=>(
                  <button key={String(o.id)} onClick={()=>setFiltroOrigen(filtroOrigen===o.id?null:o.id)}
                    className={`w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium transition
                      ${filtroOrigen===o.id?'bg-primary/15 text-primary border border-primary/20':'text-on-surface-variant hover:bg-surface-container'}`}>
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="bg-surface-container-low border border-outline-variant/15 rounded-2xl p-4">
              <p className="text-[9px] uppercase tracking-widest text-on-surface-variant font-bold mb-3">Región</p>
              <div className="space-y-1">
                <button onClick={()=>setFiltroRegion(null)}
                  className={`w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium transition
                    ${!filtroRegion?'bg-primary/15 text-primary border border-primary/20':'text-on-surface-variant hover:bg-surface-container'}`}>
                  Todas
                </button>
                {Object.keys(REGIONES).map(r=>{
                  const cnt=rutas.filter(ru=>REGIONES[r].includes(ru.destino)).length;
                  return (
                    <button key={r} onClick={()=>setFiltroRegion(filtroRegion===r?null:r)}
                      className={`w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium transition flex justify-between
                        ${filtroRegion===r?'bg-primary/15 text-primary border border-primary/20':'text-on-surface-variant hover:bg-surface-container'}`}>
                      <span>{r}</span>
                      <span className={`text-[10px] px-1.5 rounded-full ${filtroRegion===r?'bg-primary/20':'bg-surface-container'}`}>{cnt}</span>
                    </button>
                  );
                })}
              </div>
            </div>
            {(filtroRegion||filtroOrigen||busqueda)&&(
              <button onClick={()=>{setFiltroRegion(null);setFiltroOrigen(null);setBusqueda('');}}
                className="w-full text-xs text-on-surface-variant hover:text-rose-400 transition py-2 border border-outline-variant/20 rounded-xl hover:border-rose-400/30">
                ✕ Limpiar filtros
              </button>
            )}
          </div>
        </aside>

        {/* DRAWER MÓVIL */}
        {sidebarOpen&&(
          <div className="fixed inset-0 z-50 md:hidden">
            <div className="absolute inset-0 bg-black/50" onClick={()=>setSidebarOpen(false)}/>
            <div className="absolute bottom-16 left-0 right-0 bg-background rounded-t-3xl p-5 max-h-[75vh] overflow-y-auto">
              <div className="w-10 h-1 bg-outline-variant/40 rounded-full mx-auto mb-5"/>
              <p className="font-bold text-base mb-4">Filtros</p>
              <div className="space-y-4">
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-2">Origen</p>
                  <div className="flex gap-2">
                    {[{id:null,label:'Todos'},{id:'GYE',label:'GYE · Guayaquil'},{id:'UIO',label:'UIO · Quito'}].map(o=>(
                      <button key={String(o.id)} onClick={()=>setFiltroOrigen(filtroOrigen===o.id?null:o.id)}
                        className={`flex-1 py-2 rounded-xl text-xs font-bold transition border
                          ${filtroOrigen===o.id?'bg-primary text-white border-primary':'bg-surface-container text-on-surface-variant border-outline-variant/20'}`}>
                        {o.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-2">Región</p>
                  <div className="grid grid-cols-2 gap-2">
                    {[{id:null,label:'🌐 Todas'},...Object.keys(REGIONES).map(r=>({id:r,label:r}))].map(r=>(
                      <button key={String(r.id)} onClick={()=>setFiltroRegion(filtroRegion===r.id?null:r.id)}
                        className={`py-2.5 px-3 rounded-xl text-xs font-bold transition border text-left
                          ${filtroRegion===r.id?'bg-primary text-white border-primary':'bg-surface-container text-on-surface-variant border-outline-variant/20'}`}>
                        {r.label}
                      </button>
                    ))}
                  </div>
                </div>
                {(filtroRegion||filtroOrigen||busqueda)&&(
                  <button onClick={()=>{setFiltroRegion(null);setFiltroOrigen(null);setBusqueda('');setSidebarOpen(false);}}
                    className="w-full py-3 text-sm font-bold text-rose-400 border border-rose-400/20 rounded-xl">
                    ✕ Limpiar filtros
                  </button>
                )}
                <button onClick={()=>setSidebarOpen(false)}
                  className="w-full py-3 text-sm font-bold bg-primary text-white rounded-xl">
                  Ver {rutasFiltradas.length} rutas
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CONTENIDO */}
        <main className="flex-1 min-w-0 w-full overflow-hidden">
          {cargando?(
            <div className="flex flex-col items-center justify-center py-32 gap-3">
              <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin"/>
              <p className="text-on-surface-variant text-sm">Cargando datos...</p>
            </div>

          ):vista==='comparativa'?(
            <div className="space-y-2">
              {Object.entries(rutasPorDestino).map(([dest,rs])=>{
                const pGYE=getPrecio('GYE',dest), pUIO=getPrecio('UIO',dest);
                const barato=pGYE&&pUIO?(pGYE.precio<=pUIO.precio?'GYE':'UIO'):null;
                const hayGanga=pGYE?.es_ganga||pUIO?.es_ganga;
                return(
                  <div key={dest} className="bg-surface-container-low border border-outline-variant/15 rounded-2xl overflow-hidden">
                    <div className={`px-4 py-2.5 flex items-center justify-between ${hayGanga?'border-b border-amber-500/20 bg-amber-500/5':'border-b border-outline-variant/10'}`}>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="material-symbols-outlined text-primary text-[14px]">location_on</span>
                        <span className="font-bold text-sm">{dest}</span>
                        <span className="text-on-surface-variant text-xs hidden sm:block">— {getCityName(dest)}</span>
                        <span className="text-[10px] text-on-surface-variant bg-surface-container px-2 py-0.5 rounded-full">{getRegion(dest)}</span>
                      </div>
                      {hayGanga&&<span className="text-[10px] font-bold text-amber-700 dark:text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full flex-shrink-0">🔥 GANGA</span>}
                    </div>
                    <div className="grid grid-cols-2 divide-x divide-outline-variant/10">
                      {[{org:'GYE',p:pGYE},{org:'UIO',p:pUIO}].map(({org,p})=>(
                        <div key={org} className={`p-3 ${barato===org&&p?'bg-emerald-500/5':''}`}>
                          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1.5">{org} → {dest}</p>
                          {p?(
                            <>
                              <p className={`text-xl font-black ${p.es_ganga?'text-amber-700 dark:text-amber-400':barato===org?'text-emerald-700 dark:text-emerald-400':'text-on-background'}`}>
                                ${p.precio.toLocaleString()} <span className="text-xs font-normal text-on-surface-variant">USD</span>
                              </p>
                              {p.fecha_vuelo&&p.fecha_vuelo!=='N/D'&&<p className="text-[10px] text-on-surface-variant mt-0.5">📅 {p.fecha_vuelo}</p>}
                              {barato===org&&<p className="text-[10px] text-emerald-700 dark:text-emerald-400 font-bold mt-1">✓ más económico</p>}
                              {p.url_vuelo&&<a href={p.url_vuelo} target="_blank" rel="noopener noreferrer"
                                className="text-[10px] text-on-surface-variant/40 hover:text-primary flex items-center gap-0.5 mt-1 transition">
                                <span className="material-symbols-outlined text-[11px]">open_in_new</span>ver
                              </a>}
                            </>
                          ):<p className="text-xs text-on-surface-variant/40 mt-3">sin datos</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

          ):rutasFiltradas.length===0?(
            <div className="text-center py-24">
              <span className="material-symbols-outlined text-5xl text-on-surface-variant/20 block mb-3">
                {vista==='gangas'?'savings':'search_off'}
              </span>
              <p className="text-on-surface-variant text-sm">
                {vista==='gangas'?'No hay gangas activas ahora mismo':'Sin rutas con esos filtros'}
              </p>
              {(filtroRegion||filtroOrigen)&&(
                <button onClick={()=>{setFiltroRegion(null);setFiltroOrigen(null);}}
                  className="mt-3 text-xs text-primary hover:underline">Limpiar filtros</button>
              )}
            </div>

          ):(
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
              {rutasFiltradas.map(ruta=>{
                const p=getPrecio(ruta.origen,ruta.destino);
                const h=getHist(ruta.origen,ruta.destino);
                const key=`${ruta.origen}-${ruta.destino}`;
                return(
                  <RutaCard key={ruta.id} ruta={ruta} precio={p} hist={h}
                    expanded={expandido===key}
                    onExpand={()=>setExpandido(expandido===key?null:key)}
                    onDelete={()=>eliminar(ruta.id)}/>
                );
              })}
            </div>
          )}
        </main>
      </div>

      {/* ── FOOTER ── */}
      <footer className="hidden md:block text-center py-6 border-t border-outline-variant/10 mt-8">
        <img src="/logo_marcka.svg" alt="Marcka" className="h-5 w-auto mx-auto mb-2 hidden dark:block opacity-60"/>
        <img src="/logo_marcka_dark.svg" alt="Marcka" className="h-5 w-auto mx-auto mb-2 dark:hidden opacity-60"/>
        <p className="text-[10px] text-on-surface-variant/50">
          © {new Date().getFullYear()} Todos los derechos reservados · Hecho por{' '}
          <a href="https://www.marcka.art" target="_blank" rel="noopener noreferrer"
            className="hover:text-primary transition">Marcka</a>
          {' '}· <a href="https://www.marcka.art" target="_blank" rel="noopener noreferrer"
            className="hover:text-primary transition">www.marcka.art</a>
        </p>
      </footer>

      {/* ── BARRA NAVEGACIÓN INFERIOR — solo móvil ── */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-background/95 backdrop-blur-xl border-t border-outline-variant/15">
        <div className="flex items-stretch h-16 px-1">
          {[
            {id:'todas' as Vista, icon:'flight', label:'Rutas'},
            {id:'gangas' as Vista, icon:'local_fire_department', label:'Gangas'},
            {id:'comparativa' as Vista, icon:'compare_arrows', label:'vs GYE/UIO'},
            {id:'filtros' as const, icon:'tune', label:'Filtros'},
          ].map(t=>(
            <button key={t.id}
              onClick={()=>t.id==='filtros'?setSidebarOpen(!sidebarOpen):setVista(t.id as Vista)}
              className={`flex-1 flex flex-col items-center justify-center gap-0.5 relative transition-all active:scale-95
                ${(t.id!=='filtros'&&vista===t.id)||(t.id==='filtros'&&sidebarOpen)
                  ?'text-primary'
                  :'text-on-surface-variant'
                }`}>
              {t.id==='gangas'&&totalGangas>0&&(
                <span className="absolute top-2 right-[calc(50%-14px)] w-4 h-4 bg-amber-500 text-white text-[9px] font-black rounded-full flex items-center justify-center z-10">
                  {totalGangas}
                </span>
              )}
              <span className="material-symbols-outlined text-[22px]">{t.icon}</span>
              <span className="text-[10px] font-semibold leading-none">{t.label}</span>
              {((t.id!=='filtros'&&vista===t.id)||(t.id==='filtros'&&sidebarOpen))&&(
                <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-primary rounded-full"/>
              )}
            </button>
          ))}
        </div>
        <div style={{height:'env(safe-area-inset-bottom)'}} className="bg-background/95"/>
      </nav>
      <div className="h-20 md:hidden"/>

    </div>
  );
}

