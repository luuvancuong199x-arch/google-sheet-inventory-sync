"""
Module quét và phân tích dữ liệu bảng hàng từ các đại lý song song đa luồng.
Sử dụng ThreadPoolExecutor để tăng tốc độ quét từ 40 phút xuống 60-90 giây.
"""

import re
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple

from src.normalizer import (
    sanitize_unit_code,
    normalize_high_rise_unit_floor_axis,
    sanitize_single_area,
    normalize_price_to_vnd,
    normalize_numeric_or_null,
    resolve_unit_media_links,
    normalize_csbh_date,
    normalize_low_rise_type,
    normalize_high_rise_type
)

logger = logging.getLogger(__name__)

_thread_local = threading.local()

def _execute_with_retry(request_call, max_retries=3):
    """Thực thi Google API request kèm cơ chế tự động chờ (Backoff) khi chạm quota 429."""
    for attempt in range(max_retries):
        try:
            return request_call.execute()
        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "RATE_LIMIT_EXCEEDED" in err_str) and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2 + 1
                time.sleep(wait_time)
                continue
            raise e
    return request_call.execute()

def _get_thread_sheets_service(default_service=None):
    """Mỗi thread sở hữu một instance Google Sheets API riêng biệt để tránh SSL collision."""
    if not hasattr(_thread_local, 'sheets_service'):
        from src.auth import get_sheets_service
        try:
            _thread_local.sheets_service = get_sheets_service()
        except Exception:
            _thread_local.sheets_service = default_service
    return _thread_local.sheets_service

def _get_thread_drive_service():
    """Mỗi thread sở hữu một instance Google Drive API riêng biệt."""
    if not hasattr(_thread_local, 'drive_service'):
        from src.auth import get_drive_service
        _thread_local.drive_service = get_drive_service()
    return _thread_local.drive_service

def map_columns_from_headers(header_cells: List[str]) -> Dict[str, int]:
    """Ánh xạ tên cột sang chỉ số cột 0-based."""
    headers = [str(c or '').lower().strip() for c in header_cells]
    col_map = {}

    def find_col(regex_list):
        for rx in regex_list:
            for idx, h in enumerate(headers):
                if re.search(rx, h, re.IGNORECASE):
                    return idx
        return -1

    col_map["stt"] = find_col([r'^stt$'])
    col_map["unit_code"] = find_col([r'^(mã căn|ma can|mã sp|ký hiệu căn|căn số)$', r'(mã căn|ma can|ký hiệu)'])
    col_map["zone"] = find_col([r'(phân khu|phan khu|khu|tiểu khu|đường|duong)'])
    col_map["unit_type"] = find_col([r'(loại hình|loai hinh|loại căn|loai can)'])
    col_map["tcbg"] = find_col([r'(tcbg|tiêu chuẩn bàn giao|bàn giao)'])
    col_map["direction"] = find_col([r'^(hướng|huong|hướng cửa|hướng ban công)$', r'(hướng|huong)'])
    col_map["tower"] = find_col([r'^(tòa|tên tòa|toa|block)$', r'(tên tòa|tòa)'])
    col_map["floor"] = find_col([r'^(tầng|tang)$', r'(tầng|tang)'])
    col_map["axis"] = find_col([r'(trục|mã trục)'])
    col_map["land_area"] = find_col([r'(dt đất|diện tích đất|dt dat|diện tích lô đất|dtđ)', r'^(diện tích|dt)$'])
    col_map["build_area"] = find_col([r'(dtxd|dt xây dựng|diện tích xây dựng|dt sàn)'])
    col_map["net_area"] = find_col([r'(thông thủy|thong thuy|dt thông thủy)', r'^(diện tích|dt)$'])
    col_map["gross_area"] = find_col([r'(tim tường|tim tuong|dt tim tường)'])
    col_map["bedrooms"] = find_col([r'(số pn|phòng ngủ|so phong ngu)'])
    col_map["wc"] = find_col([r'(số wc|wc)'])
    col_map["frontage"] = find_col([r'(mặt tiền|mat tien|rộng mặt tiền)'])
    col_map["floors"] = find_col([r'(số tầng|so tang|tầng cao)'])
    col_map["gia_chua_vat"] = find_col([r'(chưa gồm vat|chưa vat|trước vat|giá gốc chưa vat)'])
    col_map["vat_tong"] = find_col([
        r'^vat(\s*\(tổng\))?$',
        r'^tiền vat$',
        r'^(?!.*(giá|tổng cộng|chưa gồm|gồm vat)).*(\bvat\b)'
    ])
    col_map["kpbt"] = find_col([
        r'^(kpbt|kinh phí bảo trì|kpbt\s*\(tổng\)|kinh phí bảo trì\s*\(kpbt\))$',
        r'^(?!.*(giá|tổng cộng|chưa gồm|gồm vat)).*(kpbt|kinh phí bảo trì)'
    ])
    col_map["gia_full"] = find_col([r'(gồm vat|giá full|tổng giá|giá niêm yết|giá bán gồm vat)', r'^(giá bán|giá|tổng giá)$'])
    col_map["gia_vay"] = find_col([r'(giá vay|vay nh|htls|vay 70)'])
    col_map["gia_tttd"] = find_col([r'(tiến độ|tttđ|tttd|thanh toán chuẩn)'])
    col_map["gia_tts"] = find_col([r'(thanh toán sớm|tts|tt sớm|không vay)'])
    col_map["don_gia_m2"] = find_col([r'(đơn giá|don gia|giá/m2|giá / m)'])
    col_map["gift"] = find_col([r'(quà tặng|qua tang|ưu đãi|chiết khấu)'])
    col_map["desc"] = find_col([r'(mô tả|mo ta|view|vị trí)'])
    col_map["csbh"] = find_col([r'(csbh|chính sách)'])
    col_map["bank"] = find_col([r'(ngân hàng|ngan hang|bank)'])
    col_map["note"] = find_col([r'(ghi chú|ghi chu|note)'])
    col_map["status"] = find_col([r'(trạng thái|trang thai|tình trạng)'])
    col_map["fund_group"] = find_col([r'(nhóm quỹ|nhom quy|loại quỹ|nguồn quỹ|độc quyền|^quỹ$)'])
    col_map["chi_can"] = find_col([r'(ảnh chỉ căn|chỉ căn|mặt bằng|layout|hình ảnh|link ảnh)'])
    col_map["ptg"] = find_col([r'(phiếu tính giá|ptg|bảng tính|link ptg|tài liệu)'])
    col_map["issue_date"] = find_col([r'(ngày cấp|ngay cap|ngày vào hàng|ngày cập nhật)'])

    return col_map

def detect_header_row(rows: List[List[str]]) -> Optional[Tuple[int, Dict[str, int]]]:
    """Quét 25 dòng đầu để tìm dòng Header phù hợp nhất."""
    max_scan = min(len(rows), 25)
    best_row = -1
    best_score = 0

    for r in range(max_scan):
        row_str = ' | '.join([str(c or '').lower() for c in rows[r]])
        score = 0
        if re.search(r'mã căn|ma can|mã sp|ký hiệu|căn số', row_str):
            score += 4
        if re.search(r'diện tích|dien tich|dt đất|dtđ|dtxd', row_str):
            score += 3
        if re.search(r'giá|gia ban|tổng giá|giá full|giá vay', row_str):
            score += 3
        if re.search(r'phân khu|loại hình|hướng|tòa|tầng', row_str):
            score += 2

        if score > best_score:
            best_score = score
            best_row = r

    if best_row == -1 or best_score < 4:
        return None

    col_map = map_columns_from_headers(rows[best_row])
    return (best_row, col_map)

def parse_agency_grid_data(
    grid_rows: List[List[Dict[str, Any]]],
    agency_name: str,
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str
) -> List[Dict[str, Any]]:
    """Phân tích dữ liệu ma trận ô (values, hyperlinks) thành danh sách căn hộ chuẩn hóa."""
    if not grid_rows or len(grid_rows) < 2:
        return []

    # Chuyển grid thành bảng chuỗi để nhận diện header
    text_table = []
    for row in grid_rows:
        text_row = [cell.get('formattedValue', '') for cell in row]
        text_table.append(text_row)

    detected = detect_header_row(text_table)
    if not detected or detected[1].get('unit_code', -1) == -1:
        return []

    header_idx, col_map = detected
    cm = col_map
    scanned_units = []
    in_sold_section = False

    def get_cell(row, c_idx):
        if c_idx != -1 and c_idx < len(row):
            return row[c_idx]
        return {}

    def get_val(row, c_idx):
        return get_cell(row, c_idx).get('formattedValue', '')

    def get_url(row, c_idx):
        cell = get_cell(row, c_idx)
        return cell.get('hyperlink', '') or cell.get('formattedValue', '')

    for r in range(header_idx + 1, len(grid_rows)):
        row = grid_rows[r]
        row_str = ' '.join([c.get('formattedValue', '') for c in row]).strip()

        # Kiểm tra banner ĐÃ BÁN / ĐANG BÁN
        if re.match(r'^\s*(đã bán|da ban|căn đã bán)\s*$', row_str, re.IGNORECASE):
            in_sold_section = True
            continue
        if re.match(r'^\s*(đang bán|dang ban|còn hàng|bảng hàng)\s*$', row_str, re.IGNORECASE):
            in_sold_section = False
            continue

        raw_unit = get_val(row, cm['unit_code']).strip()
        if not raw_unit or len(raw_unit) < 2:
            continue
        if re.match(r'^(stt|mã căn|tổng|ghi chú|chú thích|đang bán|đã bán)', raw_unit, re.IGNORECASE):
            continue

        unit_code = sanitize_unit_code(raw_unit)
        if not unit_code or len(unit_code) < 2:
            continue

        # Lọc bỏ các dòng banner / tiêu đề phân mục không phải mã căn thực tế
        if not re.search(r'\d', unit_code):
            continue
        if re.search(r'^(phân\s*khu|bảng\s*hàng|đơn\s*lập|song\s*lập|liền\s*kề|biệt\s*thự|shophouse|tổng\s*cộng|căn\s*hộ|ghi\s*chú|demo|test|đlmc|dlmc|lp)$', unit_code, re.IGNORECASE):
            continue
        if re.search(r'^(phân\s*khu|bảng\s*hàng|đơn\s*lập|song\s*lập|liền\s*kề|biệt\s*thự|shophouse|tổng\s*cộng|căn\s*hộ|ghi\s*chú|demo|test|đlmc|dlmc|lp)', raw_unit, re.IGNORECASE):
            continue

        raw_zone = get_val(row, cm['zone']).strip()
        tower = get_val(row, cm['tower']).strip()
        floor = get_val(row, cm['floor']).strip()
        axis = get_val(row, cm['axis']).strip()

        if not is_low_rise:
            hr_norm = normalize_high_rise_unit_floor_axis(unit_code, tower, floor, axis)
            unit_code = hr_norm['unit_code']
            tower = hr_norm['tower']
            floor = hr_norm['floor']
            axis = hr_norm['axis']

        unit_key = unit_code

        # Trạng thái căn
        raw_status = get_val(row, cm['status']).strip().lower()
        raw_note = get_val(row, cm['note']).strip().lower()
        combined_status = f"{raw_status} {raw_note}"
        is_sold_signal = bool(
            in_sold_section or
            any(kw in combined_status for kw in ['đã bán', 'da ban', 'sold', 'đã cọc', 'da coc', 'hết hàng', 'thu', 'thu hồi'])
        )

        if unit_key in existing_pool_keys:
            resolved_status = 'Đã bán' if is_sold_signal else ('Đang lock' if 'lock' in combined_status else 'Còn hàng')
        else:
            if is_sold_signal:
                continue  # Bỏ qua căn mới đã bán từ đầu
            resolved_status = 'Đang lock' if 'lock' in combined_status else 'Còn hàng'

        # Nhóm quỹ: Độc quyền vs Quỹ chung
        raw_fund = get_val(row, cm['fund_group']).strip()
        is_exclusive = bool(re.search(r'độc quyền|doc quyen|\bđq\b|\bdq\b|\bqr\b|quỹ riêng', raw_fund, re.IGNORECASE))
        fund_group = 'Độc quyền' if is_exclusive else 'Quỹ chung'

        # CSBH
        raw_csbh = get_val(row, cm['csbh']).strip()
        csbh_dict = normalize_csbh_date(raw_csbh)

        gift = get_val(row, cm['gift']).strip()
        bank = get_val(row, cm['bank']).strip()
        note = get_val(row, cm['note']).strip()

        # Media links
        chican_link = get_url(row, cm['chi_can'])
        ptg_link = get_url(row, cm['ptg'])
        unit_link = get_url(row, cm['unit_code'])

        chican_urls = [chican_link] if chican_link.startswith('http') else []
        ptg_urls = [ptg_link] if ptg_link.startswith('http') else []
        if unit_link.startswith('http'):
            chican_urls.append(unit_link)

        media = resolve_unit_media_links(chican_urls, ptg_urls)

        # Ngày cấp hàng
        raw_issue = get_val(row, cm['issue_date']).strip()
        issue_dict = normalize_csbh_date(raw_issue)
        issue_date = issue_dict['csbh_date'] or today_str

        direction = get_val(row, cm['direction']).strip()
        desc = get_val(row, cm['desc']).strip()

        if is_low_rise:
            raw_tcbg = get_val(row, cm['tcbg']).strip()
            raw_type = get_val(row, cm['unit_type']).strip()
            unit_type = normalize_low_rise_type(raw_type, raw_tcbg)
            land_area = sanitize_single_area(get_val(row, cm['land_area']), is_low_rise=True)
            build_area = sanitize_single_area(get_val(row, cm['build_area']), is_low_rise=True, is_construction=True)

            gia_chua_vat = normalize_price_to_vnd(get_val(row, cm['gia_chua_vat']))
            vat_tong = normalize_price_to_vnd(get_val(row, cm['vat_tong']), unit_hint='VAT_KPBT')
            kpbt = normalize_price_to_vnd(get_val(row, cm['kpbt']), unit_hint='VAT_KPBT')
            gia_full = normalize_price_to_vnd(get_val(row, cm['gia_full']))
            don_gia_m2 = normalize_price_to_vnd(get_val(row, cm['don_gia_m2']), unit_hint='M2')
            gia_vay = normalize_price_to_vnd(get_val(row, cm['gia_vay']))
            gia_tttd = normalize_price_to_vnd(get_val(row, cm['gia_tttd']))
            gia_tts = normalize_price_to_vnd(get_val(row, cm['gia_tts']))

            frontage = normalize_numeric_or_null(get_val(row, cm['frontage']))
            floors = normalize_numeric_or_null(get_val(row, cm['floors']), is_integer=True)

            # Loại bỏ các dòng trống không có cả diện tích lẫn giá
            has_area = bool(land_area or build_area)
            has_price = bool(gia_full or gia_chua_vat or gia_vay or gia_tttd or gia_tts)
            if not has_area and not has_price:
                continue

            # Khớp chính xác 38 cột chuẩn Thấp tầng
            row_values = [
                0, raw_zone, unit_code, raw_tcbg, unit_type, land_area, build_area,
                gia_chua_vat, vat_tong, kpbt, gia_full,
                '', '', '', '',  # Xây trc VAT, VAT, KPBT, Tổng Xây
                '', '', '', '',  # Đất trc VAT, VAT, KPBT, Tổng Đất
                don_gia_m2, gia_vay, gia_tttd, gia_tts,
                direction, frontage, floors, gift, desc, csbh_dict['csbh_date'],
                bank, note, resolved_status, fund_group,
                media['anh_chi_can'], media['anh_ptg'], media['anh_chi_can_ptg'],
                agency_name, issue_date
            ]
        else:
            raw_type = get_val(row, cm['unit_type']).strip()
            unit_type = normalize_high_rise_type(raw_type)
            net_area = sanitize_single_area(get_val(row, cm['net_area']), is_low_rise=False)
            gross_area = sanitize_single_area(get_val(row, cm['gross_area']), is_low_rise=False)
            bedrooms = get_val(row, cm['bedrooms']).strip()
            wc = normalize_numeric_or_null(get_val(row, cm['wc']), is_integer=False)

            kpbt = normalize_price_to_vnd(get_val(row, cm['kpbt']), unit_hint='VAT_KPBT')
            gia_chua_vat = normalize_price_to_vnd(get_val(row, cm['gia_chua_vat']))
            gia_full = normalize_price_to_vnd(get_val(row, cm['gia_full']))
            gia_vay = normalize_price_to_vnd(get_val(row, cm['gia_vay']))
            gia_tttd = normalize_price_to_vnd(get_val(row, cm['gia_tttd']))
            gia_tts = normalize_price_to_vnd(get_val(row, cm['gia_tts']))
            don_gia_m2 = normalize_price_to_vnd(get_val(row, cm['don_gia_m2']), unit_hint='M2')
            raw_tcbg = get_val(row, cm['tcbg']).strip()

            # Loại bỏ các dòng trống không có cả diện tích lẫn giá
            has_area = bool(net_area or gross_area)
            has_price = bool(gia_full or gia_chua_vat or gia_vay or gia_tttd or gia_tts)
            if not has_area and not has_price:
                continue

            # Khớp chính xác 31 cột chuẩn Cao tầng
            row_values = [
                0, unit_code, raw_zone, unit_type, direction, tower, floor, axis,
                net_area, gross_area, bedrooms, wc,
                kpbt, gia_chua_vat, gia_full,
                gia_vay, gia_tttd, gia_tts, don_gia_m2,
                raw_tcbg, gift, desc, csbh_dict['csbh_date'], bank,
                media['anh_chi_can'], media['anh_ptg'],
                note, resolved_status, fund_group,
                agency_name, issue_date
            ]

        scanned_units.append({
            "unit_key": unit_key,
            "is_exclusive": is_exclusive,
            "status": resolved_status,
            "row_values": row_values
        })

    return scanned_units

def fetch_agency_from_drive_xlsx(
    file_id: str,
    target_gid: Optional[int],
    agency_name: str,
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str,
    sheets_service: Any = None
) -> List[Dict[str, Any]]:
    """Tải và phân tích bảng hàng đại lý dạng file Excel (.xlsx) lưu trên Google Drive."""
    try:
        import io
        import openpyxl
        from googleapiclient.http import MediaIoBaseDownload

        drive = _get_thread_drive_service()
        req = drive.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        wb = openpyxl.load_workbook(fh, data_only=True)

        ws = wb.active or wb.worksheets[0]
        grid_rows = []
        for r in ws.iter_rows():
            row_cells = []
            for c in r:
                val = str(c.value or '') if c.value is not None else ''
                link = c.hyperlink.target if getattr(c, 'hyperlink', None) else ''
                row_cells.append({'formattedValue': val, 'hyperlink': link})
            grid_rows.append(row_cells)

        return parse_agency_grid_data(
            grid_rows,
            agency_name=agency_name,
            project_key=project_key,
            is_low_rise=is_low_rise,
            existing_pool_keys=existing_pool_keys,
            today_str=today_str
        )
    except Exception as e:
        err_msg = str(e)
        if "fileNotDownloadable" in err_msg or "Use Export with Docs Editors" in err_msg:
            # File thực chất là Google Sheet bản địa chứ không phải binary xlsx -> đọc bằng Sheets API
            return fetch_agency_from_google_sheet(
                sheets_service=sheets_service or _get_thread_sheets_service(),
                file_id=file_id,
                target_gid=target_gid,
                agency_name=agency_name,
                project_key=project_key,
                is_low_rise=is_low_rise,
                existing_pool_keys=existing_pool_keys,
                today_str=today_str
            )
        logger.warning(f"Lỗi khi đọc bảng hàng Excel .xlsx {agency_name} ({file_id}): {e}")
        return []

def fetch_agency_from_google_sheet(
    sheets_service: Any,
    file_id: str,
    target_gid: Optional[int],
    agency_name: str,
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str
) -> List[Dict[str, Any]]:
    """Tải và phân tích bảng hàng đại lý dạng Google Sheets bản địa."""
    service = _get_thread_sheets_service(sheets_service)
    try:
        # Lấy metadata danh sách sheet để tìm sheetId phù hợp
        meta = _execute_with_retry(service.spreadsheets().get(spreadsheetId=file_id))
        sheets = meta.get('sheets', [])
        chosen_sheet_title = None

        if target_gid is not None:
            for sh in sheets:
                if sh['properties']['sheetId'] == target_gid:
                    chosen_sheet_title = sh['properties']['title']
                    break

        if not chosen_sheet_title:
            if target_gid is not None:
                # Nếu GID không tìm thấy: BỎ QUA, không quét nhầm tab đầu tiên!
                logger.warning(f"Không tìm thấy GID {target_gid} trong file {agency_name} ({file_id}). Bỏ qua link.")
                return []
            chosen_sheet_title = sheets[0]['properties']['title']

        # Đọc dữ liệu ma trận ô (values + hyperlinks) chỉ trong 1 request duy nhất!
        grid_resp = _execute_with_retry(
            service.spreadsheets().get(
                spreadsheetId=file_id,
                ranges=[f"'{chosen_sheet_title}'!A1:AZ2000"],
                fields="sheets.data.rowData.values(formattedValue,hyperlink)"
            )
        )

        grid_data = grid_resp['sheets'][0]['data'][0].get('rowData', [])
        parsed_rows = []
        for r_data in grid_data:
            cells = r_data.get('values', [])
            parsed_rows.append([
                {
                    'formattedValue': c.get('formattedValue', ''),
                    'hyperlink': c.get('hyperlink', '')
                }
                for c in cells
            ])

        return parse_agency_grid_data(
            parsed_rows,
            agency_name=agency_name,
            project_key=project_key,
            is_low_rise=is_low_rise,
            existing_pool_keys=existing_pool_keys,
            today_str=today_str
        )
    except Exception as e:
        err_msg = str(e)
        if "must not be an Office file" in err_msg or "not supported for this document" in err_msg:
            return fetch_agency_from_drive_xlsx(
                file_id=file_id,
                target_gid=target_gid,
                agency_name=agency_name,
                project_key=project_key,
                is_low_rise=is_low_rise,
                existing_pool_keys=existing_pool_keys,
                today_str=today_str,
                sheets_service=service
            )
        logger.warning(f"Lỗi khi đọc bảng hàng đại lý {agency_name} ({file_id}): {e}")
        return []

def fetch_single_agency(
    sheets_service: Any,
    agency_info: Dict[str, Any],
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str
) -> List[Dict[str, Any]]:
    """Tải và phân tích 1 đại lý đơn lẻ."""
    agency_name = agency_info.get("agency", "Không rõ")
    file_id = agency_info.get("file_id")
    target_gid = agency_info.get("gid")

    if agency_info.get("is_excel"):
        return fetch_agency_from_drive_xlsx(
            file_id=file_id,
            target_gid=target_gid,
            agency_name=agency_name,
            project_key=project_key,
            is_low_rise=is_low_rise,
            existing_pool_keys=existing_pool_keys,
            today_str=today_str,
            sheets_service=sheets_service
        )

    return fetch_agency_from_google_sheet(
        sheets_service=sheets_service,
        file_id=file_id,
        target_gid=target_gid,
        agency_name=agency_name,
        project_key=project_key,
        is_low_rise=is_low_rise,
        existing_pool_keys=existing_pool_keys,
        today_str=today_str
    )

def fetch_all_agencies_for_project(
    sheets_service: Any,
    agency_links: List[Dict[str, Any]],
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str,
    max_workers: int = 5
) -> List[Dict[str, Any]]:
    """Tải và quét toàn bộ danh sách đại lý của 1 dự án song song đa luồng."""
    all_units = []
    if not agency_links:
        return all_units

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                fetch_single_agency,
                sheets_service,
                agency,
                project_key,
                is_low_rise,
                existing_pool_keys,
                today_str
            ): agency for agency in agency_links
        }

        for future in as_completed(futures):
            agency = futures[future]
            try:
                units = future.result()
                if units:
                    all_units.extend(units)
            except Exception as e:
                logger.error(f"Ngoại lệ khi quét {agency.get('agency')}: {e}")

    return all_units
