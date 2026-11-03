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

def test_sorting_by_agency_status_unit_code():
    # 2 agencies: Agency A and Agency B
    # Each agency has Còn hàng, Đang lock, Đã bán in mixed input order
    scanned_units = [
        # Agency B units
        {
            "unit_key": "B-03",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu B", "B-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đã bán"] + [""] * 4 + ['=HYPERLINK("http://b", "Agency B")', "03/11/2026"]
        },
        {
            "unit_key": "B-01",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu B", "B-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] * 4 + ['=HYPERLINK("http://b", "Agency B")', "03/11/2026"]
        },
        {
            "unit_key": "B-02",
            "is_exclusive": False,
            "status": "Đang lock",
            "row_values": [0, "Khu B", "B-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đang lock"] + [""] * 4 + ['=HYPERLINK("http://b", "Agency B")', "03/11/2026"]
        },
        # Agency A units
        {
            "unit_key": "A-03",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "A-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đã bán"] + [""] * 4 + ["Agency A", "03/11/2026"]
        },
        {
            "unit_key": "A-02",
            "is_exclusive": False,
            "status": "Đang lock",
            "row_values": [0, "Khu A", "A-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đang lock"] + [""] * 4 + ["Agency A", "03/11/2026"]
        },
        {
            "unit_key": "A-01",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "A-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] * 4 + ["Agency A", "03/11/2026"]
        },
    ]

    final_rows = smart_upsert_pool({}, scanned_units, is_low_rise=True)
    assert len(final_rows) == 6

    # Verify Agency A group comes first, sorted Còn hàng -> Đang lock -> Đã bán
    expected_order = ["A-01", "A-02", "A-03", "B-01", "B-02", "B-03"]
    actual_order = [r[2] for r in final_rows]
    assert actual_order == expected_order

    # Verify STT 1 to 6
    assert [r[0] for r in final_rows] == [1, 2, 3, 4, 5, 6]

def test_smart_upsert_pool_expiry_and_daily_stats():
    from datetime import date, timedelta
    today = date(2026, 11, 3)
    today_str = today.strftime("%d/%m/%Y")
    d29_str = (today - timedelta(days=29)).strftime("%d/%m/%Y")

    # existing_pool has:
    # 1. LK-01 from Agency A: was 'Còn hàng', issued 29 days ago -> will become EXPIRING_SOON
    # 2. LK-02 from Agency A: was 'Còn hàng', now scanned as 'Đã bán' -> will count towards sold_today!
    # 3. LK-03 from Agency B: was 'Còn hàng', issued 10 days ago (network failed, preserved)
    existing_pool = {
        "LK-01": {
            "unit_key": "LK-01",
            "row_values": [1, "Khu A", "LK-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] * 4 + ["Agency A", d29_str]
        },
        "LK-02": {
            "unit_key": "LK-02",
            "row_values": [2, "Khu A", "LK-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] * 4 + ["Agency A", "01/10/2026"]
        },
        "LK-03": {
            "unit_key": "LK-03",
            "row_values": [3, "Khu B", "LK-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] * 4 + ["Agency B", "24/10/2026"]
        }
    }

    # scanned_units has:
    # 1. LK-01 from Agency A: still 'Còn hàng', same issue date
    # 2. LK-02 from Agency A: marked 'Đã bán'
    # 3. LK-04 from Agency A: brand new unit added today!
    scanned_units = [
        {
            "unit_key": "LK-01",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] * 4 + ["Agency A", d29_str]
        },
        {
            "unit_key": "LK-02",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "LK-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đã bán"] + [""] * 4 + ["Agency A", "01/10/2026"]
        },
        {
            "unit_key": "LK-04",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-04", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] * 4 + ["Agency A", today_str]
        }
    ]

    final_rows, stats = smart_upsert_pool(
        existing_pool,
        scanned_units,
        is_low_rise=True,
        today_str=today_str,
        successful_agencies={"Agency A"},
        return_stats=True
    )

    # Check row length is 39 for all rows
    assert all(len(r) == 39 for r in final_rows)

    # LK-01 should have expiry warning at col 38
    lk01_row = next(r for r in final_rows if r[2] == "LK-01")
    assert "⚠️ Sắp hết hạn" in lk01_row[38]

    # Preserved LK-03 should also have expiry computed at col 38
    lk03_row = next(r for r in final_rows if r[2] == "LK-03")
    assert "Còn" in lk03_row[38]

    # Verify daily stats
    p_stats = stats["project_stats"]
    assert p_stats["total_units"] == 4
    assert p_stats["new_today"] == 1  # LK-04 is new today
    assert p_stats["sold_today"] == 1  # LK-02 transitioned to Đã bán
    assert p_stats["expiring_soon"] == 1  # LK-01 is 29 days

    ag_a_stats = stats["agency_stats"]["AGENCY A"]
    assert ag_a_stats["new_today"] == 1
    assert ag_a_stats["sold_today"] == 1
    assert ag_a_stats["expiring_soon"] == 1
    assert ag_a_stats["total_units"] == 3

