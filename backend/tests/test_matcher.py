from app.matching.matcher import _line_conflict
from app.matching.normalize import normalize_barcode


def test_barcode_from_ean():
    assert normalize_barcode("8901030866470") == "8901030866470"
    assert normalize_barcode("sku-12") is None


def test_line_conflict_keeps_comfort_separate():
    assert _line_conflict("comfort washing powder", "washing powder") is True
    assert _line_conflict("washing powder", "washing powder") is False
