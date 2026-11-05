import pytest
from src.config import TARGET_PROJECTS, HIGH_RISE_HEADERS
from src.db_writer import resolve_vhub_project, map_merged_row_to_db_record
from src.master_reader import parse_master_sheet_rows


def test_target_projects_mas_separated():
    # Phải có 4 dự án riêng biệt
    assert "MGC" in TARGET_PROJECTS
    assert "MEL" in TARGET_PROJECTS
    assert "HSG" in TARGET_PROJECTS
    assert "LEP" in TARGET_PROJECTS

    assert TARGET_PROJECTS["MGC"]["name"] == "Masteri Grand Coast"
    assert TARGET_PROJECTS["MGC"]["sub_tab"] == "MGC"
    assert TARGET_PROJECTS["MGC"]["type"] == "HIGH_RISE"

    assert TARGET_PROJECTS["MEL"]["name"] == "Masteri Era Landmark"
    assert TARGET_PROJECTS["MEL"]["sub_tab"] == "MEL"

    assert TARGET_PROJECTS["HSG"]["name"] == "LUMIÈRE Hanoi Seasons Garden"
    assert TARGET_PROJECTS["HSG"]["sub_tab"] == "HSG"

    assert TARGET_PROJECTS["LEP"]["name"] == "LUMIÈRE Essence Peak"
    assert TARGET_PROJECTS["LEP"]["sub_tab"] == "LEP"


def test_lep_canonical_project_resolution():
    # Kiểm tra giải quyết định danh chuẩn cho LUMIÈRE Essence Peak
    assert resolve_vhub_project("LEP") == ("lumiere-essence-peak", "LUMIÈRE Essence Peak")
    assert resolve_vhub_project("lumiere-essence-peak") == ("lumiere-essence-peak", "LUMIÈRE Essence Peak")
    assert resolve_vhub_project("LUMIÈRE Essence Peak") == ("lumiere-essence-peak", "LUMIÈRE Essence Peak")
    assert resolve_vhub_project("MAS CAO TẦNG", sub_tab="LEP") == ("lumiere-essence-peak", "LUMIÈRE Essence Peak")


def test_mas_all_projects_resolution():
    assert resolve_vhub_project("MGC") == ("masteri-grand-coast", "MASTERI GRAND COAST")
    assert resolve_vhub_project("MEL") == ("masteri-era-landmark", "MASTERI ERA LANDMARK")
    assert resolve_vhub_project("HSG") == ("lumiere-hanoi-seasons-garden", "LUMIÈRE Hanoi Seasons Garden")
    assert resolve_vhub_project("LEP") == ("lumiere-essence-peak", "LUMIÈRE Essence Peak")


def test_map_lep_high_rise_row():
    row = [""] * len(HIGH_RISE_HEADERS)
    row[0] = 1
    row[1] = "P5.3X11"  # Mã căn
    row[2] = "Lumière Peak"  # Phân khu
    row[3] = "2PN"  # Loại hình
    row[4] = "Đông Nam"  # Hướng
    row[5] = "L1"  # Tòa
    row[6] = "35"  # Tầng
    row[7] = "11"  # Trục căn
    row[8] = 68.5  # Diện tích TT
    row[9] = 74.2  # Diện tích TT
    row[10] = "2"  # PN
    row[11] = "2"  # WC
    row[12] = 150000000  # KPBT
    row[13] = 6800000000  # Chưa VAT
    row[14] = 7600000000  # Full VAT
    row[27] = "Còn hàng"
    row[28] = "Quỹ độc quyền"
    row[29] = "VHUB"

    rec = map_merged_row_to_db_record(
        row=row,
        project_key="LEP",
        is_low_rise=False,
        sub_tab="LEP"
    )

    assert rec is not None
    assert rec["product_code"] == "P5.3X11"
    assert rec["project_id"] == "lumiere-essence-peak"
    assert rec["project_name"] == "LUMIÈRE Essence Peak"
    assert rec["product_type"] == "cao_tang"
    assert rec["building_name"] == "L1"
    assert rec["base_direction_name"] == "ĐN"
