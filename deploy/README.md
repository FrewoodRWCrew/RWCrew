# Deploying RWCrew (Hostinger VPS)

Full walkthrough: `docs/deploying-to-hostinger.pdf`. Quick reference once the
server is already set up:

- Production tracks the `main` branch, deployed to `/opt/rwcrew/production`,
  served at https://rwcrew.eu.
- Test tracks the `develop` branch, deployed to `/opt/rwcrew/test`, served at
  https://test.rwcrew.eu.
- Pushing to either branch triggers `.github/workflows/deploy-production.yml`
  / `deploy-test.yml`, which SSH into the VPS and run
  `deploy/scripts/deploy.sh` for that environment.
- To redeploy by hand: `bash deploy/scripts/deploy.sh /opt/rwcrew/production`
  (or `/opt/rwcrew/test`), run from inside that folder on the VPS.
- `docker-compose.prod.yml` is shared by both environments; each folder has
  its own `.env` (see `.env.production.example` / `.env.test.example`) and
  its own `docker compose` project, so containers/volumes never collide.
- Nginx config for both subdomains: `deploy/nginx/rwcrew.conf`.

## Database access for debugging (pgAdmin)

Each environment's database is published on the VPS's `127.0.0.1` only
(test `5442`, production `5443`, set by `DB_HOST_PORT` in that folder's `.env`),
so it is never reachable from the internet. pgAdmin on your PC reaches it through
an SSH tunnel and logs in as `rwcrew_readonly`, which can read everything but
change nothing.

One-time per environment, on the VPS:
1. Add `DB_HOST_PORT=5442` (test) / `DB_HOST_PORT=5443` (production) to the
   folder's `.env` **before** deploying: a missing value makes the deploy fail.
2. After the deploy: `cd /opt/rwcrew/test && bash deploy/scripts/create-readonly-db-user.sh`
   (asks for a password; run it again any time to reset it).

pgAdmin server settings:
- Connection: host `127.0.0.1`, port `5442` / `5443`, database `rwcrew`,
  user `rwcrew_readonly`.
- Parameters: `GSS encryption mode` = `disable` (pgAdmin 9.18 on Windows crashes
  with "access violation" otherwise).
- SSH Tunnel: host = the VPS IP, port `22`, user `ubuntu`, authentication
  "Identity file" = your VPS SSH private key.
- Give the production server a red background colour so it stands out.
