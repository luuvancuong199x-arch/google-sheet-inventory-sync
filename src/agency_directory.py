"""
Module quản lý và cập nhật tab "Danh mục Link Đại lý" trên toàn bộ 12 dự án.
Ghi chú chính xác trạng thái kết nối, nguyên nhân lỗi và hướng dẫn xử lý cụ thể
cho từng đại lý theo chỉ đạo của Người dùng.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from src.config import TARGET_PROJECTS
from src.master_reader import get_project_agency_links
from src.fetcher import _execute_with_retry

logger = logging.getLogger(__name__)

DIRECTORY_TAB_NAME = "Danh mục Link Đại lý"

DIRECTORY_HEADERS = [
    "STT",
    "Tên Đại lý",
    "Phân khu / Tab",
    "Link bảng hàng nguồn",
    "Trạng thái kết nối",
    "Mô tả chi tiết / Hướng dẫn xử lý",
    "Số sản phẩm",
    "Thời gian kiểm tra"
]

def ensure_directory_sheet_exists(sheets_service: Any, spreadsheet_id: str) -> int:
    """Kiểm tra tab 'Danh mục Link Đại lý' đã tồn tại chưa, nếu chưa thì tạo mới. Trả về sheetId."""
    meta = _execute_with_retry(sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id))
    sheets = meta.get('sheets', [])
    for sh in sheets:
        if sh['properties']['title'] == DIRECTORY_TAB_NAME:
            return sh['properties']['sheetId']

    # Tạo mới sheet
    add_resp = _execute_with_retry(
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                "requests": [{
                    "addSheet": {
                        "properties": {
                            "title": DIRECTORY_TAB_NAME,
                            "gridProperties": {
                                "rowCount": 200,
                                "columnCount": 10,
                                "frozenRowCount": 1
                            }
                        }
                    }
                }]
            }
        )
    )
    new_sheet_id = add_resp['replies'][0]['addSheet']['properties']['sheetId']
    logger.info(f"Đã tạo tab '{DIRECTORY_TAB_NAME}' (sheetId={new_sheet_id}) trong file {spreadsheet_id}")
    return new_sheet_id

def apply_directory_styling(sheets_service: Any, spreadsheet_id: str, sheet_id: int, total_rows: int):
    """Định dạng giao diện chuyên nghiệp cho tab Danh mục Link Đại lý."""
    requests = [
        # 1. Đóng băng dòng 1
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        },
        # 2. Định dạng Header dòng 1 (Navy #1b365d, chữ trắng đậm)
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(DIRECTORY_HEADERS)
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.106, "green": 0.212, "blue": 0.365},
                        "textFormat": {
                            "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                            "bold": True,
                            "fontSize": 10
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"
            }
        },
        # 3. Đặt chiều rộng các cột
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 50}, "fields": "pixelSize"}},   # STT
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}, "properties": {"pixelSize": 180}, "fields": "pixelSize"}},  # Tên ĐL
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3}, "properties": {"pixelSize": 130}, "fields": "pixelSize"}},  # Phân khu
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4}, "properties": {"pixelSize": 280}, "fields": "pixelSize"}},  # Link
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5}, "properties": {"pixelSize": 230}, "fields": "pixelSize"}},  # Trạng thái
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 5, "endIndex": 6}, "properties": {"pixelSize": 460}, "fields": "pixelSize"}},  # Mô tả
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 7}, "properties": {"pixelSize": 90}, "fields": "pixelSize"}},   # Số căn
        {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 7, "endIndex": 8}, "properties": {"pixelSize": 140}, "fields": "pixelSize"}},  # Thời gian
    ]

    # 4. Định dạng có điều kiện cho cột Trạng thái (Cột E, index 4)
    # Xanh lá cho Đang hoạt động
    requests.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": total_rows, "startColumnIndex": 4, "endColumnIndex": 5}],
                "booleanRule": {
                    "condition": {
                        "type": "TEXT_CONTAINS",
                        "values": [{"userEnteredValue": "Đang hoạt động"}]
                    },
                    "format": {
                        "backgroundColor": {"red": 0.851, "green": 0.918, "blue": 0.827},
                        "textFormat": {"foregroundColor": {"red": 0.153, "green": 0.306, "blue": 0.075}, "bold": True}
                    }
                }
            },
            "index": 0
        }
    })
    # Đỏ cho Lỗi
    requests.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": total_rows, "startColumnIndex": 4, "endColumnIndex": 5}],
                "booleanRule": {
                    "condition": {
                        "type": "TEXT_STARTS_WITH",
                        "values": [{"userEnteredValue": "Lỗi:"}]
                    },
                    "format": {
                        "backgroundColor": {"red": 0.957, "green": 0.8, "blue": 0.8},
                        "textFormat": {"foregroundColor": {"red": 0.6, "green": 0.0, "blue": 0.0}, "bold": True}
                    }
                }
            },
            "index": 1
        }
    })
    # Vàng cho Cảnh báo / Trống
    requests.append({
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": total_rows, "startColumnIndex": 4, "endColumnIndex": 5}],
                "booleanRule": {
                    "condition": {
                        "type": "TEXT_CONTAINS",
                        "values": [{"userEnteredValue": "Cảnh báo:"}]
                    },
                    "format": {
                        "backgroundColor": {"red": 1.0, "green": 0.949, "blue": 0.8},
                        "textFormat": {"foregroundColor": {"red": 0.706, "green": 0.373, "blue": 0.024}, "bold": True}
                    }
                }
            },
            "index": 2
        }
    })

    try:
        _execute_with_retry(
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests}
            )
        )
    except Exception as e:
        logger.warning(f"Lỗi khi định dạng tab Danh mục Đại lý: {e}")

def update_project_agency_directory(
    sheets_service: Any,
    project_key: str,
    diagnostic_lookup: Dict[str, Any],
    sync_stats_lookup: Optional[Dict[str, Any]] = None
):
    """Cập nhật tab Danh mục Link Đại lý cho 1 dự án cụ thể."""
    cfg = TARGET_PROJECTS.get(project_key)
    if not cfg:
        return

    spreadsheet_id = cfg['id']
    sub_tabs = cfg.get('sub_tabs')
    
    # 1. Lấy danh sách link đại lý từ Master Sheet
    if sub_tabs:
        agency_links = []
        for st in sub_tabs:
            agency_links.extend(get_project_agency_links(sheets_service, project_key, sub_tab=st))
    else:
        agency_links = get_project_agency_links(sheets_service, project_key)

    if not agency_links:
        logger.info(f"Không có link đại lý nào cho dự án {project_key}")
        return

    # 2. Đảm bảo tab tồn tại
    sheet_id = ensure_directory_sheet_exists(sheets_service, spreadsheet_id)

    # 3. Chuẩn bị dữ liệu từng dòng
    current_time_str = time.strftime("%d/%m/%Y %H:%M")
    rows_data = [DIRECTORY_HEADERS]

    for idx, ag in enumerate(agency_links, 1):
        ag_name = ag['agency']
        url = ag['url']
        gid = ag.get('gid')
        sub = ag.get('sub') or 'Bảng hàng'

        # Khóa tra cứu trong diagnostic_lookup
        diag_key = (ag_name.strip().upper(), url.strip(), (sub or '').strip().upper())
        diag_info = diagnostic_lookup.get(diag_key) or diagnostic_lookup.get((ag_name.strip().upper(), url.strip()))

        # Kiểm tra sync_stats_lookup nếu có
        ag_u = ag_name.strip().upper()
        sub_u = (sub or '').strip().upper()
        p_u = project_key.strip().upper()
        sync_info = None
        if sync_stats_lookup:
            sync_info = (
                sync_stats_lookup.get((p_u, sub_u, ag_u)) or
                sync_stats_lookup.get((p_u, ag_u)) or
                sync_stats_lookup.get((ag_u, sub_u)) or
                sync_stats_lookup.get(ag_u)
            )

        if sync_info and sync_info.get('count', 0) > 0:
            count = sync_info['count']
            avail = sync_info.get('avail', 0)
            lock = sync_info.get('lock', 0)
            sold = sync_info.get('sold', 0)
            status_text = "Đang hoạt động"
            desc_text = f"Đã đồng bộ {count} căn ({avail} còn hàng, {lock} lock, {sold} đã bán)."
        elif diag_info:
            root_cause = diag_info.get('root_cause', 'UNKNOWN')
            detail = diag_info.get('detail', '')
            action = diag_info.get('recommended_action', '')
            count = 0

            if root_cause == 'CANNOT_DOWNLOAD_XLSX':
                status_text = "Lỗi: File Drive bị khóa tải"
                desc_text = "Đại lý chia sẻ file Excel nhưng tắt tính năng tải xuống (cannotDownloadFile). Hướng dẫn: Mở file trên Drive -> Tệp -> Lưu dưới dạng Google Trang tính, sau đó cập nhật link mới vào Master Sheet."
            elif root_cause == 'GID_NOT_FOUND':
                status_text = f"Lỗi: Không tìm thấy GID {gid}" if gid is not None else "Lỗi: Không tìm thấy GID"
                desc_text = f"Mã GID trong link không tồn tại trong file. Hướng dẫn: Mở link, chọn tab bảng hàng thực tế và cập nhật lại đúng mã gid trên URL vào Master Sheet ({detail[:80]})."
            elif root_cause == 'NOT_FOUND_404':
                status_text = "Lỗi: 404 Không tìm thấy file"
                desc_text = "File đã bị xóa hoặc chuyển vào thùng rác trên Google Drive. Cần liên hệ đại lý cung cấp link bảng hàng mới."
            elif root_cause == 'PERMISSION_DENIED_403':
                status_text = "Lỗi: 403 Chưa chia sẻ quyền"
                desc_text = "File ở chế độ Riêng tư (Restricted). Cần chia sẻ quyền Người xem cho email Service Account: sheet-sync-account@sheet-sync-ocp23.iam.gserviceaccount.com."
            elif root_cause == 'EMPTY_OR_SOLD_OUT':
                status_text = "Cảnh báo: Bảng hàng trống / Hết hàng"
                desc_text = "Bảng tính mở thành công nhưng không có căn nào còn diện tích hoặc giá. Đại lý có thể đã bán hết hàng hoặc đang ẩn giỏ hàng."
            elif root_cause == 'HEADER_NOT_DETECTED':
                status_text = "Lỗi: Không nhận diện được tiêu đề"
                desc_text = f"Bảng tính dùng cấu trúc đặc thù hoặc tên cột không khớp chuẩn (Mã căn, Diện tích, Giá bán): {detail[:80]}"
            elif root_cause == 'XML_BOMB_LIMIT':
                status_text = "Lỗi: File Excel vượt hạn mức (>100x)"
                desc_text = "File Excel có hàng triệu ô định dạng trống. Hướng dẫn: Mở trên Google Drive -> Tệp -> Lưu dưới dạng Google Trang tính."
            else:
                status_text = f"Lỗi: {root_cause}"
                desc_text = f"{detail[:100]}. Hành động: {action[:100]}"
        else:
            status_text = "Đang kiểm tra"
            desc_text = "Đang trong tiến trình quét kiểm toán tự động."
            count = 0

        rows_data.append([
            idx,
            ag_name,
            sub,
            url,
            status_text,
            desc_text,
            count,
            current_time_str
        ])

    # 4. Ghi đè dữ liệu vào tab
    range_write = f"'{DIRECTORY_TAB_NAME}'!A1:H{len(rows_data)+10}"
    # Xóa sạch vùng cũ trước khi ghi
    try:
        sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{DIRECTORY_TAB_NAME}'!A1:Z500"
        ).execute()
    except Exception as e_clear:
        logger.warning(f"Lỗi clear tab: {e_clear}")

    _execute_with_retry(
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{DIRECTORY_TAB_NAME}'!A1",
            valueInputOption='USER_ENTERED',
            body={"values": rows_data}
        )
    )

    # 5. Áp dụng định dạng chuyên nghiệp
    apply_directory_styling(sheets_service, spreadsheet_id, sheet_id, len(rows_data))
    logger.info(f"Đã cập nhật thành công {len(rows_data)-1} đại lý vào tab '{DIRECTORY_TAB_NAME}' cho dự án {project_key}")
