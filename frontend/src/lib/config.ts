// The address of our FastAPI backend as the BROWSER calls it. During local
// development this points at the backend's dev server (see backend/README
// or backend/.env.example). "NEXT_PUBLIC_" prefixed variables are the only
// ones Next.js allows to be read in browser (client-side) code, since
// they end up visible in the compiled JavaScript.
// Set to an empty value ("NEXT_PUBLIC_API_URL=") together with
// DEV_API_PROXY_TARGET, every call becomes relative ("/api/..."): it goes
// to whatever address the page was opened on (localhost:3000 or a phone
// tunnel) and next.config.ts forwards it to the backend — so the login
// cookies always belong to that same address.
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8020";

// The address of the backend as SERVER code calls it (server components,
// server-api.ts / server-auth.ts, the session refresh in proxy.ts). Server
// code can't use a relative URL, so with the dev proxy on it goes straight
// to DEV_API_PROXY_TARGET; otherwise it is the same address as the browser's.
// Only read on the server (DEV_API_PROXY_TARGET isn't sent to the browser).
export const SERVER_API_BASE_URL = process.env.DEV_API_PROXY_TARGET || API_BASE_URL || "http://localhost:8020";

// The public address of the site itself (e.g. "https://rwcrew.eu"), used to
// build links that end up on paper, such as the QR code on a printed karblad.
// Optional: when unset, callers fall back to the address the browser is on.
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || null;

// Set only on the test deployment (see docker-compose.prod.yml's frontend
// build args) so a banner can warn people they're not on the real site.
// Left unset for production and local development, where no banner shows.
export const ENVIRONMENT_LABEL = process.env.NEXT_PUBLIC_ENVIRONMENT_LABEL || null;
