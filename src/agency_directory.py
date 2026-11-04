"""
Module quản lý và cập nhật tab "Danh mục Link Đại lý" trên toàn bộ 12 dự án.
Hiển thị Dashboard KPI biến động trong ngày (Căn mới hôm nay, Chuyển Đã bán hôm nay,
Sắp hết hạn mốc 29 ngày, Tổng quỹ đang quản lý) và bảng danh mục chi tiết 11 cột.
"""

import os
import re
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

VN_TZ = timezone(timedelta(hours=7))
from src.config import TARGET_PROJECTS
from src.master_reader import get_project_agency_links, get_agency_links_from_target_sheet
from src.fetcher import _execute_with_retry
from src.merger import extract_clean_agency_name

logger = logging.getLogger(__name__)

DIRECTORY_TAB_NAME = "Danh mục Link Đại lý"

DIRECTORY_HEADERS = [
    "STT",
    "Tên Đại lý",
    "Phân khu / Tab",
    "Link bảng hàng nguồn",
    "Trạng thái kết nối",
    "Mô tả chi tiết / Hướng dẫn xử lý",
    "Căn mới hôm nay",
    "Chuyển Đã bán hôm nay",
    "Sắp hết hạn (29 ngày)",
    "Tổng số căn",
    "Thời gian kiểm tra"
]

def ensure_directory_sheet_exists(sheets_service: Any, spreadsheet_id: str) -> int:
    """Kiểm tra tab 'Danh mục Link Đại lý' đã tồn tại chưa, nếu chưa thì tạo mới. Trả về sheetId."""
    meta = _execute_with_retry(sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id))
    sheets = meta.get('sheets', [])
    for sh in sheets:
        if sh['properties']['title'] == DIRECTORY_TAB_NAME:
            return sh['properties']['sheetId']

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
                                "columnCount": 15,
                                "frozenRowCount": 5
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

def apply_directory_styling(
    sheets_service: Any,
    spreadsheet_id: str,
    sheet_id: int,
    total_rows: int
):
    """
    Định dạng giao diện Dashboard chuyên nghiệp cho tab Danh mục Link Đại lý:
    - Hàng 1-3: Banner KPI biến động trong ngày (Navy #1b365d, 4 thẻ chỉ số màu nổi bật).
    - Hàng 4: Dòng phân cách.
    - Hàng 5: Tiêu đề bảng 11 cột (đóng băng dòng 1-5).
    - Hàng 6+: Dữ liệu từng đại lý kèm định dạng có điều kiện.
    """
    requests = []

    # 1. Đóng băng 5 dòng đầu (Banner KPI + Tiêu đề bảng)
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {
                    "frozenRowCount": 5
                }
            },
            "fields": "gridProperties.frozenRowCount"
        }
    })

    # 2. Xóa các merge cũ trên 4 dòng đầu nếu có để tránh xung đột
    requests.append({
        "unmergeCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 4,
                "startColumnIndex": 0,
                "endColumnIndex": 11
            }
        }
    })

    # 3. Gộp ô (Merge) cho Banner & 4 Thẻ KPI:
    # Hàng 1: Tiêu đề Banner A1:K1 (cols 0-11)
    requests.append({
        "mergeCells": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 11},
            "mergeType": "MERGE_ALL"
        }
    })
    # Hàng 2: Nhãn KPI (Cols 0-3: Căn mới, 3-5: Chuyển bán, 5-8: Sắp hết hạn, 8-11: Tổng quỹ)
    requests.append({"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 3}, "mergeType": "MERGE_ALL"}})
    requests.append({"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 3, "endColumnIndex": 5}, "mergeType": "MERGE_ALL"}})
    requests.append({"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 5, "endColumnIndex": 8}, "mergeType": "MERGE_ALL"}})
    requests.append({"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 8, "endColumnIndex": 11}, "mergeType": "MERGE_ALL"}})

    # Hàng 3: Giá trị KPI (Cols tương ứng)
    requests.append({"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 0, "endColumnIndex": 3}, "mergeType": "MERGE_ALL"}})
    requests.append({"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 3, "endColumnIndex": 5}, "mergeType": "MERGE_ALL"}})
    requests.append({"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 5, "endColumnIndex": 8}, "mergeType": "MERGE_ALL"}})
    requests.append({"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 8, "endColumnIndex": 11}, "mergeType": "MERGE_ALL"}})

    # 4. Định dạng Hàng 1 (Banner Tiêu đề: Navy #1b365d, chữ trắng đậm 11pt)
    requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 11},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.106, "green": 0.212, "blue": 0.365},
                    "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 11},
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE"
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
        }
    })

    # 5. Định dạng Hàng 2 (Nhãn Thẻ KPI)
    kpi_formats = [
        # Card 1: Xanh lá cây (Căn mới)
        {"cols": (0, 3), "bg": {"red": 0.910, "green": 0.961, "blue": 0.914}, "fg": {"red": 0.106, "green": 0.369, "blue": 0.125}},
        # Card 2: Đỏ (Chuyển Đã bán)
        {"cols": (3, 5), "bg": {"red": 1.000, "green": 0.922, "blue": 0.933}, "fg": {"red": 0.718, "green": 0.110, "blue": 0.110}},
        # Card 3: Cam (Sắp hết hạn)
        {"cols": (5, 8), "bg": {"red": 1.000, "green": 0.953, "blue": 0.878}, "fg": {"red": 0.902, "green": 0.318, "blue": 0.000}},
        # Card 4: Xanh dương (Tổng quỹ)
        {"cols": (8, 11), "bg": {"red": 0.890, "green": 0.949, "blue": 0.992}, "fg": {"red": 0.051, "green": 0.278, "blue": 0.631}},
    ]

    for item in kpi_formats:
        c_start, c_end = item["cols"]
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": c_start, "endColumnIndex": c_end},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": item["bg"],
                        "textFormat": {"foregroundColor": item["fg"], "bold": True, "fontSize": 9},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
            }
        })
        # Hàng 3 (Giá trị Thẻ KPI: 15pt bold)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": c_start, "endColumnIndex": c_end},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": item["bg"],
                        "numberFormat": {"type": "TEXT"},
                        "textFormat": {"foregroundColor": item["fg"], "bold": True, "fontSize": 15},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,numberFormat,textFormat,horizontalAlignment,verticalAlignment)"
            }
        })

    # 6. Định dạng Hàng 5 (Tiêu đề bảng: Navy #1b365d, chữ trắng đậm 10pt)
    requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 0, "endColumnIndex": len(DIRECTORY_HEADERS)},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.106, "green": 0.212, "blue": 0.365},
                    "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10},
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                    "wrapStrategy": "WRAP"
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"
        }
    })

    # 7. Đặt chiều rộng các cột
    col_widths = [
        (0, 1, 45),   # STT
        (1, 2, 170),  # Tên ĐL
        (2, 3, 130),  # Phân khu
        (3, 4, 240),  # Link
        (4, 5, 200),  # Trạng thái
        (5, 6, 380),  # Mô tả
        (6, 7, 120),  # Căn mới hôm nay
        (7, 8, 130),  # Chuyển Đã bán hôm nay
        (8, 9, 130),  # Sắp hết hạn (29 ngày)
        (9, 10, 95),  # Tổng số căn
        (10, 11, 130) # Thời gian
    ]
    for start_c, end_c, px in col_widths:
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": start_c, "endIndex": end_c},
                "properties": {"pixelSize": px},
                "fields": "pixelSize"
            }
        })

    # 8. Định dạng số, text và căn giữa cho các cột dữ liệu (Hàng 6 trở đi)
    if total_rows > 5:
        # Cột số: STT (0), Căn mới (6), Chuyển bán (7), Hạn (8), Tổng căn (9)
        int_cols = [0, 6, 7, 8, 9]
        for c in int_cols:
            requests.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": c, "endColumnIndex": c + 1},
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {"type": "NUMBER", "pattern": "#,##0"},
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE"
                        }
                    },
                    "fields": "userEnteredFormat(numberFormat,horizontalAlignment,verticalAlignment)"
                }
            })

        # Cột Text căn giữa: Trạng thái (4)
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": 4, "endColumnIndex": 5},
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "TEXT"},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(numberFormat,horizontalAlignment,verticalAlignment)"
            }
        })

        # Cột Thời gian kiểm tra (10): định dạng dd/MM/yyyy HH:mm
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": 10, "endColumnIndex": 11},
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "DATE_TIME", "pattern": "dd/MM/yyyy HH:mm"},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(numberFormat,horizontalAlignment,verticalAlignment)"
            }
        })

        # Cột Mô tả (5) căn trái + wrap + text
        requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": 5, "endColumnIndex": 6},
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "TEXT"},
                        "horizontalAlignment": "LEFT",
                        "verticalAlignment": "MIDDLE",
                        "wrapStrategy": "WRAP"
                    }
                },
                "fields": "userEnteredFormat(numberFormat,horizontalAlignment,verticalAlignment,wrapStrategy)"
            }
        })

    # 9. Định dạng có điều kiện cho bảng dữ liệu (Hàng 6 trở đi)
    if total_rows > 5:
        # Col 4: Trạng thái kết nối
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": 4, "endColumnIndex": 5}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_CONTAINS", "values": [{"userEnteredValue": "Đang hoạt động"}]},
                        "format": {
                            "backgroundColor": {"red": 0.851, "green": 0.918, "blue": 0.827},
                            "textFormat": {"foregroundColor": {"red": 0.153, "green": 0.306, "blue": 0.075}, "bold": True}
                        }
                    }
                },
                "index": 0
            }
        })
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": 4, "endColumnIndex": 5}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_STARTS_WITH", "values": [{"userEnteredValue": "Lỗi:"}]},
                        "format": {
                            "backgroundColor": {"red": 0.957, "green": 0.800, "blue": 0.800},
                            "textFormat": {"foregroundColor": {"red": 0.600, "green": 0.000, "blue": 0.000}, "bold": True}
                        }
                    }
                },
                "index": 1
            }
        })
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": 4, "endColumnIndex": 5}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_CONTAINS", "values": [{"userEnteredValue": "Cảnh báo:"}]},
                        "format": {
                            "backgroundColor": {"red": 1.000, "green": 0.949, "blue": 0.800},
                            "textFormat": {"foregroundColor": {"red": 0.706, "green": 0.373, "blue": 0.024}, "bold": True}
                        }
                    }
                },
                "index": 2
            }
        })

        # Col 6: Căn mới hôm nay (> 0: xanh lá nhạt)
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": 6, "endColumnIndex": 7}],
                    "booleanRule": {
                        "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
                        "format": {
                            "backgroundColor": {"red": 0.910, "green": 0.961, "blue": 0.914},
                            "textFormat": {"foregroundColor": {"red": 0.106, "green": 0.369, "blue": 0.125}, "bold": True}
                        }
                    }
                },
                "index": 3
            }
        })

        # Col 7: Chuyển Đã bán hôm nay (> 0: đỏ nhạt)
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": 7, "endColumnIndex": 8}],
                    "booleanRule": {
                        "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
                        "format": {
                            "backgroundColor": {"red": 1.000, "green": 0.922, "blue": 0.933},
                            "textFormat": {"foregroundColor": {"red": 0.718, "green": 0.110, "blue": 0.110}, "bold": True}
                        }
                    }
                },
                "index": 4
            }
        })

        # Col 8: Sắp hết hạn (> 0: cam nhạt)
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": total_rows, "startColumnIndex": 8, "endColumnIndex": 9}],
                    "booleanRule": {
                        "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
                        "format": {
                            "backgroundColor": {"red": 1.000, "green": 0.953, "blue": 0.878},
                            "textFormat": {"foregroundColor": {"red": 0.902, "green": 0.318, "blue": 0.000}, "bold": True}
                        }
                    }
                },
                "index": 5
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

def compute_project_stats_from_sheet(
    sheets_service: Any,
    spreadsheet_id: str,
    cfg: Dict[str, Any],
    today_str: str
) -> Dict[str, Any]:
    """Quét dữ liệu hiện tại trên sheet đích để tổng hợp thống kê biến động ngày."""
    is_low_rise = (cfg['type'] == 'LOW_RISE')
    sub_tabs = cfg.get('sub_tabs') or ['Bảng hàng chuẩn hóa']
    agency_col_idx = 36 if is_low_rise else 29
    status_col_idx = 31 if is_low_rise else 27
    issue_date_col_idx = 37 if is_low_rise else 30
    expiry_col_idx = 38 if is_low_rise else 31

    agency_stats = {}
    project_stats = {
        "total_units": 0, "new_today": 0, "sold_today": 0,
        "expiring_soon": 0, "avail": 0, "lock": 0, "sold": 0
    }

    for tab in sub_tabs:
        try:
            r = _execute_with_retry(sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{tab}'!A1:AN15000"
            ))
            rows = r.get('values', [])
            if len(rows) < 2:
                continue

            for row in rows[1:]:
                ag_raw = row[agency_col_idx] if len(row) > agency_col_idx else ''
                clean_ag = extract_clean_agency_name(ag_raw).strip().upper()
                if not clean_ag:
                    continue

                st = row[status_col_idx] if len(row) > status_col_idx else ''
                issue_d = row[issue_date_col_idx] if len(row) > issue_date_col_idx else ''
                exp_v = row[expiry_col_idx] if len(row) > expiry_col_idx else ''

                for k in [(clean_ag, (tab or '').strip().upper()), clean_ag]:
                    if k not in agency_stats:
                        agency_stats[k] = {
                            "total_units": 0, "new_today": 0, "sold_today": 0,
                            "expiring_soon": 0, "avail": 0, "lock": 0, "sold": 0
                        }
                    agency_stats[k]["total_units"] += 1
                    if st == 'Còn hàng':
                        agency_stats[k]["avail"] += 1
                    elif st == 'Đang lock':
                        agency_stats[k]["lock"] += 1
                    elif st == 'Đã bán':
                        agency_stats[k]["sold"] += 1

                    if today_str and issue_d == today_str:
                        agency_stats[k]["new_today"] += 1
                    if st in ['Còn hàng', 'Đang lock'] and '⚠️ Sắp hết hạn' in str(exp_v):
                        agency_stats[k]["expiring_soon"] += 1

                project_stats["total_units"] += 1
                if st == 'Còn hàng':
                    project_stats["avail"] += 1
                elif st == 'Đang lock':
                    project_stats["lock"] += 1
                elif st == 'Đã bán':
                    project_stats["sold"] += 1
                if today_str and issue_d == today_str:
                    project_stats["new_today"] += 1
                if st in ['Còn hàng', 'Đang lock'] and '⚠️ Sắp hết hạn' in str(exp_v):
                    project_stats["expiring_soon"] += 1
        except Exception as e:
            logger.warning(f"Lỗi khi đọc thống kê từ tab {tab}: {e}")

    return {"agency_stats": agency_stats, "project_stats": project_stats}

def update_project_agency_directory(
    sheets_service: Any,
    project_key: str,
    diagnostic_lookup: Optional[Dict[str, Any]] = None,
    sync_stats_lookup: Optional[Dict[str, Any]] = None,
    project_daily_stats: Optional[Dict[str, Any]] = None,
    today_str: str = ""
):
    """Cập nhật tab Danh mục Link Đại lý cho 1 dự án cụ thể."""
    cfg = TARGET_PROJECTS.get(project_key)
    if not cfg:
        return

    spreadsheet_id = cfg['id']
    sub_tabs = cfg.get('sub_tabs')

    if not today_str:
        today_str = datetime.now(VN_TZ).strftime('%d/%m/%Y')

    # Nạp chẩn đoán lỗi nếu chưa có
    if not diagnostic_lookup:
        diag_path = 'C:/Users/admin/.gemini/antigravity-cli/brain/1ef59a04-6b02-45b8-b3a0-54112d70e49a/scratch/final_unmapped_cases.json'
        if os.path.exists(diag_path):
            try:
                with open(diag_path, encoding='utf-8') as f:
                    diag_list = json.load(f)
                diagnostic_lookup = {}
                for d in diag_list:
                    ag = d['agency'].strip().upper()
                    url = d['url'].strip()
                    sub = (d.get('subtab') or '').strip().upper()
                    diagnostic_lookup[(ag, url, sub)] = d
                    diagnostic_lookup[(ag, url)] = d
            except Exception:
                diagnostic_lookup = {}
        else:
            diagnostic_lookup = {}

    # 1. Ưu tiên lấy danh sách link đại lý trực tiếp từ tab 'Danh mục Link Đại lý' của dự án đích
    target_agency_links = get_agency_links_from_target_sheet(sheets_service, spreadsheet_id)
    if target_agency_links:
        agency_links = target_agency_links
    else:
        # Fallback Master Sheet nếu tab đích hoàn toàn trống
        if sub_tabs:
            agency_links = []
            for st in sub_tabs:
                agency_links.extend(get_project_agency_links(sheets_service, project_key, sub_tab=st))
        else:
            agency_links = get_project_agency_links(sheets_service, project_key)

    if not agency_links:
        logger.info(f"Không có link đại lý nào cho dự án {project_key}")
        return

    # 2. Thu thập thống kê biến động ngày nếu chưa được cung cấp
    if not project_daily_stats:
        project_daily_stats = compute_project_stats_from_sheet(sheets_service, spreadsheet_id, cfg, today_str)

    agency_stats = project_daily_stats.get("agency_stats", {})
    project_stats = project_daily_stats.get("project_stats", {})

    total_new_today = project_stats.get("new_today", 0)
    total_sold_today = project_stats.get("sold_today", 0)
    total_expiring_soon = project_stats.get("expiring_soon", 0)
    total_units = project_stats.get("total_units", 0)

    # 3. Đảm bảo tab tồn tại
    sheet_id = ensure_directory_sheet_exists(sheets_service, spreadsheet_id)

    # 4. Chuẩn bị dữ liệu bảng
    current_time_str = datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M")

    # Banner dòng 1
    kpi_row_1 = [f"TỔNG HỢP BIẾN ĐỘNG TRONG NGÀY ({today_str}) - CẬP NHẬT LÚC {current_time_str}"] + [""] * 10
    # Nhãn thẻ KPI dòng 2
    kpi_row_2 = [
        "🟢 CĂN MỚI HÔM NAY", "", "",
        "🔴 CHUYỂN ĐÃ BÁN HÔM NAY", "",
        "🟠 SẮP HẾT HẠN (MỐC 29 NGÀY)", "", "",
        "📊 TỔNG QUỸ ĐANG QUẢN LÝ", "", ""
    ]
    # Giá trị thẻ KPI dòng 3
    new_str = f"+{total_new_today}" if total_new_today > 0 else "0"
    sold_str = f"{total_sold_today}"
    exp_str = f"{total_expiring_soon}"
    units_str = f"{total_units:,} căn"
    kpi_row_3 = [
        new_str, "", "",
        sold_str, "",
        exp_str, "", "",
        units_str, "", ""
    ]
    # Dòng phân cách dòng 4
    separator_row = [""] * 11
    # Tiêu đề bảng dòng 5
    header_row = DIRECTORY_HEADERS

    rows_data = [
        kpi_row_1,
        kpi_row_2,
        kpi_row_3,
        separator_row,
        header_row
    ]

    distributor_counter = 1
    for ag in agency_links:
        ag_name = ag['agency']
        url = ag['url']
        gid = ag.get('gid')
        sub = ag.get('sub') or 'Bảng hàng'

        is_qc = bool(ag.get('is_general_pool') or re.search(r'quỹ chung|quy chung|quỹ cđt|quy cdt', ag_name, re.IGNORECASE))
        if is_qc:
            stt_str = "QC"
        else:
            stt_str = str(distributor_counter)
            distributor_counter += 1

        # Khóa tra cứu trong diagnostic_lookup
        diag_key = (ag_name.strip().upper(), url.strip(), (sub or '').strip().upper())
        diag_info = diagnostic_lookup.get(diag_key) or diagnostic_lookup.get((ag_name.strip().upper(), url.strip()))

        # Tra cứu số liệu thống kê đại lý
        clean_ag = extract_clean_agency_name(ag_name).strip().upper()
        sub_u = (sub or '').strip().upper()
        p_u = project_key.strip().upper()

        # Tra cứu thống kê trực tiếp từ kết quả quét link nguồn
        link_st = None
        if sync_stats_lookup:
            link_st = (
                sync_stats_lookup.get((ag_name.strip().upper(), url.strip(), sub_u)) or
                sync_stats_lookup.get((clean_ag, url.strip(), sub_u)) or
                sync_stats_lookup.get((ag_name.strip().upper(), url.strip())) or
                sync_stats_lookup.get((clean_ag, url.strip())) or
                sync_stats_lookup.get((p_u, sub_u, clean_ag)) or
                sync_stats_lookup.get(clean_ag) or
                sync_stats_lookup.get(ag_name.strip().upper())
            )

        # Tra cứu thống kê tổng hợp từ kho dữ liệu master pool
        ag_st = (
            agency_stats.get((clean_ag, sub_u)) or
            agency_stats.get(clean_ag) or
            agency_stats.get((p_u, sub_u, clean_ag)) or
            agency_stats.get((p_u, clean_ag))
        ) or link_st

        if is_qc:
            if not url:
                status_text = "Chờ cấu hình"
                desc_text = "Chưa gắn link nguồn. Vui lòng dán link bảng tính Quỹ chung có chứa GID vào Cột D."
                count = 0
                ag_new = 0
                ag_sold = 0
                ag_expiring = 0
            elif (link_st and (link_st.get('total_units', 0) > 0 or link_st.get('count', 0) > 0)) or (ag_st and (ag_st.get('total_units', 0) > 0 or ag_st.get('count', 0) > 0)):
                effective_st = link_st or ag_st
                count = effective_st.get('total_units') or effective_st.get('count', 0)
                avail = effective_st.get('avail', 0)
                lock = effective_st.get('lock', 0)
                sold = effective_st.get('sold', 0)
                ag_new = ag_st.get('new_today', 0) if ag_st else 0
                ag_sold = ag_st.get('sold_today', 0) if ag_st else 0
                ag_expiring = ag_st.get('expiring_soon', 0) if ag_st else 0
                status_text = "Đang hoạt động"
                desc_text = f"Đã đồng bộ {count} căn Quỹ chung ({avail} còn hàng, {lock} lock, {sold} đã bán)."
            else:
                status_text = "Đang hoạt động"
                desc_text = "Đã kết nối nguồn Quỹ chung (Các căn trong giỏ đang được đại lý phân phối độc quyền quản lý)."
                count = 0
                ag_new = 0
                ag_sold = 0
                ag_expiring = 0
        elif (link_st and (link_st.get('total_units', 0) > 0 or link_st.get('count', 0) > 0)) or (ag_st and (ag_st.get('total_units', 0) > 0 or ag_st.get('count', 0) > 0)):
            effective_st = link_st or ag_st
            count = effective_st.get('total_units') or effective_st.get('count', 0)
            avail = effective_st.get('avail', 0)
            lock = effective_st.get('lock', 0)
            sold = effective_st.get('sold', 0)
            ag_new = ag_st.get('new_today', 0) if ag_st else 0
            ag_sold = ag_st.get('sold_today', 0) if ag_st else 0
            ag_expiring = ag_st.get('expiring_soon', 0) if ag_st else 0

            status_text = "Đang hoạt động"
            desc_text = f"Đã đồng bộ {count} căn ({avail} còn hàng, {lock} lock, {sold} đã bán)."
        elif link_st is not None:
            status_text = "Cảnh báo: Bảng hàng trống / Hết hàng"
            desc_text = "Bảng tính kết nối thành công nhưng không có căn nào còn diện tích hoặc giá. Đại lý có thể đã bán hết hàng hoặc đang ẩn giỏ hàng."
            count = 0
            ag_new = 0
            ag_sold = 0
            ag_expiring = 0
        elif diag_info:
            root_cause = diag_info.get('root_cause', 'UNKNOWN')
            detail = diag_info.get('detail', '')
            action = diag_info.get('recommended_action', '')
            count = 0
            ag_new = 0
            ag_sold = 0
            ag_expiring = 0

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
            ag_new = 0
            ag_sold = 0
            ag_expiring = 0

        rows_data.append([
            stt_str,
            ag_name,
            sub,
            url,
            status_text,
            desc_text,
            ag_new,
            ag_sold,
            ag_expiring,
            count,
            current_time_str
        ])

    # 5. Xóa sạch vùng cũ trước khi ghi
    try:
        sheets_service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{DIRECTORY_TAB_NAME}'!A1:Z500"
        ).execute()
    except Exception as e_clear:
        logger.warning(f"Lỗi clear tab: {e_clear}")

    # 6. Ghi dữ liệu vào tab
    _execute_with_retry(
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{DIRECTORY_TAB_NAME}'!A1",
            valueInputOption='USER_ENTERED',
            body={"values": rows_data}
        )
    )

    # 7. Áp dụng định dạng chuyên nghiệp
    apply_directory_styling(sheets_service, spreadsheet_id, sheet_id, len(rows_data))
    logger.info(f"Đã cập nhật thành công {len(rows_data)-5} đại lý vào tab '{DIRECTORY_TAB_NAME}' cho dự án {project_key}")
