import { NextResponse } from "next/server";

type HeadersWithSetCookie = Headers & {
  getSetCookie?: () => string[];
};

function internalApiUrl() {
  return process.env.INTERNAL_API_URL ?? "http://localhost:8000";
}

function publicOrigin(request: Request) {
  const host =
    request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const protocol =
    request.headers.get("x-forwarded-proto") ??
    new URL(request.url).protocol.replace(":", "");
  return host ? `${protocol}://${host}` : new URL(request.url).origin;
}

export async function POST(request: Request) {
  const origin = publicOrigin(request);
  try {
    const upstream = await fetch(`${internalApiUrl()}/api/v1/auth/demo`, {
      method: "POST",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!upstream.ok) {
      return NextResponse.redirect(new URL("/entrar?error=demo", origin), 303);
    }
    const payload = (await upstream.json()) as { profile_id: string };
    const response = NextResponse.redirect(
      new URL(`/dashboard?profile=${encodeURIComponent(payload.profile_id)}`, origin),
      303,
    );
    const getSetCookie = (upstream.headers as HeadersWithSetCookie).getSetCookie;
    const setCookies = getSetCookie?.call(upstream.headers) ?? [];
    if (setCookies.length > 0) {
      for (const value of setCookies) response.headers.append("Set-Cookie", value);
    } else {
      const setCookie = upstream.headers.get("set-cookie");
      if (setCookie) response.headers.append("Set-Cookie", setCookie);
    }
    return response;
  } catch {
    return NextResponse.redirect(new URL("/entrar?error=demo", origin), 303);
  }
}
