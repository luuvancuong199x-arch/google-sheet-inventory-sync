"""
Module quét và phân tích dữ liệu bảng hàng từ các đại lý song song đa luồng.
Sử dụng ThreadPoolExecutor để tăng tốc độ quét từ 40 phút xuống 60-90 giây.
"""

import re
import time
import logging
import threading
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple

from src.config import NON_INVENTORY_TAB_REGEX
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

def _execute_with_retry(request_call, max_retries=4):
    """Thực thi Google API request kèm cơ chế tự động chờ (Backoff) khi chạm quota 429."""
    for attempt in range(max_retries):
        try:
            return request_call.execute()
        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "RATE_LIMIT_EXCEEDED" in err_str) and attempt < max_retries - 1:
                wait_time = 15 * (attempt + 1)
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

def classify_rgb_color(r: float, g: float, b: float) -> str:
    """Phân loại màu RGB (giá trị 0.0 - 1.0) thành 'red', 'yellow', hoặc 'neutral'."""
    # Trắng, xám hoặc gần đồng màu -> neutral
    if abs(r - g) < 0.05 and abs(g - b) < 0.05:
        return 'neutral'
    # Màu vàng / cam / hổ phách: cả R và G đều cao, B thấp hơn rõ rệt
    if r > 0.65 and g > 0.60 and (min(r, g) - b) >= 0.10:
        return 'yellow'
    # Màu đỏ: R vượt trội so với G và B
    if r > 0.50 and (r - max(g, b)) >= 0.10 and (r - g) >= 0.10:
        return 'red'
    return 'neutral'

def classify_hex_color(hex_str: str) -> str:
    """Phân loại màu dạng chuỗi hex (AARRGGBB hoặc RRGGBB) của openpyxl."""
    if not hex_str or not isinstance(hex_str, str):
        return 'neutral'
    s = hex_str.strip().lstrip('#')
    if len(s) == 8:
        # Bỏ qua kênh Alpha AARRGGBB
        s = s[2:]
    if len(s) != 6:
        return 'neutral'
    try:
        r = int(s[0:2], 16) / 255.0
        g = int(s[2:4], 16) / 255.0
        b = int(s[4:6], 16) / 255.0
        return classify_rgb_color(r, g, b)
    except ValueError:
        return 'neutral'

def get_openpyxl_cell_color(cell) -> str:
    """Lấy và phân loại màu nền của ô trong file openpyxl."""
    fill = getattr(cell, 'fill', None)
    if not fill or not getattr(fill, 'fill_type', None):
        return 'neutral'
    c = getattr(fill, 'start_color', None) or getattr(fill, 'fgColor', None)
    if not c:
        return 'neutral'
    rgb = getattr(c, 'rgb', None)
    if rgb and isinstance(rgb, str):
        return classify_hex_color(rgb)
    return 'neutral'

def extract_xlsx_gid_mapping(file_bytes_or_stream) -> Dict[int, str]:
    """
    Trích xuất mapping giữa Google Sheets GID và tên worksheet (sheet_name) trong file Excel (.xlsx) tải từ Google Drive.
    """
    gid_to_name = {}
    sheet_id_to_name = {}
    try:
        with zipfile.ZipFile(file_bytes_or_stream, 'r') as z:
            if 'xl/workbook.xml' in z.namelist():
                wb_xml = z.read('xl/workbook.xml').decode('utf-8', errors='ignore')
                root = ET.fromstring(wb_xml)
                for elem in root.iter():
                    if elem.tag.endswith('sheet'):
                        name = elem.attrib.get('name')
                        s_id = elem.attrib.get('sheetId')
                        if name and s_id:
                            sheet_id_to_name[str(s_id)] = name

            for n in z.namelist():
                if 'metadata' in n.lower():
                    raw = z.read(n)
                    matches = re.findall(rb'\n\x01(\d+)\x12[\n\t](\d+)', raw)
                    for s_id_b, gid_b in matches:
                        s_id = s_id_b.decode('ascii')
                        gid = int(gid_b.decode('ascii'))
                        if s_id in sheet_id_to_name:
                            gid_to_name[gid] = sheet_id_to_name[s_id]
    except Exception as e:
        logger.debug(f"Không thể trích xuất GID metadata từ xlsx: {e}")
    return gid_to_name

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
    today_str: str,
    row_hidden_flags: Optional[List[bool]] = None,
    agency_url: str = ""
) -> List[Dict[str, Any]]:
    """Phân tích dữ liệu ma trận ô (values, hyperlinks, màu sắc) thành danh sách căn hộ chuẩn hóa."""
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
        if re.search(r'^(phân\s*khu|bảng\s*hàng|đơn\s*lập|song\s*lập|liền\s*kề|biệt\s*thự|shophouse|tổng\s*cộng|căn\s*hộ|ghi\s*chú|demo|test)$', raw_unit, re.IGNORECASE):
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

        # 1. Kiểm tra dòng bị ẩn (hiddenByUser hoặc hiddenByFilter hoặc ws.row_dimensions.hidden)
        is_row_hidden = bool(row_hidden_flags and r < len(row_hidden_flags) and row_hidden_flags[r])

        # 2. Kiểm tra màu nền của dòng (quét các cột chính và các ô đầu dòng)
        row_colors = [c.get('color_type', 'neutral') for c in row[:15]]
        is_red = ('red' in row_colors)
        is_yellow = ('yellow' in row_colors)

        # 3. Giá các loại để nhận diện có thông tin mở bán thực tế hay không
        gia_chua_vat = normalize_price_to_vnd(get_val(row, cm['gia_chua_vat']))
        gia_full = normalize_price_to_vnd(get_val(row, cm['gia_full']))
        gia_vay = normalize_price_to_vnd(get_val(row, cm['gia_vay']))
        gia_tttd = normalize_price_to_vnd(get_val(row, cm['gia_tttd']))
        gia_tts = normalize_price_to_vnd(get_val(row, cm['gia_tts']))
        # Yêu cầu: Chỉ cần có một trường 'Giá chưa gồm VAT' hoặc 'Giá gồm VAT và KPBT' là đủ điều kiện giá
        has_valid_price = bool(gia_chua_vat or gia_full)

        # 4. Trạng thái căn từ văn bản nguồn
        raw_status = get_val(row, cm['status']).strip().lower()
        raw_note = get_val(row, cm['note']).strip().lower()
        combined_status = f"{raw_status} {raw_note}"
        is_sold_signal = bool(
            in_sold_section or
            any(kw in combined_status for kw in ['đã bán', 'da ban', 'sold', 'đã cọc', 'da coc', 'hết hàng', 'thu', 'thu hồi'])
        )

        # Quy tắc xác định trạng thái:
        # - Bị bôi đỏ HOẶC nguồn ghi rõ đã bán -> 'Đã bán'
        # - Không có cả 'Giá chưa gồm VAT' lẫn 'Giá gồm VAT và KPBT' -> 'Đã bán'
        # - Bị bôi vàng HOẶC nguồn ghi lock -> 'Đang lock'
        # - Đủ điều kiện giá (có Giá chưa VAT hoặc Giá full), không đỏ, không bán -> Tự động cập nhật lại là 'Còn hàng'
        if is_red or is_sold_signal:
            resolved_status = 'Đã bán'
        elif not has_valid_price:
            resolved_status = 'Đã bán'
        elif is_yellow or 'lock' in combined_status:
            resolved_status = 'Đang lock'
        else:
            resolved_status = 'Còn hàng'

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

            vat_tong = normalize_price_to_vnd(get_val(row, cm['vat_tong']), unit_hint='VAT_KPBT')
            kpbt = normalize_price_to_vnd(get_val(row, cm['kpbt']), unit_hint='VAT_KPBT')
            don_gia_m2 = normalize_price_to_vnd(get_val(row, cm['don_gia_m2']), unit_hint='M2')

            frontage = normalize_numeric_or_null(get_val(row, cm['frontage']))
            floors = normalize_numeric_or_null(get_val(row, cm['floors']), is_integer=True)

            # Loại bỏ các dòng trống không có cả diện tích lẫn giá
            has_area = bool(land_area or build_area)
            if not has_area and not has_valid_price:
                continue

            clean_agency = agency_name.strip()
            agency_cell_val = f'=HYPERLINK("{agency_url}"; "{clean_agency}")' if agency_url else clean_agency

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
                agency_cell_val, issue_date
            ]
        else:
            raw_type = get_val(row, cm['unit_type']).strip()
            unit_type = normalize_high_rise_type(raw_type)
            net_area = sanitize_single_area(get_val(row, cm['net_area']), is_low_rise=False)
            gross_area = sanitize_single_area(get_val(row, cm['gross_area']), is_low_rise=False)
            bedrooms = get_val(row, cm['bedrooms']).strip()
            wc = normalize_numeric_or_null(get_val(row, cm['wc']), is_integer=False)

            kpbt = normalize_price_to_vnd(get_val(row, cm['kpbt']), unit_hint='VAT_KPBT')
            don_gia_m2 = normalize_price_to_vnd(get_val(row, cm['don_gia_m2']), unit_hint='M2')
            raw_tcbg = get_val(row, cm['tcbg']).strip()

            # Loại bỏ các dòng trống không có cả diện tích lẫn giá
            has_area = bool(net_area or gross_area)
            if not has_area and not has_valid_price:
                continue

            clean_agency = agency_name.strip()
            agency_cell_val = f'=HYPERLINK("{agency_url}"; "{clean_agency}")' if agency_url else clean_agency

            # Khớp chính xác 31 cột chuẩn Cao tầng
            row_values = [
                0, unit_code, raw_zone, unit_type, direction, tower, floor, axis,
                net_area, gross_area, bedrooms, wc,
                kpbt, gia_chua_vat, gia_full,
                gia_vay, gia_tttd, gia_tts, don_gia_m2,
                raw_tcbg, gift, desc, csbh_dict['csbh_date'], bank,
                media['anh_chi_can'], media['anh_ptg'],
                note, resolved_status, fund_group,
                agency_cell_val, issue_date
            ]

        scanned_units.append({
            "unit_key": unit_key,
            "agency_name": clean_agency,
            "agency_url": agency_url,
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
    sheets_service: Any = None,
    agency_url: str = ""
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
        gid_to_name = extract_xlsx_gid_mapping(fh)
        fh.seek(0)
        wb = openpyxl.load_workbook(fh, data_only=True)

        skip_rx = re.compile(NON_INVENTORY_TAB_REGEX, re.IGNORECASE)

        sheets_to_scan = []
        if target_gid is not None:
            target_sheet_name = gid_to_name.get(target_gid)
            if not target_sheet_name:
                try:
                    target_sheet_name = gid_to_name.get(int(target_gid))
                except (ValueError, TypeError):
                    pass

            if target_sheet_name and target_sheet_name in wb.sheetnames:
                sheets_to_scan = [wb[target_sheet_name]]
            else:
                logger.warning(f"Không tìm thấy sheet tương ứng GID {target_gid} trong file Excel {agency_name} ({file_id}). Bỏ qua link.")
                return []
        else:
            sheets_to_scan = [
                ws for ws in wb.worksheets
                if getattr(ws, 'sheet_state', 'visible') == 'visible' and not skip_rx.search(ws.title)
            ]

        all_units = []
        for ws in sheets_to_scan:
            # Bỏ qua các tab bị ẩn (sheet hidden/veryHidden) nếu không chỉ định GID cụ thể
            if getattr(ws, 'sheet_state', 'visible') != 'visible':
                continue
            grid_rows = []
            row_hidden_flags = []
            for r_idx, r in enumerate(ws.iter_rows(), start=1):
                rd = ws.row_dimensions.get(r_idx)
                row_hidden_flags.append(bool(getattr(rd, 'hidden', False)))
                row_cells = []
                for c in r:
                    val = str(c.value or '') if c.value is not None else ''
                    link = c.hyperlink.target if getattr(c, 'hyperlink', None) else ''
                    color_type = get_openpyxl_cell_color(c)
                    row_cells.append({
                        'formattedValue': val,
                        'hyperlink': link,
                        'color_type': color_type
                    })
                grid_rows.append(row_cells)

            parsed = parse_agency_grid_data(
                grid_rows,
                agency_name=agency_name,
                project_key=project_key,
                is_low_rise=is_low_rise,
                existing_pool_keys=existing_pool_keys,
                today_str=today_str,
                row_hidden_flags=row_hidden_flags,
                agency_url=agency_url
            )
            all_units.extend(parsed)

        return all_units
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
                today_str=today_str,
                agency_url=agency_url
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
    today_str: str,
    agency_url: str = ""
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
                    # Nếu tab chỉ định bị ẩn -> bỏ qua
                    if sh['properties'].get('hidden', False):
                        logger.info(f"Tab GID {target_gid} trong {agency_name} ({file_id}) bị ẩn. Bỏ qua.")
                        return []
                    chosen_sheet_title = sh['properties']['title']
                    break

        if not chosen_sheet_title:
            if target_gid is not None:
                # Nếu GID không tìm thấy: BỎ QUA, không quét nhầm tab đầu tiên!
                logger.warning(f"Không tìm thấy GID {target_gid} trong file {agency_name} ({file_id}). Bỏ qua link.")
                return []
            for sh in sheets:
                if not sh['properties'].get('hidden', False):
                    chosen_sheet_title = sh['properties']['title']
                    break
            if not chosen_sheet_title:
                chosen_sheet_title = sheets[0]['properties']['title']

        # Đọc dữ liệu ma trận ô (values + hyperlinks + backgroundColor) và rowMetadata
        grid_resp = _execute_with_retry(
            service.spreadsheets().get(
                spreadsheetId=file_id,
                ranges=[f"'{chosen_sheet_title}'!A1:AZ2000"],
                fields="sheets(data(rowData(values(formattedValue,hyperlink,effectiveFormat.backgroundColor)),rowMetadata(hiddenByUser,hiddenByFilter)),properties(title,sheetId))"
            )
        )

        sheet_obj = grid_resp['sheets'][0]
        data_block = sheet_obj['data'][0]
        grid_data = data_block.get('rowData', [])
        row_metadata = data_block.get('rowMetadata', [])

        parsed_rows = []
        row_hidden_flags = []
        for r_idx, r_data in enumerate(grid_data):
            r_meta = row_metadata[r_idx] if r_idx < len(row_metadata) else {}
            is_h = bool(r_meta.get('hiddenByUser') or r_meta.get('hiddenByFilter'))
            row_hidden_flags.append(is_h)

            cells = r_data.get('values', [])
            parsed_cells = []
            for c in cells:
                val = c.get('formattedValue', '')
                link = c.get('hyperlink', '')
                bg = c.get('effectiveFormat', {}).get('backgroundColor', {})
                r_c = bg.get('red', 1.0)
                g_c = bg.get('green', 1.0)
                b_c = bg.get('blue', 1.0)
                color_type = classify_rgb_color(r_c, g_c, b_c)
                parsed_cells.append({
                    'formattedValue': val,
                    'hyperlink': link,
                    'color_type': color_type
                })
            parsed_rows.append(parsed_cells)

        return parse_agency_grid_data(
            parsed_rows,
            agency_name=agency_name,
            project_key=project_key,
            is_low_rise=is_low_rise,
            existing_pool_keys=existing_pool_keys,
            today_str=today_str,
            row_hidden_flags=row_hidden_flags,
            agency_url=agency_url
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
                sheets_service=service,
                agency_url=agency_url
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
    agency_url = agency_info.get("url", "")
    if file_id:
        if target_gid is not None:
            agency_url = f"https://docs.google.com/spreadsheets/d/{file_id}/edit#gid={target_gid}"
        elif not agency_url:
            agency_url = f"https://docs.google.com/spreadsheets/d/{file_id}/edit"

    if agency_info.get("is_excel"):
        return fetch_agency_from_drive_xlsx(
            file_id=file_id,
            target_gid=target_gid,
            agency_name=agency_name,
            project_key=project_key,
            is_low_rise=is_low_rise,
            existing_pool_keys=existing_pool_keys,
            today_str=today_str,
            sheets_service=sheets_service,
            agency_url=agency_url
        )

    return fetch_agency_from_google_sheet(
        sheets_service=sheets_service,
        file_id=file_id,
        target_gid=target_gid,
        agency_name=agency_name,
        project_key=project_key,
        is_low_rise=is_low_rise,
        existing_pool_keys=existing_pool_keys,
        today_str=today_str,
        agency_url=agency_url
    )

def fetch_all_agencies_for_project(
    sheets_service: Any,
    agency_links: List[Dict[str, Any]],
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str,
    max_workers: int = 5
) -> Tuple[List[Dict[str, Any]], set]:
    """Tải và quét toàn bộ danh sách đại lý của 1 dự án song song đa luồng.
    Trả về (all_units, successful_agencies) để phục vụ Smart Upsert chính xác."""
    all_units = []
    successful_agencies = set()
    if not agency_links:
        return all_units, successful_agencies

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
            ag_name = agency.get('agency')
            try:
                units = future.result()
                if units is not None:
                    successful_agencies.add(ag_name)
                    if units:
                        all_units.extend(units)
            except Exception as e:
                logger.error(f"Ngoại lệ khi quét {ag_name}: {e}")

    return all_units, successful_agencies
