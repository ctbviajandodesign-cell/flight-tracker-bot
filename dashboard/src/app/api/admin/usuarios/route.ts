import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Cliente con service role para crear usuarios
const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function POST(req: Request) {
  try {
    const { email, password, nombre, rol } = await req.json();

    if (!email || !password || !nombre || !rol) {
      return NextResponse.json({ success: false, error: 'Faltan campos requeridos' });
    }

    // Crear usuario en Supabase Auth
    const { data: authData, error: authError } = await supabaseAdmin.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
    });

    if (authError) {
      return NextResponse.json({ success: false, error: authError.message });
    }

    // Crear perfil con rol
    const { error: perfilError } = await supabaseAdmin
      .from('perfiles')
      .insert({ id: authData.user.id, email, nombre, rol });

    if (perfilError) {
      return NextResponse.json({ success: false, error: perfilError.message });
    }

    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message });
  }
}
