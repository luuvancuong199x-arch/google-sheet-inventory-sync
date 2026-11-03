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
