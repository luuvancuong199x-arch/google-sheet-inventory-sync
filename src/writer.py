"""
Module đọc và ghi dữ liệu về các file Google Trang tính đích.
Sử dụng Google Sheets API v4 batchUpdate để ghi dữ liệu và định dạng trong 1 request.
Tuyệt đối không dùng clearContents() để tránh rủi ro mất trắng trang tính khi có sự cố.
"""

import re
import logging
from typing import Dict, List, Any
from src.normalizer import sanitize_unit_code

logger = logging.getLogger(__name__)

def get_or_create_sheet(sheets_service: Any, spreadsheet_id: str, sheet_name: str) -> int:
    """
    Lấy Sheet ID (gid) của tab chỉ định. Nếu chưa tồn tại thì tự động tạo mới,
    tuyệt đối không ghi đè lên tab bìa/Dashboard đầu tiên.
    """
    meta = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = meta.get('sheets', [])
    for sh in sheets:
        if sh['properties']['title'].strip().lower() == sheet_name.strip().lower():
            return sh['properties']['sheetId']

    # Nếu chưa có thì tạo mới tab
    req = {
        "addSheet": {
            "properties": {
                "title": sheet_name
            }
        }
    }
    resp = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [req]}
    ).execute()
    new_sheet_id = resp['replies'][0]['addSheet']['properties']['sheetId']
    logger.info(f"Đã tạo mới tab '{sheet_name}' (sheetId: {new_sheet_id}) trên file đích {spreadsheet_id}")
    return new_sheet_id

def read_existing_target_pool(
    sheets_service: Any,
    spreadsheet_id: str,
    sheet_name: str,
    is_low_rise: bool
) -> Dict[str, Dict[str, Any]]:
    """
    Đọc dữ liệu hiện có trong Sheet đích để phục vụ cơ chế Smart Upsert.
    """
    try:
        range_name = f"'{sheet_name}'!A1:AL15000"
        resp = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueRenderOption='FORMATTED_VALUE'
        ).execute()

        rows = resp.get('values', [])
        if len(rows) < 2:
            return {}

        existing_pool = {}
        unit_code_col_idx = 2 if is_low_rise else 1

        for r in range(1, len(rows)):
            row = rows[r]
            if len(row) <= unit_code_col_idx:
                continue
            unit_code = str(row[unit_code_col_idx] or '').strip()
            if not unit_code:
                continue
            key = sanitize_unit_code(unit_code)
            if not key:
                continue
            # Lọc bỏ các dòng banner / tiêu đề phân mục không phải mã căn thực tế
            if not re.search(r'\d', key):
                continue
            if re.search(r'^(phân\s*khu|bảng\s*hàng|đơn\s*lập|song\s*lập|liền\s*kề|biệt\s*thự|shophouse|tổng\s*cộng|căn\s*hộ|ghi\s*chú|demo|test|đlmc|dlmc|lp)$', key, re.IGNORECASE):
                continue

            existing_pool[key] = {
                "unit_key": key,
                "row_values": row
            }

        return existing_pool
    except Exception as e:
        logger.warning(f"Không thể đọc dữ liệu cũ từ tab '{sheet_name}' ({spreadsheet_id}): {e}")
        return {}

def write_normalized_inventory(
    sheets_service: Any,
    spreadsheet_id: str,
    sheet_name: str,
    headers: List[str],
    rows: List[List[Any]],
    is_low_rise: bool
):
    """
    Ghi dữ liệu đã chuẩn hóa và cập nhật định dạng số vào Sheet đích.
    """
    sheet_id = get_or_create_sheet(sheets_service, spreadsheet_id, sheet_name)

    # 1. Ghi Header và Dữ liệu
    all_values = [headers] + rows
    write_range = f"'{sheet_name}'!A1"
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=write_range,
        valueInputOption='USER_ENTERED',
        body={"values": all_values}
    ).execute()

    # 2. Xóa các dòng thừa phía dưới nếu số dòng mới ít hơn số dòng cũ (thay vì clearContents trước)
    try:
        meta = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sh in meta.get('sheets', []):
            if sh['properties']['sheetId'] == sheet_id:
                current_total_rows = sh['properties']['gridProperties']['rowCount']
                if current_total_rows > len(all_values):
                    clear_range = f"'{sheet_name}'!A{len(all_values) + 1}:AL{current_total_rows}"
                    sheets_service.spreadsheets().values().clear(
                        spreadsheetId=spreadsheet_id,
                        range=clear_range
                    ).execute()
                break
    except Exception as e:
        logger.warning(f"Lỗi khi dọn dòng thừa: {e}")

    # 3. Định dạng NumberFormat qua batchUpdate
    if rows:
        requests = []
        # Định dạng text cho mã căn
        unit_col_idx = 2 if is_low_rise else 1
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": len(all_values),
                    "startColumnIndex": unit_col_idx,
                    "endColumnIndex": unit_col_idx + 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "TEXT"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat"
            }
        })

        # Định dạng tiền tệ #,##0 cho các cột giá
        price_start_col = 7 if is_low_rise else 12
        price_end_col = 23 if is_low_rise else 19
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": len(all_values),
                    "startColumnIndex": price_start_col,
                    "endColumnIndex": price_end_col
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "NUMBER", "pattern": "#,##0"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat"
            }
        })

        # Định dạng diện tích #,##0.##
        area_start_col = 5 if is_low_rise else 8
        area_end_col = 7 if is_low_rise else 10
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": len(all_values),
                    "startColumnIndex": area_start_col,
                    "endColumnIndex": area_end_col
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "NUMBER", "pattern": "#,##0.##"}
                    }
                },
                "fields": "userEnteredFormat.numberFormat"
            }
        })

        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()

    logger.info(f"Đã cập nhật thành công {len(rows)} căn vào tab '{sheet_name}' ({spreadsheet_id})")
