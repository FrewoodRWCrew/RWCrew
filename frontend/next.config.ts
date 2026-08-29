import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// This wraps our Next.js config so next-intl can plug itself into the
// build process — mainly so it knows where to find src/i18n/request.ts,
// which decides which language's text to load on the server.
const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  /* config options here */
};

export default withNextIntl(nextConfig);
