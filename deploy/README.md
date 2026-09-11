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
