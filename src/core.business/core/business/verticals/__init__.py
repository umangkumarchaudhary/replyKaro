# -*- coding: utf-8 -*-

"""

    Package :mod:`core.business.verticals`

    Industry templates. Add an industry by dropping a ``<name>.toml`` file in
    this folder; set a business's ``vertical`` to that name.

"""

# ----------- START: Native Imports ---------- #
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
# ----------- END: Native Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.utils.constants import DEFAULT_VERTICAL
# ----------- END: In-App Imports ---------- #

__all__ = ["Vertical", "get_vertical", "available_verticals"]

_DIR = Path(__file__).parent


@dataclass(frozen=True)
class Vertical:
    key: str
    label: str
    booking_type: str
    collect: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)


@lru_cache
def get_vertical(key: str | None) -> Vertical:
    """The template for ``key``, falling back to the generic one."""
    path = _DIR / f"{key}.toml"
    if not key or not path.is_file():
        key, path = DEFAULT_VERTICAL, _DIR / f"{DEFAULT_VERTICAL}.toml"
    return Vertical(key=key, **tomllib.loads(path.read_text(encoding="utf-8")))


def available_verticals() -> list[str]:
    return sorted(p.stem for p in _DIR.glob("*.toml"))
