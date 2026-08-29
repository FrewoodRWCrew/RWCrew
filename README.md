# RW Crew

Management program for Altsien activities.

RW Crew is a landing page ("Mainpage") with 9 tiles, each linking to its
own module (their real names/functionality are still to be decided —
they currently just show "Module 1" through "Module 9"). A super admin
decides which modules each user can open; each module has its own
admin/editor/reader roles, managed independently by that module's admin.

- **Frontend**: Next.js (see [frontend/README.md](frontend/README.md))
- **Backend**: FastAPI + PostgreSQL (see [backend/README.md](backend/README.md))
- **Local database**: `docker compose up -d db` (from this folder)

Start with the backend README, then the frontend README, to get both
running locally.
