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
import io
import csv
import urllib.request
import unicodedata
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
    normalize_high_rise_type,
    infer_grounded_zone,
    infer_grounded_low_rise_type,
    compute_expiry_warning,
    normalize_direction,
    sanitize_and_cross_validate_prices
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
    headers = [unicodedata.normalize('NFC', str(c or '')).lower().strip() for c in header_cells]
    col_map = {}

    def find_col(regex_list):
        for rx in regex_list:
            for idx, h in enumerate(headers):
                if re.search(rx, h, re.IGNORECASE):
                    return idx
        return -1

    col_map["stt"] = find_col([r'^stt$'])
    col_map["unit_code"] = find_col([
        # Pass 1: Cột định danh chuyên biệt có độ ưu tiên cao nhất (tránh nhầm với Mã căn cũ hoặc Mã căn chỉ gồm số)
        r'^(mã\s*sản\s*phẩm|ma\s*san\s*pham|mã\s*sp|mã\s*căn\s*mới(\s*/\s*ptg)?|mã\s*chuẩn|ma\s*chuan|mã\s*thương\s*mại|ma\s*thuong\s*mai)$',
        # Pass 2: Tên căn, mã căn chuẩn
        r'^(mã\s*căn|ma\s*can|tên\s*căn|ten\s*can|ký\s*hiệu\s*căn|căn\s*số|mã\s*lô)$',
        # Pass 3: Chứa mã sản phẩm / mã chuẩn / mã thương mại
        r'(mã\s*sản\s*phẩm|ma\s*san\s*pham|mã\s*sp|mã\s*căn\s*mới|mã\s*chuẩn|mã\s*thương\s*mại)',
        # Pass 4: Chứa mã căn nhưng không chứa 'cũ'
        r'(mã\s*căn(?!.*cũ)|ma\s*can(?!.*cu)|tên\s*căn|ten\s*can|ký\s*hiệu|căn\s*hộ)',
        # Pass 5: Bất kỳ mã căn nào
        r'(mã\s*căn|ma\s*can)'
    ])
    col_map["zone"] = find_col([r'(phân\s*khu|phan\s*khu|khu|tiểu\s*khu|đường|duong)'])
    col_map["unit_type"] = find_col([r'(loại\s*hình|loai\s*hinh|loại\s*căn|loai\s*can|dòng\s*căn|dong\s*can|loại\s*ch|loại\s*căn\s*hộ|loai\s*can\s*ho)'])
    col_map["tcbg"] = find_col([r'(tcbg|tiêu\s*chuẩn\s*bàn\s*giao|bàn\s*giao)'])
    col_map["direction"] = find_col([r'^(hướng|huong|hướng\s*cửa|hướng\s*ban\s*công|hướng\s*bc)$', r'(hướng|huong)'])
    col_map["tower"] = find_col([r'^(tòa|toà|tên\s*(tòa|toà)|toa|block|mã\s*(tòa|toà))$', r'(tên\s*(tòa|toà)|tòa|toà|toa)'])
    col_map["floor"] = find_col([r'^(tầng|tang|khoảng\s*tầng)$', r'(tầng|tang)'])
    col_map["axis"] = find_col([r'(trục|mã\s*trục)'])
    col_map["land_area"] = find_col([r'(dt\s*đất|diện\s*tích\s*đất|dt\s*dat|diện\s*tích\s*lô\s*đất|dtđ)', r'^(diện\s*tích|dt)$'])
    col_map["build_area"] = find_col([r'(dtxd|dt\s*xây\s*dựng|diện\s*tích\s*xây\s*dựng|dt\s*sàn|tổng\s*dtxd)'])
    col_map["net_area"] = find_col([r'(thông\s*(thủy|thuỷ)|thong\s*thuy|dt\s*thông\s*(thủy|thuỷ)|dttt|dt\s*tt)', r'^(diện\s*tích|dt)$'])
    col_map["gross_area"] = find_col([r'(tim\s*tường|tim\s*tuong|dt\s*tim\s*tường)'])
    col_map["bedrooms"] = find_col([r'(số\s*pn|phòng\s*ngủ|so\s*phong\s*ngu)'])
    col_map["wc"] = find_col([r'(số\s*wc|wc)'])
    col_map["frontage"] = find_col([r'(mặt\s*tiền|mat\s*tien|rộng\s*mặt\s*tiền)'])
    col_map["floors"] = find_col([r'(số\s*tầng|so\s*tang|tầng\s*cao)'])
    col_map["gia_chua_vat"] = find_col([r'^(?!.*(đơn\s*giá|don\s*gia|/m2|/m²)).*(chưa\s*gồm\s*vat|chưa\s*vat|trước\s*vat|giá\s*gốc\s*chưa\s*vat|giá\s*thuần)'])
    col_map["vat_tong"] = find_col([
        r'^vat(\s*\(tổng\))?$',
        r'^tiền\s*vat$',
        r'^(?!.*(giá|tổng\s*cộng|chưa\s*gồm|gồm\s*vat)).*(\bvat\b)'
    ])
    col_map["kpbt"] = find_col([
        r'^(kpbt|kinh\s*phí\s*bảo\s*trì|kpbt\s*\(tổng\)|kinh\s*phí\s*bảo\s*trì\s*\(kpbt\))$',
        r'^(?!.*(giá|tổng\s*cộng|chưa\s*gồm|gồm\s*vat)).*(kpbt|kinh\s*phí\s*bảo\s*trì)'
    ])
    col_map["gia_full"] = find_col([
        r'^(?!.*(chưa|chua|trước|truoc|đơn\s*giá|don\s*gia|/m2|/m²)).*(gồm\s*vat|gom\s*vat|giá\s*full|tổng\s*giá|giá\s*niêm\s*yết|giá\s*bán\s*gồm|giá\s*all-in)',
        r'^(giá\s*bán|giá|tổng\s*giá)$'
    ])
    col_map["gia_vay"] = find_col([r'(giá\s*vay|vay\s*nh|htls|vay\s*70|vay\s*htls|vvnh|giá\s*vvnh)'])
    col_map["gia_tttd"] = find_col([r'(tiến\s*độ|tttđ|tttd|thanh\s*toán\s*chuẩn|giá\s*tttđ|giá\s*tttd|giá\s*tiến\s*độ)'])
    col_map["gia_tts"] = find_col([r'(thanh\s*toán\s*sớm|tts|tt\s*sớm|không\s*vay|giá\s*tts|thanh\s*toán\s*nhanh)'])
    col_map["don_gia_m2"] = find_col([r'(đơn\s*giá|don\s*gia|giá/m2|giá\s*/\s*m|tr/m2)'])
    col_map["gift"] = find_col([r'(quà\s*tặng|qua\s*tang|ưu\s*đãi|chiết\s*khấu)'])
    col_map["desc"] = find_col([r'(mô\s*tả|mo\s*ta|view|vị\s*trí)'])
    col_map["csbh"] = find_col([r'(csbh|chính\s*sách)'])
    col_map["bank"] = find_col([r'(ngân\s*hàng|ngan\s*hang|bank)'])
    col_map["note"] = find_col([r'(ghi\s*chú|ghi\s*chu|note)'])
    col_map["status"] = find_col([r'(trạng\s*thái|trang\s*thai|tình\s*trạng|check\s*bán|check\s*ban)'])
    col_map["dedicated_exclusive"] = find_col([
        r'(quỹ\s*độc\s*quyền|căn\s*độc\s*quyền|hàng\s*độc\s*quyền|quỹ\s*độc\s*quyền|độc\s*quyền|doc\s*quyen)',
        r'(\bđq\b|\bdq\b|\bqđq\b|\bdqd\b)'
    ])
    col_map["fund_group"] = find_col([r'(nhóm\s*quỹ|nhom\s*quy|loại\s*quỹ|loai\s*quy|nguồn\s*quỹ|nguon\s*quy|thuộc\s*quỹ)'])
    col_map["chi_can"] = find_col([r'(ảnh\s*chỉ\s*căn|chỉ\s*căn|mặt\s*bằng|layout|hình\s*ảnh|link\s*ảnh)'])
    col_map["ptg"] = find_col([r'(phiếu\s*tính\s*giá|ptg|bảng\s*tính|link\s*ptg|tài\s*liệu)'])
    col_map["issue_date"] = find_col([r'(ngày\s*cấp|ngay\s*cap|ngày\s*vào\s*hàng|ngày\s*cập\s*nhật)'])

    return col_map

def detect_header_row(rows: List[List[str]]) -> Optional[Tuple[int, Dict[str, int]]]:
    """Quét 35 dòng đầu để tìm dòng Header phù hợp nhất."""
    max_scan = min(len(rows), 35)
    best_row = -1
    best_score = 0

    for r in range(max_scan):
        row_str = ' | '.join([unicodedata.normalize('NFC', str(c or '')).lower() for c in rows[r]])
        score = 0
        if re.search(r'mã\s*căn|ma\s*can|tên\s*căn|ten\s*can|mã\s*sp|mã\s*sản\s*phẩm|ma\s*san\s*pham|mã\s*chuẩn|mã\s*thương\s*mại|ký\s*hiệu|căn\s*số|mã\s*lô|căn\s*hộ', row_str):
            score += 4
        if re.search(r'diện\s*tích|dien\s*tich|dt\s*đất|dtđ|dtxd|dttt|dt\s*tt|thông\s*(thủy|thuỷ)', row_str):
            score += 3
        if re.search(r'giá|gia\s*ban|tổng\s*giá|giá\s*full|giá\s*vay|giá\s*thuần|tts|tttđ', row_str):
            score += 3
        if re.search(r'phân\s*khu|loại\s*hình|loại\s*căn|loại\s*ch|dòng\s*căn|hướng|tòa|toà|tầng', row_str):
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
    agency_url: str = "",
    sub_tab: str = "",
    sheet_title: str = "",
    is_general_pool: bool = False
) -> List[Dict[str, Any]]:
    """Phân tích dữ liệu ma trận ô (values, hyperlinks, màu sắc) thành danh sách căn hộ chuẩn hóa."""
    if not grid_rows or len(grid_rows) < 2:
        return []

    is_tab_exclusive = bool(re.search(r'độc quyền|doc quyen|quỹ riêng|quy rieng|\bđq\b|\bdq\b|\bqr\b', f"{sheet_title} {sub_tab}", re.IGNORECASE))

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
        val = get_cell(row, c_idx).get('formattedValue', '')
        if isinstance(val, str):
            return unicodedata.normalize('NFC', val)
        return val

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
        # Fallback: Nếu cột mã căn bị rỗng (ví dụ đại lý gộp ô tiêu đề "Mã căn" trên 2 cột nhưng dữ liệu thực tế nằm ở cột sau):
        if not raw_unit and cm.get('unit_code', -1) != -1:
            next_col_idx = cm['unit_code'] + 1
            if next_col_idx < len(row):
                cand = get_val(row, next_col_idx).strip()
                if cand and re.search(r'\d', cand) and len(cand) >= 2:
                    raw_unit = cand
        if not raw_unit or len(raw_unit) < 2:
            continue
        if re.match(r'^(stt|mã căn|tổng|ghi chú|chú thích|đang bán|đã bán)', raw_unit, re.IGNORECASE):
            continue

        raw_zone = get_val(row, cm['zone']).strip()
        tower = get_val(row, cm['tower']).strip()
        floor = get_val(row, cm['floor']).strip()
        axis = get_val(row, cm['axis']).strip()

        # Nếu cao tầng mà raw_unit chỉ là số (VD: '02', '15') nhưng có tòa hoặc tầng:
        if not is_low_rise and re.match(r'^\d{1,3}[A-Z]?$', raw_unit) and tower:
            raw_unit = f"{tower}-{floor}-{raw_unit}" if floor else f"{tower}-{raw_unit}"

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

        resolved_zone = infer_grounded_zone(unit_code, project_key, raw_zone, sub_tab)

        if not is_low_rise:
            hr_norm = normalize_high_rise_unit_floor_axis(unit_code, tower, floor, axis)
            unit_code = hr_norm['unit_code']
            tower = hr_norm['tower']
            floor = hr_norm['floor']
            axis = hr_norm['axis']

        unit_key = unit_code

        # 1. Kiểm tra dòng bị ẩn (hiddenByUser hoặc hiddenByFilter hoặc ws.row_dimensions.hidden)
        is_row_hidden = bool(row_hidden_flags and r < len(row_hidden_flags) and row_hidden_flags[r])

        # 2. Kiểm tra màu nền của dòng (quét toàn bộ các ô trong dòng)
        row_colors = [c.get('color_type', 'neutral') for c in row if isinstance(c, dict)]
        is_red = ('red' in row_colors)
        is_yellow = ('yellow' in row_colors)

        # 3. Giá các loại để nhận diện có thông tin mở bán thực tế hay không
        gia_chua_vat = normalize_price_to_vnd(get_val(row, cm['gia_chua_vat']))
        gia_full = normalize_price_to_vnd(get_val(row, cm['gia_full']))
        gia_vay = normalize_price_to_vnd(get_val(row, cm['gia_vay']))
        gia_tttd = normalize_price_to_vnd(get_val(row, cm['gia_tttd']))
        gia_tts = normalize_price_to_vnd(get_val(row, cm['gia_tts']))
        has_valid_price = bool(gia_chua_vat or gia_full or gia_vay or gia_tttd or gia_tts)
        if not gia_full:
            gia_full = gia_tttd or gia_tts or gia_vay or gia_chua_vat

        # Phục hồi giá từ dữ liệu ô nếu bảng hàng hoàn toàn KHÔNG CÓ cột giá nào được nhận diện
        has_any_price_col = any(cm.get(k, -1) != -1 for k in ['gia_full', 'gia_chua_vat', 'gia_vay', 'gia_tttd', 'gia_tts'])
        if not has_valid_price and not has_any_price_col:
            for c_idx, cell_item in enumerate(row):
                if c_idx in (cm.get('unit_code'), cm.get('stt'), cm.get('zone'), cm.get('tower'), cm.get('floor')):
                    continue
                c_val = str(cell_item.get('formattedValue', '') if isinstance(cell_item, dict) else cell_item or '').strip()
                if re.match(r'^\d{1,3}([.,]\d{3}){2,}$', c_val):
                    p_c = normalize_price_to_vnd(c_val)
                    if p_c and p_c >= 100_000_000:
                        gia_full = p_c
                        has_valid_price = True
                        break
                if re.match(r'^\d{1,2}[.,]\d{2,3}$', c_val):
                    try:
                        f_v = float(c_val.replace(',', '.'))
                        if 0.5 <= f_v <= 150:
                            gia_full = int(f_v * 1_000_000_000)
                            has_valid_price = True
                            break
                    except (ValueError, TypeError):
                        pass

        # 4. Trạng thái căn từ văn bản nguồn
        raw_status = get_val(row, cm['status']).strip().lower()
        raw_note = get_val(row, cm['note']).strip().lower()
        combined_status = f"{raw_status} {raw_note}"
        is_sold_signal = bool(
            in_sold_section or
            any(kw in combined_status for kw in ['đã bán', 'da ban', 'sold', 'đã cọc', 'da coc', 'hết hàng', 'thu', 'thu hồi'])
        )
        is_lock_signal = bool(
            re.search(r'\block|đang lock|dang lock|giữ chỗ|giu cho', combined_status, re.IGNORECASE)
        )

        # Quy tắc xác định trạng thái theo yêu cầu:
        # - Bị bôi đỏ HOẶC dòng bị ẩn HOẶC nguồn ghi rõ đã bán -> 'Đã bán'
        # - Không có cả 'Giá chưa gồm VAT' lẫn 'Giá gồm VAT và KPBT' -> 'Đã bán'
        # - Chỉ nhận 'Đang lock' nếu nguồn ghi rõ trạng thái lock trong văn bản (KHÔNG xác định dựa trên màu ô)
        # - Không xác định được lock cụ thể -> Mặc định là 'Còn hàng'
        if is_red or is_row_hidden or is_sold_signal:
            resolved_status = 'Đã bán'
        elif not has_valid_price:
            resolved_status = 'Đã bán'
        elif is_lock_signal:
            resolved_status = 'Đang lock'
        else:
            resolved_status = 'Còn hàng'

        # Nhóm quỹ theo Quy tắc chuẩn hóa:
        # 1. Quỹ chung: nguồn Quỹ chung hoặc trạng thái Check Admin -> fund_group = 'Quỹ chung'
        # 2. Vhub: nguồn đại lý tên là Vhub -> fund_group = 'Quỹ độc quyền' (toàn quyền ưu tiên)
        # 3. Các đại lý khác: nếu xác định là độc quyền của đại lý đó -> fund_group = 'Quỹ chéo'
        is_vhub = bool(re.search(r'\bvhub\b', agency_name, re.IGNORECASE))
        is_check_admin = bool(re.search(r'check\s*admin', combined_status, re.IGNORECASE))

        if is_general_pool or bool(re.search(r'quỹ chung|quy chung|quỹ cđt|quy cdt', agency_name, re.IGNORECASE)) or is_check_admin:
            is_exclusive = False
            fund_group = 'Quỹ chung'
        elif is_vhub:
            # Nguồn Quỹ độc quyền Vhub luôn ưu tiên lấy thông tin từ nguồn được gán:
            # 100% căn trong nguồn Vhub được định danh là Quỹ độc quyền (trừ khi cell ghi rõ 'Quỹ chung' / 'QC')
            fund_col = cm.get('dedicated_exclusive', -1)
            raw_excl = get_val(row, fund_col).strip() if fund_col != -1 else ''
            if re.search(r'^(quỹ\s*chung|chung|\bqc\b)$', raw_excl, re.IGNORECASE):
                is_exclusive = False
                fund_group = 'Quỹ chung'
            else:
                is_exclusive = True
                fund_group = 'Quỹ độc quyền'
        elif is_tab_exclusive:
            # Tab đại lý có tiêu đề Độc quyền (VD: Giỏ Độc quyền, NSL_ ĐỘC QUYỀN...)
            fund_col = cm.get('dedicated_exclusive', -1)
            raw_excl = get_val(row, fund_col).strip() if fund_col != -1 else ''
            if re.search(r'^(quỹ\s*chung|chung|\bqc\b)$', raw_excl, re.IGNORECASE):
                is_exclusive = False
                fund_group = 'Quỹ chung'
            else:
                is_exclusive = True
                fund_group = 'Quỹ chéo'
        else:
            # Nguồn của Đại lý phân phối thông thường
            fund_col = cm.get('dedicated_exclusive', -1)
            if fund_col != -1:
                # Trang tính CÓ cột phân loại độc quyền chuyên biệt (Độc quyền, ĐQ...)
                raw_excl = get_val(row, fund_col).strip()
                if re.search(r'độc\s*quyền|doc\s*quyen|\b(đq|dq|qđq|qdq|dqd|qr|quỹ\s*riêng|quy\s*rieng|x|có|co|1)\b', raw_excl, re.IGNORECASE):
                    is_exclusive = True
                    fund_group = 'Quỹ chéo'
                else:
                    is_exclusive = False
                    fund_group = 'Quỹ chung'
            else:
                # Trang tính KHÔNG CÓ cột phân loại độc quyền -> 100% căn là độc quyền của đại lý
                is_exclusive = True
                fund_group = 'Quỹ chéo'

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

        # Ngày cấp hàng và tính hạn cấp (30 ngày)
        raw_issue = get_val(row, cm['issue_date']).strip()
        issue_dict = normalize_csbh_date(raw_issue)
        issue_date = issue_dict['csbh_date'] or ""
        expiry_info = compute_expiry_warning(issue_date)
        expiry_display = expiry_info["display"]

        direction = normalize_direction(get_val(row, cm['direction']).strip())
        desc = get_val(row, cm['desc']).strip()

        if is_low_rise:
            raw_tcbg = get_val(row, cm['tcbg']).strip()
            raw_type = get_val(row, cm['unit_type']).strip()

            # Kiểm tra trôi cột do khuyết cột TCBG ở các bảng phụ (như ELITE CAPITAL):
            # Khi cột TCBG chứa loại hình (LK, SL, ĐL, BT, SH) và cột Loại căn lại chứa số diện tích
            if raw_tcbg in ['LK', 'SL', 'ĐL', 'BT', 'SH'] and re.match(r'^\d+([.,]\d+)?$', raw_type):
                actual_unit_type = raw_tcbg
                actual_land_area = sanitize_single_area(raw_type, is_low_rise=True)
                actual_build_area = sanitize_single_area(get_val(row, cm['land_area']), is_low_rise=True, is_construction=True)
                raw_tcbg = ""
                raw_type = actual_unit_type
                unit_type = infer_grounded_low_rise_type(unit_code, raw_type, "")
                land_area = actual_land_area
                build_area = actual_build_area
            else:
                unit_type = infer_grounded_low_rise_type(unit_code, raw_type, raw_tcbg)
                land_area = sanitize_single_area(get_val(row, cm['land_area']), is_low_rise=True)
                build_area = sanitize_single_area(get_val(row, cm['build_area']), is_low_rise=True, is_construction=True)

            vat_tong = normalize_price_to_vnd(get_val(row, cm['vat_tong']), unit_hint='VAT_KPBT')
            kpbt = normalize_price_to_vnd(get_val(row, cm['kpbt']), unit_hint='VAT_KPBT')
            don_gia_m2 = normalize_price_to_vnd(get_val(row, cm['don_gia_m2']), unit_hint='M2')

            # Đối soát giá: Nếu giá full trùng giá chưa VAT nhưng có tiền VAT > 0 -> Giá full = Chưa VAT + VAT + KPBT
            if gia_full and gia_chua_vat and gia_full == gia_chua_vat and vat_tong:
                gia_full = gia_chua_vat + vat_tong + (kpbt or 0)

            gia_chua_vat, gia_full, don_gia_m2 = sanitize_and_cross_validate_prices(
                gia_chua_vat, gia_full, don_gia_m2
            )

            frontage = normalize_numeric_or_null(get_val(row, cm['frontage']))
            floors = normalize_numeric_or_null(get_val(row, cm['floors']), is_integer=True)

            # Loại bỏ các dòng trống không có cả diện tích lẫn giá
            has_area = bool(land_area or build_area)
            has_any_area_col = any(cm.get(k, -1) != -1 for k in ['land_area', 'build_area', 'net_area', 'gross_area'])
            if not has_area and not has_any_area_col:
                for c_idx, c_item in enumerate(row):
                    if c_idx in (cm.get('unit_code'), cm.get('stt'), cm.get('zone'), cm.get('tower'), cm.get('floor')):
                        continue
                    v_str = str(c_item.get('formattedValue', '') if isinstance(c_item, dict) else c_item or '').strip()
                    if re.match(r'^\d+([.,]\d+)?$', v_str):
                        a_cand = sanitize_single_area(v_str, is_low_rise=True)
                        if a_cand and 15 <= a_cand <= 2500:
                            land_area = a_cand
                            has_area = True
                            break
            if not has_area and not has_valid_price:
                continue

            clean_agency = agency_name.strip()
            agency_cell_val = f'=HYPERLINK("{agency_url}"; "{clean_agency}")' if agency_url else clean_agency

            # Khớp chính xác 39 cột chuẩn Thấp tầng (thêm cột 39 Hạn cấp hàng)
            row_values = [
                0, resolved_zone, unit_code, raw_tcbg, unit_type, land_area, build_area,
                gia_chua_vat, vat_tong, kpbt, gia_full,
                '', '', '', '',  # Xây trc VAT, VAT, KPBT, Tổng Xây
                '', '', '', '',  # Đất trc VAT, VAT, KPBT, Tổng Đất
                don_gia_m2, gia_vay, gia_tttd, gia_tts,
                direction, frontage, floors, gift, desc, csbh_dict['csbh_date'],
                bank, note, resolved_status, fund_group,
                media['anh_chi_can'], media['anh_ptg'], media['anh_chi_can_ptg'],
                agency_cell_val, issue_date, expiry_display
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
            has_any_area_col = any(cm.get(k, -1) != -1 for k in ['land_area', 'build_area', 'net_area', 'gross_area'])
            if not has_area and not has_any_area_col:
                for c_idx, c_item in enumerate(row):
                    if c_idx in (cm.get('unit_code'), cm.get('stt'), cm.get('zone'), cm.get('tower'), cm.get('floor')):
                        continue
                    v_str = str(c_item.get('formattedValue', '') if isinstance(c_item, dict) else c_item or '').strip()
                    if re.match(r'^\d+([.,]\d+)?$', v_str):
                        a_cand = sanitize_single_area(v_str, is_low_rise=False)
                        if a_cand and 15 <= a_cand <= 400:
                            net_area = a_cand
                            has_area = True
                            break
            if not has_area and not has_valid_price:
                continue

            clean_agency = agency_name.strip()
            agency_cell_val = f'=HYPERLINK("{agency_url}"; "{clean_agency}")' if agency_url else clean_agency

            if net_area and gross_area and net_area > gross_area:
                net_area, gross_area = gross_area, net_area

            # Đối soát giá cao tầng: nếu giá full trùng giá chưa VAT nhưng có KPBT
            if gia_full and gia_chua_vat and gia_full == gia_chua_vat and kpbt:
                gia_full = gia_chua_vat + kpbt

            gia_chua_vat, gia_full, don_gia_m2 = sanitize_and_cross_validate_prices(
                gia_chua_vat, gia_full, don_gia_m2
            )

            # Khớp chính xác 32 cột chuẩn Cao tầng (thêm cột 32 Hạn cấp hàng)
            row_values = [
                0, unit_code, resolved_zone, unit_type, direction, tower, floor, axis,
                net_area, gross_area, bedrooms, wc,
                kpbt, gia_chua_vat, gia_full,
                gia_vay, gia_tttd, gia_tts, don_gia_m2,
                raw_tcbg, gift, desc, csbh_dict['csbh_date'], bank,
                media['anh_chi_can'], media['anh_ptg'],
                note, resolved_status, fund_group,
                agency_cell_val, issue_date, expiry_display
            ]

        scanned_units.append({
            "unit_key": unit_key,
            "agency_name": clean_agency,
            "agency_url": agency_url,
            "is_exclusive": is_exclusive,
            "is_vhub": is_vhub,
            "status": resolved_status,
            "issue_date": issue_date,
            "expiry_status": expiry_info["status"],
            "days_elapsed": expiry_info["days_elapsed"],
            "row_values": row_values
        })

    return scanned_units

def fetch_agency_via_gviz_csv(
    file_id: str,
    target_gid: Optional[Any],
    agency_name: str,
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str,
    agency_url: str = "",
    sub_tab: str = "",
    is_general_pool: bool = False
) -> List[Dict[str, Any]]:
    """
    Tải và phân tích bảng hàng đại lý qua Google Visualization API (CSV endpoint).
    Bypass triệt để lỗi 403 cannotDownloadFile khi chủ sở hữu khóa tải binary xlsx
    hoặc khi mã GID không trích xuất được từ metadata openpyxl.
    """
    gid_str = str(target_gid) if target_gid is not None else '0'
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&gid={gid_str}"
    logger.info(f"Đang tải qua GViz CSV endpoint: {agency_name} (file: {file_id}, gid: {gid_str})")

    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"Lỗi khi tải GViz CSV cho {agency_name} ({file_id}): {e}")
        return []

    if not content or '<html' in content.lower():
        logger.warning(f"GViz CSV trả về HTML/Lỗi cho {agency_name} ({file_id})")
        return []

    reader = csv.reader(io.StringIO(content))
    csv_rows = list(reader)
    if not csv_rows or len(csv_rows) < 2:
        return []

    grid_rows = []
    for r in csv_rows:
        grid_row = []
        for cell_val in r:
            val_clean = unicodedata.normalize('NFC', str(cell_val or '')).strip()
            grid_row.append({
                'formattedValue': val_clean,
                'hyperlink': val_clean if val_clean.startswith('http') else '',
                'color_type': 'neutral'
            })
        grid_rows.append(grid_row)

    return parse_agency_grid_data(
        grid_rows,
        agency_name=agency_name,
        project_key=project_key,
        is_low_rise=is_low_rise,
        existing_pool_keys=existing_pool_keys,
        today_str=today_str,
        row_hidden_flags=None,
        agency_url=agency_url,
        sub_tab=sub_tab,
        sheet_title="",
        is_general_pool=is_general_pool
    )

def fetch_agency_from_drive_xlsx(
    file_id: str,
    target_gid: Optional[int],
    agency_name: str,
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str,
    sheets_service: Any = None,
    agency_url: str = "",
    sub_tab: str = "",
    is_general_pool: bool = False
) -> List[Dict[str, Any]]:
    """Tải và phân tích bảng hàng đại lý dạng file Excel (.xlsx) lưu trên Google Drive."""
    fh = None
    wb = None
    try:
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
                logger.info(f"Không tìm thấy sheet tương ứng GID {target_gid} trong metadata xlsx {agency_name} ({file_id}). Thử fallback GViz CSV.")
                csv_res = fetch_agency_via_gviz_csv(
                    file_id=file_id,
                    target_gid=target_gid,
                    agency_name=agency_name,
                    project_key=project_key,
                    is_low_rise=is_low_rise,
                    existing_pool_keys=existing_pool_keys,
                    today_str=today_str,
                    agency_url=agency_url,
                    sub_tab=sub_tab,
                    is_general_pool=is_general_pool
                )
                if csv_res:
                    return csv_res
                logger.info(f"GViz CSV không có dữ liệu cho {agency_name}. Quét các tab hiển thị trong workbook đã tải.")
                sheets_to_scan = [
                    ws for ws in wb.worksheets
                    if getattr(ws, 'sheet_state', 'visible') == 'visible' and not skip_rx.search(ws.title)
                ]
        else:
            if sub_tab:
                # 1. Ưu tiên tìm tab khớp chính xác tên sub_tab được chỉ định
                exact_sheets = [
                    ws for ws in wb.worksheets
                    if ws.title.strip().lower() == sub_tab.strip().lower()
                ]
                if exact_sheets:
                    sheets_to_scan = exact_sheets
                else:
                    # 2. Tìm tab khớp regex sub_tab không thuộc danh sách tab rác
                    regex_sheets = [
                        ws for ws in wb.worksheets
                        if re.search(re.escape(sub_tab), ws.title, re.IGNORECASE) and not skip_rx.search(ws.title)
                    ]
                    if regex_sheets:
                        sheets_to_scan = regex_sheets

            if not sheets_to_scan:
                # 3. Ưu tiên tab có tên 'Bảng hàng' hoặc 'Bảng hàng chuẩn hóa' nếu có
                primary_sheets = [
                    ws for ws in wb.worksheets
                    if ws.title.strip().lower() in ['bảng hàng', 'bang hang', 'bảng hàng chuẩn hóa', 'bang hang chuan hoa']
                ]
                if primary_sheets:
                    sheets_to_scan = primary_sheets
                else:
                    sheets_to_scan = [
                        ws for ws in wb.worksheets
                        if getattr(ws, 'sheet_state', 'visible') == 'visible' and not skip_rx.search(ws.title)
                    ]

        all_units = []
        for ws in sheets_to_scan:
            # Bỏ qua các tab bị ẩn (sheet hidden/veryHidden) nếu không chỉ định GID hoặc không khớp sub_tab
            if getattr(ws, 'sheet_state', 'visible') != 'visible' and target_gid is None and not (sub_tab and re.search(re.escape(sub_tab), ws.title, re.IGNORECASE)):
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
                agency_url=agency_url,
                sub_tab=sub_tab,
                sheet_title=ws.title,
                is_general_pool=is_general_pool
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
                agency_url=agency_url,
                sub_tab=sub_tab,
                is_general_pool=is_general_pool
            )
        # Thử fallback qua GViz CSV nếu lỗi download, 403, amplification hoặc lỗi openpyxl không đọc được workbook
        logger.info(f"Drive download/xlsx đọc bị lỗi ({err_msg}). Fallback sang GViz CSV cho {agency_name} ({file_id})")
        return fetch_agency_via_gviz_csv(
            file_id=file_id,
            target_gid=target_gid,
            agency_name=agency_name,
            project_key=project_key,
            is_low_rise=is_low_rise,
            existing_pool_keys=existing_pool_keys,
            today_str=today_str,
            agency_url=agency_url,
            sub_tab=sub_tab,
            is_general_pool=is_general_pool
        )
    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass
            del wb
        if fh is not None:
            try:
                fh.close()
            except Exception:
                pass
            del fh

def fetch_agency_from_google_sheet(
    sheets_service: Any,
    file_id: str,
    target_gid: Optional[int],
    agency_name: str,
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str,
    agency_url: str = "",
    sub_tab: str = "",
    is_general_pool: bool = False
) -> List[Dict[str, Any]]:
    """Tải và phân tích bảng hàng đại lý dạng Google Sheets bản địa."""
    service = _get_thread_sheets_service(sheets_service)
    chosen_sheet_title = None
    chosen_sheet_gid = target_gid
    try:
        # Lấy metadata danh sách sheet để tìm sheetId phù hợp
        meta = _execute_with_retry(service.spreadsheets().get(spreadsheetId=file_id))
        sheets = meta.get('sheets', [])

        if target_gid is not None:
            for sh in sheets:
                if sh['properties']['sheetId'] == target_gid:
                    if not sh['properties'].get('hidden', False):
                        chosen_sheet_title = sh['properties']['title']
                        chosen_sheet_gid = sh['properties']['sheetId']
                    else:
                        logger.info(f"Tab GID {target_gid} trong {agency_name} ({file_id}) bị ẩn. Sẽ tìm tab khả dụng khác không bị ẩn.")
                    break

        skip_rx = re.compile(NON_INVENTORY_TAB_REGEX, re.IGNORECASE)

        if not chosen_sheet_title:
            # 1. Tìm tab hiển thị khớp sub_tab nếu có
            if sub_tab:
                for sh in sheets:
                    if not sh['properties'].get('hidden', False):
                        t = sh['properties']['title'].strip()
                        if not skip_rx.search(t) and re.search(re.escape(sub_tab), t, re.IGNORECASE):
                            chosen_sheet_title = sh['properties']['title']
                            chosen_sheet_gid = sh['properties']['sheetId']
                            break

            # 2. Tìm tab hiển thị có từ khóa bảng hàng / căn
            if not chosen_sheet_title:
                for sh in sheets:
                    if not sh['properties'].get('hidden', False):
                        t = sh['properties']['title'].strip()
                        if not skip_rx.search(t) and re.search(r'bảng\s*hàng|bang\s*hang|\bbh\b|quỹ|quy|căn|can|giỏ\s*hàng|gio\s*hang|bán|ban|qđq|độc\s*quyền', t, re.IGNORECASE):
                            chosen_sheet_title = sh['properties']['title']
                            chosen_sheet_gid = sh['properties']['sheetId']
                            break

            # 3. Tab hiển thị bất kỳ không thuộc NON_INVENTORY_TAB_REGEX
            if not chosen_sheet_title:
                for sh in sheets:
                    if not sh['properties'].get('hidden', False):
                        t = sh['properties']['title'].strip()
                        if not skip_rx.search(t):
                            chosen_sheet_title = sh['properties']['title']
                            chosen_sheet_gid = sh['properties']['sheetId']
                            break

            if not chosen_sheet_title:
                if target_gid is not None:
                    logger.info(f"Không tìm thấy tab hiển thị phù hợp trong Sheets API cho {agency_name} ({file_id}). Thử fallback GViz CSV.")
                    return fetch_agency_via_gviz_csv(
                        file_id=file_id,
                        target_gid=target_gid,
                        agency_name=agency_name,
                        project_key=project_key,
                        is_low_rise=is_low_rise,
                        existing_pool_keys=existing_pool_keys,
                        today_str=today_str,
                        agency_url=agency_url,
                        sub_tab=sub_tab,
                        is_general_pool=is_general_pool
                    )
                chosen_sheet_title = sheets[0]['properties']['title']
                chosen_sheet_gid = sheets[0]['properties']['sheetId']

        # Đọc dữ liệu ma trận ô (values + hyperlinks + backgroundColor) và rowMetadata
        try:
            grid_resp = _execute_with_retry(
                service.spreadsheets().get(
                    spreadsheetId=file_id,
                    ranges=[f"'{chosen_sheet_title}'!A1:AZ2000"],
                    fields="sheets(data(rowData(values(formattedValue,hyperlink,effectiveFormat.backgroundColor,userEnteredFormat.backgroundColor)),rowMetadata(hiddenByUser)),properties(title,sheetId))"
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
                # Chỉ coi là dòng bị ẩn khi chủ sở hữu cố tình ẩn hàng (hiddenByUser),
                # không tính ẩn do bộ lọc tạm thời của người xem (hiddenByFilter)
                is_h = bool(r_meta.get('hiddenByUser'))
                row_hidden_flags.append(is_h)

                cells = r_data.get('values', [])
                parsed_cells = []
                for c in cells:
                    val = c.get('formattedValue', '')
                    link = c.get('hyperlink', '')
                    bg = c.get('effectiveFormat', {}).get('backgroundColor') or c.get('userEnteredFormat', {}).get('backgroundColor')
                    if not bg:
                        color_type = 'neutral'
                    else:
                        r_c = float(bg.get('red', 0.0))
                        g_c = float(bg.get('green', 0.0))
                        b_c = float(bg.get('blue', 0.0))
                        color_type = classify_rgb_color(r_c, g_c, b_c)
                    parsed_cells.append({
                        'formattedValue': val,
                        'hyperlink': link,
                        'color_type': color_type
                    })
                parsed_rows.append(parsed_cells)
        except Exception as e_grid:
            err_grid_str = str(e_grid)
            # Nếu gặp lỗi Amplification ratio limit / 403 / zipbomb khi đọc format diện rộng:
            # Fallback đọc dữ liệu thuần qua values().get trước, sau đó chỉ truy vấn format trong phạm vi dòng thực tế
            if any(kw in err_grid_str.lower() for kw in ["amplification", "ratio", "limit", "zipbomb"]):
                logger.info(f"Sheets API get() vượt ngưỡng amplification ({err_grid_str}). Tự động chuyển sang chế độ values.get + targeted format cho {agency_name} ({file_id})")
                val_resp = _execute_with_retry(
                    service.spreadsheets().values().get(
                        spreadsheetId=file_id,
                        range=f"'{chosen_sheet_title}'!A1:AZ2000"
                    )
                )
                raw_values = val_resp.get('values', [])
                actual_num_rows = len(raw_values)
                max_fetch_row = max(actual_num_rows + 5, 20)

                color_lookup = {}
                row_hidden_flags = [False] * actual_num_rows
                try:
                    format_resp = _execute_with_retry(
                        service.spreadsheets().get(
                            spreadsheetId=file_id,
                            ranges=[f"'{chosen_sheet_title}'!A1:AZ{max_fetch_row}"],
                            fields="sheets(data(rowData(values(userEnteredFormat.backgroundColor)),rowMetadata(hiddenByUser)),properties(sheetId,title))"
                        )
                    )
                    f_sheet = format_resp.get('sheets', [{}])[0]
                    f_data = f_sheet.get('data', [{}])[0]
                    f_row_data = f_data.get('rowData', [])
                    f_row_meta = f_data.get('rowMetadata', [])

                    for r_idx, r_m in enumerate(f_row_meta):
                        if r_idx < actual_num_rows:
                            row_hidden_flags[r_idx] = bool(r_m.get('hiddenByUser'))

                    for r_idx, r_d in enumerate(f_row_data):
                        for c_idx, c_d in enumerate(r_d.get('values', [])):
                            bg = c_d.get('userEnteredFormat', {}).get('backgroundColor')
                            if bg:
                                color_lookup[(r_idx, c_idx)] = classify_rgb_color(
                                    float(bg.get('red', 0.0)),
                                    float(bg.get('green', 0.0)),
                                    float(bg.get('blue', 0.0))
                                )
                except Exception as e_fmt:
                    logger.debug(f"Không thể lấy format rút gọn cho {agency_name}: {e_fmt}")

                parsed_rows = []
                for r_idx, r_vals in enumerate(raw_values):
                    cells = []
                    for c_idx, val in enumerate(r_vals):
                        val_clean = str(val or '').strip()
                        c_type = color_lookup.get((r_idx, c_idx), 'neutral')
                        cells.append({
                            'formattedValue': val_clean,
                            'hyperlink': val_clean if val_clean.startswith('http') else '',
                            'color_type': c_type
                        })
                    parsed_rows.append(cells)
            else:
                raise e_grid

        return parse_agency_grid_data(
            parsed_rows,
            agency_name=agency_name,
            project_key=project_key,
            is_low_rise=is_low_rise,
            existing_pool_keys=existing_pool_keys,
            today_str=today_str,
            row_hidden_flags=row_hidden_flags,
            agency_url=agency_url,
            sub_tab=sub_tab,
            sheet_title=chosen_sheet_title,
            is_general_pool=is_general_pool
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
                agency_url=agency_url,
                sub_tab=sub_tab,
                is_general_pool=is_general_pool
            )
        if any(kw in err_msg.lower() for kw in ["403", "permission", "cannotdownloadfile", "amplification", "ratio", "limit", "zipbomb", "unable to parse range", "parse range"]):
            logger.info(f"Sheets API bị chặn/lỗi ({err_msg}). Fallback sang GViz CSV cho {agency_name} ({file_id})")
            return fetch_agency_via_gviz_csv(
                file_id=file_id,
                target_gid=chosen_sheet_gid or target_gid,
                agency_name=agency_name,
                project_key=project_key,
                is_low_rise=is_low_rise,
                existing_pool_keys=existing_pool_keys,
                today_str=today_str,
                agency_url=agency_url,
                sub_tab=sub_tab,
                is_general_pool=is_general_pool
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

    sub_tab = agency_info.get("sub", "")
    is_general_pool = agency_info.get("is_general_pool", False) or bool(re.search(r'quỹ chung|quy chung|quỹ cđt|quy cdt', agency_name, re.IGNORECASE))
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
            agency_url=agency_url,
            sub_tab=sub_tab,
            is_general_pool=is_general_pool
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
        agency_url=agency_url,
        sub_tab=sub_tab,
        is_general_pool=is_general_pool
    )

def fetch_all_agencies_for_project(
    sheets_service: Any,
    agency_links: List[Dict[str, Any]],
    project_key: str,
    is_low_rise: bool,
    existing_pool_keys: set,
    today_str: str,
    max_workers: int = 5,
    return_link_stats: bool = False
) -> Any:
    """Tải và quét toàn bộ danh sách đại lý của 1 dự án song song đa luồng.
    Trả về (all_units, successful_agencies) hoặc kèm link_sync_stats nếu return_link_stats=True."""
    all_units = []
    successful_agencies = set()
    link_sync_stats = {}
    if not agency_links:
        if return_link_stats:
            return all_units, successful_agencies, link_sync_stats
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
            ag_name = agency.get('agency') or 'Không rõ'
            url = agency.get('url', '')
            sub = agency.get('sub', '')
            try:
                units = future.result()
                if units is not None:
                    successful_agencies.add(ag_name)
                    avail = sum(1 for u in units if u.get('status') == 'Còn hàng')
                    lock = sum(1 for u in units if u.get('status') == 'Đang lock')
                    sold = sum(1 for u in units if u.get('status') == 'Đã bán')
                    stat_obj = {
                        'count': len(units),
                        'total_units': len(units),
                        'avail': avail,
                        'lock': lock,
                        'sold': sold
                    }
                    clean_ag = ag_name.strip().upper()
                    link_sync_stats[(clean_ag, url.strip(), (sub or '').strip().upper())] = stat_obj
                    link_sync_stats[(clean_ag, url.strip())] = stat_obj
                    link_sync_stats[clean_ag] = stat_obj
                    if units:
                        all_units.extend(units)
            except Exception as e:
                logger.error(f"Ngoại lệ khi quét {ag_name}: {e}")

    if return_link_stats:
        return all_units, successful_agencies, link_sync_stats
    return all_units, successful_agencies
