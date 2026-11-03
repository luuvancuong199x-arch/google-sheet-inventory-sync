import pytest
from src.fetcher import map_columns_from_headers, detect_header_row

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
