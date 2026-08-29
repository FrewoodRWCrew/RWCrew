# RW Crew — frontend

A Next.js app: the landing page ("Mainpage") with its 9 module tiles, the
super admin's "Manage Access" screen, and one route folder per module.

## First-time setup

```bash
npm install
cp .env.local.example .env.local
```

Make sure the backend (see ../backend/README.md) is running first — the
frontend calls it for everything (login, module data, access rights).

## Running it

```bash
npm run dev
```

Open http://localhost:3000 — it redirects to the Dutch interface
(`/nl`) by default; English is available at `/en`.

## Project layout

```
src/
  app/[locale]/
    (auth)/login/         The login page
    (protected)/          Everything that requires being logged in:
      page.tsx              the Mainpage tile grid
      admin/access/         the super admin's "Manage Access" screen
      admin/master-data/    placeholder for future master data screens
      modules/module-1..9/  one route folder per module
  components/
    shared/    Header, admin sidebar, theme/language switchers, etc.
    landing/   Landing-page-specific components (login form, tiles)
    admin/     The access-management table/dialog
  lib/         API client, types, and small shared helpers
  i18n/        Language routing configuration (next-intl)
messages/      Dutch (nl.json, default) and English (en.json) text
```
