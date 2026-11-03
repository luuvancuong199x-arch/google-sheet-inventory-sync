import pytest
from src.merger import smart_upsert_pool

def test_smart_upsert_preserves_unscanned_units():
    # Scenario: Unit 'LK-01' was in the target sheet previously.
    # In this run, Agency A failed to load, so 'LK-01' is not in scanned_units.
    # 'LK-01' MUST NOT be deleted!
    existing_pool = {
        "LK-01": {
            "unit_key": "LK-01",
            "row_values": [1, "Khu A", "LK-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 30
        }
    }
    scanned_units = [
        {
            "unit_key": "LK-02",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-02", "Thô", "LK", 120, 240, 6000000000] + [""] * 30
        }
    ]

    final_rows = smart_upsert_pool(existing_pool, scanned_units, is_low_rise=True)
    assert len(final_rows) == 2
    keys = [r[2] for r in final_rows]
    assert "LK-01" in keys
    assert "LK-02" in keys
    # STT must be sequential 1, 2
    assert final_rows[0][0] == 1
    assert final_rows[1][0] == 2

def test_smart_upsert_sold_status_priority():
    existing_pool = {}
    scanned_units = [
        {
            "unit_key": "LK-05",
            "is_exclusive": False,
            "status": "Còn hàng",
            # Col 7 is gia_chua_vat = 5000000000
            "row_values": [0, "Khu A", "LK-05", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] * 6
        },
        {
            "unit_key": "LK-05",
            "is_exclusive": True,
            "status": "Đã bán",
            # Col 7 is gia_chua_vat = 5000000000
            "row_values": [0, "Khu A", "LK-05", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đã bán"] + [""] * 6
        }
    ]

    final_rows = smart_upsert_pool(existing_pool, scanned_units, is_low_rise=True)
    assert len(final_rows) == 1
    # Status column is index 31 for low rise
    assert final_rows[0][31] == "Đã bán"

def test_unpriced_agency_cannot_overwrite_priced_agency_with_sold():
    existing_pool = {}
    scanned_units = [
        # Agency A has valid price (5 tỷ) and is Còn hàng
        {
            "unit_key": "LK-10",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-10", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] * 4 + ["Agency A", "03/11/2026"]
        },
        # Agency B lists LK-10 but has NO prices, so it got status 'Đã bán' due to missing price
        {
            "unit_key": "LK-10",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "LK-10", "Thô", "LK", 100, 200, ""] + [""] * 23 + ["Đã bán"] + [""] * 4 + ["Agency B", "03/11/2026"]
        }
    ]

    final_rows = smart_upsert_pool(existing_pool, scanned_units, is_low_rise=True)
    assert len(final_rows) == 1
    # Must preserve Agency A's Còn hàng status and price!
    assert final_rows[0][31] == "Còn hàng"
    assert final_rows[0][7] == 5000000000
    assert final_rows[0][36] == "Agency A"

def test_smart_upsert_purges_obsolete_rows_from_successful_agency():
    # If Agency A had old phantom unit 'LK-99' in existing_pool,
    # but Agency A was successfully scanned today and only has 'LK-01',
    # 'LK-99' MUST be purged!
    # Meanwhile Agency B was NOT in successful_agencies (failed), so its unit 'LK-88' is preserved.
    existing_pool = {
        "LK-99": {
            "unit_key": "LK-99",
            # Agency is col 36 for low rise
            "row_values": [1, "Khu A", "LK-99"] + [""] * 33 + ["Agency A"] + [""] * 5
        },
        "LK-88": {
            "unit_key": "LK-88",
            "row_values": [2, "Khu A", "LK-88"] + [""] * 33 + ["Agency B"] + [""] * 5
        }
    }
    scanned_units = [
        {
            "unit_key": "LK-01",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-01"] + [""] * 33 + ["Agency A"] + [""] * 5
        }
    ]

    final_rows = smart_upsert_pool(
        existing_pool,
        scanned_units,
        is_low_rise=True,
        successful_agencies={"Agency A"}
    )

    keys = [r[2] for r in final_rows]
    assert "LK-01" in keys
    assert "LK-88" in keys  # Preserved because Agency B failed
    assert "LK-99" not in keys  # Purged because Agency A refreshed successfully without it
