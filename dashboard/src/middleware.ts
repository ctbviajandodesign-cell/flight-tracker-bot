import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Rutas públicas que no requieren autenticación
const PUBLIC_PATHS = ['/login', '/_next', '/favicon.ico', '/logo_marcka']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Permitir rutas públicas
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  // Verificar cookie de sesión
  const token = request.cookies.get('auth_token')?.value
  const userId = request.cookies.get('user_id')?.value

  // Si no hay token O no hay userId → redirigir a login
  if (!token || !userId) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('from', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Verificar que el token no esté expirado (JWT tiene 3 partes)
  try {
    const parts = token.split('.')
    if (parts.length !== 3) throw new Error('Token inválido')
    
    const payload = JSON.parse(atob(parts[1]))
    const expiry = payload.exp * 1000
    
    if (Date.now() > expiry) {
      // Token expirado — limpiar cookies y redirigir
      const response = NextResponse.redirect(new URL('/login', request.url))
      response.cookies.delete('auth_token')
      response.cookies.delete('user_id')
      response.cookies.delete('user_rol')
      return response
    }
  } catch {
    // Token malformado — redirigir a login
    const response = NextResponse.redirect(new URL('/login', request.url))
    response.cookies.delete('auth_token')
    response.cookies.delete('user_id')
    response.cookies.delete('user_rol')
    return response
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|logo_marcka).*)',
  ],
}
