# TagScan device-intake watcher (Raspberry Pi)

Watches a local folder for finished CSV files and pushes them to a TagScan
backend over HTTPS (`POST /api/public/tagscan-intake`), so the Pi never
needs the backend's filesystem to be reachable directly. See
`backend/app/modules/module_1/device_router.py` for the endpoint itself.

Runs as **two independent instances** on the same Pi — one for the test
backend, one for production — since dev and prod are separate deployments
(separate database, separate registered scanners/API keys, separate
receive folder). Nothing in `watcher.py` is environment-specific; each
instance is just the same script pointed at different config.

## Install

```
sudo mkdir -p /opt/tagscan-watcher /etc/tagscan-watcher
sudo cp watcher.py /opt/tagscan-watcher/
sudo cp tagscan-watcher@.service /etc/systemd/system/

# A dedicated, unprivileged user to run the watcher as.
sudo useradd --system --no-create-home --shell /usr/sbin/nologin tagscan-watcher

# One env file per environment — see env.example for every value it needs.
sudo cp env.example /etc/tagscan-watcher/dev.env
sudo cp env.example /etc/tagscan-watcher/prod.env
sudo $EDITOR /etc/tagscan-watcher/dev.env
sudo $EDITOR /etc/tagscan-watcher/prod.env

sudo mkdir -p /home/pi/tagscan/dev/outgoing /home/pi/tagscan/dev/sent
sudo mkdir -p /home/pi/tagscan/prod/outgoing /home/pi/tagscan/prod/sent
sudo chown -R tagscan-watcher:tagscan-watcher /home/pi/tagscan

sudo systemctl daemon-reload
sudo systemctl enable --now tagscan-watcher@dev
sudo systemctl enable --now tagscan-watcher@prod
```

## Where each config value comes from

Per environment (dev backend vs. prod backend), open that deployment's own
frontend and grab:

- **`API_URL`** — the TagScan **Settings** screen (`Modules > TagScan >
  Settings`), "Device upload URL" field. Copy it exactly, including
  `/api/public/tagscan-intake`.
- **`API_KEY`** — the TagScan **Scanners** screen (`Modules > TagScan >
  Scanners`), the key icon on the relevant scanner's row → "Generate API
  key" (or "Generate new key" to rotate it — this invalidates the
  previous one immediately). The plaintext key is shown exactly once;
  paste it straight into the env file, it can't be retrieved again
  afterward.
- **`WATCH_DIR`** / **`SENT_DIR`** — wherever the CSV-producing app on
  this Pi should write its output for that environment. The producing
  app should write `file.csv.tmp` then `rename()` it to `file.csv` once
  finished, so the watcher never picks up a half-written file.

A production API key must never be pasted into `dev.env`, and a dev key
must never be pasted into `prod.env` — they belong to different Scanner
rows in different databases and won't authenticate against the other
environment anyway.

## Operating

```
sudo systemctl status tagscan-watcher@prod
sudo journalctl -u tagscan-watcher@prod -f
sudo systemctl restart tagscan-watcher@dev
```

Each instance restarts automatically on failure or reboot
(`Restart=always` in the unit file) and survives the Pi losing internet —
it just keeps retrying every `POLL_INTERVAL_SECONDS` until connectivity
comes back, and never double-delivers a file (the backend treats a
re-uploaded filename it already has as a safe, no-op "duplicate").
