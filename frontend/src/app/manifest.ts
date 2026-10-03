// The web app manifest (served by Next.js at /manifest.webmanifest). It is
// what lets a phone install RWCrew as an app on its home screen (a
// "Progressive Web App"): the name under the icon, the icons themselves,
// and that it opens full screen without the browser's address bar.

import type { MetadataRoute } from "next";
import { ENVIRONMENT_LABEL } from "@/lib/config";

// The dark green of the RW logo, also used as the splash-screen background
// while the installed app starts up.
const BRAND_GREEN = "#10261F";

export default function manifest(): MetadataRoute.Manifest {
  // The test deployment gets its own name ("RWCrew Test"), so someone who
  // installs both test and production can tell the two icons apart. They
  // are different web addresses, so they install as two separate apps.
  const name = ENVIRONMENT_LABEL ? "RWCrew Test" : "RWCrew";

  return {
    // A fixed id keeps the installed app recognised as the same app even
    // if start_url ever changes.
    id: "/",
    name,
    short_name: name,
    description: "RW Crew management application",
    // Opening the installed app lands on the module overview: the proxy
    // redirects bare "/" to the visitor's own language (Dutch by default).
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: BRAND_GREEN,
    theme_color: BRAND_GREEN,
    icons: [
      // Regular icons (rounded corners already drawn in).
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      // Full-bleed version that Android may crop to a circle or squircle;
      // the logo sits inside the required safe zone.
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
