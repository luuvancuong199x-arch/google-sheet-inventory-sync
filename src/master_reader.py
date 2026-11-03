"""
Module đọc danh mục liên kết đại lý động từ file Google Trang tính Master.
Hỗ trợ cả bảng phân phối thông thường (1 cột link) và bảng MAS Cao Tầng (nhiều cột tiểu dự án MGC, MEL, HSG, LEP).
"""

import re
import logging
from typing import List, Dict, Optional, Any
from src.config import MASTER_SPREADSHEET_ID

logger = logging.getLogger(__name__)

def parse_spreadsheet_url_and_gids(raw_url: str) -> List[Dict[str, Any]]:
    """
    Phân tích URL Google Spreadsheet, trích xuất Spreadsheet ID và TẤT CẢ các GID được chỉ định.
    Hỗ trợ:
      - 1 URL thông thường: ?gid=1592630955
      - Nhiều GID cách nhau bởi dấu phẩy: ?gid=1592630955,1143879447
      - Nhiều tham số gid: ?gid=1592630955&gid=1143879447
      - Không có GID: gid=None
    """
    if not raw_url or not isinstance(raw_url, str):
        return []

    clean_url = raw_url.strip()
    if 'docs.google.com/spreadsheets' not in clean_url:
        return []

    # Khớp Spreadsheet ID (chuỗi ít nhất 15 ký tự)
    id_match = re.search(r'/spreadsheets/(?:u/\d+/)?d/([a-zA-Z0-9_-]{15,})', clean_url)
    if not id_match:
        return []
    spreadsheet_id = id_match.group(1)

    # Nhận diện file Excel (.xlsx) tải lên Google Drive
    is_excel = bool(re.search(r'rtpof=true|\.xlsx', clean_url, re.IGNORECASE))

    # Tìm tất cả GID
    gids = []
    for m in re.finditer(r'[?#&]gid=([0-9,]+)', clean_url):
        for part in m.group(1).split(','):
            part = part.strip()
            if part.isdigit():
                gids.append(int(part))

    if not gids:
        return [{
            "spreadsheet_id": spreadsheet_id,
            "gid": None,
            "url": clean_url,
            "is_excel": is_excel
        }]

    seen_gids = set()
    results = []
    for g in gids:
        if g not in seen_gids:
            seen_gids.add(g)
            results.append({
                "spreadsheet_id": spreadsheet_id,
                "gid": g,
                "url": clean_url,
                "is_excel": is_excel
            })
    return results

def parse_spreadsheet_url_and_gid(raw_url: str) -> Optional[Dict[str, Any]]:
    """
    Phân tích URL Google Spreadsheet, trích xuất Spreadsheet ID và GID (sheetId).
    Đồng thời phát hiện nếu liên kết trỏ tới file Excel lưu trên Drive (rtpof=true).
    """
    entries = parse_spreadsheet_url_and_gids(raw_url)
    return entries[0] if entries else None

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
                        parts = re.split(r'[;\n]+|,\s*(?=https?://)|\s+(?=https?://)', cell_val)
                        for part in parts:
                            for parsed in parse_spreadsheet_url_and_gids(part):
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

            parts = re.split(r'[;\n]+|,\s*(?=https?://)|\s+(?=https?://)', link_cell)
            for part in parts:
                for parsed in parse_spreadsheet_url_and_gids(part):
                    add_entry(agency_name, parsed, sub=None)

    return results

_MASTER_WORKBOOK_CACHE = None

def _get_master_workbook_openpyxl():
    global _MASTER_WORKBOOK_CACHE
    if _MASTER_WORKBOOK_CACHE is not None:
        return _MASTER_WORKBOOK_CACHE
    from src.auth import get_drive_service
    from googleapiclient.http import MediaIoBaseDownload
    import io
    import openpyxl

    drive = get_drive_service()
    req = drive.files().get_media(fileId=MASTER_SPREADSHEET_ID)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    _MASTER_WORKBOOK_CACHE = openpyxl.load_workbook(fh, data_only=True)
    return _MASTER_WORKBOOK_CACHE

def get_project_agency_links(
    sheets_service: Any,
    project_key: str,
    sub_tab: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Truy vấn trực tiếp Master Sheet qua Google Sheets API v4 hoặc Drive API (.xlsx) và trả về danh sách các link đại lý.
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
        # Nếu file là Office file (.xlsx) hoặc có lỗi Sheets API, dùng fallback Drive API + openpyxl
        try:
            wb = _get_master_workbook_openpyxl()
            if project_key in wb.sheetnames:
                ws = wb[project_key]
                rows = [[str(c.value or '') if c.value is not None else '' for c in r] for r in ws.iter_rows()]
                return parse_master_sheet_rows(rows, project_key, sub_tab_filter=sub_tab)
            else:
                logger.error(f"Không tìm thấy tab '{project_key}' trong Master Sheet (.xlsx)")
                return []
        except Exception as ex2:
            logger.error(f"Lỗi khi đọc tab '{project_key}' từ Master Sheet: {e} | Fallback xlsx: {ex2}")
            return []
