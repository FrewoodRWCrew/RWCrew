# RWCrew mobile app

React Native + Expo (SDK 57) phone app for the RWCrew backend. See the "Mobile app (`mobile/`)"
section of the root `CLAUDE.md` for the architecture rules and the local dev loop.

Two variants, installable side by side:

| Variant    | App name    | Package              | Backend                | EAS profile  |
|------------|-------------|----------------------|------------------------|--------------|
| test       | RWCrew Test | `eu.rwcrew.app.test` | https://test.rwcrew.eu | `test`       |
| production | RWCrew      | `eu.rwcrew.app`      | https://rwcrew.eu      | `production` |

## Releasing Android (APK, no Play Store)

Android builds are signed APKs made in the cloud by EAS, hosted on our own VPS under
`/downloads/`, and linked from the web "Mobile App" page (module-10).

### One-time setup (PC)

1. `npm install -g eas-cli`, then `eas login` with the account that owns `rwcrewmobile`
   (`eas whoami` to check).
2. Checks in `mobile/`: `npx tsc --noEmit`, `npx expo-doctor`, `npm run lint`.

### Build

1. Set `version` in `app.config.ts` (e.g. `1.0.0`). The Android `versionCode` is incremented by EAS itself.
2. In `mobile/` (PowerShell): `$env:EXPO_NO_DOTENV="1"; eas build --platform android --profile test`
   (or `--profile production`). `EXPO_NO_DOTENV` keeps your local `.env.development.local` (LAN
   `API_URL`) out of the build: the PowerShell variable covers your PC, and `eas.json` sets the same variable
   for Expo's build server, which otherwise loads that file from the upload. Without it, `app.config.ts` may stop the build with an "API_URL ... is a local
   development address" error. That error is the safety check working, not a bug.
   - First build of a variant: answer **Yes** to "Generate a new Android Keystore?".
   - **Back the keystore up right away**: `eas credentials` → Android → the profile → download the
     keystore and store the `.jks` file + passwords in a password manager. Every later APK must be signed
     with the same key, otherwise phones refuse to install it as an update.
3. When the build is finished, download the `.apk` from the link EAS prints (expo.dev links expire, so
   always host the file yourself).

### Publish on the VPS

```bash
# From the PC (test shown; production: /opt/rwcrew/production/downloads/, rwcrew-<version>.apk)
scp rwcrew-test-1.0.0.apk <user>@<vps>:/opt/rwcrew/test/downloads/

# On the VPS
cd /opt/rwcrew/test/downloads
cp rwcrew-test-1.0.0.apk rwcrew-test-latest.apk     # stable link used by the download page
```

- First time only: `mkdir -p /opt/rwcrew/{test,production}/downloads`, copy `deploy/nginx/rwcrew.conf`'s
  `location /downloads/` block into the server's nginx config **including the certbot `443` blocks**, then
  `sudo nginx -t && sudo systemctl reload nginx`.
- Check: `curl -I https://test.rwcrew.eu/downloads/rwcrew-test-latest.apk` → `200` and
  `Content-Type: application/vnd.android.package-archive`.
- Update the environment's `.env` (`MOBILE_LATEST_VERSION`, `MOBILE_CHANGELOG`, `MOBILE_ANDROID_DOWNLOAD_URL`,
  see `.env.test.example`) and run `docker compose -f docker-compose.prod.yml up -d backend` in
  `/opt/rwcrew/test` (or `production`).
- Grant users **Mobile App (module-10)** in "Manage Access" so they see the download page.
- Tag production releases: `git tag mobile-v1.0.0 && git push origin mobile-v1.0.0`.

### Installing on a phone

1. Open the site → "Mobile App" tile → Android download.
2. Chrome may warn about the file type → **Download anyway**, then open it.
3. Allow Chrome to **Install unknown apps** when Android asks, go back, tap **Install**.
4. Play Protect may flag an unknown app → **More details → Install anyway**.

### Later updates

- **JavaScript-only changes** (screens, texts, logic): `eas update --channel test` (or `production`), no new
  APK. Apps download it in the background and use it from the next start. Only reaches builds with the same
  `version`.
- **Native changes** (new Expo package, permissions, icon, SDK upgrade) or a version bump: build a new APK
  and publish it as above. Users install it over the old app; login and data are kept as long as the keystore
  is the same.
- Only raise `MOBILE_MIN_APP_VERSION` for breaking API changes — older apps then get told to update.
