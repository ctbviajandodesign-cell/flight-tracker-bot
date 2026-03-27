'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

type Perfil = {
  id: string;
  email: string;
  nombre: string;
  rol: 'superadmin' | 'admin' | 'user';
  activo: boolean;
  creado_at: string;
};

export default function AdminPage() {
  const [perfiles, setPerfiles] = useState<Perfil[]>([]);
  const [miRol, setMiRol] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [nuevoUsuario, setNuevoUsuario] = useState({ email: '', nombre: '', password: '', rol: 'user' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const router = useRouter();

  useEffect(() => {
    cargarDatos();
  }, []);

  const cargarDatos = async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { router.push('/login'); return; }

      const { data: miPerfil } = await supabase.from('perfiles').select('rol').eq('id', user.id).single();
      if (!miPerfil || miPerfil.rol === 'user') { router.push('/'); return; }
      setMiRol(miPerfil.rol);

      const { data } = await supabase.from('perfiles').select('*').order('creado_at', { ascending: false });
      setPerfiles(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const crearUsuario = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setSuccess('');
    try {
      const res = await fetch('/api/admin/usuarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nuevoUsuario),
      });
      const data = await res.json();
      if (!data.success) { setError(data.error); return; }
      setSuccess('Usuario creado correctamente');
      setMostrarForm(false);
      setNuevoUsuario({ email: '', nombre: '', password: '', rol: 'user' });
      cargarDatos();
    } catch (e) {
      setError('Error al crear usuario');
    }
  };

  const toggleActivo = async (id: string, activo: boolean) => {
    await supabase.from('perfiles').update({ activo: !activo }).eq('id', id);
    cargarDatos();
  };

  const cambiarRol = async (id: string, rol: string) => {
    await supabase.from('perfiles').update({ rol }).eq('id', id);
    cargarDatos();
  };

  const ROL_COLORS: Record<string, string> = {
    superadmin: 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/20',
    admin: 'bg-primary/15 text-primary border-primary/20',
    user: 'bg-surface-container text-on-surface-variant border-outline-variant/20',
  };

  if (loading) return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin"/>
    </div>
  );

  return (
    <div className="min-h-screen bg-background text-on-background font-sans">
      <header className="sticky top-0 z-40 bg-background/90 backdrop-blur-xl border-b border-outline-variant/15">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center gap-3">
          <button onClick={() => router.push('/')} className="p-2 rounded-xl text-on-surface-variant hover:text-on-surface transition">
            <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          </button>
          <div>
            <h1 className="font-black text-sm">Panel de Administración</h1>
            <p className="text-[10px] text-on-surface-variant">Gestión de usuarios y accesos</p>
          </div>
          <button onClick={() => setMostrarForm(!mostrarForm)}
            className="ml-auto flex items-center gap-1.5 bg-primary text-white font-bold px-4 py-2 rounded-xl text-xs hover:bg-primary/90 transition">
            <span className="material-symbols-outlined text-[16px]">{mostrarForm ? 'close' : 'person_add'}</span>
            {mostrarForm ? 'Cancelar' : 'Nuevo usuario'}
          </button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-6">

        {/* Alertas */}
        {error && <p className="text-rose-400 text-sm bg-rose-500/10 border border-rose-500/20 px-4 py-3 rounded-xl mb-4">{error}</p>}
        {success && <p className="text-emerald-400 text-sm bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 rounded-xl mb-4">✅ {success}</p>}

        {/* Formulario nuevo usuario */}
        {mostrarForm && (
          <div className="bg-surface-container-low border border-outline-variant/20 rounded-2xl p-5 mb-6">
            <h2 className="font-bold text-sm mb-4">Crear nuevo usuario</h2>
            <form onSubmit={crearUsuario}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1">Nombre</label>
                  <input required value={nuevoUsuario.nombre} onChange={e => setNuevoUsuario({...nuevoUsuario, nombre: e.target.value})}
                    placeholder="Nombre completo"
                    className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-primary"/>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1">Email</label>
                  <input required type="email" value={nuevoUsuario.email} onChange={e => setNuevoUsuario({...nuevoUsuario, email: e.target.value})}
                    placeholder="correo@ejemplo.com"
                    className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-primary"/>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1">Contraseña</label>
                  <input required type="password" value={nuevoUsuario.password} onChange={e => setNuevoUsuario({...nuevoUsuario, password: e.target.value})}
                    placeholder="Mínimo 8 caracteres"
                    className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-primary"/>
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold block mb-1">Rol</label>
                  <select value={nuevoUsuario.rol} onChange={e => setNuevoUsuario({...nuevoUsuario, rol: e.target.value})}
                    className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-3 py-2.5 text-sm outline-none focus:border-primary">
                    <option value="user">👤 Usuario — solo consultar</option>
                    <option value="admin">⚙️ Admin — editar rutas</option>
                    {miRol === 'superadmin' && <option value="superadmin">👑 Superadmin — control total</option>}
                  </select>
                </div>
              </div>
              <div className="flex justify-end">
                <button type="submit" className="flex items-center gap-1.5 bg-primary text-white font-bold px-5 py-2.5 rounded-xl text-sm hover:bg-primary/90 transition">
                  <span className="material-symbols-outlined text-[16px]">save</span>Crear usuario
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Lista de usuarios */}
        <div className="bg-surface-container-low border border-outline-variant/15 rounded-2xl overflow-hidden">
          <div className="px-5 py-3 border-b border-outline-variant/10">
            <p className="font-bold text-sm">{perfiles.length} usuarios registrados</p>
          </div>
          <div className="divide-y divide-outline-variant/10">
            {perfiles.map(p => (
              <div key={p.id} className="px-5 py-4 flex items-center gap-4 flex-wrap">
                <div className="w-9 h-9 bg-primary/10 rounded-xl flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-primary text-[18px]">person</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-sm truncate">{p.nombre}</p>
                  <p className="text-xs text-on-surface-variant truncate">{p.email}</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Rol badge + selector */}
                  {miRol === 'superadmin' ? (
                    <select value={p.rol} onChange={e => cambiarRol(p.id, e.target.value)}
                      className={`text-[10px] font-bold px-2 py-1 rounded-full border bg-transparent outline-none cursor-pointer ${ROL_COLORS[p.rol]}`}>
                      <option value="user">👤 user</option>
                      <option value="admin">⚙️ admin</option>
                      <option value="superadmin">👑 superadmin</option>
                    </select>
                  ) : (
                    <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${ROL_COLORS[p.rol]}`}>
                      {p.rol}
                    </span>
                  )}
                  {/* Toggle activo */}
                  <button onClick={() => toggleActivo(p.id, p.activo)}
                    className={`text-[10px] font-bold px-3 py-1 rounded-full border transition ${
                      p.activo
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20 hover:bg-rose-500/20'
                    }`}>
                    {p.activo ? '✓ activo' : '✕ inactivo'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
