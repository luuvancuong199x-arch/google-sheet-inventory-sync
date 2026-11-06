"""
Module đọc danh mục liên kết đại lý động từ file Google Trang tính Master.
Hỗ trợ cả bảng phân phối thông thường (1 cột link) và bảng MAS Cao Tầng (nhiều cột tiểu dự án MGC, MEL, HSG, LEP).
"""

import re
import time
import logging
from typing import List, Dict, Optional, Any
from src.config import MASTER_SPREADSHEET_ID

logger = logging.getLogger(__name__)

def _execute_api_call(request_call, max_retries=4):
    """Thực thi Google API request kèm cơ chế tự động chờ (Backoff) khi chạm quota 429."""
    for attempt in range(max_retries):
        try:
            return request_call.execute()
        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "RATE_LIMIT_EXCEEDED" in err_str) and attempt < max_retries - 1:
                wait_time = 15 * (attempt + 1)
                logger.warning(f"Chạm giới hạn tần suất Google API (429). Tự động chờ {wait_time}s trước khi thử lại (lần {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            raise e
    return request_call.execute()

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
    p_upper = str(project_key or '').strip().upper()
    if p_upper in ('MAS CAO TẦNG', 'MGC', 'MEL', 'HSG', 'LEP'):
        sub_tabs = ['MGC', 'MEL', 'HSG', 'LEP']
        target_sub = sub_tab_filter or (p_upper if p_upper in sub_tabs else None)
        for r in range(1, len(rows)):
            row = rows[r]
            if len(row) < 2:
                continue
            agency_name = str(row[1] or '').strip()
            if not agency_name:
                continue

            for s_idx, s_name in enumerate(sub_tabs):
                if target_sub and s_name.upper() != target_sub.upper():
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

def get_agency_links_from_target_sheet(
    sheets_service: Any,
    spreadsheet_id: str,
    sub_tab: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Đọc danh mục đại lý và link trực tiếp từ tab 'Danh mục Link Đại lý' của bảng tính dự án đích.
    Tab này là Nguồn Quản Lý Duy Nhất (Single Source of Truth).
    Hỗ trợ nhận diện 'Quỹ chung' (is_general_pool=True) và trích xuất đúng GID.
    """
    try:
        resp = _execute_api_call(sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="'Danh mục Link Đại lý'!A6:D250",
            valueRenderOption='FORMATTED_VALUE'
        ))
        rows = resp.get('values', [])
        if not rows:
            return []

        results = []
        seen = set()

        for row in rows:
            if len(row) < 4:
                continue
            agency_name = str(row[1] or '').strip()
            sub_val = str(row[2] or '').strip()
            link_cell = str(row[3] or '').strip()

            if not agency_name or not link_cell:
                continue

            # Kiểm tra lọc sub_tab nếu có (ví dụ MAS CAO TẦNG: MGC, MEL, HSG, LEP)
            if sub_tab and sub_val and sub_val.upper() != 'BẢNG HÀNG' and sub_tab.upper() != sub_val.upper():
                continue

            # Nếu dự án LEP đang tạm thời dùng chung file với MGC (1fV1_...), bỏ qua các dòng không ghi rõ LEP
            if spreadsheet_id == '1fV1_ZKQXVzsrdMa8ElSpVu-32cj4vPTzgftN81sDynM' and sub_tab == 'LEP' and (not sub_val or sub_val.upper() != 'LEP'):
                continue

            is_general_pool = bool(re.search(r'quỹ chung|quy chung|quỹ cđt|quy cdt', agency_name, re.IGNORECASE))

            parts = re.split(r'[;\n]+|,\s*(?=https?://)|\s+(?=https?://)', link_cell)
            for part in parts:
                for parsed in parse_spreadsheet_url_and_gids(part):
                    key = (
                        agency_name.upper().strip(),
                        parsed["spreadsheet_id"],
                        parsed["gid"],
                        (sub_val or "").upper()
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({
                        "agency": agency_name,
                        "file_id": parsed["spreadsheet_id"],
                        "gid": parsed["gid"],
                        "url": parsed["url"],
                        "sub": sub_val if sub_val and sub_val.upper() != 'BẢNG HÀNG' else None,
                        "is_excel": parsed["is_excel"],
                        "is_general_pool": is_general_pool
                    })
        return results
    except Exception as e:
        logger.warning(f"Không thể đọc danh mục từ tab 'Danh mục Link Đại lý' ({spreadsheet_id}): {e}")
        return []

def get_project_agency_links(
    sheets_service: Any,
    project_key: str,
    sub_tab: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Truy vấn trực tiếp Master Sheet qua Google Sheets API v4 hoặc Drive API (.xlsx) và trả về danh sách các link đại lý.
    """
    p_upper = str(project_key or '').strip().upper()
    master_tab_key = 'MAS CAO TẦNG' if p_upper in ('MAS CAO TẦNG', 'MGC', 'MEL', 'HSG', 'LEP') else project_key
    sub_filter = sub_tab or (p_upper if p_upper in ('MGC', 'MEL', 'HSG', 'LEP') else None)
    try:
        range_name = f"'{master_tab_key}'!A1:Z500"
        resp = _execute_api_call(sheets_service.spreadsheets().values().get(
            spreadsheetId=MASTER_SPREADSHEET_ID,
            range=range_name,
            valueRenderOption='FORMATTED_VALUE'
        ))

        rows = resp.get('values', [])
        return parse_master_sheet_rows(rows, master_tab_key, sub_tab_filter=sub_filter)
    except Exception as e:
        # Nếu file là Office file (.xlsx) hoặc có lỗi Sheets API, dùng fallback Drive API + openpyxl
        try:
            wb = _get_master_workbook_openpyxl()
            if master_tab_key in wb.sheetnames:
                ws = wb[master_tab_key]
                rows = [[str(c.value or '') if c.value is not None else '' for c in r] for r in ws.iter_rows()]
                return parse_master_sheet_rows(rows, master_tab_key, sub_tab_filter=sub_filter)
            else:
                logger.error(f"Không tìm thấy tab '{master_tab_key}' trong Master Sheet (.xlsx)")
                return []
        except Exception as ex2:
            logger.error(f"Lỗi khi đọc tab '{master_tab_key}' từ Master Sheet: {e} | Fallback xlsx: {ex2}")
            return []
