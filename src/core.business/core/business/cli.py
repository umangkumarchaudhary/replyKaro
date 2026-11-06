# -*- coding: utf-8 -*-

"""

    Module :mod:`core.business.cli`

    ``replykaro-load``: create or update businesses from TOML/JSON spec files.

        uv run replykaro-load examples/<business>.toml [more files...]

"""

# ----------- START: Native Imports ---------- #
import argparse
# ----------- END: Native Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.business.spec import import_business, load_spec_file
from core.business.verticals import available_verticals
from core.db.session import init_db, session_scope
# ----------- END: In-App Imports ---------- #

__all__ = ["main"]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="replykaro-load", description="Create or update businesses from TOML/JSON spec files."
    )
    parser.add_argument("files", nargs="+", help="business spec files (.toml or .json)")
    args = parser.parse_args(argv)

    init_db()
    known = available_verticals()
    with session_scope() as session:
        for path in args.files:
            spec = load_spec_file(path)
            tenant = import_business(session, spec)
            note = "" if spec.vertical in known else f"  (no '{spec.vertical}' template → using generic)"
            print(
                f"✓ {tenant.name}  slug={tenant.slug}  vertical={spec.vertical}{note}\n"
                f"  {len(spec.products)} products/services, {len(spec.faqs)} FAQs, {len(spec.offers)} offers"
            )


if __name__ == "__main__":
    main()
