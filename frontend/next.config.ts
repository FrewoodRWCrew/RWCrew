import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// This wraps our Next.js config so next-intl can plug itself into the
// build process — mainly so it knows where to find src/i18n/request.ts,
// which decides which language's text to load on the server.
const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  // Produces a self-contained ".next/standalone" build (app code + only the
  // node_modules it actually needs) instead of requiring a full npm install
  // on the server — this is what the production Docker image (see
  // frontend/Dockerfile and docs/deploying-to-hostinger.pdf) copies into its
  // final, minimal runtime stage.
  output: "standalone",

  // Local phone testing over an HTTPS tunnel (a Cloudflare quick tunnel, see
  // .env.local.example): phones only allow the camera and GPS on HTTPS, so
  // the dev server is reached through a temporary *.trycloudflare.com
  // address. Next.js's dev server refuses requests from other addresses
  // unless they are listed here; this setting has no effect on production.
  allowedDevOrigins: ["*.trycloudflare.com"],

  // Only when DEV_API_PROXY_TARGET is set (in .env.local, for phone testing):
  // forward "/api/..." to the local backend, so app and API share the
  // tunnel's single address — the same way nginx does it in production.
  async rewrites() {
    const target = process.env.DEV_API_PROXY_TARGET;
    return target ? [{ source: "/api/:path*", destination: `${target}/api/:path*` }] : [];
  },
};

export default withNextIntl(nextConfig);
