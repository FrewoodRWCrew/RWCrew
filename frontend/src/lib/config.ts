// The address of our FastAPI backend. During local development this
// points at the backend's dev server (see backend/README or
// backend/.env.example). "NEXT_PUBLIC_" prefixed variables are the only
// ones Next.js allows to be read in browser (client-side) code, since
// they end up visible in the compiled JavaScript.
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8020";
