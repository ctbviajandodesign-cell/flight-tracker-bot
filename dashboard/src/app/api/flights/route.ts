import { NextResponse } from 'next/server';
import { GoogleSpreadsheet } from 'google-spreadsheet';
export const dynamic = 'force-dynamic';
import { JWT } from 'google-auth-library';
import path from 'path';
import fs from 'fs';

const SPREADSHEET_ID = '1gawYqtTmsM8cEwW7s-IOFPoeRN-oJO4nO9JcmBmreUk';

const getDoc = async () => {
  let email, key;

  if (process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL && process.env.GOOGLE_PRIVATE_KEY) {
    // Modo Vercel (Hosting)
    email = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
    // La llave puede estar en BASE64 o como texto plano con saltos de línea escapados (\\n).
    const rawKey = process.env.GOOGLE_PRIVATE_KEY || '';
    if (rawKey.includes('BEGIN PRIVATE KEY')) {
      key = rawKey.replace(/\\n/g, '\n');
    } else {
      key = Buffer.from(rawKey, 'base64').toString('utf8'); 
      key = key.replace(/\\n/g, '\n');
    }
  } else {
    // Modo Local (Tu Computadora)
    const credsPath = path.join(process.cwd(), '../credentials.json');
    if (!fs.existsSync(credsPath)) {
      throw new Error('Faltan credenciales: Configura Vercel ENV vars o usa credentials.json localmente.');
    }
    const creds = JSON.parse(fs.readFileSync(credsPath, 'utf-8'));
    email = creds.client_email;
    key = creds.private_key;
  }
  
  const jwt = new JWT({
    email: email,
    key: key,
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  });

  const doc = new GoogleSpreadsheet(SPREADSHEET_ID, jwt);
  await doc.loadInfo();
  return doc;
};

export async function GET() {
  try {
    const doc = await getDoc();
    const sheet = doc.sheetsByIndex[0]; 
    const rows = await sheet.getRows();
    
    const flights = rows.map((row) => {
      return {
        id: row.rowNumber,
        origen: row.get('ORIGEN') || row.get('Origen') || row.get('origen') || '',
        destino: row.get('DESTINO') || row.get('Destino') || row.get('destino') || '',
        ida: row.get('MES DE INICIO') || row.get('Mes_Inicio') || row.get('ida') || '',
        vuelta: row.get('MES DE FIN') || row.get('Mes_Fin') || row.get('vuelta') || '',
        alerta: row.get('Precio_Alerta') || row.get('Alerta') || row.get('alerta') || 0,
        dias_paquete: row.get('Dias_del_Paquete') || row.get('dias_paquete') || '',
        pais_destino: row.get('PAIS_DESTINO') || row.get('pais_destino') || '',
      };
    }).filter(f => f.origen && f.destino);

    return NextResponse.json({ success: true, flights });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const doc = await getDoc();
    const sheet = doc.sheetsByIndex[0];
    await sheet.loadHeaderRow();
    const headers = sheet.headerValues;

    const setVal = (row: any, keys: string[], val: any) => {
      for (const k of keys) { if (headers.includes(k)) { row[k] = val; return; } }
      row[keys[keys.length-1]] = val;
    };

    // ── UPDATE fila existente ──────────────────────────────────
    if (body._update && body.id) {
      const rows = await sheet.getRows();
      const row = rows.find(r => r.rowNumber === body.id);
      if (row) {
        setVal(row, ['ORIGEN','Origen','origen'], body.origen);
        setVal(row, ['DESTINO','Destino','destino'], body.destino);
        setVal(row, ['MES DE INICIO','Mes_Inicio','ida'], body.ida || '');
        setVal(row, ['MES DE FIN','Mes_Fin','vuelta'], body.vuelta || '');
        setVal(row, ['PRECIO ALERTA','Precio_Alerta','Alerta','alerta'], body.alerta || 0);
        setVal(row, ['Dias_del_Paquete','dias_paquete'], body.dias_paquete || '');
        setVal(row, ['PAIS_DESTINO','pais_destino'], body.pais_destino || '');
        await row.save();
      }
      return NextResponse.json({ success: true });
    }

    // ── INSERT fila nueva ──────────────────────────────────────
    const newRow: any = {};
    setVal(newRow, ['ORIGEN','Origen','origen'], body.origen);
    setVal(newRow, ['DESTINO','Destino','destino'], body.destino);
    setVal(newRow, ['MES DE INICIO','Mes_Inicio','ida'], body.ida || '');
    setVal(newRow, ['MES DE FIN','Mes_Fin','vuelta'], body.vuelta || '');
    setVal(newRow, ['PRECIO ALERTA','Precio_Alerta','Alerta','alerta'], body.alerta || 0);
    setVal(newRow, ['Dias_del_Paquete','dias_paquete'], body.dias_paquete || '');
    setVal(newRow, ['PAIS_DESTINO','pais_destino'], body.pais_destino || '');
    await sheet.addRow(newRow);

    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const rowId = searchParams.get('id');
    
    if (!rowId) return NextResponse.json({ success: false }, { status: 400 });

    const doc = await getDoc();
    const sheet = doc.sheetsByIndex[0];
    const rows = await sheet.getRows();
    
    const rowToDelete = rows.find(r => r.rowNumber === Number(rowId));
    if (rowToDelete) {
      await rowToDelete.delete();
    }

    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
