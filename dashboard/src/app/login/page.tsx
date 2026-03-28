'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authError) {
        setError('Email o contraseña incorrectos');
        return;
      }

      if (!data.session) {
        setError('No se pudo iniciar sesión');
        return;
      }

      // Verificar perfil activo
      const { data: perfil, error: perfilError } = await supabase
        .from('perfiles')
        .select('rol, activo, nombre')
        .eq('id', data.user.id)
        .single();

      if (perfilError || !perfil) {
        setError('No se encontró tu perfil. Contacta al administrador.');
        await supabase.auth.signOut();
        return;
      }

      if (!perfil.activo) {
        setError('Tu cuenta está desactivada. Contacta al administrador.');
        await supabase.auth.signOut();
        return;
      }

      // Guardar cookies con max-age de 7 días
      const maxAge = 60 * 60 * 24 * 7;
      const secure = window.location.protocol === 'https:' ? '; Secure' : '';
      document.cookie = `auth_token=${data.session.access_token}; path=/; max-age=${maxAge}; SameSite=Lax${secure}`;
      document.cookie = `user_rol=${perfil.rol}; path=/; max-age=${maxAge}; SameSite=Lax${secure}`;
      document.cookie = `user_id=${data.user.id}; path=/; max-age=${maxAge}; SameSite=Lax${secure}`;

      router.push('/');
      router.refresh();

    } catch (e) {
      setError('Error al iniciar sesión. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-10 h-10 bg-primary/15 rounded-2xl flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-[24px]">travel_explore</span>
            </div>
            <span className="text-2xl text-on-background" style={{fontFamily:"'Bebas Neue', sans-serif", letterSpacing:'0.05em'}}>MARCKA</span>
          </div>
          <h1 className="text-base font-semibold text-on-surface-variant">Monitor de Vuelos</h1>
          <p className="text-on-surface-variant text-sm mt-1">Ingresa con tu cuenta</p>
        </div>

        {/* Formulario */}
        <div className="bg-surface-container-low border border-outline-variant/20 rounded-2xl p-6 shadow-xl">
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-xs uppercase tracking-widest text-on-surface-variant font-bold block mb-2">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="tu@email.com"
                autoComplete="email"
                className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-3 text-sm outline-none focus:border-primary transition"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-widest text-on-surface-variant font-bold block mb-2">
                Contraseña
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                className="w-full bg-surface-container border border-outline-variant/30 rounded-xl px-4 py-3 text-sm outline-none focus:border-primary transition"
              />
            </div>

            {error && (
              <p className="text-rose-400 text-xs bg-rose-500/10 border border-rose-500/20 px-3 py-2 rounded-lg">
                ⚠️ {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white font-bold py-3 rounded-xl hover:bg-primary/90 transition disabled:opacity-50 flex items-center justify-center gap-2 mt-2">
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
                  Verificando...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[18px]">login</span>
                  Ingresar
                </>
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-on-surface-variant mt-4">
          ¿Sin acceso? Contacta al administrador del sistema.
        </p>
      </div>
    </div>
  );
}
