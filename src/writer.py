"""
Module đọc và ghi dữ liệu về các file Google Trang tính đích.
Sử dụng Google Sheets API v4 batchUpdate để ghi dữ liệu và định dạng trong 1 request.
Tuyệt đối không dùng clearContents() để tránh rủi ro mất trắng trang tính khi có sự cố.
"""

import re
import time
import logging
from typing import Dict, List, Any
from src.normalizer import sanitize_unit_code, realign_legacy_row

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

def get_or_create_sheet(sheets_service: Any, spreadsheet_id: str, sheet_name: str) -> int:
    """
    Lấy Sheet ID (gid) của tab chỉ định. Nếu chưa tồn tại thì tự động tạo mới,
    tuyệt đối không ghi đè lên tab bìa/Dashboard đầu tiên.
    """
    meta = _execute_api_call(sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id))
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
    resp = _execute_api_call(sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [req]}
    ))
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
        range_name = f"'{sheet_name}'!A1:AN15000"
        resp = _execute_api_call(sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueRenderOption='FORMATTED_VALUE'
        ))

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

            if is_low_rise:
                row = realign_legacy_row(row, is_low_rise=True)

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
    _execute_api_call(sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=write_range,
        valueInputOption='USER_ENTERED',
        body={"values": all_values}
    ))

    # 2. Xóa các dòng thừa phía dưới nếu số dòng mới ít hơn số dòng cũ (thay vì clearContents trước)
    try:
        meta = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sh in meta.get('sheets', []):
            if sh['properties']['sheetId'] == sheet_id:
                current_total_rows = sh['properties']['gridProperties']['rowCount']
                if current_total_rows > len(all_values):
                    clear_range = f"'{sheet_name}'!A{len(all_values) + 1}:AN{current_total_rows}"
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

        # Cột Trạng thái: Căn giữa, Danh sách chọn (Dropdown list), và Quy tắc thẻ màu (Xanh lá - Cam - Đỏ)
        status_col_idx = 31 if is_low_rise else 27
        expiry_col_idx = 38 if is_low_rise else 31

        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": len(all_values),
                    "startColumnIndex": status_col_idx,
                    "endColumnIndex": status_col_idx + 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        })

        # Cột Hạn cấp hàng: Căn giữa
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": len(all_values),
                    "startColumnIndex": expiry_col_idx,
                    "endColumnIndex": expiry_col_idx + 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        })

        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": len(all_values),
                    "startColumnIndex": status_col_idx,
                    "endColumnIndex": status_col_idx + 1
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [
                            {"userEnteredValue": "Còn hàng"},
                            {"userEnteredValue": "Đang lock"},
                            {"userEnteredValue": "Đã bán"}
                        ]
                    },
                    "showCustomUi": True,
                    "strict": False
                }
            }
        })

        # Kiểm tra xem quy tắc màu sắc (Conditional Formatting) đã có chưa để không tạo trùng lặp
        has_status_cf = False
        has_expiry_cf = False
        try:
            cf_meta = _execute_api_call(sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields="sheets(properties(sheetId),conditionalFormats)"
            ))
            for sh in cf_meta.get('sheets', []):
                if sh['properties']['sheetId'] == sheet_id:
                    for cf in sh.get('conditionalFormats', []):
                        for r in cf.get('ranges', []):
                            if r.get('startColumnIndex') == status_col_idx:
                                has_status_cf = True
                            if r.get('startColumnIndex') == expiry_col_idx:
                                has_expiry_cf = True
                    break
        except Exception as e:
            logger.warning(f"Lỗi khi kiểm tra conditional formats: {e}")

        if not has_status_cf:
            # 1. Còn hàng: Nền xanh lá cây nhạt, chữ xanh lá cây đậm, in đậm
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": status_col_idx,
                            "endColumnIndex": status_col_idx + 1
                        }],
                        "booleanRule": {
                            "condition": {
                               "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "Còn hàng"}]
                            },
                            "format": {
                                "backgroundColor": {"red": 0.851, "green": 0.918, "blue": 0.827},
                                "textFormat": {
                                    "foregroundColor": {"red": 0.153, "green": 0.306, "blue": 0.075},
                                    "bold": True
                                }
                            }
                        }
                    },
                    "index": 0
                }
            })
            # 2. Đang lock: Nền cam nhạt, chữ cam đậm, in đậm
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": status_col_idx,
                            "endColumnIndex": status_col_idx + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "Đang lock"}]
                            },
                            "format": {
                                "backgroundColor": {"red": 0.988, "green": 0.898, "blue": 0.804},
                                "textFormat": {
                                    "foregroundColor": {"red": 0.706, "green": 0.373, "blue": 0.024},
                                    "bold": True
                                }
                            }
                        }
                    },
                    "index": 1
                }
            })
            # 3. Đã bán: Nền đỏ nhạt, chữ đỏ đậm, in đậm
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": status_col_idx,
                            "endColumnIndex": status_col_idx + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "Đã bán"}]
                            },
                            "format": {
                                "backgroundColor": {"red": 0.957, "green": 0.800, "blue": 0.800},
                                "textFormat": {
                                    "foregroundColor": {"red": 0.600, "green": 0.0, "blue": 0.0},
                                    "bold": True
                                }
                            }
                        }
                    },
                    "index": 2
                }
            })

        if not has_expiry_cf:
            # Cảnh báo hạn cấp hàng
            # 1. ⚠️ Sắp hết hạn (mốc 29 ngày): Nền cam nhạt, chữ cam đậm
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": expiry_col_idx,
                            "endColumnIndex": expiry_col_idx + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_CONTAINS",
                                "values": [{"userEnteredValue": "⚠️ Sắp hết hạn"}]
                            },
                            "format": {
                                "backgroundColor": {"red": 1.0, "green": 0.949, "blue": 0.8},
                                "textFormat": {
                                    "foregroundColor": {"red": 0.706, "green": 0.373, "blue": 0.024},
                                    "bold": True
                                }
                            }
                        }
                    },
                    "index": 0
                }
            })
            # 2. ⛔ Đã hết hạn (quá 30 ngày): Nền đỏ nhạt, chữ đỏ đậm
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": expiry_col_idx,
                            "endColumnIndex": expiry_col_idx + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_CONTAINS",
                                "values": [{"userEnteredValue": "⛔ Đã hết hạn"}]
                            },
                            "format": {
                                "backgroundColor": {"red": 0.957, "green": 0.800, "blue": 0.800},
                                "textFormat": {
                                    "foregroundColor": {"red": 0.600, "green": 0.0, "blue": 0.0},
                                    "bold": True
                                }
                            }
                        }
                    },
                    "index": 1
                }
            })

        _execute_api_call(sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ))

    logger.info(f"Đã cập nhật thành công {len(rows)} căn vào tab '{sheet_name}' ({spreadsheet_id})")
