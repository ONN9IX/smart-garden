"""Install a legally reviewed JSON bundle; never publishes drafts implicitly.

python -m app.cli.privacy_catalog /protected/catalog.json [--reviewed]
This command records supplied approval, not legal certification.
"""

import argparse
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.privacy_catalog import CatalogInput, install_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--reviewed", action="store_true")
    args = parser.parse_args()
    try:
        catalog = CatalogInput.model_validate_json(args.bundle.read_text())
        with SessionLocal.begin() as db:
            install_catalog(
                db, catalog, reviewed=args.reviewed, app_env=get_settings().app_env
            )
    except (ValueError, OSError, SQLAlchemyError):
        # Validation error details may contain legal contacts or SQL input.
        raise SystemExit(
            "Catalog rejected; validate the protected bundle without logging its contents"
        ) from None
    print(
        "Catalog installed; real-data use still requires separate legal and operational acceptance"
    )


if __name__ == "__main__":
    main()
