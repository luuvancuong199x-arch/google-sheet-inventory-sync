import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from src.config import LOW_RISE_HEADERS, HIGH_RISE_HEADERS
from src.db_writer import (
    resolve_vhub_project,
    map_merged_row_to_db_record,
    has_inventory_changed,
    bulk_upsert_products_to_db,
)
from src.daemon import get_adaptive_interval_sec, get_process_memory_mb
from datetime import datetime


def test_adaptive_polling_intervals():
    assert get_adaptive_interval_sec(datetime(2026, 11, 4, 10, 0)) == 120
    assert get_adaptive_interval_sec(datetime(2026, 11, 4, 19, 30)) == 300
    assert get_adaptive_interval_sec(datetime(2026, 11, 4, 2, 15)) == 1800
    assert get_process_memory_mb() >= 0.0


def test_resolve_vhub_project():
    assert resolve_vhub_project("làng vân") == ("vinhomes-hai-van-bay", "VINHOMES HẢI VÂN BAY")
    assert resolve_vhub_project("DƯƠNG KINH") == ("vinhomes-golden-city", "VINHOMES GOLDEN CITY")
    assert resolve_vhub_project("MAS CAO TẦNG", sub_tab="MGC") == (
        "masteri-grand-coast",
        "MASTERI GRAND COAST",
    )
    assert resolve_vhub_project("MAS CAO TẦNG", sub_tab="HSG") == (
        "lumiere-hanoi-seasons-garden",
        "LUMIÈRE Hanoi Seasons Garden",
    )


def test_map_low_rise_row_to_db_record():
    row = [""] * len(LOW_RISE_HEADERS)
    row[0] = 1
    row[1] = "Đảo Ngọc"
    row[2] = "HC4-02"
    row[3] = "Bàn giao thô"
    row[4] = "Liền kề"
    row[5] = 111.6
    row[6] = 246.1
    row[7] = 13500000000
    row[8] = 1350000000
    row[9] = 98829217
    row[10] = 14948829217
    row[11] = 3000000000
    row[12] = 300000000
    row[13] = 50000000
    row[14] = 3350000000
    row[15] = 10500000000
    row[16] = 1050000000
    row[17] = 48829217
    row[18] = 11598829217
    row[19] = 133950083
    row[20] = 15100000000
    row[21] = 14500000000
    row[22] = 13748000000
    row[23] = "Đông Bắc, Tây Nam"
    row[24] = 6.0
    row[25] = "4"
    row[26] = "Voucher Vinmec 100tr"
    row[27] = "Căn góc công viên"
    row[28] = "20/08/2026"
    row[29] = "MB, VCB"
    row[30] = "TTĐC"
    row[31] = "Còn hàng"
    row[32] = "Quỹ độc quyền"
    row[33] = "https://drive.google.com/file/d/img1/view"
    row[34] = '=HYPERLINK("https://drive.google.com/file/d/ptg1/view", "Xem PTG")'
    row[35] = "https://drive.google.com/file/d/combo1/view"
    row[36] = '=HYPERLINK("https://docs.google.com/spreadsheets/d/123", "VHS")'
    row[37] = "01/11/2026"
    row[38] = "Còn 27 ngày (Đã bán 3 ngày)"

    rec = map_merged_row_to_db_record(
        row=row,
        project_key="làng vân",
        is_low_rise=True,
    )

    assert rec is not None
    assert rec["product_code"] == "HC4-02"
    assert rec["project_id"] == "vinhomes-hai-van-bay"
    assert rec["project_name"] == "VINHOMES HẢI VÂN BAY"
    assert rec["product_type"] == "thap_tang"
    assert rec["subdivision_name"] == "Đảo Ngọc"
    assert rec["delivery_standards"] == "Bàn giao thô"
    assert rec["apartment_type_name"] == "Liền kề"
    assert rec["land_area"] == Decimal("111.6")
    assert rec["construction_area"] == Decimal("246.1")
    assert rec["price_before_vat"] == Decimal("13500000000")
    assert rec["total_price"] == Decimal("14948829217")
    assert rec["early_payment_price"] == Decimal("13748000000")
    assert rec["front_width"] == Decimal("6.0")
    assert rec["floor_count"] == "4"
    assert rec["policy_date"] == date(2026, 8, 20)
    assert rec["supporting_banks"] == "MB, VCB"
    assert rec["state_line"] == "available"
    assert rec["state_line_name"] == "Còn hàng"
    assert rec["fund_groups_sell_name"] == "Quỹ độc quyền"
    assert rec["fund_type"] == "Quỹ đối tác"
    assert rec["partner"] == "VHS"
    assert rec["product_images"] == ["https://drive.google.com/file/d/img1/view"]
    assert rec["pricing_sheet_images"] == ["https://drive.google.com/file/d/ptg1/view"]
    assert rec["x_link_layout_design"] == "https://drive.google.com/file/d/combo1/view"

    meta = rec["metadata"]
    assert meta["partner"] == "VHS"
    assert meta["allocationDate"] == "2026-11-01"
    assert meta["filterKeys"]["typeKey"] == "lienke"
    assert meta["filterKeys"]["subdivisionKey"] == "daongoc"
    assert meta["filterKeys"]["subdivisionAcronym"] == "dn"
    assert meta["filterKeys"]["directionKeys"] == ["dong_bac", "tay_nam"]


def test_map_high_rise_row_to_db_record():
    row = [""] * len(HIGH_RISE_HEADERS)
    row[0] = 1
    row[1] = "MGC-S1-12A05"
    row[2] = "The Wave"
    row[3] = "2PN+"
    row[4] = "Đông Nam"
    row[5] = "S1"
    row[6] = "12A"
    row[7] = "05"
    row[8] = 68.5
    row[9] = 74.2
    row[10] = "2"
    row[11] = "2.5"
    row[12] = 95000000
    row[13] = 4750000000
    row[14] = 5320000000
    row[15] = 5400000000
    row[16] = 5200000000
    row[17] = 4950000000
    row[18] = 71800000
    row[19] = "Full nội thất"
    row[20] = "Miễn phí QLVH"
    row[21] = "View biển hồ"
    row[22] = "CSBH-Q4"
    row[23] = "TCB"
    row[24] = ""
    row[25] = ""
    row[26] = "Căn đẹp"
    row[27] = "Đang lock"
    row[28] = "Quỹ chung"
    row[29] = "Quỹ chung"
    row[30] = "04/11/2026"
    row[31] = "Còn 30 ngày"

    rec = map_merged_row_to_db_record(
        row=row,
        project_key="MAS CAO TẦNG",
        is_low_rise=False,
        sub_tab="MGC",
    )

    assert rec is not None
    assert rec["product_code"] == "MGC-S1-12A05"
    assert rec["project_id"] == "masteri-grand-coast"
    assert rec["product_type"] == "cao_tang"
    assert rec["building_name"] == "S1"
    assert rec["number_of_floor"] == "12A"
    assert rec["floor_sort_order"] == 12
    assert rec["apartment_axis_code"] == "05"
    assert rec["carpet_area"] == Decimal("68.5")
    assert rec["built_up_area"] == Decimal("74.2")
    assert rec["number_of_room"] == "2"
    assert rec["number_of_wc"] == "2.5"
    assert rec["state_line"] == "locked"
    assert rec["state_line_name"] == "Đang lock"
    assert rec["fund_groups_sell_name"] == "Quỹ chung"
    assert rec["fund_type"] == "Quỹ CĐT"
    assert rec["partner"] is None
    assert rec["policy_code"] == "CSBH-Q4"
    assert rec["policy_date"] is None
    assert rec["metadata"]["filterKeys"]["typeKey"] == "2pn+"


def test_has_inventory_changed():
    row1 = [1, "Đảo Ngọc", "HC4-02", "Thô", "LK"] + [""] * 34
    row1[10] = "14,948,829,217"
    row1[31] = "Còn hàng"
    existing_pool = {
        "HC4-02": {
            "unit_key": "HC4-02",
            "row_values": list(row1),
        }
    }
    merged_same = [list(row1)]
    merged_same[0][10] = 14948829217  # Numeric vs formatted string with commas
    assert has_inventory_changed(existing_pool, merged_same, is_low_rise=True) is False

    merged_diff = [list(row1)]
    merged_diff[0][31] = "Đã bán"
    assert has_inventory_changed(existing_pool, merged_diff, is_low_rise=True) is True


def test_bulk_upsert_products_to_db_executes_chunks_and_notify():
    row = [""] * len(LOW_RISE_HEADERS)
    row[0] = 1
    row[1] = "Đảo Ngọc"
    row[2] = "HC4-02"
    row[10] = 14948829217
    row[31] = "Còn hàng"
    row[32] = "Quỹ độc quyền"
    row[36] = "VHS"

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    with patch("src.db_writer.get_db_connection", return_value=mock_conn), patch(
        "src.db_writer.execute_values"
    ) as mock_exec_values:
        result = bulk_upsert_products_to_db(
            rows=[row],
            project_key="làng vân",
            is_low_rise=True,
            chunk_size=200,
        )

    assert result["upserted"] == 1
    assert result["project_id"] == "vinhomes-hai-van-bay"
    assert mock_exec_values.call_count == 1
    assert mock_conn.commit.called
