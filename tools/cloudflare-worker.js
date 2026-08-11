/**
 * Cloudflare Worker — free reverse proxy so the site is reachable from Iran.
 *
 * Deploy (free, ~5 minutes):
 *   1. Sign up at https://dash.cloudflare.com (email only, no card)
 *   2. Workers & Pages -> Create -> Create Worker -> name: nimabuilds -> Deploy
 *   3. "Edit code" -> delete everything -> paste this file -> Deploy
 *   4. Your Iran-friendly URL: https://nimabuilds.<your-subdomain>.workers.dev
 */

const ORIGIN = "https://nimabuilds.pythonanywhere.com";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const target = ORIGIN + url.pathname + url.search;

    const headers = new Headers(request.headers);
    // let the backend's rate limiter see the real visitor IP
    const realIp = request.headers.get("CF-Connecting-IP");
    if (realIp) headers.set("X-Forwarded-For", realIp);

    const resp = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });

    // keep redirects on the proxy domain
    const out = new Headers(resp.headers);
    const loc = out.get("Location");
    if (loc && loc.startsWith(ORIGIN)) {
      out.set("Location", loc.replace(ORIGIN, url.origin));
    }
    return new Response(resp.body, { status: resp.status, headers: out });
  },
};
