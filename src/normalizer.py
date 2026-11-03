"""
Module chuẩn hóa dữ liệu toàn diện cho bảng hàng 12 dự án bất động sản.
Khắc phục triệt để các lỗi logic của hệ thống cũ:
1. Không áp dụng bảng né tầng phong thủy vào trục căn (Axis).
2. Bảo toàn số phòng vệ sinh (WC) thập phân (2.5 WC).
3. Bảo toàn 100% liên kết thư mục Google Drive (Folder/OpenID).
4. Phân biệt chính xác đơn vị Tỷ và Triệu, không xóa giá < 1.5 tỷ.
5. Kiểm định ngày tháng thực tế bằng datetime.date (chặn 31/02).
"""

import re
from datetime import date
from typing import Dict, Any, List, Optional, Tuple
from src.config import DEFAULT_POLICY_YEAR

# Bảng quy đổi tầng phong thủy (CHỈ ÁP DỤNG CHO TẦNG, TUYỆT ĐỐI KHÔNG ÁP DỤNG CHO TRỤC CĂN)
FLOOR_COMMERCIAL_MAP = {
    '1': '01', '01': '01',
    '2': '02', '02': '02',
    '3': '03', '03': '03',
    '4': '05A', '04': '05A', '5A': '05A', '05A': '05A', '3A': '03A', '03A': '03A',
    '5': '05', '05': '05',
    '6': '06', '06': '06', '6A': '06A', '06A': '06A',
    '7': '08A', '07': '08A', '8A': '08A', '08A': '08A',
    '8': '08', '08': '08',
    '9': '09', '09': '09',
    '10': '10',
    '11': '11',
    '12': '12',
    '13': '12A', '12A': '12A',
    '14': '15A', '15A': '15A',
    '15': '15',
    '16': '16',
    '17': '17',
    '18': '18'
}

def to_commercial_floor_code(raw_token: Any) -> str:
    """Chuẩn hóa mã tầng thương mại theo phong thủy."""
    if raw_token is None:
        return ''
    s = str(raw_token).strip().upper()
    s = re.sub(r'^(TẦNG|TANG|SỐ|SO)\s*', '', s, flags=re.IGNORECASE).strip()
    if not s:
        return ''
    if s in FLOOR_COMMERCIAL_MAP:
        return FLOOR_COMMERCIAL_MAP[s]
    if re.match(r'^\d[A-Z]$', s):
        return '0' + s
    if re.match(r'^\d$', s):
        padded = '0' + s
        return FLOOR_COMMERCIAL_MAP.get(padded, padded)
    return s

def to_axis_code(raw_token: Any) -> str:
    """
    Chuẩn hóa mã trục căn (Axis) trên mặt bằng tầng.
    TUYỆT ĐỐI không áp dụng bảng né tầng phong thủy vào trục căn!
    Trục 4 giữ nguyên là 04, trục 7 giữ nguyên là 07, trục 13 giữ nguyên là 13.
    """
    if raw_token is None:
        return ''
    s = str(raw_token).strip().upper()
    s = re.sub(r'^(TRỤC|TRUC|CĂN|CAN|SỐ|SO)\s*', '', s, flags=re.IGNORECASE).strip()
    if not s:
        return ''
    if re.match(r'^\d$', s):
        return '0' + s
    if re.match(r'^\d[A-Z]$', s):
        return '0' + s
    return s

def sanitize_unit_code(raw_code: Any) -> str:
    """Làm sạch mã căn, loại bỏ emoji, ký tự trang trí, ghi chú trong ngoặc."""
    if not raw_code:
        return ''
    s = str(raw_code).strip().upper()
    # Loại bỏ emoji và sao
    s = re.sub(r'[✨🔥💥💎⭐🌟⚡📌📍🎯🏷️✅❌⚠️\*]+', '', s)
    # Loại bỏ tiền tố mã căn: hoặc cắt phần trước dấu hai chấm nếu dấu hai chấm chứa chữ ghi chú
    if ':' in s:
        parts = s.split(':', 1)
        if any(kw in parts[0] for kw in ['MÃ', 'CĂN', 'BT', 'LK', 'SH', 'CH']):
            s = parts[0].strip() if len(parts[0].strip()) >= 3 else parts[1].strip()
        else:
            s = parts[0].strip()
    # Cắt bỏ phần mở ngoặc đơn (Góc, Xẻ khe...)
    s = s.split('(')[0].strip()
    # Cắt bỏ từ khóa đuôi góc/xẻ khe
    s = re.sub(r'\s+(GÓC|GOC|XẺ KHE|XE KHE|THƯỜNG|THUONG)$', '', s, flags=re.IGNORECASE).strip()
    # Xóa khoảng trắng thừa và ký tự nối đầu/cuối
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'^[-._]+|[-._]+$', '', s)
    return s

def normalize_high_rise_unit_floor_axis(
    raw_unit_code: Any,
    raw_tower: Any = '',
    raw_floor: Any = '',
    raw_axis: Any = ''
) -> Dict[str, str]:
    """
    Chuẩn hóa bộ 4 thông số cao tầng: Tên tòa, Tầng, Mã trục, Mã căn.
    """
    unit = str(raw_unit_code or '').strip().upper().replace(' ', '')
    tower = str(raw_tower or '').strip().upper()
    floor = to_commercial_floor_code(raw_floor)
    axis = to_axis_code(raw_axis)

    # 1. Dạng dấu gạch ngang: 'A1-29-05', 'M1-10-04'
    hyphen_parts = unit.split('-')
    if len(hyphen_parts) >= 3:
        raw_ax_part = hyphen_parts[-1]
        raw_fl_part = hyphen_parts[-2]
        raw_tw_part = '-'.join(hyphen_parts[:-2])
        norm_fl = to_commercial_floor_code(raw_fl_part)
        norm_ax = to_axis_code(raw_ax_part)
        if not tower:
            tower = raw_tw_part
        if not floor:
            floor = norm_fl
        if not axis:
            axis = norm_ax
        unit = f"{raw_tw_part}-{norm_fl}-{norm_ax}"
        return {"unit_code": unit, "tower": tower, "floor": floor, "axis": axis}

    # 2. Dạng 2 dấu chấm ở Q9: 'S6.0619.06' -> Tòa S6.06, Tầng 19, Trục 06
    two_dot = re.match(r'^([A-Z]\d{1,2}\.\d{2})(\d{2}[A-Z]?)\.(\d{2}[A-Z]?)$', unit)
    if two_dot:
        tw = two_dot.group(1)
        norm_fl = to_commercial_floor_code(two_dot.group(2))
        norm_ax = to_axis_code(two_dot.group(3))
        if not tower:
            tower = tw
        if not floor:
            floor = norm_fl
        if not axis:
            axis = norm_ax
        unit = f"{tw}.{norm_fl}.{norm_ax}"
        return {"unit_code": unit, "tower": tower, "floor": floor, "axis": axis}

    # 3. Dạng TòaTầng.Trục ở Q9: 'BE130.04', 'BS1114.15'
    tower_floor_dot = re.match(r'^([A-Z]{2,3}\d{1,2})(\d{2}[A-Z]?)\.(\d{2}[A-Z]?)$', unit)
    if tower_floor_dot:
        tw = tower_floor_dot.group(1)
        norm_fl = to_commercial_floor_code(tower_floor_dot.group(2))
        norm_ax = to_axis_code(tower_floor_dot.group(3))
        if not tower:
            tower = tw
        if not floor:
            floor = norm_fl
        if not axis:
            axis = norm_ax
        unit = f"{tw}{norm_fl}.{norm_ax}"
        return {"unit_code": unit, "tower": tower, "floor": floor, "axis": axis}

    # 4. Dạng Tòa.TầngTrục: 'P2.2602'
    dot_match = re.match(r'^([A-Z0-9]+)\.(\d{2}[A-Z]?)(\d{2}[A-Z]?)$', unit)
    if dot_match:
        tw = dot_match.group(1)
        norm_fl = to_commercial_floor_code(dot_match.group(2))
        norm_ax = to_axis_code(dot_match.group(3))
        if not tower:
            tower = tw
        if not floor:
            floor = norm_fl
        if not axis:
            axis = norm_ax
        unit = f"{tw}.{norm_fl}{norm_ax}"
        return {"unit_code": unit, "tower": tower, "floor": floor, "axis": axis}

    return {"unit_code": unit, "tower": tower, "floor": floor, "axis": axis}

def sanitize_single_area(raw_val: Any, is_low_rise: bool = True, is_construction: bool = False) -> Any:
    """Làm sạch và trả về số thực diện tích m²."""
    if raw_val is None or raw_val == '':
        return ''
    if isinstance(raw_val, (int, float)):
        num = float(raw_val)
    else:
        s = str(raw_val).strip()
        s = re.sub(r'm2|m²|m', '', s, flags=re.IGNORECASE).strip()
        s = re.sub(r'^[.,-]+|[.,-]+$', '', s).strip()
        if not s or re.match(r'^(-|0|n/a|#ref!|#value!|#error!)$', s, re.IGNORECASE):
            return ''
        if ',' in s and '.' not in s:
            s = s.replace(',', '.')
        elif '.' in s and ',' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif '.' in s and s.count('.') > 1:
            s = s.replace('.', '')
        try:
            num = float(s)
        except ValueError:
            return ''

    if num <= 0:
        return ''

    # Khắc phục lỗi Date Serial (40000 - 50000)
    if 40000 <= num <= 50000 and num.is_integer():
        # Excel Epoch
        from datetime import datetime, timedelta
        dt = datetime(1899, 12, 30) + timedelta(days=num)
        return round(float(f"{dt.day}.{dt.month}"), 2)

    return round(num, 2)

def normalize_price_to_vnd(raw_val: Any, unit_hint: str = 'TOTAL') -> Any:
    """
    Quy đổi giá tiền về số nguyên VNĐ đồng nhất.
    Phân biệt chính xác giữa Tỷ và Triệu, không xóa nhầm các căn có giá < 1.5 tỷ.
    """
    if raw_val is None or raw_val == '':
        return ''

    if isinstance(raw_val, (int, float)):
        num = float(raw_val)
        if num <= 0:
            return ''
        if unit_hint == 'M2':
            if num < 5:
                return ''
            if num < 1000:
                return int(round(num * 1e6))
            if num < 1_000_000:
                return int(round(num * 1e3))
            return int(round(num))

        if unit_hint == 'VAT_KPBT':
            if num < 1000:
                return int(round(num * 1e6))  # 60 triệu KPBT
            if num < 1_000_000:
                return int(round(num * 1e6))
            return int(round(num))

        # Giá tổng (TOTAL)
        if num < 0.4:
            return ''  # Giá quá nhỏ
        if num < 1000:
            return int(round(num * 1e9))  # 1.2 tỷ -> 1.200.000.000
        if num < 1_000_000:
            return int(round(num * 1e6))  # 850 triệu -> 850.000.000
        return int(round(num))

    s = str(raw_val).strip()
    if not s or re.match(r'^(0|0,0|0\.0|-|n/a|đã bán|còn hàng|lock|check|thu|#ref!|#value!|#error!)$', s, re.IGNORECASE):
        return ''

    s = s.split('\n')[0].strip()
    s = re.sub(r'\([^)]*\)', '', s).strip()

    is_ty = bool(re.search(r'tỷ|ty', s, re.IGNORECASE))
    is_tr = bool(re.search(r'triệu|tr', s, re.IGNORECASE))

    s = re.sub(r'vnđ|vnd|đồng|₫', '', s, flags=re.IGNORECASE).strip()
    s = re.sub(r'^[.,-]+|[.,-]+$', '', s).strip()
    s = re.sub(r'[^\d.,]', '', s)
    if not s:
        return ''

    # Chuẩn hóa dấu phân cách
    if s.count('.') >= 2:
        s = s.replace('.', '').replace(',', '.')
    elif s.count(',') >= 2:
        s = s.replace(',', '')
    elif '.' in s and ',' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        parts = s.split(',')
        if len(parts) > 1 and len(parts[1]) == 3 and float(parts[0]) > 100:
            s = s.replace(',', '')
        else:
            s = s.replace(',', '.')
    elif '.' in s:
        parts = s.split('.')
        if len(parts) > 1 and len(parts[1]) == 3 and float(parts[0]) >= 100:
            s = s.replace('.', '')

    try:
        val_float = float(s)
    except ValueError:
        return ''

    if val_float <= 0:
        return ''

    if is_ty:
        return int(round(val_float * 1e9))
    if is_tr:
        return int(round(val_float * 1e6))

    return normalize_price_to_vnd(val_float, unit_hint=unit_hint)

def normalize_numeric_or_null(val: Any, is_integer: bool = False) -> Any:
    """
    Chuẩn hóa số thực / số nguyên.
    BẢO TOÀN DẤU CHẤM THẬP PHÂN cho số WC (ví dụ 1.5, 2.5 WC).
    """
    if val is None or val == '':
        return ''
    if isinstance(val, (int, float)):
        return int(round(val)) if is_integer else round(float(val), 2)

    s = str(val).strip().replace(',', '.')
    try:
        num = float(s)
        if abs(num) < 1e-9:
            return ''
        return int(round(num)) if is_integer else round(num, 2)
    except ValueError:
        return ''

def repair_drive_url(raw_url: str) -> str:
    """Sửa lỗi thiếu dấu chấm trong URL Google Drive/Docs."""
    if not raw_url:
        return ''
    s = str(raw_url).strip()
    s = re.sub(r'^https?://drivegooglecom/', 'https://drive.google.com/', s, flags=re.IGNORECASE)
    s = re.sub(r'^https?://docsgooglecom/', 'https://docs.google.com/', s, flags=re.IGNORECASE)
    return s

def resolve_unit_media_links(
    chican_urls: Optional[List[str]] = None,
    ptg_urls: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Tổng hợp link ảnh chỉ căn, link phiếu tính giá (PTG) và link gộp Cột 36 (Ảnh chỉ căn + PTG).
    BẢO TOÀN 100% link thư mục Drive (/folders/...).
    """
    final_chi_can = []
    final_ptg = []
    seen = set()

    def add_url(target_list, u):
        repaired = repair_drive_url(u)
        if repaired and repaired.startswith('http') and repaired not in seen:
            seen.add(repaired)
            target_list.append(repaired)

    for u in (chican_urls or []):
        add_url(final_chi_can, u)
    for u in (ptg_urls or []):
        add_url(final_ptg, u)

    str_chi_can = ' ; '.join(final_chi_can)
    str_ptg = ' ; '.join(final_ptg)
    
    # Cột 36: Gộp cả chỉ căn và PTG
    combined_list = []
    for u in final_chi_can + final_ptg:
        if u not in combined_list:
            combined_list.append(u)
    str_combined = ' ; '.join(combined_list)

    return {
        "anh_chi_can": str_chi_can,
        "anh_ptg": str_ptg,
        "anh_chi_can_ptg": str_combined
    }

def normalize_csbh_date(raw_csbh: Any, default_year: int = DEFAULT_POLICY_YEAR) -> Dict[str, str]:
    """
    Chuẩn hóa ngày CSBH.
    Xác minh ngày thực tế hợp lệ bằng datetime.date (chặn 31/02).
    """
    if not raw_csbh:
        return {"csbh_date": "", "extra_gift": "", "extra_bank": "", "extra_note": ""}

    s = str(raw_csbh).strip().rstrip('.').strip()

    # Kiểm tra ngày đầy đủ dd/mm/yyyy
    m_full = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})', s)
    if m_full:
        d = int(m_full.group(1))
        m = int(m_full.group(2))
        y = int(m_full.group(3))
        if y < 100:
            y += 2000
        try:
            val_date = date(y, m, d)
            return {
                "csbh_date": f"{val_date.day:02d}/{val_date.month:02d}/{val_date.year}",
                "extra_gift": "",
                "extra_bank": "",
                "extra_note": ""
            }
        except ValueError:
            return {"csbh_date": "", "extra_gift": "", "extra_bank": "", "extra_note": s}

    # Ngày ngắn dd/mm
    if not re.search(r'\d+%', s) and not re.search(r'tháng|thang', s, re.IGNORECASE):
        m_short = re.search(r'(?:^|\b)(\d{1,2})[/.-](\d{1,2})(?:\b|$)', s)
        if m_short:
            d = int(m_short.group(1))
            m = int(m_short.group(2))
            try:
                val_date = date(default_year, m, d)
                return {
                    "csbh_date": f"{val_date.day:02d}/{val_date.month:02d}/{val_date.year}",
                    "extra_gift": "",
                    "extra_bank": "",
                    "extra_note": ""
                }
            except ValueError:
                return {"csbh_date": "", "extra_gift": "", "extra_bank": "", "extra_note": s}

    return {"csbh_date": "", "extra_gift": "", "extra_bank": "", "extra_note": s}

def normalize_low_rise_type(raw_val: Any, raw_tcbg: Any = '') -> str:
    """Chuẩn hóa loại hình thấp tầng: LK, SH, BTSL, BTĐL, BTTL, TMDV."""
    s = str(raw_val or '').strip().upper()
    tcbg = str(raw_tcbg or '').strip().upper()
    if (s in ['LIỀN KỀ', 'LK']) and 'SONG LẬP' in tcbg:
        return 'BTSL'
    if not s:
        return ''
    if 'SONG LẬP' in s and 'SHOP' in s:
        return 'BTSL'
    if 'LIỀN KỀ' in s and 'SHOP' in s:
        return 'SH'
    if 'ĐƠN LẬP' in s or s in ['ĐL', 'DL', 'BTĐL', 'BTDL']:
        return 'BTĐL'
    if 'SONG LẬP' in s or s in ['SL', 'BTSL']:
        return 'BTSL'
    if 'TỨ LẬP' in s or s in ['TL', 'BTTL']:
        return 'BTTL'
    if 'SHOPHOUSE' in s or s in ['SH', 'SHOP'] or 'NHÀ PHỐ' in s:
        return 'SH'
    if 'TMDV' in s or 'THƯƠNG MẠI' in s:
        return 'TMDV'
    if 'LIỀN KỀ' in s or s == 'LK':
        return 'LK'
    return s

def normalize_high_rise_type(raw_val: Any) -> str:
    """Chuẩn hóa loại hình cao tầng: STUDIO, 1PN+, 2PN+, PENTHOUSE, DUPLEX..."""
    s = str(raw_val or '').strip().upper().replace(' ', '')
    s = s.replace('BR', 'PN')
    if not s:
        return ''
    if 'STUDIO' in s or s == 'STU':
        return 'STUDIO'
    if 'PENTHOUSE' in s or s == 'PEN':
        return 'PENTHOUSE'
    if 'DUPLEX' in s or s == 'DUP':
        return 'DUPLEX'
    if re.match(r'^1PN\+1', s):
        return '1PN+'
    if re.match(r'^2PN\+1', s):
        return '2PN+'
    if re.match(r'^3PN\+1', s):
        return '3PN+'
    return s
