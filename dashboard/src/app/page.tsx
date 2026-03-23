'use client';

import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const IATA_MAP: Record<string, string> = {
  GYE: "Guayaquil",
  UIO: "Quito",
  CUE: "Cuenca",
  SCY: "San Cristóbal",
  GPS: "Baltra",
  BOG: "Bogotá",
  MDE: "Medellín",
  PTY: "Panamá",
  MIA: "Miami",
  NYC: "Nueva York",
  MAD: "Madrid",
  BCN: "Barcelona",
  LIM: "Lima",
  SCL: "Santiago",
  EZE: "Buenos Aires",
  MEX: "Ciudad de México",
  CUN: "Cancún",
  MCO: "Orlando",
  LAX: "Los Ángeles"
};

const getCityName = (code: string) => IATA_MAP[code.toUpperCase()] || "Internacional";

export default function Dashboard() {
  const [rutas, setRutas] = useState<any[]>([]);
  const [cargando, setCargando] = useState(true);
  const [errorSync, setErrorSync] = useState('');
  const [filtro, setFiltro] = useState('');

  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [nuevoVuelo, setNuevoVuelo] = useState({ origen: '', destino: '', ida: '', vuelta: '', alerta: '', dias_paquete: '' });
  const [tipoFecha, setTipoFecha] = useState<'mes' | 'exacta'>('mes');

  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  const cargarRutas = async () => {
    try {
      setCargando(true);
      const res = await fetch('/api/flights');
      const data = await res.json();
      if (data.success) {
        setRutas(data.flights);
        setErrorSync('');
      } else {
        setErrorSync(data.error || 'Error al cargar vuelos');
      }
    } catch (e: any) {
      setErrorSync(e.message);
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    setMounted(true);
    cargarRutas();
  }, []);

  const eliminarRuta = async (id: number) => {
    try {
      setRutas(rutas.filter(ruta => ruta.id !== id)); // Optimistic UI
      const res = await fetch(`/api/flights?id=${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Falló al eliminar');
      cargarRutas();
    } catch (e: any) {
      setErrorSync('Error eliminando ruta: ' + e.message);
      cargarRutas(); // Rollback
    }
  };

  const agregarRuta = async (e: React.FormEvent) => {
    e.preventDefault();
    const tempId = Date.now();
    const nuevaRuta = { 
      id: tempId, 
      ...nuevoVuelo, 
      alerta: nuevoVuelo.alerta ? Number(nuevoVuelo.alerta) : '',
      dias_paquete: nuevoVuelo.dias_paquete ? Number(nuevoVuelo.dias_paquete) : '' 
    };
    
    setRutas([...rutas, nuevaRuta]); // Optimistic UI
    setMostrarFormulario(false);
    setNuevoVuelo({ origen: '', destino: '', ida: '', vuelta: '', alerta: '', dias_paquete: '' });

    try {
      const res = await fetch('/api/flights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nuevaRuta)
      });
      if (!res.ok) throw new Error('Falló al agregar');
      cargarRutas();
    } catch (e: any) {
      setErrorSync('Error agregando ruta: ' + e.message);
      cargarRutas(); // Rollback
    }
  };

  const parseDateString = (dateStr: string, tipo: 'mes' | 'exacta') => {
    if (!dateStr) return null;
    const parts = dateStr.split('-');
    if (parts.length === 2 && tipo === 'mes') {
      return new Date(Number(parts[0]), Number(parts[1]) - 1, 1);
    }
    if (parts.length === 3) {
      return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    }
    return null;
  };

  const formatDateObj = (date: Date | null, tipo: 'mes' | 'exacta') => {
    if (!date) return '';
    return tipo === 'mes' ? format(date, 'yyyy-MM') : format(date, 'yyyy-MM-dd');
  };

  const rutasFiltradas = rutas.filter((ruta) => {
    const term = filtro.toLowerCase();
    const ciudadOrigen = getCityName(ruta.origen).toLowerCase();
    const ciudadDestino = getCityName(ruta.destino).toLowerCase();
    return (
      ruta.origen.toLowerCase().includes(term) ||
      ruta.destino.toLowerCase().includes(term) ||
      ciudadOrigen.includes(term) ||
      ciudadDestino.includes(term)
    );
  });

  return (
    <div className="min-h-screen bg-background text-on-background relative overflow-hidden font-sans transition-colors duration-300 pb-20">
      <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-primary/5 rounded-full blur-[120px] pointer-events-none z-0"></div>
      <div className="absolute bottom-[-10%] left-[20%] w-[40%] h-[40%] bg-secondary/5 rounded-full blur-[120px] pointer-events-none z-0"></div>

      <div className="max-w-5xl mx-auto p-8 relative z-10 pt-16">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 border-b border-outline-variant/20 pb-6 gap-6">
          <div>
            <h1 className="text-4xl font-extrabold bg-gradient-to-r from-primary to-primary-container bg-clip-text text-transparent mb-2">Mis Vuelos a Monitorear</h1>
            <p className="text-on-surface-variant text-sm">
              Estos son los destinos sincronizados con tu Excel oficial.
            </p>
            {errorSync && <p className="text-error mt-2 text-xs font-bold bg-error/10 p-2 rounded">{errorSync}</p>}
          </div>
          <div className="flex flex-col md:flex-row items-center gap-4">
            {mounted && (
              <div className="flex bg-surface-container-low border border-outline-variant/20 rounded-xl p-1 shadow-sm">
                <button onClick={() => setTheme('light')} className={`p-2 rounded-lg flex items-center justify-center transition ${theme === 'light' ? 'bg-surface text-primary shadow-sm ring-1 ring-outline-variant/20' : 'text-on-surface-variant hover:text-on-surface'}`} title="Modo Claro">
                  <span className="material-symbols-outlined text-[20px]">light_mode</span>
                </button>
                <button onClick={() => setTheme('dark')} className={`p-2 rounded-lg flex items-center justify-center transition ${theme === 'dark' ? 'bg-surface text-primary shadow-sm ring-1 ring-outline-variant/20' : 'text-on-surface-variant hover:text-on-surface'}`} title="Modo Oscuro">
                  <span className="material-symbols-outlined text-[20px]">dark_mode</span>
                </button>
                <button onClick={() => setTheme('system')} className={`p-2 rounded-lg flex items-center justify-center transition ${theme === 'system' ? 'bg-surface text-primary shadow-sm ring-1 ring-outline-variant/20' : 'text-on-surface-variant hover:text-on-surface'}`} title="Automático">
                  <span className="material-symbols-outlined text-[20px]">desktop_windows</span>
                </button>
              </div>
            )}
            <button 
              onClick={() => setMostrarFormulario(!mostrarFormulario)}
              className="bg-primary text-surface-container-lowest px-6 py-3 rounded-xl font-bold shadow-[0_0_20px_rgba(143,245,255,0.2)] hover:brightness-110 flex items-center gap-2 transition whitespace-nowrap"
            >
              <span className="material-symbols-outlined font-bold text-xl">{mostrarFormulario ? "close" : "add"}</span>
              {mostrarFormulario ? "Cancelar Agregar" : "Agregar Nueva Ruta"}
            </button>
          </div>
        </header>

        {/* Buscador de Rutas Interactivo */}
        {!mostrarFormulario && rutas.length > 0 && (
          <div className="mb-8 relative max-w-md animate-in fade-in slide-in-from-bottom-2">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">search</span>
            <input 
              type="text" 
              placeholder="Buscar por código (ej. GYE) o ciudad (Miami)..." 
              value={filtro}
              onChange={(e) => setFiltro(e.target.value)}
              className="w-full bg-surface-container-low text-on-surface border border-outline-variant/20 rounded-full py-3 pl-12 pr-4 outline-none focus:border-primary shadow-sm transition-all focus:shadow-md focus:ring-2 ring-primary/20 placeholder:text-on-surface-variant/70 text-sm font-medium"
            />
            {filtro && (
              <button onClick={() => setFiltro('')} className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface">
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            )}
          </div>
        )}

        {mostrarFormulario && (
          <form onSubmit={agregarRuta} className="bg-surface-container-low border border-outline-variant/10 p-6 rounded-2xl mb-10 shadow-xl transition-all animate-in fade-in slide-in-from-top-4">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
              <h2 className="text-xl font-bold text-primary flex items-center gap-2">
                <span className="material-symbols-outlined">flight_takeoff</span>
                Detalles de la nueva ruta
              </h2>
              <div className="flex bg-surface-container-highest rounded-lg border border-outline-variant/20 overflow-hidden shadow-sm">
                <button 
                  type="button"
                  onClick={() => setTipoFecha('mes')}
                  className={`px-4 py-2 text-xs font-bold transition flex items-center gap-2 ${tipoFecha === 'mes' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-container'}`}
                >
                  <span className="material-symbols-outlined text-[16px]">calendar_view_month</span>
                  Mes Entero
                </button>
                <button 
                  type="button"
                  onClick={() => setTipoFecha('exacta')}
                  className={`px-4 py-2 text-xs font-bold transition flex items-center gap-2 ${tipoFecha === 'exacta' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-container'}`}
                >
                  <span className="material-symbols-outlined text-[16px]">event</span>
                  Días Exactos
                </button>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
              <div className="flex flex-col">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant block mb-2 font-bold">Origen</label>
                <input required value={nuevoVuelo.origen} onChange={(e) => setNuevoVuelo({...nuevoVuelo, origen: e.target.value.toUpperCase()})} type="text" maxLength={3} placeholder="GYE" className="w-full bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary placeholder:text-outline-variant/50 uppercase h-[46px]" />
              </div>
              <div className="flex flex-col">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant block mb-2 font-bold">Destino</label>
                <input required value={nuevoVuelo.destino} onChange={(e) => setNuevoVuelo({...nuevoVuelo, destino: e.target.value.toUpperCase()})} type="text" maxLength={3} placeholder="MAD" className="w-full bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary placeholder:text-outline-variant/50 uppercase h-[46px]" />
              </div>
              <div className="flex flex-col relative">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant block mb-2 font-bold flex gap-1 items-center">
                  {tipoFecha === 'mes' ? 'Mes Ida' : 'Día Ida'}
                </label>
                <DatePicker 
                  selected={parseDateString(nuevoVuelo.ida, tipoFecha)}
                  onChange={(date: Date | null) => setNuevoVuelo({...nuevoVuelo, ida: formatDateObj(date, tipoFecha)})} 
                  dateFormat={tipoFecha === 'mes' ? "MM/yyyy" : "dd/MM/yyyy"}
                  showMonthYearPicker={tipoFecha === 'mes'}
                  locale={es}
                  wrapperClassName="w-full"
                  placeholderText={tipoFecha === 'mes' ? "Mes / Año" : "Elige un día"}
                  className="w-full bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary placeholder:text-outline-variant/50 cursor-pointer h-[46px]"
                />
              </div>
              <div className="flex flex-col relative">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant block mb-2 font-bold flex gap-1 items-center">
                  {tipoFecha === 'mes' ? 'Mes Vuelta' : 'Día Vuelta'}
                </label>
                <DatePicker 
                  selected={parseDateString(nuevoVuelo.vuelta, tipoFecha)}
                  onChange={(date: Date | null) => setNuevoVuelo({...nuevoVuelo, vuelta: formatDateObj(date, tipoFecha)})} 
                  dateFormat={tipoFecha === 'mes' ? "MM/yyyy" : "dd/MM/yyyy"}
                  showMonthYearPicker={tipoFecha === 'mes'}
                  locale={es}
                  wrapperClassName="w-full"
                  placeholderText={tipoFecha === 'mes' ? "Mes / Año" : "Elige un día"}
                  className="w-full bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary placeholder:text-outline-variant/50 cursor-pointer h-[46px]"
                />
              </div>
              <div className="flex flex-col">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant block mb-2 font-bold" title="Duración exacta de viaje dentro del mes">Días Viaje</label>
                <input value={nuevoVuelo.dias_paquete} onChange={(e) => setNuevoVuelo({...nuevoVuelo, dias_paquete: e.target.value})} type="number" placeholder="Opc. Ej: 6" className="w-full bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary placeholder:text-outline-variant/50 h-[46px]" />
              </div>
              <div className="flex flex-col">
                <label className="text-xs uppercase tracking-widest text-on-surface-variant block mb-2 font-bold" title="Si lo dejas en blanco, calcula la mediana">Alerta $ USD</label>
                <input value={nuevoVuelo.alerta} onChange={(e) => setNuevoVuelo({...nuevoVuelo, alerta: e.target.value})} type="number" placeholder="Opcional" className="w-full bg-surface-container text-on-surface border border-outline-variant/20 rounded-lg p-3 outline-none focus:border-primary placeholder:text-outline-variant/50 h-[46px]" />
              </div>
            </div>
            <div className="mt-6 flex justify-end">
              <button type="submit" className="bg-gradient-to-r from-primary to-primary-container text-on-primary font-bold px-8 py-3 rounded-lg hover:brightness-110 flex items-center gap-2 transition shadow-md">
                <span className="material-symbols-outlined">save</span>
                Guardar Ruta en Excel
              </button>
            </div>
          </form>
        )}

        {cargando ? (
          <div className="text-center py-20 bg-surface-container-low rounded-2xl border border-outline-variant/10">
            <span className="material-symbols-outlined text-6xl text-primary animate-pulse mb-4">cloud_sync</span>
            <p className="text-primary text-lg font-bold">Sincronizando la base de datos de vuelos...</p>
          </div>
        ) : rutas.length === 0 ? (
          <div className="text-center py-20 bg-surface-container-low rounded-2xl border border-outline-variant/10">
            <span className="material-symbols-outlined text-6xl text-outline-variant mb-4">flight</span>
            <p className="text-on-surface-variant text-lg">Tu Excel está vacío. ¡Agrega tu primer vuelo de monitoreo hoy!</p>
          </div>
        ) : rutasFiltradas.length === 0 ? (
          <div className="text-center py-20 bg-surface-container-low rounded-2xl border border-outline-variant/10">
            <span className="material-symbols-outlined text-6xl text-outline-variant mb-4">search_off</span>
            <p className="text-on-surface-variant text-lg">No se encontraron rutas con el texto <strong>"{filtro}"</strong>.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {rutasFiltradas.map((ruta) => (
              <div key={ruta.id} className="bg-surface-container-low border border-outline-variant/10 hover:border-outline-variant/30 transition-all rounded-2xl p-6 relative group shadow-sm">
                <button 
                  onClick={() => eliminarRuta(ruta.id)}
                  className="absolute top-6 right-6 text-outline-variant hover:text-error transition opacity-0 group-hover:opacity-100"
                  title="Eliminar del monitoreo"
                >
                  <span className="material-symbols-outlined">delete</span>
                </button>
                
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-12 h-12 bg-surface-container-highest rounded-full flex items-center justify-center text-primary border border-outline-variant/20">
                    <span className="material-symbols-outlined font-light text-2xl">flight_takeoff</span>
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold tracking-tight text-on-background flex items-center gap-3">
                      <div className="flex flex-col items-start leading-none group-hover:-translate-y-0.5 transition-transform">
                        <span>{ruta.origen}</span>
                        <span className="text-[9px] text-on-surface-variant font-medium uppercase tracking-wider mt-1.5 opacity-80">{getCityName(ruta.origen)}</span>
                      </div>
                      <span className="text-outline-variant/50 font-light flex items-center h-full pb-3 text-xl">→</span>
                      <div className="flex flex-col items-start leading-none group-hover:-translate-y-0.5 transition-transform">
                        <span>{ruta.destino}</span>
                        <span className="text-[9px] text-on-surface-variant font-medium uppercase tracking-wider mt-1.5 opacity-80">{getCityName(ruta.destino)}</span>
                      </div>
                    </h3>
                    <p className="text-[10px] uppercase tracking-widest text-primary font-bold mt-3 border-t border-outline-variant/10 pt-2 inline-block">
                      {ruta.alerta ? `Presupuesto: $${ruta.alerta} USD` : 'Búsqueda de Gangas Activada ⚡'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 bg-surface-container p-4 rounded-xl border border-outline-variant/10 relative">
                  {ruta.dias_paquete && (
                    <div className="absolute -top-3 right-4 bg-secondary text-surface-container-lowest text-[10px] uppercase font-bold px-3 py-1 rounded-full shadow-sm">
                      Paquete {ruta.dias_paquete} Días
                    </div>
                  )}
                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-on-surface-variant mb-1 font-bold">Salida / Mes</p>
                    <p className="font-medium flex items-center gap-1 text-on-surface text-sm">
                      <span className="material-symbols-outlined text-[16px] text-tertiary">calendar_today</span>
                      {ruta.ida}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-on-surface-variant mb-1 font-bold">Retorno / Mes</p>
                    <p className="font-medium flex items-center gap-1 text-on-surface text-sm">
                      <span className="material-symbols-outlined text-[16px] text-tertiary">calendar_today</span>
                      {ruta.vuelta}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
