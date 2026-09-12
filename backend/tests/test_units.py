from app.matching.normalize import normalize_name
from app.matching.units import parse_size, price_per_canonical_unit


def test_kg_and_grams_are_the_same_variant():
    kilo = parse_size("Surf Excel Matic Detergent Powder 1 KG")
    grams = parse_size("Surf Excel Matic Powder 1000g")
    assert kilo.key == grams.key
    assert kilo.key == (1, 1000.0, "g")
    assert kilo.label == "1 kg"


def test_half_kilo_is_not_one_kilo():
    small = parse_size("Surf Excel Matic 500g")
    large = parse_size("Surf Excel Matic 1kg")
    assert small.key != large.key
    assert small.key == (1, 500.0, "g")


def test_multipack_is_distinct():
    single = parse_size("Coke 1.5L")
    twin = parse_size("Coke 2 × 1.5L")
    assert single.key == (1, 1500.0, "ml")
    assert twin.key == (2, 1500.0, "ml")
    assert single.key != twin.key


def test_name_normalization_strips_size():
    assert normalize_name("Surf Excel Matic Detergent Powder 1 KG", "Surf Excel") == "matic detergent powder"
    assert normalize_name("Surf Excel Matic Powder 1000g", "Surf Excel") == "matic powder"


def test_price_per_kg():
    size = parse_size("500g")
    amount, unit = price_per_canonical_unit(280, size)
    assert unit == "Rs/kg"
    assert amount == 560.0
