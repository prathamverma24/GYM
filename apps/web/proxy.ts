import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const SESSION_COOKIE = "athleteos_session";

export function proxy(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", `${request.nextUrl.pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/workouts/:path*",
    "/exercises/:path*",
    "/nutrition/:path*",
    "/habits/:path*",
    "/progress/:path*",
    "/body-scan/:path*",
    "/calendar/:path*",
    "/settings/:path*",
    "/profile/:path*",
    "/reports/:path*",
    "/admin/:path*",
  ],
};
