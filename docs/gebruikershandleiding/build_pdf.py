"""Bouwt de RWCrew-gebruikershandleiding (PDF) uit de bronbestanden in deze map.

Gebruik (vanuit de repo-root, met eender welke Python 3.10+; geen extra pakketten nodig):

    python docs/gebruikershandleiding/build_pdf.py

Resultaat: docs/RWCrew-Gebruikershandleiding.pdf

Dit script hergebruikt de bouwlogica van de ontwikkelaarshandleiding
(docs/handleiding/build_pdf.py: nummering, inhoudsopgave, Paged.js en afdrukken via
Edge/Chrome). Het zet enkel de mappen, de titel en de uitvoer om naar die van de
gebruikershandleiding.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

# Mappen en bestanden, relatief ten opzichte van dit script.
HIER = Path(__file__).resolve().parent
BASIS_SCRIPT = HIER.parent / "handleiding" / "build_pdf.py"

# De bouwlogica van de ontwikkelaarshandleiding inladen als module.
spec = importlib.util.spec_from_file_location("handleiding_build", BASIS_SCRIPT)
basis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(basis)

# Eigen hoofdstukken, eigen opmaak en eigen uitvoerbestand; Paged.js blijft gedeeld.
basis.HOOFDSTUKKEN = HIER / "hoofdstukken"
basis.STIJL = HIER / "stijl.css"
basis.UITVOER = HIER.parent / "RWCrew-Gebruikershandleiding.pdf"

# De HTML-titel (die in de PDF-eigenschappen terechtkomt) aanpassen.
_originele_bouw_html = basis.bouw_html


def bouw_html() -> str:
    return _originele_bouw_html().replace(
        "<title>RWCrew – Ontwikkelaarshandleiding</title>",
        "<title>RWCrew – Gebruikershandleiding</title>",
    )


basis.bouw_html = bouw_html

if __name__ == "__main__":
    basis.main()
