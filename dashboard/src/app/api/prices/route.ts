import { NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';

const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_KEY = process.env.SUPABASE_KEY!;

export async function GET() {
  try {
    if (!SUPABASE_URL || !SUPABASE_KEY) {
      return NextResponse.json({ success: false, error: 'Supabase no configurado' }, { status: 500 });
    }

    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/vuelos_historial?select=*&order=fecha.desc&limit=1000`,
      {
        headers: {
          apikey: SUPABASE_KEY,
          Authorization: `Bearer ${SUPABASE_KEY}`,
        },
        cache: 'no-store',
      }
    );

    if (!res.ok) {
      throw new Error(`Supabase error: ${res.status}`);
    }

    const data: any[] = await res.json();

    const ultimoPorRuta: Record<string, any> = {};
    for (const row of data) {
      if (!ultimoPorRuta[row.ruta]) {
        ultimoPorRuta[row.ruta] = row;
      }
    }

    const historialPorRuta: Record<string, any[]> = {};
    for (const row of data) {
      if (!historialPorRuta[row.ruta]) historialPorRuta[row.ruta] = [];
      if (historialPorRuta[row.ruta].length < 30) {
        historialPorRuta[row.ruta].push({
          fecha: row.fecha,
          precio: row.precio,
          es_ganga: row.es_ganga,
        });
      }
    }

    return NextResponse.json({
      success: true,
      precios: Object.values(ultimoPorRuta),
      historial: historialPorRuta,
    });

  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
