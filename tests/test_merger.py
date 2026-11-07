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
            "row_values": [0, "Khu A", "LK-10", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] + ["Agency A", "03/11/2026"] + [""] * 3
        },
        # Agency B lists LK-10 but has NO prices, so it got status 'Đã bán' due to missing price
        {
            "unit_key": "LK-10",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "LK-10", "Thô", "LK", 100, 200, ""] + [""] * 23 + ["Đã bán"] + [""] + ["Agency B", "03/11/2026"] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool(existing_pool, scanned_units, is_low_rise=True)
    assert len(final_rows) == 1
    # Must preserve Agency A's Còn hàng status and price!
    assert final_rows[0][31] == "Còn hàng"
    assert final_rows[0][7] == 5000000000
    assert final_rows[0][33] == "Agency A"

def test_smart_upsert_purges_obsolete_rows_from_successful_agency():
    # If Agency A had old phantom unit 'LK-99' in existing_pool,
    # but Agency A was successfully scanned today and only has 'LK-01',
    # 'LK-99' MUST be purged!
    # Meanwhile Agency B was NOT in successful_agencies (failed), so its unit 'LK-88' is preserved.
    existing_pool = {
        "LK-99": {
            "unit_key": "LK-99",
            # Agency is col 36 for low rise
            "row_values": [1, "Khu A", "LK-99"] + [""] * 30 + ["Agency A"] + [""] * 5
        },
        "LK-88": {
            "unit_key": "LK-88",
            "row_values": [2, "Khu A", "LK-88"] + [""] * 30 + ["Agency B"] + [""] * 5
        }
    }
    scanned_units = [
        {
            "unit_key": "LK-01",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-01"] + [""] * 30 + ["Agency A"] + [""] * 5
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
            "row_values": [0, "Khu B", "B-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đã bán"] + [""] + ['=HYPERLINK("http://b", "Agency B")', "03/11/2026"] + [""] * 3
        },
        {
            "unit_key": "B-01",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu B", "B-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] + ['=HYPERLINK("http://b", "Agency B")', "03/11/2026"] + [""] * 3
        },
        {
            "unit_key": "B-02",
            "is_exclusive": False,
            "status": "Đang lock",
            "row_values": [0, "Khu B", "B-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đang lock"] + [""] + ['=HYPERLINK("http://b", "Agency B")', "03/11/2026"] + [""] * 3
        },
        # Agency A units
        {
            "unit_key": "A-03",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "A-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đã bán"] + [""] + ["Agency A", "03/11/2026"] + [""] * 3
        },
        {
            "unit_key": "A-02",
            "is_exclusive": False,
            "status": "Đang lock",
            "row_values": [0, "Khu A", "A-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đang lock"] + [""] + ["Agency A", "03/11/2026"] + [""] * 3
        },
        {
            "unit_key": "A-01",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "A-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] + ["Agency A", "03/11/2026"] + [""] * 3
        },
    ]

    final_rows = smart_upsert_pool({}, scanned_units, is_low_rise=True)
    assert len(final_rows) == 6

    # Verify:
    # 1. Các căn hoạt động (Còn hàng, Đang lock) luôn nằm ở phần trên (nhóm theo Đại lý A-Z)
    # 2. Toàn bộ các căn Đã bán bị đẩy xuống đáy của trang tính (không nằm xen kẽ trong nhóm đại lý)
    expected_order = ["A-01", "A-02", "B-01", "B-02", "A-03", "B-03"]
    actual_order = [r[2] for r in final_rows]
    assert actual_order == expected_order

    # Verify STT 1 to 6
    assert [r[0] for r in final_rows] == [1, 2, 3, 4, 5, 6]

def test_smart_upsert_pool_expiry_and_daily_stats():
    from datetime import date, timedelta
    today = date.today()
    today_str = today.strftime("%d/%m/%Y")
    d29_str = (today - timedelta(days=29)).strftime("%d/%m/%Y")

    # existing_pool has:
    # 1. LK-01 from Agency A: was 'Còn hàng', issued 29 days ago -> will become EXPIRING_SOON
    # 2. LK-02 from Agency A: was 'Còn hàng', now scanned as 'Đã bán' -> will count towards sold_today!
    # 3. LK-03 from Agency B: was 'Còn hàng', issued 10 days ago (network failed, preserved)
    existing_pool = {
        "LK-01": {
            "unit_key": "LK-01",
            "row_values": [1, "Khu A", "LK-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] + ["Agency A", d29_str] + [""] * 3
        },
        "LK-02": {
            "unit_key": "LK-02",
            "row_values": [2, "Khu A", "LK-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] + ["Agency A", "01/10/2026"] + [""] * 3
        },
        "LK-03": {
            "unit_key": "LK-03",
            "row_values": [3, "Khu B", "LK-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] + ["Agency B", "24/10/2026"] + [""] * 3
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
            "row_values": [0, "Khu A", "LK-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] + ["Agency A", d29_str] + [""] * 3
        },
        {
            "unit_key": "LK-02",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "LK-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đã bán"] + [""] + ["Agency A", "01/10/2026"] + [""] * 3
        },
        {
            "unit_key": "LK-04",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-04", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng"] + [""] + ["Agency A", today_str] + [""] * 3
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

    # LK-01 should have expiry warning at col 35
    lk01_row = next(r for r in final_rows if r[2] == "LK-01")
    assert "⚠️ Sắp hết hạn" in lk01_row[35]

    # Preserved LK-03 should also have expiry computed at col 35
    lk03_row = next(r for r in final_rows if r[2] == "LK-03")
    assert "Còn" in lk03_row[35]

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

def test_exclusive_agency_available_cannot_be_overwritten_by_general_sold():
    # Scenario: Agency A (Độc quyền) lists LK-20 as Còn hàng with valid price
    # Agency B (Quỹ chung) lists LK-20 as Đã bán (e.g. hid the row or marked red)
    # Result: LK-20 MUST belong to Agency A and MUST remain 'Còn hàng'!
    scanned_units = [
        # Agency B (Quỹ chung) scanned first
        {
            "unit_key": "LK-20",
            "agency_name": "Agency B",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "LK-20", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Đã bán", "Quỹ chung"] + ["Agency B", "03/11/2026", "Còn 30 ngày"] + [""] * 3
        },
        # Agency A (Độc quyền) scanned second
        {
            "unit_key": "LK-20",
            "agency_name": "Agency A",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-20", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["Agency A", "03/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool({}, scanned_units, is_low_rise=True)
    assert len(final_rows) == 1
    row = final_rows[0]
    # Unit code
    assert row[2] == "LK-20"
    # Status MUST remain Còn hàng
    assert row[31] == "Còn hàng"
    # Agency MUST be Agency A
    assert row[33] == "Agency A"
    # Nhóm quỹ MUST be Độc quyền
    assert row[32] == "Độc quyền"

def test_make_sort_key_quy_chung_at_the_bottom():
    # Agencies A and B, plus Quỹ chung
    # Quỹ chung MUST sort at the very end
    scanned_units = [
        {
            "unit_key": "LK-01",
            "agency_name": "Quỹ chung",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Quỹ chung"] + ["Quỹ chung", "04/11/2026", "Còn 30 ngày"] + [""] * 3
        },
        {
            "unit_key": "LK-02",
            "agency_name": "VHS",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["VHS", "04/11/2026", "Còn 30 ngày"] + [""] * 3
        },
        {
            "unit_key": "LK-03",
            "agency_name": "BHS",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["BHS", "04/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool({}, scanned_units, is_low_rise=True)
    assert len(final_rows) == 3
    # Row 0: Quỹ chung (hiển thị đầu bảng theo quy tắc mới)
    assert final_rows[0][33] == "Quỹ chung"
    # Row 1: BHS
    assert final_rows[1][33] == "BHS"
    # Row 2: VHS
    assert final_rows[2][33] == "VHS"

def test_reallocation_when_exclusive_expired():
    from datetime import date, timedelta
    today = date.today()
    today_str = today.strftime("%d/%m/%Y")
    d40_ago_str = (today - timedelta(days=40)).strftime("%d/%m/%Y")

    # existing_pool: LK-99 belonged to Agency A 40 days ago (> 30 days -> EXPIRED)
    existing_pool = {
        "LK-99": {
            "unit_key": "LK-99",
            "row_values": [1, "Khu A", "LK-99", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["Agency A", d40_ago_str, "⛔ Đã hết hạn (Quá 10 ngày)"] + [""] * 3
        }
    }

    # Now Agency B scans LK-99 as exclusive with price
    scanned_units = [
        {
            "unit_key": "LK-99",
            "agency_name": "Agency B",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-99", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["Agency B", "", ""] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool(existing_pool, scanned_units, is_low_rise=True, today_str=today_str)
    assert len(final_rows) == 1
    row = final_rows[0]
    assert row[2] == "LK-99"
    # Agency transferred to Agency B
    assert row[33] == "Agency B"
    # Issue date reset to today_str!
    assert row[34] == today_str
    # Expiry reset to 30 days!
    assert "Còn 30 ngày" in row[35]

def test_agency_marking_common_fund_yields_to_official_general_pool():
    # Scenario like AN3-12:
    # Agency NOVASKY has AN3-12 marked 'Chung' (is_exclusive=False)
    # Official 'Quỹ chung' also has AN3-12 (is_exclusive=False)
    # Both have valid prices. Official Quỹ chung MUST win!
    scanned_units = [
        {
            "unit_key": "AN3-12",
            "agency_name": "NOVASKY",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Đảo Ngọc", "AN3-12", "Hoàn thiện", "LK", 70, 208, 10000000000] + [""] * 23 + ["Còn hàng", "Quỹ chung"] + ["NOVASKY", "04/11/2026", "Còn 30 ngày"] + [""] * 3
        },
        {
            "unit_key": "AN3-12",
            "agency_name": "Quỹ chung",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Đảo Ngọc", "AN3-12", "Hoàn thiện", "LK", 70, 208, 10000000000] + [""] * 23 + ["Còn hàng", "Quỹ chung"] + ["Quỹ chung", "04/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool({}, scanned_units, is_low_rise=True)
    assert len(final_rows) == 1
    assert final_rows[0][2] == "AN3-12"
    assert final_rows[0][32] == "Quỹ chung"
    assert final_rows[0][33] == "Quỹ chung"

def test_active_exclusive_candidate_overrides_inactive_protected_owner():
    # Scenario like SV5-07:
    # Existing owner MAI VIET had the unit recorded with an issue date within 30 days.
    # But MAI VIET has hidden or marked the unit as 'Đã bán'.
    # Meanwhile, DAT XANH MT scans the unit as active ('Còn hàng') with full price.
    # DAT XANH MT MUST win and status MUST be 'Còn hàng'.
    existing_pool = {
        "SV5-07": {
            "unit_key": "SV5-07",
            "row_values": [1, "Đảo Ngọc", "SV5-07", "Hoàn thiện", "LK", 70, 192.3, 16497494953] + [""] * 23 + ["Đã bán", "Độc quyền"] + ["MAI VIỆT", "01/11/2026", "Còn 27 ngày"] + [""] * 3
        }
    }
    scanned_units = [
        # MAI VIET scanned first, still 'Đã bán'
        {
            "unit_key": "SV5-07",
            "agency_name": "MAI VIỆT",
            "is_exclusive": True,
            "status": "Đã bán",
            "row_values": [0, "Đảo Ngọc", "SV5-07", "Hoàn thiện", "LK", 70, 192.3, 16497494953, 1541747818, 82487475, 18121730246] + [""] * 20 + ["Đã bán", "Độc quyền"] + ["MAI VIỆT", "01/11/2026", "Còn 27 ngày"] + [""] * 3
        },
        # DAT XANH MT scanned second, 'Còn hàng'
        {
            "unit_key": "SV5-07",
            "agency_name": "Đất xanh MT",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Đảo Ngọc", "SV5-07", "Hoàn thiện", "LK", 70, 192.3, 15692938557, 1461292179, 82487475, 17236718211] + [""] * 20 + ["Còn hàng", "Độc quyền"] + ["Đất xanh MT", "04/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool(existing_pool, scanned_units, is_low_rise=True, today_str="04/11/2026")
    assert len(final_rows) == 1
    row = final_rows[0]
    assert row[2] == "SV5-07"
    assert row[31] == "Còn hàng"
    assert row[33] == "Đất xanh MT"
    assert row[32] == "Độc quyền"
    assert row[34] == "04/11/2026"

def test_richer_pricing_overrides_sparse_agency_when_both_active():
    # Scenario like ĐLHV-09:
    # Agency MGLAND lists ĐLHV-09 with only 1 price field.
    # Agency DAT XANH MT lists ĐLHV-09 with 4 detailed price fields.
    # DAT XANH MT MUST win due to higher data fidelity and price completeness.
    existing_pool = {
        "ĐLHV-09": {
            "unit_key": "ĐLHV-09",
            "row_values": [1, "Bạch Vân", "ĐLHV-09", "Thô", "LK", 80, 244.9, ""] + [""] * 2 + [8756092369] + [""] * 20 + ["Còn hàng", "Độc quyền"] + ["MGLAND", "01/11/2026", "Còn 27 ngày"] + [""] * 3
        }
    }
    scanned_units = [
        # MGLAND scanned first (1 price field)
        {
            "unit_key": "ĐLHV-09",
            "agency_name": "MGLAND",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Bạch Vân", "ĐLHV-09", "Thô", "LK", 80, 244.9, ""] + [""] * 2 + [8756092369] + [""] * 20 + ["Còn hàng", "Độc quyền"] + ["MGLAND", "01/11/2026", "Còn 27 ngày"] + [""] * 3
        },
        # DAT XANH MT scanned second (4 price fields)
        {
            "unit_key": "ĐLHV-09",
            "agency_name": "Đất xanh MT",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Bạch Vân", "ĐLHV-09", "Thô", "LK", 80, 244.9, 8038027068, 680372219, 37693082, 8756092369] + [""] * 20 + ["Còn hàng", "Độc quyền"] + ["Đất xanh MT", "04/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool(existing_pool, scanned_units, is_low_rise=True, today_str="04/11/2026")
    assert len(final_rows) == 1
    row = final_rows[0]
    assert row[2] == "ĐLHV-09"
    assert row[31] == "Còn hàng"
    assert row[33] == "Đất xanh MT"
    assert row[7] == 8038027068







def test_issue_date_preserved_on_repeated_sync():
    """
    Kiểm tra bảo toàn ngày cấp hàng:
    - Căn hộ đã có trong kho từ hôm qua (04/11/2026), hôm nay (05/11/2026) quét lại không có ngày cấp:
      -> PHẢI giữ nguyên 04/11/2026.
    - Căn hộ mới toanh hôm nay xuất hiện lần đầu:
      -> Được gán 05/11/2026.
    - Căn hộ chuyển từ Agency A sang Agency B hôm nay:
      -> Được gán 05/11/2026.
    """
    existing_pool = {
        "LK-OLD": {
            "unit_key": "LK-OLD",
            "row_values": [1, "Khu A", "LK-OLD", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["Agency A", "04/11/2026", "Còn 29 ngày"] + [""] * 3
        },
        "LK-TRANSFER": {
            "unit_key": "LK-TRANSFER",
            "row_values": [2, "Khu A", "LK-TRANSFER", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["Agency A", "04/11/2026", "Còn 29 ngày"] + [""] * 3
        }
    }

    scanned_units = [
        # LK-OLD: quét lại cùng Agency A, nguồn không ghi ngày cấp (để rỗng)
        {
            "unit_key": "LK-OLD",
            "agency_name": "Agency A",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-OLD", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["Agency A", "", ""] + [""] * 3
        },
        # LK-TRANSFER: quét sang Agency B (chuyển đại lý), nguồn không ghi ngày cấp
        {
            "unit_key": "LK-TRANSFER",
            "agency_name": "Agency B",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-TRANSFER", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["Agency B", "", ""] + [""] * 3
        },
        # LK-NEW: Căn mới toanh hôm nay
        {
            "unit_key": "LK-NEW",
            "agency_name": "Agency A",
            "is_exclusive": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-NEW", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Độc quyền"] + ["Agency A", "", ""] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool(
        existing_pool,
        scanned_units,
        is_low_rise=True,
        today_str="05/11/2026",
        successful_agencies={"Agency A", "Agency B"}
    )

    by_key = {r[2]: r for r in final_rows}

    # LK-OLD must keep 04/11/2026 (col 37)
    assert by_key["LK-OLD"][34] == "04/11/2026"

    # LK-TRANSFER must update to 05/11/2026 because owner changed
    assert by_key["LK-TRANSFER"][34] == "05/11/2026"
    assert by_key["LK-TRANSFER"][33] == "Agency B"

    # LK-NEW must get 05/11/2026 because it is brand new
    assert by_key["LK-NEW"][34] == "05/11/2026"


def test_vhub_exclusive_source_wins_over_general_pool():
    """
    Nguồn Quỹ độc quyền Vhub luôn ưu tiên lấy thông tin từ nguồn được gán:
    Nếu một căn xuất hiện ở cả Quỹ chung (chính thức) và VHUB:
    -> VHUB PHẢI CHIẾN THẮNG (Đại lý = VHUB, Nhóm quỹ = Quỹ độc quyền).
    """
    scanned_units = [
        # Quỹ chung quét trước với giá đầy đủ
        {
            "unit_key": "LK-VHUB-01",
            "agency_name": "Quỹ chung",
            "is_exclusive": False,
            "is_vhub": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-VHUB-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Quỹ chung"] + ["Quỹ chung", "03/11/2026", "Còn 30 ngày"] + [""] * 3
        },
        # VHUB quét sau với thông tin từ nguồn được gán
        {
            "unit_key": "LK-VHUB-01",
            "agency_name": "VHUB",
            "is_exclusive": True,
            "is_vhub": True,
            "status": "Đang lock",
            "row_values": [0, "Khu A", "LK-VHUB-01", "Thô", "LK", 100, 200, 5200000000] + [""] * 23 + ["Đang lock", "Quỹ độc quyền"] + ["VHUB", "05/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool({}, scanned_units, is_low_rise=True, today_str="05/11/2026")
    assert len(final_rows) == 1
    row = final_rows[0]
    assert row[2] == "LK-VHUB-01"
    assert row[31] == "Đang lock"
    assert row[32] == "Quỹ độc quyền"
    assert row[33] == "VHUB"
    assert row[7] == 5200000000


def test_vhub_exclusive_source_wins_over_other_agency_with_more_prices():
    """
    Nếu Đại lý khác có nhiều trường giá hơn nhưng căn đó thuộc nguồn Quỹ độc quyền VHUB:
    -> VHUB VẪN PHẢI CHIẾN THẮNG vì nguồn VHUB được ưu tiên tuyệt đối.
    """
    scanned_units = [
        # Agency A điền nhiều giá hơn
        {
            "unit_key": "LK-VHUB-02",
            "agency_name": "Agency A",
            "is_exclusive": True,
            "is_vhub": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-VHUB-02", "Thô", "LK", 100, 200, 5000000000, 500000000, 100000000, 5600000000] + [""] * 20 + ["Còn hàng", "Quỹ chéo"] + ["Agency A", "03/11/2026", "Còn 30 ngày"] + [""] * 3
        },
        # VHUB chỉ có 1 trường giá
        {
            "unit_key": "LK-VHUB-02",
            "agency_name": "VHUB",
            "is_exclusive": True,
            "is_vhub": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-VHUB-02", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Quỹ độc quyền"] + ["VHUB", "05/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool({}, scanned_units, is_low_rise=True, today_str="05/11/2026")
    assert len(final_rows) == 1
    row = final_rows[0]
    assert row[2] == "LK-VHUB-02"
    assert row[32] == "Quỹ độc quyền"
    assert row[33] == "VHUB"


def test_vhub_takes_over_existing_unit_from_old_agency():
    """
    Căn hộ trước đây thuộc Agency A (< 30 ngày), nhưng đợt này VHUB đưa vào giỏ độc quyền:
    -> VHUB PHẢI LẤY ĐƯỢC QUYỀN SỞ HỮU, bảo vệ chủ sở hữu cũ không ngăn cản VHUB.
    """
    existing_pool = {
        "LK-VHUB-03": {
            "unit_key": "LK-VHUB-03",
            "row_values": [1, "Khu A", "LK-VHUB-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Quỹ chéo"] + ["Agency A", "01/11/2026", "Còn 26 ngày"] + [""] * 3
        }
    }
    scanned_units = [
        {
            "unit_key": "LK-VHUB-03",
            "agency_name": "Agency A",
            "is_exclusive": True,
            "is_vhub": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-VHUB-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Quỹ chéo"] + ["Agency A", "01/11/2026", "Còn 26 ngày"] + [""] * 3
        },
        {
            "unit_key": "LK-VHUB-03",
            "agency_name": "VHUB",
            "is_exclusive": True,
            "is_vhub": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-VHUB-03", "Thô", "LK", 100, 200, 5000000000] + [""] * 23 + ["Còn hàng", "Quỹ độc quyền"] + ["VHUB", "05/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    final_rows = smart_upsert_pool(existing_pool, scanned_units, is_low_rise=True, today_str="05/11/2026", successful_agencies={"Agency A", "VHUB"})
    assert len(final_rows) == 1
    row = final_rows[0]
    assert row[2] == "LK-VHUB-03"
    assert row[32] == "Quỹ độc quyền"
    assert row[33] == "VHUB"


def test_sold_today_persistence_across_cycles():
    """
    Kiểm tra tính bền vững của chỉ số Chuyển Đã bán hôm nay qua nhiều chu kỳ:
    - Chu kỳ N: Căn chuyển từ Còn hàng -> Đã bán (được tag [Đã bán 07/11/2026]).
    - Chu kỳ N+1 (vài phút sau): Đọc lại kho cũ đã là Đã bán, đợt quét mới vẫn là Đã bán.
      -> PHẢI TIẾP TỤC ĐƯỢC TÍNH vào sold_today suốt cả ngày!
    """
    today = "07/11/2026"
    # Chu kỳ N: kho cũ là Còn hàng, vừa quét được Đã bán
    existing_pool_1 = {
        "LK-SOLD-01": {
            "unit_key": "LK-SOLD-01",
            "row_values": [1, "Khu A", "LK-SOLD-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["Ghi chú cũ", "Còn hàng", "Quỹ chéo", "Agency A", "01/11/2026", "Còn 24 ngày"] + [""] * 3
        }
    }
    scanned_1 = [
        {
            "unit_key": "LK-SOLD-01",
            "agency_name": "Agency A",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "LK-SOLD-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["", "Đã bán", "Quỹ chéo", "Agency A", "01/11/2026", "Còn 24 ngày"] + [""] * 3
        }
    ]
    rows_1, stats_1 = smart_upsert_pool(existing_pool_1, scanned_1, is_low_rise=True, today_str=today, return_stats=True)
    assert stats_1["project_stats"]["sold_today"] == 1
    assert stats_1["agency_stats"]["AGENCY A"]["sold_today"] == 1
    assert "[Đã bán 07/11/2026]" in rows_1[0][30]

    # Chu kỳ N+1: kho cũ lúc này chính là kết quả của chu kỳ N
    existing_pool_2 = {
        "LK-SOLD-01": {
            "unit_key": "LK-SOLD-01",
            "row_values": rows_1[0]
        }
    }
    scanned_2 = scanned_1  # đại lý vẫn quét ra Đã bán
    rows_2, stats_2 = smart_upsert_pool(existing_pool_2, scanned_2, is_low_rise=True, today_str=today, return_stats=True)
    # Vẫn phải giữ sold_today = 1 (không bị tụt về 0 sau 1 chu kỳ)
    assert stats_2["project_stats"]["sold_today"] == 1
    assert stats_2["agency_stats"]["AGENCY A"]["sold_today"] == 1


def test_transition_to_sold_tracked_today():
    """
    Kiểm tra khi căn chuyển trạng thái sang Đã bán trong ngày:
    - Căn LK-ACTIVE trước đó Còn hàng.
    - Agency A quét ra LK-ACTIVE với trạng thái Đã bán (qua từ khóa / gạch ngang).
    -> Căn này phải được chuyển sang Đã bán, gắn tag [Đã bán hôm nay] và tính vào sold_today!
    """
    today = "07/11/2026"
    existing_pool = {
        "LK-ACTIVE": {
            "unit_key": "LK-ACTIVE",
            "row_values": [1, "Khu A", "LK-ACTIVE", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["", "Còn hàng", "Quỹ chéo", "Agency A", "01/11/2026", "Còn 24 ngày"] + [""] * 3
        }
    }
    scanned = [
        {
            "unit_key": "LK-ACTIVE",
            "agency_name": "Agency A",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "LK-ACTIVE", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["", "Đã bán", "Quỹ chéo", "Agency A", "07/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    rows, stats = smart_upsert_pool(
        existing_pool,
        scanned,
        is_low_rise=True,
        today_str=today,
        successful_agencies={"Agency A"},
        return_stats=True
    )
    by_key = {r[2]: r for r in rows}
    assert "LK-ACTIVE" in by_key
    assert by_key["LK-ACTIVE"][31] == "Đã bán"
    assert "[Đã bán 07/11/2026]" in by_key["LK-ACTIVE"][30]
    assert stats["project_stats"]["sold_today"] == 1
    assert stats["agency_stats"]["AGENCY A"]["sold_today"] == 1


def test_sold_today_resets_on_next_day():
    """
    Kiểm tra sang ngày mới, các căn đã bán của ngày hôm trước không bị tính vào sold_today của ngày mới.
    """
    existing_pool = {
        "LK-YESTERDAY": {
            "unit_key": "LK-YESTERDAY",
            "row_values": [1, "Khu A", "LK-YESTERDAY", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["[Đã bán 06/11/2026]", "Đã bán", "Quỹ chéo", "Agency A", "01/11/2026", "Còn 24 ngày"] + [""] * 3
        }
    }
    scanned = [
        {
            "unit_key": "LK-YESTERDAY",
            "agency_name": "Agency A",
            "is_exclusive": False,
            "status": "Đã bán",
            "row_values": [0, "Khu A", "LK-YESTERDAY", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["", "Đã bán", "Quỹ chéo", "Agency A", "01/11/2026", "Còn 24 ngày"] + [""] * 3
        }
    ]
    today = "07/11/2026"
    rows, stats = smart_upsert_pool(existing_pool, scanned, is_low_rise=True, today_str=today, return_stats=True)
    assert stats["project_stats"]["sold_today"] == 0


def test_removed_active_unit_marked_sold_and_counted_today():
    """
    Tiêu chí 3: Căn không xuất hiện ở những chu kỳ đồng bộ sau đó:
    - Căn LK-ABSENT trước đó là 'Còn hàng'.
    - Agency A quét thành công nhưng KHÔNG CÒN LK-ABSENT trong bảng hàng nguồn mới.
    -> Căn này chuyển thành 'Đã bán' kèm ghi chú '[Đã bán {today_str}] Đã xóa khỏi bảng hàng nguồn', và tính vào sold_today!
    """
    today = "07/11/2026"
    existing_pool = {
        "LK-ABSENT": {
            "unit_key": "LK-ABSENT",
            "row_values": [1, "Khu A", "LK-ABSENT", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["", "Còn hàng", "Quỹ chéo", "Agency A", "01/11/2026", "Còn 24 ngày"] + [""] * 3
        }
    }
    # Agency A quét thành công nhưng danh sách trả về chỉ có căn khác
    scanned = [
        {
            "unit_key": "LK-OTHER",
            "agency_name": "Agency A",
            "is_exclusive": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-OTHER", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["", "Còn hàng", "Quỹ chéo", "Agency A", "07/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]

    rows, stats = smart_upsert_pool(
        existing_pool,
        scanned,
        is_low_rise=True,
        today_str=today,
        successful_agencies={"Agency A"},
        return_stats=True
    )
    by_key = {r[2]: r for r in rows}
    assert "LK-ABSENT" in by_key
    assert by_key["LK-ABSENT"][31] == "Đã bán"
    assert "[Đã bán 07/11/2026] Đã xóa khỏi bảng hàng nguồn" in by_key["LK-ABSENT"][30]
    assert stats["project_stats"]["sold_today"] == 1
    assert stats["agency_stats"]["AGENCY A"]["sold_today"] == 1


def test_vhub_and_official_qc_always_win_over_third_party_agencies():
    """
    Quy tắc thẩm quyền nguồn:
    Nếu dự án có Quỹ độc quyền Vhub và Quỹ chung được khai báo rõ ràng,
    các sản phẩm ở các nguồn này LUÔN THẮNG và được ghi nhận là Độc quyền hoặc Quỹ chung.
    Các đại lý khác dù có giá đầy đủ hơn cũng KHÔNG được đè nguồn Quỹ độc quyền Vhub hay Quỹ chung!
    """
    # Trường hợp 1: Quỹ chung vs Đại lý bên ngoài có nhiều trường giá
    scanned_qc = [
        {
            "unit_key": "LK-SHARED-01",
            "agency_name": "Agency Khác",
            "is_exclusive": False,
            "is_vhub": False,
            "is_general_pool": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-SHARED-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["", "Còn hàng", "Quỹ chéo", "Agency Khác", "07/11/2026", "Còn 30 ngày"] + [""] * 3
        },
        {
            "unit_key": "LK-SHARED-01",
            "agency_name": "Quỹ chung",
            "is_exclusive": False,
            "is_vhub": False,
            "is_general_pool": True,
            "status": "Còn hàng",
            # Quỹ chung không có giá
            "row_values": [0, "Khu A", "LK-SHARED-01", "Thô", "LK", 100, 200, ""] + [""] * 22 + ["", "Còn hàng", "Quỹ chung", "Quỹ chung", "07/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]
    rows_qc = smart_upsert_pool({}, scanned_qc, is_low_rise=True, today_str="07/11/2026")
    assert len(rows_qc) == 1
    # Quỹ chung phải thắng!
    assert rows_qc[0][32] == "Quỹ chung"
    assert "Quỹ chung" in rows_qc[0][33]

    # Trường hợp 2: Vhub độc quyền vs Quỹ chung và Agency Khác
    scanned_vhub = [
        {
            "unit_key": "LK-VHUB-01",
            "agency_name": "Quỹ chung",
            "is_exclusive": False,
            "is_vhub": False,
            "is_general_pool": True,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-VHUB-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["", "Còn hàng", "Quỹ chung", "Quỹ chung", "07/11/2026", "Còn 30 ngày"] + [""] * 3
        },
        {
            "unit_key": "LK-VHUB-01",
            "agency_name": "Vhub",
            "is_exclusive": True,
            "is_vhub": True,
            "is_general_pool": False,
            "status": "Còn hàng",
            "row_values": [0, "Khu A", "LK-VHUB-01", "Thô", "LK", 100, 200, 5000000000] + [""] * 22 + ["", "Còn hàng", "Quỹ độc quyền", "Vhub", "07/11/2026", "Còn 30 ngày"] + [""] * 3
        }
    ]
    rows_vhub = smart_upsert_pool({}, scanned_vhub, is_low_rise=True, today_str="07/11/2026")
    assert len(rows_vhub) == 1
    # Vhub phải thắng và là Quỹ độc quyền!
    assert rows_vhub[0][32] == "Quỹ độc quyền"
    assert "Vhub" in rows_vhub[0][33]

