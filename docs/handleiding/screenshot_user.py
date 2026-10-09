"""Tijdelijke gebruiker voor de schermafbeeldingen van de handleiding.

Gebruik (vanuit de repo-root, met de Python van de backend, tegen de LOKALE database):

    backend/.venv/Scripts/python docs/handleiding/screenshot_user.py setup
    backend/.venv/Scripts/python docs/handleiding/screenshot_user.py cleanup

"setup" exporteert ook alle namen, e-mailadressen, telefoonnummers en IP-adressen naar
.screenshot-namen.json (niet in Git), zodat screenshots.py ze kan maskeren. "setup" maakt de superbeheerder screenshots@voorbeeld.be aan met toegang tot elke module en, in elke
module met rollen per scherm, een rol "Screenshots (tijdelijk)" met alle rechten op alle schermen.
Het wachtwoord wordt in docs/handleiding/.screenshot-login geschreven (niet in Git), waar
screenshots.py het leest. "cleanup" verwijdert de gebruiker, die rollen, zijn inloghistoriek en dat bestand.
"""

import importlib
import json
import secrets
import sys
from pathlib import Path

# De backend-code importeerbaar maken (app.*) en de backend/.env laten lezen.
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
import os  # noqa: E402

os.chdir(REPO / "backend")

from sqlalchemy import delete, select, text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db import base  # noqa: E402,F401  (registreert alle modellen)
from app.db.models.login_history import LoginHistory  # noqa: E402
from app.db.models.module import Module  # noqa: E402
from app.db.models.user import User  # noqa: E402
from app.db.models.user_module_access import UserModuleAccess  # noqa: E402

EMAIL = "screenshots@voorbeeld.be"
ROL_NAAM = "Screenshots (tijdelijk)"
LOGIN_BESTAND = Path(__file__).resolve().parent / ".screenshot-login"
NAMEN_BESTAND = Path(__file__).resolve().parent / ".screenshot-namen.json"

# Per module met rollen per scherm: het voorvoegsel van de modelbestanden en -klassen.
ROLLEN_MODULES = [
    ("tagscan", "Tagscan"),
    ("kartracker", "KarTracker"),
    ("intervention_requests", "InterventionRequests"),
    ("stockmaster", "StockMaster"),
    ("altsien_select", "AltsienSelect"),
    ("masterdata", "MasterData"),
]


def modellen(bestand: str, klasse: str):
    """De vier rechtenmodellen van één module: scherm, rol, rolrecht, gebruikersrol."""
    def laad(achtervoegsel_bestand: str, achtervoegsel_klasse: str):
        module = importlib.import_module(f"app.db.models.{bestand}_{achtervoegsel_bestand}")
        return getattr(module, f"{klasse}{achtervoegsel_klasse}")

    return (
        laad("screen", "Screen"),
        laad("role", "Role"),
        laad("role_permission", "RolePermission"),
        laad("user_role", "UserRole"),
    )


def setup() -> None:
    wachtwoord = secrets.token_urlsafe(16)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == EMAIL)) is not None:
            sys.exit("De screenshotgebruiker bestaat al; voer eerst 'cleanup' uit.")

        gebruiker = User(
            email=EMAIL,
            display_name="Demo Beheerder",
            hashed_password=hash_password(wachtwoord),
            is_super_admin=True,
            is_active=True,
        )
        db.add(gebruiker)
        db.flush()

        # Toegang tot elke actieve module.
        for module in db.scalars(select(Module).where(Module.is_active.is_(True))):
            db.add(UserModuleAccess(user_id=gebruiker.id, module_id=module.id))

        # In elke module met rollen per scherm: een rol met alle rechten, toegekend aan de gebruiker.
        for bestand, klasse in ROLLEN_MODULES:
            Scherm, Rol, RolRecht, GebruikersRol = modellen(bestand, klasse)
            rol = Rol(name=ROL_NAAM)
            db.add(rol)
            db.flush()
            for scherm in db.scalars(select(Scherm)):
                db.add(RolRecht(role_id=rol.id, screen_id=scherm.id, can_view=True, can_create=True, can_edit=True, can_delete=True))
            db.add(GebruikersRol(user_id=gebruiker.id, role_id=rol.id))

        db.commit()

    LOGIN_BESTAND.write_text(f"{EMAIL}\n{wachtwoord}\n", encoding="utf-8")
    exporteer_persoonsgegevens()
    print(f"Aangemaakt: {EMAIL} (wachtwoord in {LOGIN_BESTAND.name})")


def exporteer_persoonsgegevens() -> None:
    """Schrijft alle namen, e-mailadressen, telefoonnummers en IP-adressen uit de database naar
    .screenshot-namen.json, zodat screenshots.py ze op het scherm kan vervangen door fictieve waarden."""
    bronnen = {
        "namen": [
            ('"Landing_users"', "display_name"),
            ('"MasterData_team_responsible"', "name"),
            ('"InterventionRequests_mailing_recipient"', "name"),
            ('"InterventionRequests_request"', "employee_name"),
            ('"InterventionRequests_request"', "handled_by"),
            ('"StockMaster_document"', "created_by_name"),
            ('"StockMaster_movement"', "created_by_name"),
            ('"StockMaster_kar_requirement"', "updated_by_name"),
            ('"StockMaster_reason"', "created_by_name"),
        ],
        "emails": [
            ('"Landing_users"', "email"),
            ('"MasterData_team_responsible"', "email"),
            ('"InterventionRequests_mailing_recipient"', "email"),
            ('"Landing_login_history"', "email_attempted"),
        ],
        "telefoons": [
            ('"Landing_users"', "phone"),
            ('"MasterData_team_responsible"', "phone"),
            ('"InterventionRequests_request"', "employee_phone"),
        ],
        "ips": [('"Landing_login_history"', "ip_address")],
    }
    resultaat: dict[str, list[str]] = {}
    with SessionLocal() as db:
        for soort, kolommen in bronnen.items():
            waarden: set[str] = set()
            for tabel, kolom in kolommen:
                for (waarde,) in db.execute(text(f"SELECT DISTINCT {kolom} FROM {tabel} WHERE {kolom} IS NOT NULL")):
                    if str(waarde).strip() and waarde != "Demo Beheerder":
                        waarden.add(str(waarde).strip())
            resultaat[soort] = sorted(waarden, key=len, reverse=True)   # langste eerst vervangen
    NAMEN_BESTAND.write_text(json.dumps(resultaat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Persoonsgegevens om te maskeren: {', '.join(f'{len(v)} {k}' for k, v in resultaat.items())}")


def cleanup() -> None:
    with SessionLocal() as db:
        gebruiker = db.scalar(select(User).where(User.email == EMAIL))
        for bestand, klasse in ROLLEN_MODULES:
            _Scherm, Rol, RolRecht, GebruikersRol = modellen(bestand, klasse)
            rol = db.scalar(select(Rol).where(Rol.name == ROL_NAAM))
            if rol is not None:
                db.execute(delete(GebruikersRol).where(GebruikersRol.role_id == rol.id))
                db.execute(delete(RolRecht).where(RolRecht.role_id == rol.id))
                db.delete(rol)
        db.execute(delete(LoginHistory).where(LoginHistory.email_attempted == EMAIL))
        if gebruiker is not None:
            db.delete(gebruiker)
        db.commit()

        # Controle: niets meer over.
        over = db.scalar(select(User).where(User.email == EMAIL))
        rollen_over = sum(
            1 for bestand, klasse in ROLLEN_MODULES
            if db.scalar(select(modellen(bestand, klasse)[1]).where(modellen(bestand, klasse)[1].name == ROL_NAAM))
        )
    LOGIN_BESTAND.unlink(missing_ok=True)
    NAMEN_BESTAND.unlink(missing_ok=True)
    print(f"Opgeruimd: gebruiker over = {over is not None}, tijdelijke rollen over = {rollen_over}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("setup", "cleanup"):
        sys.exit("Gebruik: screenshot_user.py setup|cleanup")
    setup() if sys.argv[1] == "setup" else cleanup()
