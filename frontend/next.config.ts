import { execSync } from "node:child_process";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// This wraps our Next.js config so next-intl can plug itself into the
// build process — mainly so it knows where to find src/i18n/request.ts,
// which decides which language's text to load on the server.
const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

/** One git value for the local version label, or "" when git isn't
 * available (e.g. inside the Docker build, which has no .git folder). */
function gitValue(command: string): string {
  try {
    return execSync(command, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

const nextConfig: NextConfig = {
  // The version label (see src/lib/config.ts): on the server it is passed in
  // by deploy/scripts/deploy.sh; locally it is read from git, so localhost
  // shows the commit it's running too.
  env: {
    NEXT_PUBLIC_APP_COMMIT: process.env.NEXT_PUBLIC_APP_COMMIT || gitValue("git rev-parse --short HEAD"),
    NEXT_PUBLIC_APP_COMMIT_DATE:
      process.env.NEXT_PUBLIC_APP_COMMIT_DATE ||
      gitValue("git log -1 --format=%cd --date=format-local:%Y.%m.%d"),
  },

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
  // "192.168.*.*" lets a phone on the same Wi-Fi open http://<PC's IP>:3000
  // (pages work, but without HTTPS the phone blocks the camera and GPS).
  allowedDevOrigins: ["*.trycloudflare.com", "192.168.*.*"],

  // Only when DEV_API_PROXY_TARGET is set (in .env.local, for phone testing):
  // forward "/api/..." to the local backend, so app and API share the
  // tunnel's single address — the same way nginx does it in production.
  async rewrites() {
    const target = process.env.DEV_API_PROXY_TARGET;
    return target ? [{ source: "/api/:path*", destination: `${target}/api/:path*` }] : [];
  },
};

export default withNextIntl(nextConfig);
