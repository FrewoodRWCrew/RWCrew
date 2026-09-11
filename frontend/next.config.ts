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
};

export default withNextIntl(nextConfig);
