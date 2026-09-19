// The address of our FastAPI backend. During local development this
// points at the backend's dev server (see backend/README or
// backend/.env.example). "NEXT_PUBLIC_" prefixed variables are the only
// ones Next.js allows to be read in browser (client-side) code, since
// they end up visible in the compiled JavaScript.
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8020";

// The public address of the site itself (e.g. "https://rwcrew.eu"), used to
// build links that end up on paper, such as the QR code on a printed karblad.
// Optional: when unset, callers fall back to the address the browser is on.
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || null;

// Set only on the test deployment (see docker-compose.prod.yml's frontend
// build args) so a banner can warn people they're not on the real site.
// Left unset for production and local development, where no banner shows.
export const ENVIRONMENT_LABEL = process.env.NEXT_PUBLIC_ENVIRONMENT_LABEL || null;
