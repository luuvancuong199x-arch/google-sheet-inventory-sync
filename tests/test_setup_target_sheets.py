import pytest
from src.setup_target_sheets import build_sheet_spec, update_config_file_with_new_ids

def test_build_sheet_spec():
    headers = ["STT", "Mã căn", "Giá full"]
    spec = build_sheet_spec("Test Tab", headers)
    assert spec["properties"]["title"] == "Test Tab"
    assert spec["properties"]["gridProperties"]["frozenRowCount"] == 1
    row_values = spec["data"][0]["rowData"][0]["values"]
    assert len(row_values) == 3
    assert row_values[0]["userEnteredValue"]["stringValue"] == "STT"
    assert row_values[1]["userEnteredValue"]["stringValue"] == "Mã căn"
    assert row_values[2]["userEnteredValue"]["stringValue"] == "Giá full"

def test_update_config_file_with_new_ids(tmp_path):
    temp_config = tmp_path / "config.py"
    temp_config.write_text(
        "TARGET_PROJECTS = {\n"
        "    'làng vân': {\n"
        "        'id': 'OLD_ID_1',\n"
        "        'name': 'Dự án Làng Vân'\n"
        "    }\n"
        "}\n",
        encoding="utf-8"
    )

    update_config_file_with_new_ids({"làng vân": "NEW_ID_999"}, config_path=str(temp_config))
    updated_content = temp_config.read_text(encoding="utf-8")
    assert "'id': 'NEW_ID_999'" in updated_content
