"""
Module đọc danh mục liên kết đại lý động từ file Google Trang tính Master.
Hỗ trợ cả bảng phân phối thông thường (1 cột link) và bảng MAS Cao Tầng (nhiều cột tiểu dự án MGC, MEL, HSG, LEP).
"""

import re
import logging
from typing import List, Dict, Optional, Any
from src.config import MASTER_SPREADSHEET_ID

logger = logging.getLogger(__name__)

def parse_spreadsheet_url_and_gid(raw_url: str) -> Optional[Dict[str, Any]]:
    """
    Phân tích URL Google Spreadsheet, trích xuất Spreadsheet ID và GID (sheetId).
    Đồng thời phát hiện nếu liên kết trỏ tới file Excel lưu trên Drive (rtpof=true).
    """
    if not raw_url or not isinstance(raw_url, str):
        return None

    clean_url = raw_url.strip()
    if 'docs.google.com/spreadsheets' not in clean_url:
        return None

    # Khớp Spreadsheet ID (chuỗi ít nhất 15 ký tự)
    id_match = re.search(r'/spreadsheets/(?:u/\d+/)?d/([a-zA-Z0-9_-]{15,})', clean_url)
    if not id_match:
        return None
    spreadsheet_id = id_match.group(1)

    # Khớp GID nếu có
    gid_match = re.search(r'[?#&]gid=(\d+)', clean_url)
    gid = int(gid_match.group(1)) if gid_match else None

    # Nhận diện file Excel (.xlsx) tải lên Google Drive
    is_excel = bool(re.search(r'rtpof=true|\.xlsx', clean_url, re.IGNORECASE))

    return {
        "spreadsheet_id": spreadsheet_id,
        "gid": gid,
        "url": clean_url,
        "is_excel": is_excel
    }

def parse_master_sheet_rows(
    rows: List[List[str]],
    project_key: str,
    sub_tab_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Phân tích dữ liệu dạng ma trận dòng/cột từ một sheet dự án trong Master Sheet.
    """
    if not rows or len(rows) < 2:
        return []

    results = []
    seen = set()

    def add_entry(agency: str, parsed: Dict[str, Any], sub: Optional[str] = None):
        key = (
            agency.upper().strip(),
            parsed["spreadsheet_id"],
            parsed["gid"],
            (sub or "").upper()
        )
        if key in seen:
            return
        seen.add(key)
        results.append({
            "agency": agency.strip(),
            "file_id": parsed["spreadsheet_id"],
            "gid": parsed["gid"],
            "url": parsed["url"],
            "sub": sub,
            "is_excel": parsed["is_excel"]
        })

    # Xử lý riêng cho dự án MAS CAO TẦNG (Headers: STT, TÊN ĐL, MGC, MEL, HSG, LEP)
    if project_key == 'MAS CAO TẦNG':
        sub_tabs = ['MGC', 'MEL', 'HSG', 'LEP']
        for r in range(1, len(rows)):
            row = rows[r]
            if len(row) < 2:
                continue
            agency_name = str(row[1] or '').strip()
            if not agency_name:
                continue

            for s_idx, s_name in enumerate(sub_tabs):
                if sub_tab_filter and s_name.upper() != sub_tab_filter.upper():
                    continue
                col_idx = 2 + s_idx
                if col_idx < len(row):
                    cell_val = str(row[col_idx] or '').strip()
                    if cell_val:
                        parts = re.split(r'[;\n]+', cell_val)
                        for part in parts:
                            parsed = parse_spreadsheet_url_and_gid(part)
                            if parsed:
                                add_entry(agency_name, parsed, sub=s_name)
    else:
        # Bảng thông thường (Cột 1: Tên đại lý, Cột 2: Link bảng hàng)
        for r in range(1, len(rows)):
            row = rows[r]
            if len(row) < 3:
                continue
            agency_name = str(row[1] or '').strip()
            link_cell = str(row[2] or '').strip()
            if not agency_name or not link_cell:
                continue

            parts = re.split(r'[;\n]+', link_cell)
            for part in parts:
                parsed = parse_spreadsheet_url_and_gid(part)
                if parsed:
                    add_entry(agency_name, parsed, sub=None)

    return results

def get_project_agency_links(
    sheets_service: Any,
    project_key: str,
    sub_tab: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Truy vấn trực tiếp Master Sheet qua Google Sheets API v4 và trả về danh sách các link đại lý.
    """
    try:
        range_name = f"'{project_key}'!A1:Z500"
        resp = sheets_service.spreadsheets().values().get(
            spreadsheetId=MASTER_SPREADSHEET_ID,
            range=range_name,
            valueRenderOption='FORMATTED_VALUE'
        ).execute()

        rows = resp.get('values', [])
        return parse_master_sheet_rows(rows, project_key, sub_tab_filter=sub_tab)
    except Exception as e:
        logger.error(f"Lỗi khi đọc tab '{project_key}' từ Master Sheet: {e}")
        return []
