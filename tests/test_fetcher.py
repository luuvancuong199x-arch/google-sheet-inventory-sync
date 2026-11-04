import pytest
from src.fetcher import (
    map_columns_from_headers,
    detect_header_row,
    classify_rgb_color,
    classify_hex_color,
    parse_agency_grid_data
)

def test_map_columns_from_headers():
    headers = ["STT", "Phân khu", "Mã căn", "Loại hình", "DT đất", "DTXD", "Giá full", "Ảnh chỉ căn"]
    col_map = map_columns_from_headers(headers)
    assert col_map["stt"] == 0
    assert col_map["zone"] == 1
    assert col_map["unit_code"] == 2
    assert col_map["unit_type"] == 3
    assert col_map["land_area"] == 4
    assert col_map["build_area"] == 5
    assert col_map["gia_full"] == 6
    assert col_map["chi_can"] == 7

def test_detect_header_row():
    rows = [
        ["BẢNG HÀNG DỰ ÁN 2026", "", "", ""],
        ["Cập nhật ngày 01/01/2026", "", "", ""],
        ["STT", "Phân khu", "Mã căn", "DT đất", "Giá bán"]
    ]
    detected = detect_header_row(rows)
    assert detected is not None
    header_idx, col_map = detected
    assert header_idx == 2
    assert col_map["unit_code"] == 2
    assert col_map["land_area"] == 3

def test_color_classifier():
    assert classify_hex_color("FFFF0000") == "red"
    assert classify_hex_color("#EA4335") == "red"
    assert classify_hex_color("FFFFFF00") == "yellow"
    assert classify_hex_color("#FFF2CC") == "yellow"
    assert classify_hex_color("FFFFFFFF") == "neutral"
    assert classify_hex_color(None) == "neutral"

def test_red_yellow_hidden_status_resolution():
    headers = ["STT", "Phân khu", "Mã căn", "DT đất", "Giá bán", "Trạng thái"]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        # Row 1: Red background -> Đã bán
        [{"formattedValue": "1", "color_type": "red"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-01"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": ""}],
        # Row 2: Yellow background nhưng không có chữ lock -> Mặc định 'Còn hàng' (không tự nhận lock theo màu vàng nữa)
        [{"formattedValue": "2", "color_type": "yellow"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-02"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": ""}],
        # Row 3: Sold text -> Đã bán
        [{"formattedValue": "3"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-03"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": "Đã bán"}],
        # Row 4: Normal visible có giá -> Còn hàng
        [{"formattedValue": "4"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-04"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": ""}],
        # Row 5: Nguồn ghi rõ lock -> Đang lock
        [{"formattedValue": "5"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-05"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": "Đang lock"}],
        # Row 6: Dòng bị ẩn -> Đã bán
        [{"formattedValue": "6"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-06"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": ""}],
    ]
    # Row 6 (index 6 trong grid_rows) bị ẩn
    row_hidden_flags = [False, False, False, False, False, False, True]

    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="TEST_AGENCY",
        project_key="test_project",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="03/11/2026",
        row_hidden_flags=row_hidden_flags
    )

    by_key = {u["unit_key"]: u["status"] for u in parsed}
    assert by_key["LK-01"] == "Đã bán"
    assert by_key["LK-02"] == "Còn hàng"  # Vàng không còn là lock
    assert by_key["LK-03"] == "Đã bán"
    assert by_key["LK-04"] == "Còn hàng"
    assert by_key["LK-05"] == "Đang lock"
    assert by_key["LK-06"] == "Đã bán"  # Ẩn dòng là Đã bán

def test_no_price_becomes_sold():
    headers = ["STT", "Phân khu", "Mã căn", "DT đất", "Giá bán"]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        # Có DT đất nhưng không có Giá bán -> Tự động 'Đã bán'
        [{"formattedValue": "1"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-05"}, {"formattedValue": "100"}, {"formattedValue": ""}],
        # Có cả DT đất và Giá bán -> 'Còn hàng'
        [{"formattedValue": "2"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-06"}, {"formattedValue": "100"}, {"formattedValue": "4500000000"}],
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="TEST_AGENCY",
        project_key="test_project",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="03/11/2026"
    )
    by_key = {u["unit_key"]: u["status"] for u in parsed}
    assert by_key["LK-05"] == "Đã bán"
    assert by_key["LK-06"] == "Còn hàng"

def test_agency_without_exclusive_column_defaults_to_exclusive():
    headers = ["STT", "Phân khu", "Mã căn", "DT đất", "Giá bán"]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [{"formattedValue": "1"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-01"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}],
        [{"formattedValue": "2"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-02"}, {"formattedValue": "120"}, {"formattedValue": "6000000000"}],
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="BHS PARTNERS",
        project_key="test_project",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="04/11/2026",
        sheet_title="Sheet 1"
    )
    assert len(parsed) == 2
    assert parsed[0]["is_exclusive"] is True
    assert parsed[0]["row_values"][32] == "Độc quyền"
    assert parsed[1]["is_exclusive"] is True
    assert parsed[1]["row_values"][32] == "Độc quyền"

def test_agency_with_dedicated_exclusive_column_classifies_row_by_row():
    headers = ["STT", "Phân khu", "Mã căn", "DT đất", "Giá bán", "Độc quyền"]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [{"formattedValue": "1"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-01"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": "ĐQ"}],
        [{"formattedValue": "2"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-02"}, {"formattedValue": "120"}, {"formattedValue": "6000000000"}, {"formattedValue": ""}],
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="NSL",
        project_key="test_project",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="04/11/2026",
        sheet_title="Sheet 1"
    )
    assert len(parsed) == 2
    assert parsed[0]["is_exclusive"] is True
    assert parsed[0]["row_values"][32] == "Độc quyền"
    assert parsed[1]["is_exclusive"] is False
    assert parsed[1]["row_values"][32] == "Quỹ chung"

def test_general_pool_is_always_general_fund():
    headers = ["STT", "Phân khu", "Mã căn", "DT đất", "Giá bán"]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [{"formattedValue": "1"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-01"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}],
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="Quỹ chung",
        project_key="test_project",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="04/11/2026",
        sheet_title="Sheet 1",
        is_general_pool=True
    )
    assert len(parsed) == 1
    assert parsed[0]["is_exclusive"] is False
    assert parsed[0]["row_values"][32] == "Quỹ chung"

def test_gia_full_and_chua_vat_column_mapping():
    headers = ['Mã căn', 'Loại hình', 'DT đất', 'DTXD', 'Giá chưa gồm VAT', 'VAT', 'KPBT', 'Giá gồm VAT và KPBT', 'Check bán']
    col_map = map_columns_from_headers(headers)
    assert col_map["gia_chua_vat"] == 4
    assert col_map["gia_full"] == 7  # Must match 'Giá gồm VAT và KPBT', NOT 'Giá chưa gồm VAT'!
    assert col_map["status"] == 8    # Must match 'Check bán'

def test_price_reconciliation_when_identical():
    # If gia_full mistakenly equals gia_chua_vat but vat_tong > 0, gia_full should reconcile
    headers = ['Mã căn', 'TCBG', 'Loại hình', 'DT đất', 'DTXD', 'Giá chưa gồm VAT', 'VAT', 'KPBT', 'Giá gồm VAT']
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [
            {"formattedValue": "HC5-06"},
            {"formattedValue": "Hoàn thiện"},
            {"formattedValue": "LK"},
            {"formattedValue": "70"},
            {"formattedValue": "207"},
            {"formattedValue": "11.832.171.209"},
            {"formattedValue": "1.075.215.444"},
            {"formattedValue": "57.586.996"},
            {"formattedValue": "11.832.171.209"}  # identical to gia_chua_vat in source
        ]
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="Hợp Long",
        project_key="test_project",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="04/11/2026"
    )
    assert len(parsed) == 1
    # gia_full should be reconciled to 11.832.171.209 + 1.075.215.444 + 57.586.996 = 12.964.973.649
    assert parsed[0]["row_values"][7] == 11_832_171_209  # Giá chưa gồm VAT
    assert parsed[0]["row_values"][10] == 12_964_973_649 # Giá gồm VAT và KPBT đã đối soát!

def test_shifted_table_detection():
    # When TCBG is omitted and column is shifted (TCBG has 'SL', Loại căn has '140', Hướng has '11.833')
    headers = ['STT', 'Tên khu', 'Mã Căn', 'TCBG', 'Loại căn', 'DT đất', 'DTXD', 'Hướng cửa', 'Mô tả', 'Giá gồm VAT và KPBT', 'Check bán']
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [
            {"formattedValue": "1"},
            {"formattedValue": "Bạch Vân"},
            {"formattedValue": "BV1-25"},
            {"formattedValue": "SL"},         # Shifted!
            {"formattedValue": "140"},        # Shifted area!
            {"formattedValue": "302,1"},      # Shifted build area!
            {"formattedValue": "12.732,0"},   # Price
            {"formattedValue": "11.833"},     # Price in direction column!
            {"formattedValue": "12.732"},
            {"formattedValue": "11.833"},
            {"formattedValue": "Thu hồi"}     # Status Thu hồi
        ]
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="ELITE CAPITAL",
        project_key="test_project",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="04/11/2026"
    )
    assert len(parsed) == 1
    unit = parsed[0]
    assert unit["status"] == "Đã bán"  # 'Thu hồi' -> Đã bán
    assert unit["row_values"][4] == "BTSL"  # Grounded unit type for SL is BTSL
    assert unit["row_values"][5] == 140.0 # Land area correctly detected as 140
    assert unit["row_values"][20] == ""   # Direction cleaned (no 11.833)!

def test_tab_exclusive_with_contract_fund_column():
    headers = ['Mã căn', 'TCBG', 'Loại căn', 'DT đất', 'DTXD', 'Giá chưa gồm VAT', 'VAT', 'KPBT', 'Giá gồm VAT và KPBT', 'Quỹ']
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [
            {"formattedValue": "ĐLHV-09"},
            {"formattedValue": "Thô"},
            {"formattedValue": "LK"},
            {"formattedValue": "80"},
            {"formattedValue": "244,9"},
            {"formattedValue": "8.038.027.068"},
            {"formattedValue": "680.372.219"},
            {"formattedValue": "37.693.082"},
            {"formattedValue": "8.756.092.369"},
            {"formattedValue": "HDMB"}  # Contract fund, not general pool!
        ]
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="Đất xanh MT",
        project_key="làng vân",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="04/11/2026",
        sheet_title="Giỏ Độc quyền"
    )
    assert len(parsed) == 1
    assert parsed[0]["is_exclusive"] is True
    assert parsed[0]["row_values"][32] == "Độc quyền"



