const SAFE_IP = /^[0-9a-fA-F:.]{3,64}$/;

export function forwardClientAddress(
  target: Headers,
  source: Pick<Headers, "get">,
) {
  const raw =
    source.get("x-forwarded-for")?.split(",", 1)[0].trim() ??
    source.get("x-real-ip")?.trim();
  if (raw && SAFE_IP.test(raw)) {
    target.set("X-Forwarded-For", raw);
  }
}
