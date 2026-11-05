import pytest
from src.master_reader import parse_spreadsheet_url_and_gid, parse_master_sheet_rows

def test_parse_spreadsheet_url_and_gid():
    url1 = "https://docs.google.com/spreadsheets/d/1ONPUJuewSw1xu_I5SSgnr1YUqIEyGcUJ/edit?gid=841746683"
    p1 = parse_spreadsheet_url_and_gid(url1)
    assert p1 is not None
    assert p1["spreadsheet_id"] == "1ONPUJuewSw1xu_I5SSgnr1YUqIEyGcUJ"
    assert p1["gid"] == 841746683
    assert p1["is_excel"] is False

    # Excel file on Drive
    url_excel = "https://docs.google.com/spreadsheets/d/1twefTWN7o9qILJkG5PsqJXQ9XccKR9IC/edit?usp=sharing&ouid=106158638514325987385&rtpof=true&sd=true"
    pe = parse_spreadsheet_url_and_gid(url_excel)
    assert pe is not None
    assert pe["spreadsheet_id"] == "1twefTWN7o9qILJkG5PsqJXQ9XccKR9IC"
    assert pe["gid"] is None
    assert pe["is_excel"] is True

    # Invalid URL
    assert parse_spreadsheet_url_and_gid("https://example.com/not-sheets") is None
    assert parse_spreadsheet_url_and_gid("") is None

def test_parse_master_sheet_rows_standard():
    rows = [
        ["STT", "TÊN ĐL", "LINK BẢNG HÀNG", "TRẠNG THÁI"],
        ["1", "VHS", "https://docs.google.com/spreadsheets/d/1ONPUJuewSw1xu_I5SSgnr1YUqIEyGcUJ/edit?gid=841746683", "Công khai"],
        ["2", "BHS", "https://docs.google.com/spreadsheets/d/1s27ks61cq_4vloR7C49hRS2Skt6HSWiVBN7qFl_cZyo/edit?gid=920510806", "Đang bán"]
    ]
    links = parse_master_sheet_rows(rows, project_key="làng vân")
    assert len(links) == 2
    assert links[0]["agency"] == "VHS"
    assert links[0]["file_id"] == "1ONPUJuewSw1xu_I5SSgnr1YUqIEyGcUJ"
    assert links[0]["gid"] == 841746683

def test_parse_master_sheet_rows_mas_cao_tang():
    rows = [
        ["STT", "TÊN ĐL", "MGC", "MEL", "HSG", "LEP"],
        [
            "1", "ATD",
            "https://docs.google.com/spreadsheets/d/15WpuPJeolLrLEokEelQcPgqy7aORuVV-SpAXb9L2Pgg/edit?gid=1831326906",
            "https://docs.google.com/spreadsheets/d/1zVxwzcSi3xzybh0PLLgFb35vrnRzPOl8cPAy0ANaqvs/edit?gid=1831326906",
            "", ""
        ]
    ]
    links_mgc = parse_master_sheet_rows(rows, project_key="MAS CAO TẦNG", sub_tab_filter="MGC")
    assert len(links_mgc) == 1
    assert links_mgc[0]["sub"] == "MGC"
    assert links_mgc[0]["file_id"] == "15WpuPJeolLrLEokEelQcPgqy7aORuVV-SpAXb9L2Pgg"

    links_all = parse_master_sheet_rows(rows, project_key="MAS CAO TẦNG", sub_tab_filter=None)
    assert len(links_all) == 2
    assert {l["sub"] for l in links_all} == {"MGC", "MEL"}

    links_mgc_direct = parse_master_sheet_rows(rows, project_key="MGC")
    assert len(links_mgc_direct) == 1
    assert links_mgc_direct[0]["sub"] == "MGC"

    links_mel_direct = parse_master_sheet_rows(rows, project_key="MEL")
    assert len(links_mel_direct) == 1
    assert links_mel_direct[0]["sub"] == "MEL"

def test_parse_spreadsheet_url_multiple_gids():
    from src.master_reader import parse_spreadsheet_url_and_gids
    # Comma-separated GIDs
    url_comma = "https://docs.google.com/spreadsheets/d/1-KcwSLpuSQGhqOZ8BycoRLeE3DUrawan/edit?gid=1592630955,1143879447"
    entries = parse_spreadsheet_url_and_gids(url_comma)
    assert len(entries) == 2
    assert entries[0]["gid"] == 1592630955
    assert entries[1]["gid"] == 1143879447

    # Multiple links in single cell separated by semicolon or whitespace
    rows = [
        ["STT", "TÊN ĐL", "LINK BẢNG HÀNG"],
        ["1", "MAYHOMES", "https://docs.google.com/spreadsheets/d/1-KcwSLpuSQGhqOZ8BycoRLeE3DUrawan/edit?gid=1592630955; https://docs.google.com/spreadsheets/d/1-KcwSLpuSQGhqOZ8BycoRLeE3DUrawan/edit?gid=1143879447"]
    ]
    parsed_rows = parse_master_sheet_rows(rows, "OCP2-3")
    assert len(parsed_rows) == 2
    assert parsed_rows[0]["gid"] == 1592630955
    assert parsed_rows[1]["gid"] == 1143879447

def test_get_agency_links_from_target_sheet():
    from unittest.mock import MagicMock
    from src.master_reader import get_agency_links_from_target_sheet

    mock_service = MagicMock()
    mock_service.spreadsheets().values().get().execute.return_value = {
        "values": [
            ["QC", "Quỹ chung", "Bảng hàng", "https://docs.google.com/spreadsheets/d/12l8C00BxvuzEEEgu2ngjkmOUXc1eC_kn/edit?gid=585501108#gid=585501108"],
            ["1", "VHS", "Bảng hàng", "https://docs.google.com/spreadsheets/d/1ONPUJuewSw1xu_I5SSgnr1YUqIEyGcUJ/edit?gid=841746683"],
            ["2", "Đất xanh MT", "Bảng hàng", "https://docs.google.com/spreadsheets/d/15mLWBzjkjf8Co-S5CvrAIpJMhn8hK_LNgm8ZmgTuQJI/edit?gid=1725370903,111222333"]
        ]
    }

    links = get_agency_links_from_target_sheet(mock_service, "dummy_id")
    assert len(links) == 4
    # Check Quỹ chung
    assert links[0]["agency"] == "Quỹ chung"
    assert links[0]["is_general_pool"] is True
    assert links[0]["gid"] == 585501108

    # Check regular agency
    assert links[1]["agency"] == "VHS"
    assert links[1]["is_general_pool"] is False
    assert links[1]["gid"] == 841746683

    # Check multiple GIDs
    assert links[2]["agency"] == "Đất xanh MT"
    assert links[2]["gid"] == 1725370903
    assert links[3]["agency"] == "Đất xanh MT"
    assert links[3]["gid"] == 111222333

