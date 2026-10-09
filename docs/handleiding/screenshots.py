"""Maakt de schermafbeeldingen voor de handleiding (docs/handleiding/afbeeldingen/*.png).

Voorwaarden:
  1. De lokale applicatie draait (database, backend op :8020, frontend op :3000 met de dev-proxy).
  2. De tijdelijke gebruiker bestaat:
         backend/.venv/Scripts/python docs/handleiding/screenshot_user.py setup
     Dat schrijft ook .screenshot-login en .screenshot-namen.json (niet in Git).

Gebruik (vanuit de repo-root, eender welke Python 3.10+; geen extra pakketten):

    python docs/handleiding/screenshots.py              # alle schermafbeeldingen
    python docs/handleiding/screenshots.py 16 20        # alleen de opnames waarvan de naam zo begint

Daarna de gebruiker weer opruimen met "screenshot_user.py cleanup".

Persoonsgegevens: vóór elke opname vervangt een stukje JavaScript op het scherm alle namen,
e-mailadressen, telefoonnummers en IP-adressen uit de database door fictieve waarden, plus alles
wat op een e-mailadres of Belgisch gsm-nummer lijkt.
"""

from __future__ import annotations

import base64
import json
import re
import sys
import tempfile
import time
from pathlib import Path

# DevTools-client en browserstart delen met het PDF-script.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pdf import AFBEELDINGEN, start_browser  # noqa: E402

HIER = Path(__file__).resolve().parent
BASIS = "http://localhost:3000"
LOGIN_BESTAND = HIER / ".screenshot-login"
NAMEN_BESTAND = HIER / ".screenshot-namen.json"

# Seizoen dat de seizoenkiezer standaard toont (id in MasterData_season; 1 = "2026").
SEIZOEN_ID = "1"

# Fictieve namen die de echte namen vervangen (in volgorde, telkens dezelfde vervanging).
FICTIEVE_NAMEN = [
    "An Peeters", "Bart Janssens", "Charlotte Maes", "Dirk Jacobs", "Els Mertens", "Filip Willems",
    "Griet Claes", "Hans Goossens", "Ilse Wouters", "Jan De Smet", "Katrien Dubois", "Luc Lambert",
    "Marie Hermans", "Nico Martens", "Olga Peeters", "Pieter Leroy", "Raf Coppens", "Sofie Vermeulen",
    "Tom Vandenberghe", "Ursula Pauwels",
]

# Venstergroottes: pc en telefoon.
PC = {"width": 1440, "height": 900, "deviceScaleFactor": 1.25, "mobile": False}
TELEFOON = {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True}
TELEFOON_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)

# JavaScript-hulpjes voor acties: op een knop klikken op basis van zijn tekst of aria-label.
KLIK_TEKST = """(tekst => {
  const knop = [...document.querySelectorAll('button, a')].find(b => b.textContent.trim() === tekst);
  if (knop) knop.click();
  return !!knop;
})"""
KLIK_RECHTEN = """(() => {
  // De knop "Rechten" van de eerste rol die niet de tijdelijke screenshotrol is.
  const rij = [...document.querySelectorAll('tr')].find(r =>
    r.querySelector('[aria-label="Rechten"]') && !r.textContent.includes('Screenshots'));
  const knop = rij && rij.querySelector('[aria-label="Rechten"]');
  if (knop) knop.click();
  return !!knop;
})()"""

# De opnames: (bestandsnaam, adres, venster, wachttijd in seconden, optionele JavaScript-actie).
# Opnames met "voor_login" worden gemaakt voordat de demogebruiker inlogt.
VOOR_LOGIN = [
    ("01-login", "/nl/login", PC, 2, None),
    ("40-m-login", "/nl/m/login", TELEFOON, 2, None),
    ("36-publiek-formulier", "/nl/intervention-request", PC, 2, None),
]
NA_LOGIN = [
    ("02-startscherm", "/nl", PC, 3, None),
    ("03-manage-access", "/nl/admin/access", PC, 3, None),
    ("04-login-history", "/nl/admin/login-history", PC, 3, None),
    ("05-tagscan-bestanden", "/nl/modules/module-1/files", PC, 3, None),
    ("06-tagscan-linedata", "/nl/modules/module-1/tag-linedata", PC, 3, None),
    ("07-tagscan-headerdata", "/nl/modules/module-1/tag-headerdata", PC, 3, None),
    ("08-tagscan-scanners", "/nl/modules/module-1/scanners", PC, 3, None),
    ("09-tagscan-instellingen", "/nl/modules/module-1/settings", PC, 3, None),
    ("10-kartracker-kpi", "/nl/modules/module-2", PC, 4, None),
    ("11-kartracker-karren", "/nl/modules/module-2/kar-management", PC, 3, None),
    ("12-kartracker-plan-kar", "/nl/modules/module-2/actions/plan-kar", PC, 3, None),
    ("13-kartracker-planning", "/nl/modules/module-2/actions/kar-planning", PC, 3, None),
    ("14-kartracker-kaart", "/nl/modules/module-2/actions/kar-map", PC, 8, None),
    ("15-interventie-kpi", "/nl/modules/module-3", PC, 4, None),
    ("16-interventie-lijst", "/nl/modules/module-3/intervention-requests", PC, 3, None),
    ("17-interventie-nieuw", "/nl/modules/module-3/intervention-requests", PC, 3, KLIK_TEKST + '("Nieuwe aanvraag")'),
    ("18-interventie-mailinglijst", "/nl/modules/module-3/settings/mailing-list", PC, 3, None),
    ("19-rechten-rollen", "/nl/modules/module-3/access-rights/roles", PC, 3, None),
    ("20-rechten-matrix", "/nl/modules/module-3/access-rights/roles", PC, 3, KLIK_RECHTEN),
    ("21-rechten-gebruikers", "/nl/modules/module-3/access-rights/users", PC, 3, None),
    ("22-stockmaster-kpi", "/nl/modules/module-4", PC, 4, None),
    ("23-stockmaster-voorraad", "/nl/modules/module-4/stock", PC, 3, None),
    ("24-stockmaster-karren", "/nl/modules/module-4/kars", PC, 3, None),
    ("25-stockmaster-kar", "/nl/modules/module-4/kars/36", PC, 3, None),
    ("26-stockmaster-boekingen", "/nl/modules/module-4/bookings", PC, 3, None),
    ("27-stockmaster-bestellen", "/nl/modules/module-4/order-needs", PC, 3, None),
    ("28-stockmaster-karbehoefte", "/nl/modules/module-4/requirements", PC, 3, None),
    ("29-altsien-overzicht", "/nl/modules/module-8/ploeg-wizard?season=1", PC, 3, None),
    ("30-altsien-wizard", "/nl/modules/module-8/ploeg-wizard/15?season=1", PC, 4, None),
    ("31-altsien-ploegfiche", "/nl/modules/module-8/ploegfiche?season=1&team=15", PC, 4, None),
    ("32-masterdata-jaren", "/nl/modules/module-9/season", PC, 3, None),
    ("33-masterdata-ploegen", "/nl/modules/module-9/teams", PC, 3, None),
    ("34-masterdata-upload", "/nl/modules/module-9/data-upload-download", PC, 3, None),
    ("35-mobile-app", "/nl/modules/module-10", PC, 3, None),
    ("41-m-start", "/nl/m", TELEFOON, 3, None),
    ("42-m-kartracker", "/nl/m/module-2", TELEFOON, 3, None),
    ("43-m-planning", "/nl/m/module-2/planning", TELEFOON, 3, None),
    ("44-m-kar", "/nl/m/module-2/kar/B004", TELEFOON, 3, None),
    ("45-m-akties", "/nl/m/module-3", TELEFOON, 3, None),
    ("46-m-aanvraag", "/nl/m/module-3/request/new", TELEFOON, 3, None),
    ("47-m-kpi", "/nl/m/module-3/kpi", TELEFOON, 3, None),
]


def maskeer_script(gegevens: dict) -> str:
    """JavaScript dat alle persoonsgegevens op het scherm door fictieve waarden vervangt."""
    # Testwaarden zoals "test" of "123" niet maskeren: die komen ook in gewone teksten voor.
    namen = [n for n in gegevens["namen"] if len(n) >= 5]
    telefoons = [t for t in gegevens["telefoons"] if len(re.sub(r"\D", "", t)) >= 8]
    paren: list[tuple[str, str]] = [("Screenshots (tijdelijk)", "Demo-rol")]
    paren += [(email, "naam@voorbeeld.be") for email in gegevens["emails"]]
    paren += [(tel, "0470 00 00 00") for tel in telefoons]
    paren += [(ip, "192.0.2.10") for ip in gegevens["ips"]]
    paren += [(naam, FICTIEVE_NAMEN[i % len(FICTIEVE_NAMEN)]) for i, naam in enumerate(namen)]
    return r"""
(paren => {
  const vervang = s => {
    // Eerst alles wat op een e-mailadres of gsm-nummer lijkt, daarna de exacte waarden uit de
    // database (namen, vaste nummers, IP-adressen). Andersom zou een naam binnen een
    // e-mailadres vervangen worden en het adres onherkenbaar maken.
    s = s.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g,
                  m => m.endsWith('@voorbeeld.be') ? (m === 'screenshots@voorbeeld.be' ? 'demo@voorbeeld.be' : m) : 'naam@voorbeeld.be');
    s = s.replace(/(?:\+32\s?|0032\s?|\b0)4\d{2}[\s./]?\d{2}[\s./]?\d{2}[\s./]?\d{2}\b/g, '0470 00 00 00');
    // Alleen als los woord vervangen, nooit midden in een ander woord of een ploegnaam.
    for (const [echt, nep] of paren) {
      if (!s.includes(echt)) continue;
      const patroon = new RegExp('(?<![\\p{L}\\d])' + echt.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![\\p{L}\\d])', 'gu');
      s = s.replace(patroon, nep);
    }
    return s;
  };
  // De ontwikkelbadge van Next.js ("N" linksonder) hoort niet op een schermafbeelding.
  document.querySelectorAll('nextjs-portal').forEach(e => e.remove());
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const nieuw = vervang(n.nodeValue);
    if (nieuw !== n.nodeValue) n.nodeValue = nieuw;
  }
  for (const veld of document.querySelectorAll('input, textarea')) {
    if (veld.value) veld.value = vervang(veld.value);
  }
  for (const el of document.querySelectorAll('[title]')) el.title = vervang(el.title);
  return true;
})(__PAREN__)
""".replace("__PAREN__", json.dumps(paren, ensure_ascii=False))


def wacht_op_pagina(devtools, extra_seconden: float) -> None:
    """Wacht tot de pagina geladen is, en dan nog even voor gegevens, kaarten en animaties."""
    deadline = time.monotonic() + 30
    while devtools.evalueer("document.readyState") != "complete":
        if time.monotonic() > deadline:
            break
        time.sleep(0.3)
    time.sleep(extra_seconden)


def zet_venster(devtools, venster: dict) -> None:
    """Pc- of telefoonformaat instellen (met telefoon-User-Agent voor het telefoonformaat)."""
    devtools.roep("Emulation.setDeviceMetricsOverride", **venster)
    devtools.roep("Emulation.setUserAgentOverride", userAgent=TELEFOON_UA if venster["mobile"] else "")


def maak_opname(devtools, naam: str, pad: str, venster: dict, wachten: float, actie: str | None, masker: str) -> None:
    zet_venster(devtools, venster)
    for poging in range(3):
        devtools.roep("Page.navigate", url=BASIS + pad)
        wacht_op_pagina(devtools, wachten)
        # Een foutpagina van de browser (frontend onbereikbaar) of van Next.js: opnieuw proberen.
        if devtools.evalueer("location.protocol.startsWith('http') && !document.title.includes('localhost')")                 and not devtools.evalueer("!!document.querySelector('nextjs-portal')?.shadowRoot?.querySelector('[data-nextjs-dialog]')"):
            break
        print(f"  {naam}: pagina niet geladen, poging {poging + 2}...")
        time.sleep(10)
    else:
        sys.exit(f"{naam}: {BASIS + pad} laadt niet; draait de frontend nog?")
    if actie:
        if not devtools.evalueer(actie):
            print(f"  waarschuwing: actie voor {naam} vond niets om op te klikken")
        time.sleep(1.5)
    devtools.evalueer(masker)
    time.sleep(0.2)
    beeld = devtools.roep("Page.captureScreenshot", format="png", captureBeyondViewport=False)
    (AFBEELDINGEN / f"{naam}.png").write_bytes(base64.b64decode(beeld["data"]))
    print(f"  {naam}.png  ({BASIS}{pad})")


def main() -> None:
    if not LOGIN_BESTAND.exists() or not NAMEN_BESTAND.exists():
        sys.exit("Eerst 'screenshot_user.py setup' uitvoeren (met de Python van de backend).")
    email, wachtwoord = LOGIN_BESTAND.read_text(encoding="utf-8").split()[:2]
    masker = maskeer_script(json.loads(NAMEN_BESTAND.read_text(encoding="utf-8")))
    filters = sys.argv[1:]
    gekozen = lambda lijst: [o for o in lijst if not filters or any(o[0].startswith(f) for f in filters)]  # noqa: E731
    AFBEELDINGEN.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tijdelijk:
        profiel = Path(tijdelijk) / "profiel"
        profiel.mkdir()
        with start_browser(profiel) as devtools:
            devtools.roep("Runtime.enable")
            # Belgische weergave van datums en getallen in de formulieren.
            devtools.roep("Emulation.setLocaleOverride", locale="nl-BE")

            # Licht thema (beter leesbaar op papier) en een vast seizoen in de seizoenkiezer.
            devtools.roep("Page.navigate", url=BASIS + "/nl/login")
            wacht_op_pagina(devtools, 1)
            devtools.evalueer(
                f"localStorage.setItem('theme','light'); localStorage.setItem('rwcrew.selectedSeasonId','{SEIZOEN_ID}'); true"
            )

            print("Opnames zonder login:")
            for opname in gekozen(VOOR_LOGIN):
                maak_opname(devtools, *opname, masker)

            # Inloggen als de demogebruiker, via dezelfde API als het loginformulier.
            zet_venster(devtools, PC)
            devtools.roep("Page.navigate", url=BASIS + "/nl/login")
            wacht_op_pagina(devtools, 1)
            # awaitPromise: wachten tot het fetch-antwoord binnen is en de cookies gezet zijn.
            resultaat = devtools.roep(
                "Runtime.evaluate",
                expression=(
                    f"fetch('/api/auth/login', {{method: 'POST', credentials: 'include', "
                    f"headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{email: {json.dumps(email)}, "
                    f"password: {json.dumps(wachtwoord)}, client: 'web'}})}}).then(r => r.status)"
                ),
                awaitPromise=True,
                returnByValue=True,
            )
            if resultaat.get("result", {}).get("value") != 200:
                sys.exit(f"Inloggen mislukt: {resultaat}")

            print("Opnames na login:")
            for opname in gekozen(NA_LOGIN):
                maak_opname(devtools, *opname, masker)

    print(f"Klaar: {AFBEELDINGEN}")


if __name__ == "__main__":
    main()
