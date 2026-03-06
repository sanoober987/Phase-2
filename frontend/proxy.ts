import { NextRequest, NextResponse } from "next/server";

const PROTECTED_ROUTES = ["/dashboard", "/profile"];
const AUTH_ROUTES = ["/login", "/signup"];

/**
 * Lightweight JWT expiry check for Edge middleware.
 * Does NOT verify the signature (no crypto in Edge without jose).
 * Signature verification happens on every backend API call.
 * This check prevents obviously expired tokens from passing the guard.
 */
function isTokenExpired(token: string): boolean {
  try {
    // JWT is base64url-encoded: header.payload.signature
    const payloadB64 = token.split(".")[1];
    if (!payloadB64) return true;

    // atob handles base64url if we pad correctly
    const padded = payloadB64.replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(padded);
    const payload = JSON.parse(json) as { exp?: number };

    if (!payload.exp) return false; // no expiry claim — treat as valid
    return payload.exp * 1000 < Date.now();
  } catch {
    // Malformed token — treat as expired
    return true;
  }
}

export default function proxy(request: NextRequest)  {
  const { pathname } = request.nextUrl;

  const token = request.cookies.get("auth_token")?.value;

  // A token is only "valid" for middleware purposes if it exists AND is not expired
  const hasValidToken = !!token && !isTokenExpired(token);

  const isProtected = PROTECTED_ROUTES.some((route) =>
    pathname.startsWith(route)
  );
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname.startsWith(route));

  // Unauthenticated (or expired token) trying to reach a protected route
  if (isProtected && !hasValidToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    // Clear the stale cookie so the browser does not resend it
    const response = NextResponse.redirect(loginUrl);
    if (token) {
      response.cookies.delete("auth_token");
    }
    return response;
  }

  // Authenticated user trying to reach login/signup → go to dashboard
  if (isAuthRoute && hasValidToken) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/profile/:path*", "/login", "/signup"],
};
