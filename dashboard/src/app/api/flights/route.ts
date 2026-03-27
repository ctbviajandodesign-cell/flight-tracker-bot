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
    
    const newRow: any = {};
    
    if (headers.includes('ORIGEN')) newRow['ORIGEN'] = body.origen;
    else if (headers.includes('Origen')) newRow['Origen'] = body.origen;
    else newRow['origen'] = body.origen;
    
    if (headers.includes('DESTINO')) newRow['DESTINO'] = body.destino;
    else if (headers.includes('Destino')) newRow['Destino'] = body.destino;
    else newRow['destino'] = body.destino;
    
    if (headers.includes('MES DE INICIO')) newRow['MES DE INICIO'] = body.ida;
    else if (headers.includes('Mes_Inicio')) newRow['Mes_Inicio'] = body.ida;
    else newRow['ida'] = body.ida;
    
    if (headers.includes('MES DE FIN')) newRow['MES DE FIN'] = body.vuelta;
    else if (headers.includes('Mes_Fin')) newRow['Mes_Fin'] = body.vuelta;
    else newRow['vuelta'] = body.vuelta;
    
    if (headers.includes('Precio_Alerta')) newRow['Precio_Alerta'] = body.alerta || 0;
    else if (headers.includes('Alerta')) newRow['Alerta'] = body.alerta || 0;
    else newRow['alerta'] = body.alerta || 0;

    if (headers.includes('Dias_del_Paquete')) newRow['Dias_del_Paquete'] = body.dias_paquete || '';
    else newRow['dias_paquete'] = body.dias_paquete || '';

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
