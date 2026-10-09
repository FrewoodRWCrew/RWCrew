// Takes the screenshots used in the module help manuals (the PDFs built by
// backend/app/help/help_pdf.py) from the running localhost app, so they can
// be refreshed with one command after a screen changes:
//
//   HELP_SHOTS_EMAIL=... HELP_SHOTS_PASSWORD=... npm run help:screenshots [module-4 ...]
//
// - Needs the app running locally (backend on 8020, frontend on 3000) and a
//   login that can see every screen of the module(s) (e.g. a super admin
//   with module access).
// - Uses playwright-core with the Microsoft Edge installed on Windows, so no
//   browser download is needed (HELP_SHOTS_BROWSER=chrome to use Chrome).
// - Shots are taken in Dutch, light theme, and cropped to the module's page
//   area (right of its own sidebar). They land in
//   backend/app/help/content/<module_N>/images/<file>.png, the names the
//   Markdown manuals refer to.

import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const BASE_URL = process.env.HELP_SHOTS_URL ?? "http://localhost:3000";
const EMAIL = process.env.HELP_SHOTS_EMAIL;
const PASSWORD = process.env.HELP_SHOTS_PASSWORD;
const CHANNEL = process.env.HELP_SHOTS_BROWSER === "chrome" ? "chrome" : "msedge";
const CONTENT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../backend/app/help/content");

// The local test data the shots are taken on: a season and a kar that has
// needs and stock (change these when the local database is rebuilt).
const SEASON = process.env.HELP_SHOTS_SEASON ?? "1";
const KAR = process.env.HELP_SHOTS_KAR ?? "36";

// Per module: the page to open, the file to write and, optionally, the name
// of a button to click first (e.g. to load a list) or a "prepare" step that
// fills in the screen first (e.g. pick the first team in a dropdown).
const SHOTS = {
  "module-1": [
    { file: "overview.png", path: "/modules/module-1" },
    { file: "files.png", path: "/modules/module-1/files" },
    { file: "header-data.png", path: "/modules/module-1/tag-headerdata" },
    { file: "line-data.png", path: "/modules/module-1/tag-linedata" },
    { file: "tag-management.png", path: "/modules/module-1/tag-management" },
    { file: "scanners.png", path: "/modules/module-1/scanners" },
    { file: "data-upload.png", path: "/modules/module-1/data-upload-download" },
    { file: "roles.png", path: "/modules/module-1/access-rights/roles" },
    { file: "users.png", path: "/modules/module-1/access-rights/users" },
    { file: "settings.png", path: "/modules/module-1/settings" },
  ],
  "module-2": [
    { file: "overview.png", path: "/modules/module-2" },
    { file: "movement.png", path: "/modules/module-2/actions" },
    { file: "kar-planning.png", path: "/modules/module-2/actions/kar-planning" },
    { file: "kar-map.png", path: "/modules/module-2/actions/kar-map" },
    { file: "plan-kar.png", path: "/modules/module-2/actions/plan-kar", prepare: pickFirstOption },
    { file: "kar-management.png", path: "/modules/module-2/kar-management" },
    { file: "distributiepunten.png", path: "/modules/module-2/distributiepunten" },
    { file: "zones.png", path: "/modules/module-2/zones" },
    { file: "afleverlocaties.png", path: "/modules/module-2/afleverlocaties" },
    { file: "kar-statuses.png", path: "/modules/module-2/kar-statuses" },
    { file: "delivery-dates.png", path: "/modules/module-2/delivery-dates" },
    { file: "data-upload.png", path: "/modules/module-2/data-upload-download" },
    { file: "groundplan.png", path: "/modules/module-2/groundplan" },
    { file: "roles.png", path: "/modules/module-2/access-rights/roles" },
    { file: "users.png", path: "/modules/module-2/access-rights/users" },
  ],
  "module-4": [
    { file: "kpi.png", path: `/modules/module-4?season=${SEASON}` },
    { file: "stock.png", path: "/modules/module-4/stock" },
    { file: "kars.png", path: `/modules/module-4/kars?season=${SEASON}` },
    { file: "book-in.png", path: "/modules/module-4/book-in" },
    { file: "kar-load.png", path: `/modules/module-4/kars/load?kar=${KAR}&season=${SEASON}` },
    { file: "book-out.png", path: "/modules/module-4/book-out" },
    { file: "kar-dispatch.png", path: `/modules/module-4/kars/dispatch?kar=${KAR}&season=${SEASON}` },
    { file: "kar-return.png", path: `/modules/module-4/kars/return?season=${SEASON}` },
    { file: "kar-unload.png", path: `/modules/module-4/kars/unload?kar=${KAR}&season=${SEASON}` },
    { file: "count.png", path: `/modules/module-4/count?kar=${KAR}`, click: "Lijst laden" },
    { file: "requirements.png", path: `/modules/module-4/requirements?kar=${KAR}&season=${SEASON}` },
    { file: "order-needs.png", path: `/modules/module-4/order-needs?season=${SEASON}` },
    { file: "bookings.png", path: "/modules/module-4/bookings" },
    { file: "reasons.png", path: "/modules/module-4/settings/reasons" },
    { file: "roles.png", path: "/modules/module-4/access-rights/roles" },
    { file: "users.png", path: "/modules/module-4/access-rights/users" },
  ],
};

// Open the first dropdown of the page itself (not the header's year
// selector) and choose its first option.
async function pickFirstOption(page) {
  await page.locator("main nav.w-60 + div").getByRole("combobox").first().click();
  await page.getByRole("option").first().click();
}

if (!EMAIL || !PASSWORD) {
  console.error("Set HELP_SHOTS_EMAIL and HELP_SHOTS_PASSWORD (a local login that sees every screen).");
  process.exit(1);
}

// Only the modules named on the command line, or all of them.
const modules = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(SHOTS);

const browser = await chromium.launch({ channel: CHANNEL });
const context = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: "nl-BE" });
// Light theme before the app's own script reads it (next-themes' "theme"
// key), and the header's year (season-provider.tsx) set to SEASON.
await context.addInitScript((season) => {
  try {
    window.localStorage.setItem("theme", "light");
    window.localStorage.setItem("rwcrew.selectedSeasonId", season);
  } catch {}
}, SEASON);
const page = await context.newPage();

// Log in once through the real login form; the cookies stay in the context.
await page.goto(`${BASE_URL}/nl/login`);
await page.locator('input[type="email"]').fill(EMAIL);
await page.locator('input[type="password"]').fill(PASSWORD);
await page.locator('button[type="submit"]').click();
await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 15000 });

for (const moduleKey of modules) {
  const outDir = path.join(CONTENT_DIR, moduleKey.replace("-", "_"), "images");
  await mkdir(outDir, { recursive: true });

  for (const shot of SHOTS[moduleKey] ?? []) {
    await page.goto(`${BASE_URL}/nl${shot.path}`);
    await page.waitForLoadState("networkidle");
    if (shot.click) {
      await page.getByRole("button", { name: shot.click }).first().click();
      await page.waitForLoadState("networkidle");
    }
    if (shot.prepare) {
      await shot.prepare(page);
      await page.waitForLoadState("networkidle");
    }
    // Wait for the start-up splash screen (shown on every full page load) to
    // be gone, let charts and lists finish drawing, drop the text cursor and
    // scroll back to the top (a click may have scrolled the page).
    await page
      .locator('div.fixed.inset-0[aria-live="polite"]')
      .waitFor({ state: "detached", timeout: 10000 })
      .catch(() => {});
    await page.waitForTimeout(800);
    await page.evaluate(() => {
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
      document.querySelector("main")?.scrollTo(0, 0);
    });

    // The module's page area (the block right of the module's own sidebar),
    // cut off below its last content instead of at the window's bottom
    // edge when the page is short.
    const clip = await page.evaluate(() => {
      const area = document.querySelector("main nav.w-60 + div");
      if (!area) return null;
      const box = area.getBoundingClientRect();
      let bottom = box.top;
      for (const element of area.querySelectorAll("*")) {
        const rect = element.getBoundingClientRect();
        if (rect.height > 0 && rect.bottom > bottom) bottom = rect.bottom;
      }
      const height = Math.min(bottom + 24, window.innerHeight) - box.top;
      return { x: box.left, y: box.top, width: box.width, height };
    });
    await page.screenshot({ path: path.join(outDir, shot.file), clip: clip ?? undefined });
    console.log(`${moduleKey}: ${shot.file}`);
  }
}

await browser.close();
