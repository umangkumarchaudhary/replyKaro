# -*- coding: utf-8 -*-

"""

    Module :mod:`core.utils.money`

    Rupee amounts: read "₹7.98 Lakh" style text into numbers, and format numbers back.

"""

# ----------- START: Native Imports ---------- #
import re
# ----------- END: Native Imports ---------- #

__all__ = ["LAKH", "CRORE", "extract_prices", "parse_price", "format_price"]

LAKH = 100_000
CRORE = 10_000_000

_UNITS = {"lakh": LAKH, "lac": LAKH, "l": LAKH, "cr": CRORE, "crore": CRORE, "k": 1_000}

# "₹16.8 lakh", "Rs 9.99L", "₹15,000", "INR 2 cr", "₹50k", "14.49 lakh", "1.2 crore"
_PRICE = re.compile(
    r"(?:₹|\brs\.?|\binr)\s*(\d[\d,]*(?:\.\d+)?)\s*(lakh|lac|l\b|cr\b|crore|k\b)?"
    r"|(\d[\d,]*(?:\.\d+)?)\s*(lakh|lac|crore|cr\b)",
    re.IGNORECASE,
)


def extract_prices(text: str) -> list[int]:
    """Every rupee amount mentioned in ``text``, in rupees."""
    out = []
    for m in _PRICE.finditer(text):
        number, unit = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        value = float(number.replace(",", "")) * _UNITS.get((unit or "").lower(), 1)
        out.append(round(value))
    return out


def parse_price(value: int | float | str | None) -> float | None:
    """Accept 798000, "798000", "₹7.98 Lakh", "Rs 1,500" → rupees."""
    if value is None or isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    try:
        return float(text.replace(",", ""))
    except ValueError:
        pass
    found = extract_prices(text)
    if not found:
        raise ValueError(f"Can't read a price from {value!r}")
    return float(found[0])


def format_price(rupees: float | None) -> str:
    if rupees is None:
        return ""
    if rupees >= CRORE:
        return f"₹{rupees / CRORE:.2f} Cr"
    if rupees >= LAKH:
        return f"₹{rupees / LAKH:.2f} Lakh"
    return f"₹{rupees:,.0f}"
