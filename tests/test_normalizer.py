import pytest
from src.normalizer import (
    sanitize_unit_code,
    normalize_high_rise_unit_floor_axis,
    sanitize_single_area,
    normalize_price_to_vnd,
    normalize_numeric_or_null,
    repair_drive_url,
    resolve_unit_media_links,
    normalize_csbh_date,
    normalize_low_rise_type,
    normalize_high_rise_type,
    normalize_direction,
    realign_legacy_row
)

def test_sanitize_unit_code():
    assert sanitize_unit_code("✨LK-05 (Góc)") == "LK-05"
    assert sanitize_unit_code("BT-01: Căn đẹp") == "BT-01"
    assert sanitize_unit_code("  s6.0619.06*  ") == "S6.0619.06"
    assert sanitize_unit_code("SH-10 Xẻ khe") == "SH-10"

def test_normalize_high_rise_unit_floor_axis_grounded_rules():
    # Quy tắc: 05 là 05, 05A là 05A; 08 là 08, 08A là 08A; 12 là 12, 12A là 12A; 15 là 15, 15A là 15A
    # Tuyệt đối không tự phỏng đoán hay hoán đổi số. 04 giữ 04, 07 giữ 07, 13 giữ 13, 14 giữ 14.
    res1 = normalize_high_rise_unit_floor_axis("M1-10-04", raw_tower="", raw_floor="10", raw_axis="04")
    assert res1["axis"] == "04"
    assert res1["tower"] == "M1"
    assert res1["floor"] == "10"
    assert res1["unit_code"] == "M1-10-04"

    res2 = normalize_high_rise_unit_floor_axis("A1-04-07", raw_tower="", raw_floor="4", raw_axis="7")
    assert res2["floor"] == "04"
    assert res2["axis"] == "07"
    assert res2["unit_code"] == "A1-04-07"

    res3 = normalize_high_rise_unit_floor_axis("BS11-14-13", raw_tower="", raw_floor="14", raw_axis="13")
    assert res3["floor"] == "14"
    assert res3["axis"] == "13"
    assert res3["unit_code"] == "BS11-14-13"

    # Bảo tồn 05 và 05A riêng biệt
    res_05 = normalize_high_rise_unit_floor_axis("M1-10-05", raw_tower="", raw_floor="10", raw_axis="05")
    assert res_05["axis"] == "05"
    res_05a = normalize_high_rise_unit_floor_axis("M1-10-05A", raw_tower="", raw_floor="10", raw_axis="5A")
    assert res_05a["axis"] == "05A"

    # Bảo tồn 08 và 08A riêng biệt
    res_08 = normalize_high_rise_unit_floor_axis("M1-10-08", raw_tower="", raw_floor="10", raw_axis="8")
    assert res_08["axis"] == "08"
    res_08a = normalize_high_rise_unit_floor_axis("M1-10-08A", raw_tower="", raw_floor="10", raw_axis="8A")
    assert res_08a["axis"] == "08A"

    # Bảo tồn 12 và 12A riêng biệt
    res_12 = normalize_high_rise_unit_floor_axis("M1-10-12", raw_tower="", raw_floor="10", raw_axis="12")
    assert res_12["axis"] == "12"
    res_12a = normalize_high_rise_unit_floor_axis("M1-10-12A", raw_tower="", raw_floor="10", raw_axis="12A")
    assert res_12a["axis"] == "12A"

def test_normalize_high_rise_hsg_grounded_rules():
    # Dự án HSG: Chuẩn hóa theo bảng hàng độc quyền (HH-A-[Tầng]-[Trục] và HH-B-[Tầng]-[Trục])
    # Tên tòa chuẩn hóa L1 và L2 để khớp 100% với 3D Building block
    hsg1 = normalize_high_rise_unit_floor_axis("HHA-18-05A", raw_tower="L1", project_key="HSG")
    assert hsg1["unit_code"] == "HH-A-18-05A"
    assert hsg1["tower"] == "L1"
    assert hsg1["floor"] == "18"
    assert hsg1["axis"] == "05A"

    hsg2 = normalize_high_rise_unit_floor_axis("HHA2819", raw_tower="", project_key="HSG")
    assert hsg2["unit_code"] == "HH-A-28-19"
    assert hsg2["tower"] == "L1"
    assert hsg2["floor"] == "28"
    assert hsg2["axis"] == "19"

    hsg3 = normalize_high_rise_unit_floor_axis("HHB1021", raw_tower="", project_key="HSG")
    assert hsg3["unit_code"] == "HH-B-10-21"
    assert hsg3["tower"] == "L2"
    assert hsg3["floor"] == "10"
    assert hsg3["axis"] == "21"

    hsg4 = normalize_high_rise_unit_floor_axis("A-37-05A", raw_tower="A", project_key="HSG")
    assert hsg4["unit_code"] == "HH-A-37-05A"
    assert hsg4["tower"] == "L1"

    hsg5 = normalize_high_rise_unit_floor_axis("B-22-12A", raw_tower="B", project_key="HSG")
    assert hsg5["unit_code"] == "HH-B-22-12A"
    assert hsg5["tower"] == "L2"

    hsg6 = normalize_high_rise_unit_floor_axis("HH-A-31-05", raw_tower="HH-A", project_key="HSG")
    assert hsg6["axis"] == "05"  # 05 là 05, bảo tồn tuyệt đối giá trị gốc
    assert hsg6["unit_code"] == "HH-A-31-05"
    assert hsg6["tower"] == "L1"

    # Lọc bỏ các căn dự án khác bị lẫn trong sheet đại lý
    assert normalize_high_rise_unit_floor_axis("C5L1-18-18A", project_key="HSG") is None
    assert normalize_high_rise_unit_floor_axis("C1Z2-11-06", project_key="HSG") is None
    assert normalize_high_rise_unit_floor_axis("B1-06-15", project_key="HSG") is None

def test_wc_decimal_preservation():
    # Crucial bug fix: 2.5 WC must NOT become 25 WC!
    assert normalize_numeric_or_null("2.5", is_integer=False) == 2.5
    assert normalize_numeric_or_null("1,5", is_integer=False) == 1.5
    assert normalize_numeric_or_null(2, is_integer=True) == 2
    assert normalize_numeric_or_null("", is_integer=False) == ""

def test_normalize_price_to_vnd():
    # Millions vs Billions
    assert normalize_price_to_vnd(8.5, unit_hint="TOTAL") == 8_500_000_000
    assert normalize_price_to_vnd("8.5 tỷ", unit_hint="TOTAL") == 8_500_000_000
    assert normalize_price_to_vnd("850 triệu", unit_hint="TOTAL") == 850_000_000
    assert normalize_price_to_vnd("1.2 tỷ", unit_hint="TOTAL") == 1_200_000_000
    # Full price in VND
    assert normalize_price_to_vnd(9_405_703_811, unit_hint="TOTAL") == 9_405_703_811

def test_repair_drive_url():
    assert repair_drive_url("https://drivegooglecom/drive/folders/123") == "https://drive.google.com/drive/folders/123"
    assert repair_drive_url("https://docsgooglecom/spreadsheets/d/456") == "https://docs.google.com/spreadsheets/d/456"

def test_resolve_unit_media_links_preserves_folder():
    # Crucial bug fix: Drive folder must NOT be dropped!
    folder_url = "https://drive.google.com/drive/folders/1abcDEFghijKLMN"
    res = resolve_unit_media_links(chican_urls=[folder_url], ptg_urls=[])
    assert res["anh_chi_can"] == folder_url
    assert res["anh_ptg"] == ""
    assert res["anh_chi_can_ptg"] == folder_url

def test_normalize_csbh_date():
    from datetime import datetime, date
    # Valid date
    assert normalize_csbh_date("23/12/2025.")["csbh_date"] == "23/12/2025"
    assert normalize_csbh_date("04/05", default_year=2026)["csbh_date"] == "04/05/2026"
    
    # Datetime and ISO format
    assert normalize_csbh_date(datetime(2026, 11, 1, 0, 0))["csbh_date"] == "01/11/2026"
    assert normalize_csbh_date("2026-11-01 00:00:00")["csbh_date"] == "01/11/2026"
    assert normalize_csbh_date(date(2026, 11, 1))["csbh_date"] == "01/11/2026"

    # Invalid date (31/02) must be rejected!
    res_invalid = normalize_csbh_date("31/02/2026")
    assert res_invalid["csbh_date"] == ""  # Rejected, not a valid date!

def test_non_inventory_tab_regex_bg():
    import re
    from src.config import NON_INVENTORY_TAB_REGEX
    rx = re.compile(NON_INVENTORY_TAB_REGEX, re.IGNORECASE)
    assert rx.search("Ngày BG dự kiến Vịnh Tiên") is not None
    assert rx.search("Hạn BG") is not None
    assert rx.search("Lịch BG 2026") is not None
    assert rx.search("Tiến độ thi công") is not None
    assert rx.search("Bảng hàng") is None
    assert rx.search("Bảng hàng Vịnh Tiên") is None

def test_normalize_types():
    assert normalize_low_rise_type("Liền kề", "") == "LK"
    assert normalize_low_rise_type("Shophouse", "") == "SH"
    assert normalize_low_rise_type("Biệt thự song lập", "") == "BTSL"
    assert normalize_high_rise_type("2BR+1") == "2PN+"
    assert normalize_high_rise_type("Studio") == "STUDIO"

def test_infer_grounded_zone():
    from src.normalizer import infer_grounded_zone
    # VX -> Vịnh Xanh (yêu cầu người dùng)
    assert infer_grounded_zone("VX2-46", "OCP2-3") == "Vịnh Xanh"
    assert infer_grounded_zone("VX4-157", "OCP2-3", existing_zone="Vịnh Xuân 4") == "Vịnh Xanh 4"
    assert infer_grounded_zone("KĐ7-117", "OCP2-3") == "Kinh Đô Ánh Sáng"
    assert infer_grounded_zone("BM3-08", "HLX") == "Bình Minh"
    assert infer_grounded_zone("P1.1101", "MIK OCP") == "The Pavilion"
    assert infer_grounded_zone("C5L2-03-09", "MAS CAO TẦNG", sub_tab="MGC") == "Masteri Grand Coast"
    # Không sáng tạo giá trị mới khi không có căn cứ
    assert infer_grounded_zone("XYZ-999", "OCP2-3") == ""

def test_infer_grounded_low_rise_type():
    from src.normalizer import infer_grounded_low_rise_type
    assert infer_grounded_low_rise_type("LK2-05", "") == "LK"
    assert infer_grounded_low_rise_type("SH-10", "") == "SH"
    assert infer_grounded_low_rise_type("BTSL-01", "") == "BTSL"
    assert infer_grounded_low_rise_type("BTĐL-03", "") == "BTĐL"
    assert infer_grounded_low_rise_type("UNKNOWN-01", "") == ""

def test_compute_expiry_warning():
    from datetime import date, timedelta
    from src.normalizer import compute_expiry_warning

    today = date(2026, 11, 3)

    # 1. Cấp hôm nay (0 ngày) -> Còn 30 ngày
    res_today = compute_expiry_warning("03/11/2026", today_date=today)
    assert res_today["status"] == "NORMAL"
    assert res_today["days_remaining"] == 30
    assert res_today["display"] == "Còn 30 ngày"

    # 2. Cấp cách đây 10 ngày -> Còn 20 ngày
    d10 = today - timedelta(days=10)
    res_10 = compute_expiry_warning(d10.strftime("%d/%m/%Y"), today_date=today)
    assert res_10["status"] == "NORMAL"
    assert res_10["days_remaining"] == 20
    assert res_10["display"] == "Còn 20 ngày"

    # 3. Mốc 29 ngày -> ⚠️ Sắp hết hạn (Còn 1 ngày)
    d29 = today - timedelta(days=29)
    res_29 = compute_expiry_warning(d29.strftime("%d/%m/%Y"), today_date=today)
    assert res_29["status"] == "EXPIRING_SOON"
    assert res_29["days_remaining"] == 1
    assert res_29["days_elapsed"] == 29
    assert res_29["display"] == "⚠️ Sắp hết hạn (Còn 1 ngày)"

    # 4. Mốc 30 ngày (đúng ngày hết hạn) -> ⛔ Đã hết hạn (Hôm nay)
    d30 = today - timedelta(days=30)
    res_30 = compute_expiry_warning(d30.strftime("%d/%m/%Y"), today_date=today)
    assert res_30["status"] == "EXPIRED"
    assert res_30["days_remaining"] == 0
    assert res_30["days_elapsed"] == 30
    assert res_30["display"] == "⛔ Đã hết hạn (Hôm nay)"

    # 5. Mốc quá hạn 5 ngày (35 ngày) -> ⛔ Đã hết hạn (Quá 5 ngày)
    d35 = today - timedelta(days=35)
    res_35 = compute_expiry_warning(d35.strftime("%d/%m/%Y"), today_date=today)
    assert res_35["status"] == "EXPIRED"
    assert res_35["days_remaining"] == -5
    assert res_35["days_elapsed"] == 35
    assert res_35["display"] == "⛔ Đã hết hạn (Quá 5 ngày)"

    # 6. Ngày rỗng hoặc không hợp lệ -> UNKNOWN
    assert compute_expiry_warning("")["status"] == "UNKNOWN"
    assert compute_expiry_warning("invalid-date")["status"] == "UNKNOWN"

def test_normalize_direction():
    assert normalize_direction("ĐB") == "ĐB"
    assert normalize_direction("Đông Bắc") == "ĐB"
    assert normalize_direction("Hướng Đông") == "Đông"
    assert normalize_direction("TÂY NAM") == "TN"
    assert normalize_direction("TN-TB") == "TN-TB"
    assert normalize_direction("ĐB/ĐN") == "ĐB-ĐN"
    # Rejects shifted numbers/prices
    assert normalize_direction("11.833") == ""
    assert normalize_direction("9.920") == ""
    assert normalize_direction("32.004") == ""
    assert normalize_direction("7.552") == ""
    assert normalize_direction("") == ""
    assert normalize_direction("-") == ""

def test_normalize_price_rejects_dates_and_extreme_m2():
    # Dates should return empty
    assert normalize_price_to_vnd("2028-10-01 00:00:00", unit_hint="M2") == ""
    assert normalize_price_to_vnd("01/10/2028", unit_hint="M2") == ""
    # M2 extreme unit price rejection (> 1 billion or < 1 million)
    assert normalize_price_to_vnd(20_281_001_000_000, unit_hint="M2") == ""
    assert normalize_price_to_vnd("20.281.001.000.000", unit_hint="M2") == ""
    assert normalize_price_to_vnd(0.5, unit_hint="M2") == ""  # 0.5 * 1e6 = 500_000 (< 1 million)
    # Valid M2 prices
    assert normalize_price_to_vnd(85_000_000, unit_hint="M2") == 85_000_000
    assert normalize_price_to_vnd("75.5 triệu/m2", unit_hint="M2") == 75_500_000

def test_realign_legacy_row():
    # 1. Cấu trúc mới Phương án 2 (Trạng thái -> Nhóm quỹ -> Đại lý -> Ngày cấp -> Hạn cấp -> 3 Ảnh ở cuối)
    canonical_pa2 = [''] * 30 + ['Ghi chu', 'Còn hàng', 'Quỹ chéo', 'BHOMES', '05/11/2026', 'Còn 29 ngày', 'https://img1', '', 'https://img3']
    res_canon = realign_legacy_row(canonical_pa2, is_low_rise=True)
    assert res_canon[31] == 'Còn hàng'
    assert res_canon[32] == 'Quỹ chéo'
    assert res_canon[33] == 'BHOMES'
    assert res_canon[34] == '05/11/2026'
    assert res_canon[35] == 'Còn 29 ngày'
    assert res_canon[36] == 'https://img1'
    assert res_canon[38] == 'https://img3'

    # 2. Dòng từ định dạng trước (Ảnh ở 33-35, Đại lý ở 36, Ngày ở 37, Hạn ở 38)
    prev_layout_row = [''] * 30 + ['Ghi chu', 'Còn hàng', 'Quỹ chéo', 'https://img1', '', 'https://img3', 'BHOMES', '05/11/2026', 'Còn 29 ngày']
    res_prev = realign_legacy_row(prev_layout_row, is_low_rise=True)
    assert res_prev[31] == 'Còn hàng'
    assert res_prev[32] == 'Quỹ chéo'
    assert res_prev[33] == 'BHOMES'
    assert res_prev[34] == '05/11/2026'
    assert res_prev[35] == 'Còn 29 ngày'
    assert res_prev[36] == 'https://img1'
    assert res_prev[38] == 'https://img3'

    # 3. Dòng legacy sâu (col 34 là Trạng thái): QCBEST cũ
    legacy_qc = [''] * 30 + ['', 'https://drive/folder', '', 'QCBEST', 'Còn hàng', 'Quỹ chung', '6/10/2026', '', '']
    res_qc = realign_legacy_row(legacy_qc, is_low_rise=True)
    assert res_qc[31] == 'Còn hàng'
    assert res_qc[32] == 'Quỹ chung'
    assert res_qc[33] == 'QCBEST'
    assert res_qc[34] == '6/10/2026'
    assert res_qc[36] == 'https://drive/folder'

    # 4. Dòng legacy sâu: ATD HOMES cũ
    legacy_atd = [''] * 30 + ['', '', 'https://drive/img2', 'https://drive/img3', 'Còn hàng', 'Quỹ chéo', 'ATD HOMES', '04/11/2026', 'Còn 28 ngày']
    res_atd = realign_legacy_row(legacy_atd, is_low_rise=True)
    assert res_atd[31] == 'Còn hàng'
    assert res_atd[32] == 'Quỹ chéo'
    assert res_atd[33] == 'ATD HOMES'
    assert res_atd[34] == '04/11/2026'
    assert res_atd[35] == 'Còn 28 ngày'
    assert res_atd[36] == ''
    assert res_atd[37] == 'https://drive/img2'
    assert res_atd[38] == 'https://drive/img3'

    # 5. Dòng từ định dạng trước không có link ảnh (col 33-35 trống, Đại lý ở 36, Ngày ở 37)
    prev_no_img = [''] * 30 + ['TTĐC', 'Còn hàng', 'Quỹ độc quyền', '', '', '', 'VHUB', '46331', '']
    res_no_img = realign_legacy_row(prev_no_img, is_low_rise=True)
    assert res_no_img[31] == 'Còn hàng'
    assert res_no_img[32] == 'Quỹ độc quyền'
    assert res_no_img[33] == 'VHUB'
    assert res_no_img[34] == '05/11/2026'
    assert res_no_img[36] == ''
    assert res_no_img[37] == ''

