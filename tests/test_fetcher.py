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
        # Row 1: Red background nhưng không có chữ bán -> 'Còn hàng' (không tự nhận Đã bán theo màu đỏ nữa)
        [{"formattedValue": "1", "color_type": "red"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-01"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": ""}],
        # Row 2: Yellow background nhưng không có chữ lock -> Mặc định 'Còn hàng' (không tự nhận lock theo màu vàng nữa)
        [{"formattedValue": "2", "color_type": "yellow"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-02"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": ""}],
        # Row 3: Sold text -> Đã bán
        [{"formattedValue": "3"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-03"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": "Đã bán"}],
        # Row 4: Normal visible có giá -> Còn hàng
        [{"formattedValue": "4"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-04"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": ""}],
        # Row 5: Nguồn ghi rõ lock -> Đang lock
        [{"formattedValue": "5"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-05"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}, {"formattedValue": "Đang lock"}],
        # Row 6: Dòng bị ẩn nhưng không có chữ bán -> 'Còn hàng' (tránh lỗi khi người dùng bật Filter View)
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
    assert by_key["LK-01"] == "Còn hàng"  # Màu đỏ không chốt Đã bán
    assert by_key["LK-02"] == "Còn hàng"  # Vàng không còn là lock
    assert by_key["LK-03"] == "Đã bán"    # Văn bản rõ ràng Đã bán
    assert by_key["LK-04"] == "Còn hàng"
    assert by_key["LK-05"] == "Đang lock" # Văn bản rõ ràng Đang lock
    assert by_key["LK-06"] == "Còn hàng"  # Ẩn dòng không chốt Đã bán

def test_no_price_keeps_available():
    headers = ["STT", "Phân khu", "Mã căn", "DT đất", "Giá bán"]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        # Có DT đất nhưng chưa có Giá bán -> Không ép Đã bán, giữ 'Còn hàng'
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
    assert by_key["LK-05"] == "Còn hàng"
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
    assert parsed[0]["row_values"][32] == "Quỹ chéo"
    assert parsed[1]["is_exclusive"] is True
    assert parsed[1]["row_values"][32] == "Quỹ chéo"

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
    assert parsed[0]["row_values"][32] == "Quỹ chéo"
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
    assert parsed[0]["row_values"][32] == "Quỹ chéo"

def test_vhub_agency_sets_fund_group_quy_doc_quyen():
    headers = ["STT", "Phân khu", "Mã căn", "DT đất", "Giá bán"]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [{"formattedValue": "1"}, {"formattedValue": "Khu A"}, {"formattedValue": "LK-01"}, {"formattedValue": "100"}, {"formattedValue": "5000000000"}],
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="Vhub",
        project_key="test_project",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="04/11/2026",
        sheet_title="Sheet 1"
    )
    assert len(parsed) == 1
    assert parsed[0]["is_exclusive"] is True
    assert parsed[0]["row_values"][32] == "Quỹ độc quyền"

def test_expanded_header_mappings():
    from src.fetcher import map_columns_from_headers
    headers = ["STT", "Mã sản phẩm", "Loại CH", "DTTT", "Giá TTTĐ (Tạm tính)"]
    col_map = map_columns_from_headers(headers)
    assert col_map["unit_code"] == 1
    assert col_map["unit_type"] == 2
    assert col_map["net_area"] == 3
    assert col_map["gia_tttd"] == 4

def test_heuristic_recovery_when_headers_unmapped():
    # Trường hợp tiêu đề bị gộp ô, khuyết tên cột diện tích và giá
    headers = ["STT", "Mã căn", "", "", ""]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [{"formattedValue": "1"}, {"formattedValue": "P1.1001"}, {"formattedValue": "47.5"}, {"formattedValue": "3.500.000.000"}, {"formattedValue": ""}],
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="AURA",
        project_key="MIK OCP",
        is_low_rise=False,
        existing_pool_keys=set(),
        today_str="05/11/2026",
        sheet_title="Sheet 1"
    )
    assert len(parsed) == 1
    assert parsed[0]["unit_key"] == "P1.1001"
    assert parsed[0]["row_values"][8] == 47.5
    assert parsed[0]["row_values"][14] == 3500000000
    assert parsed[0]["status"] == "Còn hàng"

def test_nfd_unicode_header_mapping_and_parsing():
    # NFD unicode headers as found in NOVASKY, QUEENLAND, MDL
    headers = [
        'BA\u0309NG HA\u0300NG TOA\u0300',
        'MA\u0303 C\u0102N',
        'DO\u0300NG C\u0102N',
        'H\u01af\u01a0\u0301NG',
        'DI\u00ca\u0323N TI\u0301CH',
        'GIA\u0301 TI\u00ca\u0301N \u0110O\u0302\u0323'
    ]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [
            {"formattedValue": "L2"},
            {"formattedValue": "HH-B-10-15"},
            {"formattedValue": "2BR+1MR"},
            {"formattedValue": "TB-TN"},
            {"formattedValue": "101,7"},
            {"formattedValue": "16.820.083.065"}
        ]
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="NOVASKY",
        project_key="LUMIÈRE Hanoi Seasons Garden",
        is_low_rise=False,
        existing_pool_keys=set(),
        today_str="05/11/2026"
    )
    assert len(parsed) == 1
    assert parsed[0]["unit_key"] == "HH-B-10-15"
    assert parsed[0]["row_values"][8] == 101.7
    assert parsed[0]["row_values"][14] == 16_820_083_065
    assert parsed[0]["status"] == "Còn hàng"

def test_ten_can_and_ma_chuan_mapping():
    # Headers with 'Tên Căn', 'Mã chuẩn', 'Mã căn mới/PTG'
    headers_hsg = ['Tòa', 'Tên Căn', 'DT Thông thủy', 'Giá tiến độ chuẩn']
    col_map_hsg = map_columns_from_headers(headers_hsg)
    assert col_map_hsg["unit_code"] == 1

    headers_hocmon = ['STT', 'Khu', 'Mã chuẩn', 'DT Đất', 'Giá full']
    col_map_hm = map_columns_from_headers(headers_hocmon)
    assert col_map_hm["unit_code"] == 2

    headers_cangio = ['STT', 'Mã căn cũ', 'Phân khu', 'Mã căn mới/PTG', 'DT đất', 'Giá full']
    col_map_cg = map_columns_from_headers(headers_cangio)
    assert col_map_cg["unit_code"] == 3  # Chooses Mã căn mới/PTG instead of Mã căn cũ!

def test_high_rise_numeric_unit_code_composition():
    # High-rise table where unit code is pure number but tower & floor exist
    headers = ['STT', 'Toà', 'Tầng', 'Mã căn', 'DT Thông thủy', 'Giá bán']
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [
            {"formattedValue": "1"},
            {"formattedValue": "M1"},
            {"formattedValue": "08A"},
            {"formattedValue": "02"},
            {"formattedValue": "31,68"},
            {"formattedValue": "2.209.052.131"}
        ]
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="Aura",
        project_key="MIK OCP",
        is_low_rise=False,
        existing_pool_keys=set(),
        today_str="05/11/2026"
    )
    assert len(parsed) == 1
    assert parsed[0]["unit_key"] == "M1-08A-02"
    assert parsed[0]["status"] == "Còn hàng"


def test_mgc_headers_don_gia_tts_and_gia_tdc_preserve_total_price():
    # Kiểm tra bảng hàng MGC có cả 'Đơn giá TTS', 'GIÁ CHƯA VAT VÀ KPBT', 'Giá Vay NH', 'Giá TĐC', 'Giá TTS'
    headers = [
        "STT", "TÒA", "Mã căn", "Loại căn", "Hướng", "View", "DT thông thủy",
        "Đơn giá TTS", "GIÁ CHƯA  VAT VÀ KPBT", "Giá Vay NH\n(tạm tính)",
        "Giá TĐC\n(tạm tính)", "Giá TTS\n(tạm tính)"
    ]
    col_map = map_columns_from_headers(headers)
    assert col_map["don_gia_m2"] == 7
    assert col_map["gia_chua_vat"] == 8
    assert col_map["gia_vay"] == 9
    assert col_map["gia_tttd"] == 10
    assert col_map["gia_tts"] == 11

    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [
            {"formattedValue": "1"},
            {"formattedValue": "L1"},
            {"formattedValue": "C5L1-21-02"},
            {"formattedValue": "2BR+"},
            {"formattedValue": ""},
            {"formattedValue": ""},
            {"formattedValue": "72,8"},
            {"formattedValue": "71.493.912"},
            {"formattedValue": "5.511.588.468"},
            {"formattedValue": "6.149.774.186"},
            {"formattedValue": "5.753.119.229"},
            {"formattedValue": "5.204.756.829"},
        ]
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="Vhub",
        project_key="MGC",
        is_low_rise=False,
        existing_pool_keys=set(),
        today_str="06/11/2026"
    )
    assert len(parsed) == 1
    row_vals = parsed[0]["row_values"]
    assert row_vals[13] == 5_511_588_468  # Giá chưa VAT
    assert row_vals[14] == 5_753_119_229  # Giá full fallback từ Giá TĐC (không bị ghi đè bởi Đơn giá TTS)
    assert row_vals[16] == 5_753_119_229  # Giá TTTĐ
    assert row_vals[17] == 5_204_756_829  # Giá TTS
    assert row_vals[18] == 71_493_912     # Đơn giá / m²


def test_strikethrough_triggers_sold_status():
    """Kiểm tra ô có thuộc tính gạch ngang (strikethrough) chuyển trạng thái thành Đã bán."""
    headers = ["STT", "Mã căn", "Giá full", "Trạng thái"]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [
            {"formattedValue": "1", "is_strikethrough": False},
            {"formattedValue": "LK-01", "is_strikethrough": True},
            {"formattedValue": "5.000.000.000", "is_strikethrough": False},
            {"formattedValue": "Còn hàng", "is_strikethrough": False},
        ]
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="Agency Test",
        project_key="HLX",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="07/11/2026"
    )
    assert len(parsed) == 1
    assert parsed[0]["status"] == "Đã bán"
    assert parsed[0]["row_values"][31] == "Đã bán"


def test_color_does_not_trigger_sold_status():
    """Kiểm tra màu chữ đỏ (is_fg_red) hoặc màu nền (color_type='red') KHÔNG làm đổi trạng thái thành Đã bán."""
    headers = ["STT", "Mã căn", "Giá full", "Trạng thái"]
    grid_rows = [
        [{"formattedValue": h} for h in headers],
        [
            {"formattedValue": "1", "is_fg_red": False},
            {"formattedValue": "LK-02", "is_fg_red": True, "color_type": "red"},
            {"formattedValue": "5.000.000.000", "color_type": "red"},
            {"formattedValue": "Còn hàng", "is_fg_red": False},
        ]
    ]
    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="Agency Test",
        project_key="HLX",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="07/11/2026"
    )
    assert len(parsed) == 1
    assert parsed[0]["status"] == "Còn hàng"
    assert parsed[0]["row_values"][31] == "Còn hàng"


def test_extended_sold_keywords():
    """Kiểm tra các từ khóa cọc, khóa căn, ráp căn, ttđc, hđmb đều chuyển Đã bán."""
    headers = ["STT", "Mã căn", "Giá full", "Trạng thái", "Ghi chú"]
    test_cases = [
        ("LK-01", "Còn hàng", "Khách đã cọc thiện chí"),
        ("LK-02", "Đang lock", "Khóa căn chờ ráp"),
        ("LK-03", "Còn hàng", "Đã ký TTĐC"),
        ("LK-04", "Còn hàng", "Vào cọc hôm nay"),
    ]
    grid_rows = [[{"formattedValue": h} for h in headers]]
    for idx, (code, st, note) in enumerate(test_cases, 1):
        grid_rows.append([
            {"formattedValue": str(idx)},
            {"formattedValue": code},
            {"formattedValue": "5.000.000.000"},
            {"formattedValue": st},
            {"formattedValue": note},
        ])

    parsed = parse_agency_grid_data(
        grid_rows,
        agency_name="Agency Test",
        project_key="HLX",
        is_low_rise=True,
        existing_pool_keys=set(),
        today_str="07/11/2026"
    )
    assert len(parsed) == 4
    for item in parsed:
        assert item["status"] == "Đã bán"
        assert item["row_values"][31] == "Đã bán"






