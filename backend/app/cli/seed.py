# This script prepares a freshly-created database for first use:
#   1. It makes sure all 9 modules exist as rows in the "Landing_modules" table.
#   2. It makes sure a starting set of seasons exists in "MasterData_season".
#   3. It creates the very first super-admin user account, so there is
#      someone who can log in and start granting access to everyone else.
#
# Run it from the "backend" folder with the virtual environment active,
# for example:
#   python -m app.cli.seed --email admin@rwcrew.example --password "ChangeMe123!" --name "RW Crew Admin"
#
# It is safe to run more than once: modules/seasons are only added if
# missing, and it refuses to create a second user with the same email
# address.

import argparse

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.user import User
from app.modules.registry import MODULE_DEFINITIONS

# The seasons that should already exist the first time anyone opens the
# Master Data screen, so it isn't empty. More can always be added by hand
# afterwards from that same screen.
STARTER_SEASON_NAMES = ["2026", "2027", "2028", "2029"]


def seed_modules() -> None:
    """Make sure every module in MODULE_DEFINITIONS exists in the database."""
    with SessionLocal() as db:
        existing_keys = set(db.scalars(select(Module.key)).all())

        for definition in MODULE_DEFINITIONS:
            if definition.key in existing_keys:
                # This module row already exists — leave it as-is, so we
                # don't overwrite a name an admin may have already changed.
                continue
            db.add(Module(key=definition.key, name=definition.name, sort_order=definition.sort_order))

        db.commit()


def seed_seasons() -> None:
    """Make sure every season in STARTER_SEASON_NAMES exists in the database."""
    with SessionLocal() as db:
        existing_names = set(db.scalars(select(Season.name)).all())

        for name in STARTER_SEASON_NAMES:
            if name in existing_names:
                # Already there — leave it alone.
                continue
            db.add(Season(name=name))

        db.commit()


def seed_super_admin(email: str, password: str, display_name: str) -> None:
    """Create the first super-admin account, unless that email is already taken."""
    with SessionLocal() as db:
        already_exists = db.scalar(select(User).where(User.email == email)) is not None
        if already_exists:
            print(f"A user with email '{email}' already exists — skipping creation.")
            return

        db.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                display_name=display_name,
                is_super_admin=True,
            )
        )
        db.commit()
        print(f"Created super-admin user '{email}'.")


def main() -> None:
    # Read the admin's details from the command line, so no personal
    # details need to be hard-coded into this file.
    parser = argparse.ArgumentParser(description="Seed the RW Crew database with modules and a super admin.")
    parser.add_argument("--email", required=True, help="Login email for the first super-admin user")
    parser.add_argument("--password", required=True, help="Login password for the first super-admin user")
    parser.add_argument("--name", required=True, help="Display name for the first super-admin user")
    arguments = parser.parse_args()

    seed_modules()
    seed_seasons()
    seed_super_admin(email=arguments.email, password=arguments.password, display_name=arguments.name)


if __name__ == "__main__":
    main()
