import pytest

from core.utils.money import extract_prices, format_price, parse_price


@pytest.mark.parametrize("text, expected", [
    ("Hector starts at ₹14.49 Lakh*", [1_449_000]),
    ("Rs 9.99L only", [999_000]),
    ("EMI from ₹15,000/month", [15_000]),
    ("bonus up to ₹50k", [50_000]),
    ("about 16.8 lakh on-road", [1_680_000]),
    ("Gloster ₹1.2 crore? no, 38.88 lakh", [12_000_000, 3_888_000]),
    ("₹4.99 Lakh + ₹3.1/km", [499_000, 3]),
])
def test_extract_prices(text, expected):
    assert extract_prices(text) == expected


@pytest.mark.parametrize("text", [
    "Our hours 10 AM to 7 PM",  # "rs 10" inside "hours" must not count as a price
    "Range up to 449 km, warranty 1,20,000 km",
    "Call 7799935258",
])
def test_no_false_prices(text):
    assert extract_prices(text) == []


def test_parse_and_format():
    assert parse_price("₹7.98 Lakh") == 798_000
    assert parse_price("1,500") == 1500
    assert parse_price(500) == 500
    assert parse_price(None) is None
    with pytest.raises(ValueError):
        parse_price("call us")
    assert format_price(798_000) == "₹7.98 Lakh"
    assert format_price(1500) == "₹1,500"
    assert format_price(12_000_000) == "₹1.20 Cr"
