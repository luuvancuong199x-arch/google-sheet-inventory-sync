import pytest
from unittest.mock import MagicMock
from src.agency_directory import (
    DIRECTORY_HEADERS,
    ensure_directory_sheet_exists,
    update_project_agency_directory,
    DIRECTORY_TAB_NAME
)

def test_directory_headers_count():
    assert len(DIRECTORY_HEADERS) == 14
    assert DIRECTORY_HEADERS[0] == "STT"
    assert DIRECTORY_HEADERS[1] == "Tên Đại lý"
    assert DIRECTORY_HEADERS[6] == "Căn mới hôm nay"
    assert DIRECTORY_HEADERS[7] == "Chuyển Đã bán hôm nay"
    assert DIRECTORY_HEADERS[8] == "Sắp hết hạn (29 ngày)"
    assert DIRECTORY_HEADERS[9] == "Còn hàng"
    assert DIRECTORY_HEADERS[10] == "Lock"
    assert DIRECTORY_HEADERS[11] == "Đã bán"
    assert DIRECTORY_HEADERS[12] == "Tổng số căn"
    assert DIRECTORY_HEADERS[13] == "Thời gian kiểm tra"

def test_update_project_agency_directory_mock():
    mock_service = MagicMock()
    mock_spreadsheets = mock_service.spreadsheets.return_value
    mock_values = mock_spreadsheets.values.return_value

    # Mock spreadsheets().get()
    mock_spreadsheets.get.return_value.execute.return_value = {
        "sheets": [
            {
                "properties": {
                    "title": DIRECTORY_TAB_NAME,
                    "sheetId": 12345
                }
            }
        ]
    }

    # Mock spreadsheets().values().clear() and update()
    mock_values.clear.return_value.execute.return_value = {}
    mock_values.update.return_value.execute.return_value = {}
    mock_spreadsheets.batchUpdate.return_value.execute.return_value = {}

    project_daily_stats = {
        "agency_stats": {
            "HOMEPLUS": {
                "total_units": 10,
                "new_today": 2,
                "sold_today": 1,
                "expiring_soon": 1,
                "avail": 8,
                "lock": 1,
                "sold": 1
            }
        },
        "project_stats": {
            "total_units": 10,
            "new_today": 2,
            "sold_today": 1,
            "expiring_soon": 1,
            "avail": 8,
            "lock": 1,
            "sold": 1
        }
    }

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "src.agency_directory.get_project_agency_links",
            lambda service, p_key, sub_tab=None: [
                {"agency": "HOMEPLUS", "url": "https://example.com/hp", "gid": 0, "sub": "Bảng hàng"}
            ]
        )

        update_project_agency_directory(
            sheets_service=mock_service,
            project_key="OCP2-3",
            diagnostic_lookup={},
            project_daily_stats=project_daily_stats,
            today_str="03/11/2026"
        )

    # Verify update was called
    update_calls = mock_values.update.call_args_list
    assert len(update_calls) > 0
    body = update_calls[0].kwargs.get("body", {})
    values = body.get("values", [])

    # Row 1 is KPI title banner
    assert "TỔNG HỢP BIẾN ĐỘNG TRONG NGÀY" in values[0][0]
    # Row 2 is KPI labels
    assert "🟢 CĂN MỚI HÔM NAY" in values[1][0]
    # Row 3 is KPI values
    assert "+2" in values[2][0]  # new_today
    assert "1" in values[2][3]   # sold_today
    assert "1" in values[2][6]   # expiring_soon
    assert "10 căn" in values[2][9] # total_units in Card 4 (starts at col 9)
    # Row 4 is separator
    assert values[3] == [""] * 14
    # Row 5 is header
    assert values[4] == DIRECTORY_HEADERS
    # Row 6+ are agencies
    assert len(values) >= 6
    # Check Agency row metrics
    homeplus_row = values[5]
    assert homeplus_row[1] == "HOMEPLUS"
    assert homeplus_row[4] == "Đang hoạt động"
    assert homeplus_row[5] == "Đã kết nối và đồng bộ thành công 10 căn."
    assert homeplus_row[6] == 2   # new_today
    assert homeplus_row[7] == 1   # sold_today
    assert homeplus_row[8] == 1   # expiring_soon
    assert homeplus_row[9] == 8   # avail (Còn hàng)
    assert homeplus_row[10] == 1  # lock (Lock)
    assert homeplus_row[11] == 1  # sold (Đã bán)
    assert homeplus_row[12] == 10 # total_units (Tổng số căn)

def test_compute_project_stats_dynamic_headers():
    from src.agency_directory import compute_project_stats_from_sheet

    mock_service = MagicMock()
    mock_values = mock_service.spreadsheets.return_value.values.return_value
    
    # Header where Trạng thái is at col 34, Đại lý at col 36
    header = [f"Col{i}" for i in range(40)]
    header[34] = "Trạng thái"
    header[36] = "Đại lý"
    header[37] = "Ngày cấp hàng"
    header[38] = "Hạn cấp hàng (Còn lại)"

    row1 = ["" for _ in range(40)]
    row1[34] = "Còn hàng"
    row1[36] = "HOMEPLUS"
    row1[37] = "06/11/2026"
    row1[38] = "⚠️ Sắp hết hạn"

    row2 = ["" for _ in range(40)]
    row2[34] = "Đã bán"
    row2[36] = "HOMEPLUS"

    row3 = ["" for _ in range(40)]
    row3[34] = "Đang lock"
    row3[36] = "Vhub"

    mock_values.get.return_value.execute.return_value = {
        "values": [header, row1, row2, row3]
    }

    stats = compute_project_stats_from_sheet(
        mock_service,
        "dummy_sheet_id",
        {"type": "LOW_RISE", "id": "dummy"},
        today_str="06/11/2026"
    )

    ps = stats["project_stats"]
    assert ps["total_units"] == 3
    assert ps["avail"] == 1
    assert ps["lock"] == 1
    assert ps["sold"] == 1
    assert ps["new_today"] == 1
    assert ps["expiring_soon"] == 1

    ags = stats["agency_stats"]
    assert ags["HOMEPLUS"]["avail"] == 1
    assert ags["HOMEPLUS"]["sold"] == 1
    assert ags["VHUB"]["lock"] == 1

