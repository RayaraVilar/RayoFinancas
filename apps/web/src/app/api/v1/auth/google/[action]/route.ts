import { NextResponse } from "next/server";

import { forwardClientAddress } from "@/lib/proxy-headers";

type RouteContext = {
  params: Promise<{ action: string }>;
};

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

export async function GET(request: Request, context: RouteContext) {
  const { action } = await context.params;
  if (action !== "start" && action !== "callback") {
    return NextResponse.json({ detail: "Not Found" }, { status: 404 });
  }

  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL(`/api/v1/auth/google/${action}`, internalApiUrl());
  upstreamUrl.search = requestUrl.search;

  const upstreamHeaders = new Headers({
    Accept: "text/html,application/xhtml+xml",
  });
  forwardClientAddress(upstreamHeaders, request.headers);
  const cookie = request.headers.get("cookie");
  if (cookie) upstreamHeaders.set("Cookie", cookie);
  const requestId = request.headers.get("x-request-id");
  if (requestId) upstreamHeaders.set("X-Request-Id", requestId);

  try {
    const upstream = await fetch(upstreamUrl, {
      method: "GET",
      headers: upstreamHeaders,
      redirect: "manual",
      cache: "no-store",
    });
    const responseHeaders = new Headers();
    const location = upstream.headers.get("location");
    if (location) responseHeaders.set("Location", location);

    const getSetCookie = (upstream.headers as HeadersWithSetCookie).getSetCookie;
    const setCookies = getSetCookie?.call(upstream.headers) ?? [];
    if (setCookies.length > 0) {
      for (const value of setCookies) responseHeaders.append("Set-Cookie", value);
    } else {
      const setCookie = upstream.headers.get("set-cookie");
      if (setCookie) responseHeaders.append("Set-Cookie", setCookie);
    }

    return new Response(null, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.redirect(new URL("/entrar?error=google", publicOrigin(request)), 303);
  }
}
