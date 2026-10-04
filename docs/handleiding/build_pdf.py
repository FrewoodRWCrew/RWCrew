"""Bouwt de RWCrew-ontwikkelaarshandleiding (PDF) uit de bronbestanden in deze map.

Gebruik (vanuit de repo-root, met eender welke Python 3.10+; geen extra pakketten nodig):

    python docs/handleiding/build_pdf.py

Resultaat: docs/RWCrew-Ontwikkelaarshandleiding.pdf

Hoe het werkt:
  1. Alle hoofdstukbestanden in hoofdstukken/ worden in naamvolgorde aan elkaar
     geplakt, samen met stijl.css en Paged.js (vendor/), tot één HTML-bestand.
  2. Dit script nummert de hoofdstukken (1, 2, ...), paragrafen (1.1), subparagrafen
     (1.1.1), figuren en tabellen, vult kruisverwijzingen in
     (<a class="ref" href="#id"></a>) en maakt de inhoudsopgave en de lijsten van
     figuren en tabellen.
  3. Microsoft Edge of Google Chrome opent die HTML zonder venster ("headless").
     Paged.js zet de tekst in A4-pagina's met kop- en voettekst en vult de
     paginanummers in de inhoudsopgave in. Dit script wacht via het DevTools-protocol
     van de browser tot Paged.js klaar is, en laat de browser dan naar PDF afdrukken.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# Mappen en bestanden, relatief ten opzichte van dit script.
HIER = Path(__file__).resolve().parent
HOOFDSTUKKEN = HIER / "hoofdstukken"
STIJL = HIER / "stijl.css"
PAGEDJS = HIER / "vendor" / "paged.polyfill.js"
UITVOER = HIER.parent / "RWCrew-Ontwikkelaarshandleiding.pdf"

# Waar Edge of Chrome meestal staat (Windows, macOS, Linux), in volgorde van voorkeur.
BROWSER_KANDIDATEN = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "microsoft-edge",
    "google-chrome",
    "chromium",
]

# Plaatsaanduidingen die dit script in de HTML invult.
TOC_MARKER = "<!-- INHOUDSOPGAVE -->"
FIGUREN_MARKER = "<!-- LIJST-FIGUREN -->"
TABELLEN_MARKER = "<!-- LIJST-TABELLEN -->"

# Draait in de browser na Paged.js: zet "Pagina X van Y" in elke voettekst en meldt
# daarna aan dit script dat de opmaak klaar is (window.__handleidingKlaar).
NA_OPMAAK_SCRIPT = """
class HandleidingKlaar extends Paged.Handler {
  afterRendered(pages) {
    const totaal = pages.length;
    document.querySelectorAll(".pagedjs_page").forEach((pagina, index) => {
      // Het voorblad heeft geen voettekst.
      if (pagina.classList.contains("pagedjs_voorblad_page")) return;
      const vak = pagina.querySelector(".pagedjs_margin-bottom-right > .pagedjs_margin-content");
      if (vak) {
        vak.classList.add("met-totaal");
        vak.setAttribute("data-label", "Pagina " + (index + 1) + " van " + totaal);
      }
    });
    window.__handleidingPaginas = totaal;
    window.__handleidingKlaar = true;
  }
}
Paged.registerHandlers(HandleidingKlaar);
"""

# Hoe lang we maximaal op Paged.js wachten, in seconden.
MAX_WACHTTIJD = 300


# ---------------------------------------------------------------------------
# HTML samenstellen en nummeren
# ---------------------------------------------------------------------------


def slug(tekst: str) -> str:
    """Maak van een titel een eenvoudige id, bv. 'Wat is RWCrew?' -> 'wat-is-rwcrew'."""
    tekst = re.sub(r"<[^>]+>", "", tekst).lower()
    tekst = re.sub(r"[^a-z0-9]+", "-", tekst)
    return tekst.strip("-") or "sectie"


def platte_tekst(fragment: str) -> str:
    """HTML-fragment naar platte tekst (voor de inhoudsopgave)."""
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).replace("\xad", "").strip()


def nummer_document(bron: str) -> tuple[str, list, list, list]:
    """Nummert koppen, figuren en tabellen in documentvolgorde.

    Geeft de genummerde HTML terug, plus de gegevens voor de inhoudsopgave en de
    lijsten van figuren en tabellen. Elk element met een id krijgt een label
    (bv. '§4.2', 'figuur 4.1') dat de kruisverwijzingen daarna gebruiken.
    """
    toc: list[tuple[str, str, str, str]] = []   # (soort, id, nummer, titel)
    figuren: list[tuple[str, str, str]] = []     # (id, nummer, bijschrift)
    tabellen: list[tuple[str, str, str]] = []
    labels: dict[str, str] = {}
    gebruikte_ids: set[str] = set()

    # Tellers: hoofdstuk, bijlage, paragraaf, subparagraaf, figuur en tabel binnen een
    # hoofdstuk, en het nummer van het huidige hoofdstuk ("" = nog in het voorwerk).
    staat = {"h1": 0, "bijlage": 0, "h2": 0, "h3": 0, "fig": 0, "tab": 0, "hoofd": ""}

    def unieke_id(voorstel: str) -> str:
        kandidaat, teller = voorstel, 2
        while kandidaat in gebruikte_ids:
            kandidaat = f"{voorstel}-{teller}"
            teller += 1
        gebruikte_ids.add(kandidaat)
        return kandidaat

    # Eén reguliere expressie die alle te nummeren elementen in volgorde vindt.
    patroon = re.compile(
        r'(?P<deel><section class="deel"[^>]*>)'
        r"|(?P<kop><h(?P<niveau>[123])(?P<attrs>[^>]*)>(?P<titel>.*?)</h(?P=niveau)>)"
        r'|(?P<figuur><figure class="diagram"(?P<fattrs>[^>]*)>)'
        r"|(?P<bijschrift><figcaption>)"
        r"|(?P<tabel><table(?P<tattrs>[^>]*)>\s*<caption>)",
        re.S,
    )

    uitvoer: list[str] = []
    positie = 0
    wachtende_figuur: str | None = None   # id van de figuur waarvan het bijschrift nog komt

    for treffer in patroon.finditer(bron):
        uitvoer.append(bron[positie : treffer.start()])
        positie = treffer.end()
        stuk = treffer.group(0)

        if treffer.group("deel"):
            # Scheidingspagina van een deel: komt in de inhoudsopgave, zonder nummer.
            id_match = re.search(r'id="([^"]+)"', stuk)
            toc_match = re.search(r'data-toc="([^"]+)"', stuk)
            if id_match and toc_match:
                gebruikte_ids.add(id_match.group(1))
                toc.append(("deel", id_match.group(1), "", html.unescape(toc_match.group(1))))
            uitvoer.append(stuk)

        elif treffer.group("kop"):
            niveau, attrs, titel = treffer.group("niveau"), treffer.group("attrs"), treffer.group("titel")
            # Alleen hoofdstuktitels (class="hoofdstuk") en h2/h3 in de hoofdtekst tellen mee;
            # h1's van het voorblad, het voorwerk en de delen niet.
            is_hoofdstuk = niveau == "1" and "hoofdstuk" in attrs
            if niveau == "1" and not is_hoofdstuk:
                uitvoer.append(stuk)
                continue
            # h2/h3 vóór het eerste hoofdstuk (voorwerk) blijven ongenummerd.
            if not is_hoofdstuk and not staat["hoofd"]:
                uitvoer.append(stuk)
                continue

            id_match = re.search(r'id="([^"]+)"', attrs)
            element_id = unieke_id(id_match.group(1) if id_match else slug(titel))
            if not id_match:
                attrs = f'{attrs} id="{element_id}"'

            if is_hoofdstuk:
                if "bijlage" in attrs:
                    staat["bijlage"] += 1
                    nummer = chr(ord("A") + staat["bijlage"] - 1)
                    labels[element_id] = f"bijlage {nummer}"
                    getoond = f"Bijlage {nummer}"
                else:
                    staat["h1"] += 1
                    nummer = str(staat["h1"])
                    labels[element_id] = f"hoofdstuk {nummer}"
                    getoond = nummer
                staat.update(h2=0, h3=0, fig=0, tab=0, hoofd=nummer)
                toc.append(("h1", element_id, getoond, platte_tekst(titel)))
            elif niveau == "2":
                staat["h2"] += 1
                staat["h3"] = 0
                nummer = getoond = f'{staat["hoofd"]}.{staat["h2"]}'
                labels[element_id] = f"§{nummer}"
                toc.append(("h2", element_id, nummer, platte_tekst(titel)))
            else:
                staat["h3"] += 1
                nummer = getoond = f'{staat["hoofd"]}.{staat["h2"]}.{staat["h3"]}'
                labels[element_id] = f"§{nummer}"

            uitvoer.append(f'<h{niveau}{attrs}><span class="num">{getoond}</span> {titel}</h{niveau}>')

        elif treffer.group("figuur"):
            fattrs = treffer.group("fattrs")
            staat["fig"] += 1
            id_match = re.search(r'id="([^"]+)"', fattrs)
            nummer = f'{staat["hoofd"]}.{staat["fig"]}'
            element_id = unieke_id(id_match.group(1) if id_match else f"figuur-{nummer}")
            if not id_match:
                fattrs = f'{fattrs} id="{element_id}"'
            labels[element_id] = f"figuur {nummer}"
            wachtende_figuur = element_id
            uitvoer.append(f'<figure class="diagram"{fattrs}>')

        elif treffer.group("bijschrift"):
            if wachtende_figuur is None:
                # Bijschrift van een ander soort figuur: niet nummeren.
                uitvoer.append(stuk)
                continue
            nummer = labels[wachtende_figuur].split(" ", 1)[1]
            einde = bron.find("</figcaption>", positie)
            figuren.append((wachtende_figuur, nummer, platte_tekst(bron[positie:einde])))
            uitvoer.append(f'<figcaption><span class="fig-num">Figuur {nummer}</span> – ')
            wachtende_figuur = None

        elif treffer.group("tabel"):
            # Tabellen in het voorwerk (vóór hoofdstuk 1) blijven ongenummerd.
            if not staat["hoofd"]:
                uitvoer.append(stuk)
                continue
            tattrs = treffer.group("tattrs")
            staat["tab"] += 1
            id_match = re.search(r'id="([^"]+)"', tattrs)
            nummer = f'{staat["hoofd"]}.{staat["tab"]}'
            element_id = unieke_id(id_match.group(1) if id_match else f"tabel-{nummer}")
            if not id_match:
                tattrs = f'{tattrs} id="{element_id}"'
            labels[element_id] = f"tabel {nummer}"
            einde = bron.find("</caption>", positie)
            tabellen.append((element_id, nummer, platte_tekst(bron[positie:einde])))
            uitvoer.append(f"<table{tattrs}><caption>Tabel {nummer} – ")

    uitvoer.append(bron[positie:])
    genummerd = "".join(uitvoer)

    # Kruisverwijzingen invullen: <a class="ref" href="#id"></a> -> '§4.2' enz.
    def vul_ref(match: re.Match) -> str:
        doel, inhoud = match.group(1), match.group(2)
        if doel not in labels:
            print(f"  waarschuwing: verwijzing naar onbekende id '#{doel}'", file=sys.stderr)
            return match.group(0)
        return f'<a class="ref" href="#{doel}">{inhoud or labels[doel]}</a>'

    genummerd = re.sub(r'<a class="ref" href="#([^"]+)">(.*?)</a>', vul_ref, genummerd)
    return genummerd, toc, figuren, tabellen


def maak_toc(toc: list) -> str:
    """De inhoudsopgave als HTML-lijst (paginanummers vult Paged.js in)."""
    regels = ['<ul class="toc">']
    for soort, element_id, nummer, titel in toc:
        num = f'<span class="toc-num">{html.escape(nummer)}</span>' if nummer else ""
        regels.append(
            f'<li class="toc-{soort}"><a href="#{element_id}"><span class="toc-titel">{num}'
            f'{html.escape(titel)}</span><span class="toc-puntjes"></span></a></li>'
        )
    regels.append("</ul>")
    return "\n".join(regels)


def maak_lijst(items: list, woord: str) -> str:
    """Lijst van figuren of tabellen, in dezelfde opmaak als de inhoudsopgave."""
    regels = ['<ul class="toc toc-lijst">']
    for element_id, nummer, bijschrift in items:
        regels.append(
            f'<li class="toc-h2"><a href="#{element_id}"><span class="toc-titel">'
            f'<span class="toc-num">{woord} {nummer}</span>{html.escape(bijschrift)}</span>'
            f'<span class="toc-puntjes"></span></a></li>'
        )
    regels.append("</ul>")
    return "\n".join(regels)


def bouw_html() -> str:
    """Plakt alle bronbestanden samen en geeft de volledige, genummerde HTML terug."""
    fragmenten = sorted(HOOFDSTUKKEN.glob("*.html"))
    if not fragmenten:
        sys.exit(f"Geen hoofdstukken gevonden in {HOOFDSTUKKEN}")
    inhoud = "\n".join(bestand.read_text(encoding="utf-8") for bestand in fragmenten)

    inhoud, toc, figuren, tabellen = nummer_document(inhoud)
    inhoud = inhoud.replace(TOC_MARKER, maak_toc(toc))
    inhoud = inhoud.replace(FIGUREN_MARKER, maak_lijst(figuren, "Figuur"))
    inhoud = inhoud.replace(TABELLEN_MARKER, maak_lijst(tabellen, "Tabel"))

    aantal_hoofdstukken = sum(1 for t in toc if t[0] == "h1")
    print(f"  {aantal_hoofdstukken} hoofdstukken/bijlagen, {len(figuren)} figuren, {len(tabellen)} tabellen")

    # De CSS en Paged.js worden in de HTML geplakt: Paged.js kan via file:// geen
    # losse stylesheets ophalen.
    return (
        '<!doctype html>\n<html lang="nl">\n<head>\n<meta charset="utf-8">\n'
        "<title>RWCrew – Ontwikkelaarshandleiding</title>\n"
        f"<style>\n{STIJL.read_text(encoding='utf-8')}\n</style>\n"
        f"<script>\n{PAGEDJS.read_text(encoding='utf-8')}\n</script>\n"
        f"<script>\n{NA_OPMAAK_SCRIPT}\n</script>\n"
        f"</head>\n<body>\n{inhoud}\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------
# De browser aansturen (DevTools-protocol over een websocket, alleen standaardbibliotheek)
# ---------------------------------------------------------------------------


def zoek_browser() -> str:
    """Geef het pad van Edge of Chrome terug, of stop met een duidelijke melding."""
    for kandidaat in BROWSER_KANDIDATEN:
        if Path(kandidaat).is_file():
            return kandidaat
        gevonden = shutil.which(kandidaat)
        if gevonden:
            return gevonden
    sys.exit("Geen Microsoft Edge of Google Chrome gevonden: installeer er één om de PDF te maken.")


class DevTools:
    """Minimale websocket-client voor het Chrome DevTools-protocol.

    Genoeg om een pagina te openen, JavaScript te evalueren en naar PDF af te drukken;
    zo is er geen extra pakket (Puppeteer, Playwright, websockets) nodig.
    """

    def __init__(self, ws_url: str) -> None:
        match = re.match(r"ws://([^:/]+):(\d+)(/.*)", ws_url)
        if not match:
            raise RuntimeError(f"Onverwacht DevTools-adres: {ws_url}")
        host, poort, pad = match.group(1), int(match.group(2)), match.group(3)
        self.sock = socket.create_connection((host, poort), timeout=MAX_WACHTTIJD)
        self.volgnummer = 0

        # Websocket-handdruk: een gewoon HTTP-verzoek met "Upgrade: websocket".
        sleutel = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(
            (
                f"GET {pad} HTTP/1.1\r\nHost: {host}:{poort}\r\nUpgrade: websocket\r\n"
                f"Connection: Upgrade\r\nSec-WebSocket-Key: {sleutel}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        antwoord = b""
        while b"\r\n\r\n" not in antwoord:
            antwoord += self.sock.recv(4096)
        if b" 101 " not in antwoord.split(b"\r\n", 1)[0]:
            raise RuntimeError("De browser weigerde de DevTools-verbinding.")
        self.buffer = antwoord.split(b"\r\n\r\n", 1)[1]

    def _lees(self, aantal: int) -> bytes:
        while len(self.buffer) < aantal:
            blok = self.sock.recv(1 << 20)
            if not blok:
                raise RuntimeError("DevTools-verbinding onverwacht gesloten.")
            self.buffer += blok
        data, self.buffer = self.buffer[:aantal], self.buffer[aantal:]
        return data

    def _verstuur_frame(self, opcode: int, payload: bytes) -> None:
        # Een client moet zijn frames maskeren (websocket-regel).
        masker = os.urandom(4)
        kop = bytes([0x80 | opcode])
        lengte = len(payload)
        if lengte < 126:
            kop += bytes([0x80 | lengte])
        elif lengte < 1 << 16:
            kop += bytes([0x80 | 126]) + lengte.to_bytes(2, "big")
        else:
            kop += bytes([0x80 | 127]) + lengte.to_bytes(8, "big")
        gemaskeerd = bytes(b ^ masker[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(kop + masker + gemaskeerd)

    def _ontvang_bericht(self) -> dict:
        delen: list[bytes] = []
        while True:
            byte1, byte2 = self._lees(2)
            opcode, laatste = byte1 & 0x0F, byte1 & 0x80
            lengte = byte2 & 0x7F
            if lengte == 126:
                lengte = int.from_bytes(self._lees(2), "big")
            elif lengte == 127:
                lengte = int.from_bytes(self._lees(8), "big")
            payload = self._lees(lengte)
            if opcode == 0x9:          # ping -> pong
                self._verstuur_frame(0xA, payload)
                continue
            if opcode == 0x8:          # sluiten
                raise RuntimeError("De browser sloot de DevTools-verbinding.")
            delen.append(payload)
            if laatste:
                return json.loads(b"".join(delen))

    def roep(self, methode: str, **parameters) -> dict:
        """Stuur één DevTools-commando en wacht op het antwoord daarop."""
        self.volgnummer += 1
        mijn_id = self.volgnummer
        self._verstuur_frame(0x1, json.dumps({"id": mijn_id, "method": methode, "params": parameters}).encode())
        while True:
            bericht = self._ontvang_bericht()
            if bericht.get("id") == mijn_id:
                if "error" in bericht:
                    raise RuntimeError(f"{methode} mislukte: {bericht['error']}")
                return bericht.get("result", {})

    def evalueer(self, expressie: str):
        resultaat = self.roep("Runtime.evaluate", expression=expressie, returnByValue=True)
        return resultaat.get("result", {}).get("value")


def druk_af(browser: str, html_bestand: Path, profiel_map: Path) -> tuple[bytes, int]:
    """Opent de HTML in een onzichtbare browser, wacht op Paged.js en geeft de PDF terug."""
    proces = subprocess.Popen(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--remote-debugging-port=0",
            # Een eigen, tijdelijk profiel: botst niet met een geopende Edge/Chrome.
            f"--user-data-dir={profiel_map}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # Met poort 0 kiest de browser zelf een vrije poort en schrijft die in dit bestand.
        poortbestand = profiel_map / "DevToolsActivePort"
        deadline = time.monotonic() + 30
        while not (poortbestand.exists() and poortbestand.read_text().strip()):
            if time.monotonic() > deadline or proces.poll() is not None:
                sys.exit("De browser startte niet in headless-modus.")
            time.sleep(0.2)
        poort = int(poortbestand.read_text().splitlines()[0])

        with urllib.request.urlopen(f"http://127.0.0.1:{poort}/json/list") as antwoord:
            doelen = json.load(antwoord)
        pagina = next(doel for doel in doelen if doel.get("type") == "page")
        devtools = DevTools(pagina["webSocketDebuggerUrl"])

        devtools.roep("Page.enable")
        devtools.roep("Page.navigate", url=html_bestand.as_uri())

        # Wachten tot Paged.js alle pagina's heeft opgemaakt.
        deadline = time.monotonic() + MAX_WACHTTIJD
        while not devtools.evalueer("window.__handleidingKlaar === true"):
            if time.monotonic() > deadline:
                sys.exit("Paged.js werd niet op tijd klaar met de opmaak.")
            time.sleep(0.5)
        paginas = int(devtools.evalueer("window.__handleidingPaginas"))

        resultaat = devtools.roep(
            "Page.printToPDF",
            printBackground=True,
            preferCSSPageSize=True,
            displayHeaderFooter=False,
            # Bladwijzers in de PDF op basis van de koppen.
            generateDocumentOutline=True,
        )
        try:
            devtools.roep("Browser.close")
        except RuntimeError:
            pass
        return base64.b64decode(resultaat["data"]), paginas
    finally:
        try:
            proces.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proces.kill()


def main() -> None:
    browser = zoek_browser()
    print(f"Browser: {browser}")
    print("HTML samenstellen...")
    volledige_html = bouw_html()

    # ignore_cleanup_errors: de browser kan zijn profielbestanden nog even vasthouden.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tijdelijk:
        tijdelijke_map = Path(tijdelijk)
        html_bestand = tijdelijke_map / "handleiding.html"
        html_bestand.write_text(volledige_html, encoding="utf-8")
        profiel_map = tijdelijke_map / "profiel"
        profiel_map.mkdir()

        print("Opmaken met Paged.js en afdrukken naar PDF...")
        pdf, paginas = druk_af(browser, html_bestand, profiel_map)

    UITVOER.write_bytes(pdf)
    print(f"Klaar: {UITVOER} ({paginas} pagina's)")


if __name__ == "__main__":
    main()
