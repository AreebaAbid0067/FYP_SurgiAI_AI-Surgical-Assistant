import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL, SessionUser, TOKEN_COOKIE } from "./app/lib/config";

// Every page requires a valid session; the backend remains the authority.
// Administrators are confined to the admin area and surgeons are kept out of it.
const ADMIN_PREFIXES = ["/verification", "/admin"];
const SHARED_PREFIXES = ["/settings", "/privacy"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(TOKEN_COOKIE)?.value;

  let user: SessionUser | null = null;
  if (token) {
    try {
      const response = await fetch(`${BACKEND_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (response.ok) user = (await response.json()) as SessionUser;
    } catch {
      user = null;
    }
  }

  if (pathname === "/login") {
    if (!user) return NextResponse.next();
    return NextResponse.redirect(new URL(user.role === "admin" ? "/verification" : "/", request.url));
  }

  if (!user) {
    const redirect = NextResponse.redirect(new URL("/login", request.url));
    if (token) redirect.cookies.delete(TOKEN_COOKIE);
    return redirect;
  }

  if (SHARED_PREFIXES.some((prefix) => pathname.startsWith(prefix))) return NextResponse.next();

  const isAdminArea = ADMIN_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  if (user.role === "surgeon" && isAdminArea) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  if (user.role === "admin" && !isAdminArea) {
    return NextResponse.redirect(new URL("/verification", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
