// The mass test's screen check: after the data of last year was loaded
// (backend/masstest), open every Atelier screen for one season and each of
// its festivals, like a person would, and note per screen how long it took,
// console errors, page errors and failed API calls. The findings go to a
// JSON file that `python -m masstest screens <file> --env <env> --out <folder>`
// turns into the same Excel issue report as the data run.
//
//   MASSTEST_EMAIL=... MASSTEST_PASSWORD=... MASSTEST_SEASON=2026 \
//     node scripts/mass-test-screens.mjs <output.json> [web address]
//
// - Web address: default http://localhost:3000 (test: https://test.rwcrew.eu).
// - MASSTEST_SEASON: the season's name or id.
// - Uses playwright-core with the installed Edge (MASSTEST_BROWSER=chrome for Chrome).
// - Write the JSON outside the repo: it can hold names from the screens' errors.

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright-core";

const OUTPUT = process.argv[2];
const BASE_URL = (process.argv[3] ?? "http://localhost:3000").replace(/\/$/, "");
const EMAIL = process.env.MASSTEST_EMAIL;
const PASSWORD = process.env.MASSTEST_PASSWORD;
const SEASON = process.env.MASSTEST_SEASON;
const CHANNEL = process.env.MASSTEST_BROWSER === "chrome" ? "chrome" : "msedge";
// A screen slower than this (seconds) is reported.
const SLOW_SECONDS = 3;
const API = "/api/modules/module-5";

if (!OUTPUT || !EMAIL || !PASSWORD || !SEASON) {
  console.error("Usage: MASSTEST_EMAIL=… MASSTEST_PASSWORD=… MASSTEST_SEASON=<name|id> node scripts/mass-test-screens.mjs <output.json> [web address]");
  process.exit(1);
}

// The screens to open: once per season, and once per festival of the season.
const seasonScreens = (season) => [
  ["KPI", `/modules/module-5?season=${season}`],
  ["Openstaand (alle festivals)", `/modules/module-5/desk/open?season=${season}&festival=all`],
  ["Retourproblemen (alle festivals)", `/modules/module-5/desk/return-issues?season=${season}&festival=all`],
  ["Stock", "/modules/module-5/stock"],
  ["Boekingen", "/modules/module-5/stock/bookings"],
  ["Te bestellen", `/modules/module-5/stock/order-needs?season=${season}`],
];
const festivalScreens = (season, festival) => [
  ["Uitgifte & inname", `/modules/module-5/desk?festival=${festival}`],
  ["Openstaand", `/modules/module-5/desk/open?season=${season}&festival=${festival}`],
  ["Retourproblemen", `/modules/module-5/desk/return-issues?season=${season}&festival=${festival}`],
  ["Reservaties", `/modules/module-5/reservations?season=${season}&festival=${festival}`],
  ["Voorbereiden", `/modules/module-5/reservations/preparation?season=${season}&festival=${festival}`],
];

const issues = [];
let checked = 0;

// Write what was found (also after a failure halfway).
async function save(blocker) {
  await mkdir(path.dirname(path.resolve(OUTPUT)), { recursive: true });
  await writeFile(OUTPUT, JSON.stringify({ base_url: BASE_URL, checked, blocker, issues }, null, 2), "utf8");
  console.log(`${checked} screen(s) checked, ${issues.length} issue(s) -> ${OUTPUT}`);
}

const browser = await chromium.launch({ channel: CHANNEL });
try {
  const context = await browser.newContext({ viewport: { width: 1500, height: 950 }, locale: "nl-BE" });
  const page = await context.newPage();

  // Log in through the real login form.
  await page.goto(`${BASE_URL}/nl/login`);
  await page.locator('input[type="email"]').fill(EMAIL);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator('button[type="submit"]').click();
  try {
    await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 15000 });
  } catch {
    await save(`Logging in as ${EMAIL} on ${BASE_URL} failed.`);
    process.exit(2);
  }

  // The season (by name or id) and its festivals, through the same API the screens use.
  const seasons = await (await page.request.get(`${BASE_URL}${API}/seasons`)).json();
  const season = seasons.find((row) => String(row.id) === SEASON || row.name === SEASON);
  if (!season) {
    await save(`Season '${SEASON}' not found in Atelier.`);
    process.exit(2);
  }
  const festivals = await (await page.request.get(`${BASE_URL}${API}/festivals?season_id=${season.id}`)).json();

  // Per page: console errors, uncaught errors and failed API calls.
  let problems = [];
  page.on("console", (message) => {
    if (message.type() === "error") problems.push(`console: ${message.text().slice(0, 300)}`);
  });
  page.on("pageerror", (error) => problems.push(`page error: ${String(error).slice(0, 300)}`));
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 400) {
      problems.push(`${response.status()} ${response.request().method()} ${new URL(response.url()).pathname}`);
    }
  });

  // Open one screen and note what went wrong and how long it took.
  async function check(module, name, route) {
    problems = [];
    const url = `${BASE_URL}/nl${route}`;
    const started = Date.now();
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
      await page.locator('div.fixed.inset-0[aria-live="polite"]').waitFor({ state: "detached", timeout: 15000 }).catch(() => {});
    } catch (error) {
      problems.push(`navigation: ${String(error).slice(0, 300)}`);
    }
    const seconds = (Date.now() - started) / 1000;
    checked += 1;
    if (problems.length) {
      issues.push({
        code: "screen_error", module, url,
        description: `Screen '${name}' showed ${problems.length} problem(s) while loading.`,
        text: problems.join("\n"), params: [],
      });
    }
    if (seconds > SLOW_SECONDS) {
      issues.push({
        code: "slow_screen", module, url,
        description: `Screen '${name}' took ${seconds.toFixed(1)} s to load.`,
        text: "", params: [seconds.toFixed(1), SLOW_SECONDS],
      });
    }
    console.log(`${seconds.toFixed(1)} s  ${problems.length ? "!!" : "ok"}  ${name}  ${route}`);
  }

  // A PDF download: must answer 200 with a PDF.
  async function checkPdf(module, name, apiPath) {
    const started = Date.now();
    const response = await page.request.get(`${BASE_URL}${apiPath}`);
    const seconds = (Date.now() - started) / 1000;
    checked += 1;
    const type = response.headers()["content-type"] ?? "";
    if (!response.ok() || !type.includes("pdf")) {
      issues.push({
        code: "screen_error", module, url: apiPath,
        description: `PDF '${name}' failed (${response.status()}).`,
        text: (await response.text()).slice(0, 500), params: [],
      });
    } else if (seconds > SLOW_SECONDS) {
      issues.push({
        code: "slow_screen", module, url: apiPath,
        description: `PDF '${name}' took ${seconds.toFixed(1)} s.`, text: "", params: [seconds.toFixed(1), SLOW_SECONDS],
      });
    }
    console.log(`${seconds.toFixed(1)} s  ${response.ok() ? "ok" : "!!"}  ${name}`);
  }

  for (const [name, route] of seasonScreens(season.id)) await check("atelier", name, route);
  for (const festival of festivals) {
    for (const [name, route] of festivalScreens(season.id, festival.id)) {
      await check("atelier", `${name} · ${festival.name}`, route);
    }
    if (festival.days.length) {
      await checkPdf("atelier", `Picklijst · ${festival.name}`, `${API}/preparation/pdf?festival_id=${festival.id}&day=${festival.days[0]}`);
    }
  }
  await checkPdf("atelier", "Bestellijst", `${API}/stock/order-needs/pdf?season_id=${season.id}`);
  await save(null);
} finally {
  await browser.close();
}
