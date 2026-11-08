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
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from src.config import DEFAULT_POLICY_YEAR

# Bảng quy đổi hệ mã thương mại (Quy tắc nghiệp vụ: Áp dụng cho cả Mã Tầng và Mã Trục/Căn số)
# Chuẩn hóa về hệ mã thương mại: 01, 02, 03, 05A (từ 04), 05, 06, 08A (từ 07), 08, 09, 10, 11, 12, 12A (từ 13), 15A (từ 14), 15, 16, 17, 18...
COMMERCIAL_CODE_MAP = {
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

JUNK_CODE_REGEX = re.compile(
    r'(CỌC|COC|TIỀN\s*THUÊ|TIEN\s*THUE|CAM\s*KẾT|CAM\s*KET|'
    r'THÔ\s*KHÔNG|THÔ\s*CÓ|GIÃN\s*XÂY|HOÀN\s*THIỆN|BẢNG\s*HÀNG|BANG\s*HANG|'
    r'QUỸ\s*THÔ|QUY\s*THO|QUỸ\s*HOÀN|QUY\s*HOAN|SỐ\s*TIỀN|SO\s*TIEN|'
    r'VNĐ|VND|TRIỆU|TRIEU|DỰ\s*ÁN|DU\s*AN|PHÂN\s*KHU|PHAN\s*KHU|'
    r'THIÊN\s*ĐƯỜNG|THIEN\s*DUONG|THIÊNĐƯỜNG|THIENDUONG|'
    r'VỊNH\s*BÌNH\s*MINH|VINH\s*BINH\s*MINH|VỊNHBÌNHMINH|VINHBINHMINH|'
    r'THÔNG\s*BÁO|THONG\s*BAO|XÂY\s*SAU|XAY\s*SAU)',
    re.IGNORECASE
)

def to_commercial_code(raw_token: Any) -> str:
    """
    Quy tắc chuẩn hóa hệ mã thương mại cho cả Tầng và Trục/Căn số:
    - 04 hoặc 4   -> 05A
    - 07 hoặc 7   -> 08A
    - 13          -> 12A
    - 14          -> 15A
    - Các số từ 1-9 pad số 0 phía trước: 01, 02, 03, 05, 06, 08, 09
    """
    if raw_token is None:
        return ''
    s = str(raw_token).strip().upper()
    s = re.sub(r'^(TẦNG|TANG|TRỤC|TRUC|CĂN|CAN|SỐ|SO)\s*', '', s, flags=re.IGNORECASE).strip()
    if not s:
        return ''
    if s in COMMERCIAL_CODE_MAP:
        return COMMERCIAL_CODE_MAP[s]
    if re.match(r'^\d[A-Z]$', s):
        return '0' + s
    if re.match(r'^\d$', s):
        padded = '0' + s
        return COMMERCIAL_CODE_MAP.get(padded, padded)
    return s

def to_commercial_floor_code(raw_token: Any) -> str:
    """Chuẩn hóa mã tầng thương mại."""
    return to_commercial_code(raw_token)

def to_axis_code(raw_token: Any) -> str:
    """Chuẩn hóa mã trục căn / căn số theo quy tắc hệ mã thương mại (04->05A, 07->08A, 13->12A, 14->15A)."""
    return to_commercial_code(raw_token)

def sanitize_unit_code(raw_code: Any) -> str:
    """Làm sạch mã căn, loại bỏ emoji, ký tự trang trí, ghi chú trong ngoặc, chặn dòng quảng cáo/thông báo."""
    if not raw_code:
        return ''
    s = str(raw_code).strip().upper()
    # Loại bỏ bullet/ký tự gạch đầu dòng
    s = re.sub(r'^[•\-\*­\s]+', '', s)
    # Loại bỏ emoji và sao
    s = re.sub(r'[✨🔥💥💎⭐🌟⚡📌📍🎯🏷️✅❌⚠️\*]+', '', s)
    # Cắt bỏ phần mở ngoặc đơn (Góc, Xẻ khe, cam kết...)
    s = s.split('(')[0].split(',')[0].split('\n')[0].split(';')[0].strip()
    # Loại bỏ tiền tố mã căn: hoặc cắt phần trước dấu hai chấm nếu dấu hai chấm chứa chữ ghi chú
    if ':' in s:
        parts = s.split(':', 1)
        left, right = parts[0].strip(), parts[1].strip()
        if re.search(r'\d', left) and re.search(r'[A-ZÀ-Ỹ]', left):
            s = left
        elif re.search(r'\d', right):
            s = right
        else:
            s = left
    # Nếu có dấu cách: kiểm tra từ đầu tiên có phải mã căn chuẩn không (VD: AS4-49 Căn góc 3 mặt tiền -> AS4-49)
    tokens = s.split()
    if tokens:
        first = tokens[0].strip('.,-')
        if re.match(r'^[A-ZÀ-Ỹ0-9]{1,10}[-_.][A-ZÀ-Ỹ0-9]{1,10}$', first):
            s = first
        else:
            s = ''.join(tokens)
    # Cắt bỏ từ khóa đuôi góc/xẻ khe/thường
    s = re.sub(r'\s+(GÓC|GOC|XẺ KHE|XE KHE|THƯỜNG|THUONG)$', '', s, flags=re.IGNORECASE).strip()
    # Xóa khoảng trắng thừa và ký tự nối đầu/cuối
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'^[-._]+|[-._]+$', '', s)
    # Chặn triệt để dòng thông báo, chính sách, banner
    if JUNK_CODE_REGEX.search(s):
        return ''
    if len(s) < 2 or len(s) > 25:
        return ''
    if not re.search(r'\d', s) or not re.search(r'[A-ZÀ-Ỹ]', s):
        return ''
    if re.match(r'^\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}$', s):
        return ''
    return s

def normalize_high_rise_unit_floor_axis(
    raw_unit_code: Any,
    raw_tower: Any = '',
    raw_floor: Any = '',
    raw_axis: Any = '',
    project_key: str = '',
    sub_tab: str = ''
) -> Optional[Dict[str, str]]:
    """
    Chuẩn hóa bộ 4 thông số cao tầng: Tên tòa, Tầng, Mã trục, Mã căn.
    Tuân thủ tuyệt đối mẫu chuẩn từ Bảng hàng Độc quyền của từng dự án.
    Nếu phát hiện căn của dự án khác bị lẫn trong sheet đại lý, trả về None để loại bỏ.
    """
    unit = str(raw_unit_code or '').strip().upper().replace(' ', '')
    tower = str(raw_tower or '').strip().upper()
    floor = to_commercial_floor_code(raw_floor)
    axis = to_axis_code(raw_axis)

    pkey = (project_key or sub_tab or '').strip().upper()

    # =========================================================================
    # 0. QUY TẮC CHUẨN HÓA DỰ ÁN HSG (LUMIÈRE HANOI SEASONS GARDEN)
    # Cơ sở: Bảng hàng độc quyền Vhub (Tòa L1: HH-A, Tòa L2: HH-B)
    # =========================================================================
    if pkey in ('HSG', 'LUMIÈRE HANOI SEASONS GARDEN', 'LUMIERE HANOI SEASONS GARDEN', 'LUMIERE-HANOI-SEASONS-GARDEN'):
        # 0.1 Lọc bỏ các căn thuộc dự án khác (C1, C2, C3, C5, F1, B1, Palma, The Bloom, V1, V2, V3, S1, S2, M1, M2, M3, Y1, Y2, Y3, Z1, Z2, Z3...)
        foreign_prefixes = r'^(c1|c2|c3|c5|f1|b1|palma|the\s*bloom|v1|v2|v3|s1|s2|m1|m2|m3|y1|y2|y3|z1|z2|z3)'
        if re.search(foreign_prefixes, unit, re.IGNORECASE) or re.search(foreign_prefixes, tower, re.IGNORECASE):
            return None

        target_tower = None
        target_code_prefix = None
        target_floor = None
        target_axis = None

        # Concatenated format: HHA2819, HHB1021
        m_concat_a = re.match(r'^HHA(\d{2})([0-9]{2}[A-Z]?)$', unit, re.IGNORECASE)
        m_concat_b = re.match(r'^HHB(\d{2})([0-9]{2}[A-Z]?)$', unit, re.IGNORECASE)

        # Hyphen/Dot/Space format: HH-A-19-20, HHA-19-20, A-19-20, L1-19-20
        m_sep_a = re.match(r'^(?:HH[-_.\s]*A|HHA|A|L1)[-_.\s]+(\d+[A-Z]?)[-_.\s]+(\d+[A-Z]?)$', unit, re.IGNORECASE)
        m_sep_b = re.match(r'^(?:HH[-_.\s]*B|HHB|B|L2)[-_.\s]+(\d+[A-Z]?)[-_.\s]+(\d+[A-Z]?)$', unit, re.IGNORECASE)

        if m_concat_a:
            target_tower = 'L1'
            target_code_prefix = 'HH-A'
            target_floor = m_concat_a.group(1)
            target_axis = m_concat_a.group(2)
        elif m_concat_b:
            target_tower = 'L2'
            target_code_prefix = 'HH-B'
            target_floor = m_concat_b.group(1)
            target_axis = m_concat_b.group(2)
        elif m_sep_a:
            target_tower = 'L1'
            target_code_prefix = 'HH-A'
            target_floor = m_sep_a.group(1)
            target_axis = m_sep_a.group(2)
        elif m_sep_b:
            target_tower = 'L2'
            target_code_prefix = 'HH-B'
            target_floor = m_sep_b.group(1)
            target_axis = m_sep_b.group(2)
        else:
            clean_tw = re.sub(r'^(tòa|toà|block)\s*', '', tower, flags=re.IGNORECASE).strip().upper()
            if clean_tw in ('L1', 'HH-A', 'HHA', 'A'):
                target_tower = 'L1'
                target_code_prefix = 'HH-A'
            elif clean_tw in ('L2', 'HH-B', 'HHB', 'B'):
                target_tower = 'L2'
                target_code_prefix = 'HH-B'
            else:
                return None

            parts = [p for p in re.split(r'[-_.\s]+', unit) if p]
            if len(parts) >= 2 and re.search(r'\d', parts[-1]):
                target_axis = parts[-1]
                target_floor = parts[-2]
            else:
                target_floor = floor
                target_axis = axis

        if not target_tower or not target_floor or not target_axis:
            return None

        fl_str = str(target_floor).strip().upper()
        ax_str = str(target_axis).strip().upper()

        if re.match(r'^\d$', ax_str):
            ax_str = f"0{ax_str}"
        elif re.match(r'^\d[A-Z]$', ax_str):
            ax_str = f"0{ax_str}"

        if re.match(r'^\d$', fl_str):
            fl_str = f"0{fl_str}"

        # Trục trên Tòa L1: Trên 3D mặt bằng chỉ có trục 05A, không có trục 05
        if target_tower == 'L1' and ax_str == '05':
            ax_str = '05A'

        norm_unit = f"{target_code_prefix}-{fl_str}-{ax_str}"
        return {
            "unit_code": norm_unit,
            "tower": target_tower,
            "floor": fl_str,
            "axis": ax_str,
            "subdivision": target_code_prefix
        }

    # =========================================================================
    # 0.5 QUY TẮC CHUẨN HÓA DỰ ÁN MGC (MASTERI GRAND COAST)
    # =========================================================================
    if pkey in ('MGC', 'MASTERI GRAND COAST', 'MASTERI-GRAND-COAST'):
        if re.search(r'^(c1|c2|hh|a-|b-)', unit, re.IGNORECASE) or re.search(r'^(c1|c2|hh|a-|b-)', tower, re.IGNORECASE):
            return None
        m_mgc = re.match(r'^(?:C5)?([LZ]\d)[-_.\s]+(\d+[A-Z]?)[-_.\s]+(\d+[A-Z]?)$', unit, re.IGNORECASE)
        if m_mgc:
            tw_code = m_mgc.group(1).upper()
            fl_code = m_mgc.group(2).upper()
            ax_code = m_mgc.group(3).upper()
            if re.match(r'^\d$', ax_code): ax_code = f"0{ax_code}"
            if re.match(r'^\d$', fl_code): fl_code = f"0{fl_code}"
            return {
                "unit_code": f"C5{tw_code}-{fl_code}-{ax_code}",
                "tower": tw_code,
                "floor": fl_code,
                "axis": ax_code,
                "subdivision": f"C5{tw_code}"
            }

    # =========================================================================
    # 0.6 QUY TẮC CHUẨN HÓA DỰ ÁN MEL (MASTERI ERA LANDMARK)
    # =========================================================================
    if pkey in ('MEL', 'MASTERI ERA LANDMARK', 'MASTERI-ERA-LANDMARK'):
        if re.search(r'^(c5|hh|a-|b-)', unit, re.IGNORECASE) or re.search(r'^(c5|hh|a-|b-)', tower, re.IGNORECASE):
            return None

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
    Chặn triệt để chuỗi ngày tháng và ngưỡng giá bất thường cho đơn giá m2.
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
                res_m2 = int(round(num * 1e6))
            elif num < 1_000_000:
                res_m2 = int(round(num * 1e3))
            else:
                res_m2 = int(round(num))
            # Chặn đơn giá m2 bất thường (> 1 tỷ/m2 hoặc < 1 triệu/m2)
            if res_m2 > 1_000_000_000 or (0 < res_m2 < 1_000_000):
                return ''
            return res_m2

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

    # Chặn chuỗi ngày tháng (VD: 2028-10-01 00:00:00 hoặc 01/10/2028)
    if re.search(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}', s):
        return ''

    s = s.split('\n')[0].strip()
    s = re.sub(r'\([^)]*\)', '', s).strip()

    is_ty = bool(re.search(r'tỷ|ty', s, re.IGNORECASE))
    is_tr = bool(re.search(r'triệu|tr', s, re.IGNORECASE))

    s = re.sub(r'/(m2|m²)|m2|m²', '', s, flags=re.IGNORECASE).strip()
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

    res = normalize_price_to_vnd(val_float, unit_hint=unit_hint)
    if unit_hint == 'M2' and isinstance(res, (int, float)):
        if res > 1_000_000_000 or (0 < res < 1_000_000):
            return ''
    return res

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

DIRECTION_MAP = {
    'ĐÔNG': 'Đông', 'DONG': 'Đông', 'EAST': 'Đông', 'E': 'Đông', 'Đ': 'Đông', 'D': 'Đông',
    'TÂY': 'Tây', 'TAY': 'Tây', 'WEST': 'Tây', 'W': 'Tây', 'T': 'Tây',
    'NAM': 'Nam', 'SOUTH': 'Nam', 'S': 'Nam', 'N': 'Nam',
    'BẮC': 'Bắc', 'BAC': 'Bắc', 'NORTH': 'Bắc', 'B': 'Bắc',
    'ĐÔNG BẮC': 'ĐB', 'DONG BAC': 'ĐB', 'ĐB': 'ĐB', 'DB': 'ĐB', 'NE': 'ĐB', 'NORTHEAST': 'ĐB',
    'ĐÔNG NAM': 'ĐN', 'DONG NAM': 'ĐN', 'ĐN': 'ĐN', 'DN': 'ĐN', 'SE': 'ĐN', 'SOUTHEAST': 'ĐN',
    'TÂY BẮC': 'TB', 'TAY BAC': 'TB', 'TB': 'TB', 'NW': 'TB', 'NORTHWEST': 'TB',
    'TÂY NAM': 'TN', 'TAY NAM': 'TN', 'TN': 'TN', 'SW': 'TN', 'SOUTHWEST': 'TN',
    'ĐÔNG - BẮC': 'ĐB', 'ĐÔNG-BẮC': 'ĐB', 'ĐÔNG/BẮC': 'ĐB',
    'ĐÔNG - NAM': 'ĐN', 'ĐÔNG-NAM': 'ĐN', 'ĐÔNG/NAM': 'ĐN',
    'TÂY - BẮC': 'TB', 'TÂY-BẮC': 'TB', 'TÂY/BẮC': 'TB',
    'TÂY - NAM': 'TN', 'TÂY-NAM': 'TN', 'TÂY/NAM': 'TN',
    'CHÍNH ĐÔNG': 'Đông', 'CHÍNH TÂY': 'Tây', 'CHÍNH NAM': 'Nam', 'CHÍNH BẮC': 'Bắc',
    'ĐB-ĐN': 'ĐB-ĐN', 'ĐB/ĐN': 'ĐB-ĐN', 'TN-TB': 'TN-TB', 'TN/TB': 'TN-TB',
    'ĐN-TN': 'ĐN-TN', 'ĐN/TN': 'ĐN-TN', 'ĐB-TB': 'ĐB-TB', 'ĐB/TB': 'ĐB-TB',
    'TB-ĐB': 'TB-ĐB', 'TB/ĐB': 'TB-ĐB', 'TB-TN': 'TB-TN', 'TB/TN': 'TB-TN',
    'ĐB-TN': 'ĐB-TN', 'ĐB/TN': 'ĐB-TN', 'TN-ĐB': 'TN-ĐB', 'TN/ĐB': 'TN-ĐB'
}

def normalize_direction(raw_direction: Any) -> str:
    """
    Chuẩn hóa hướng nhà / hướng cửa / hướng ban công.
    Loại bỏ triệt để các giá trị số hoặc text rác (VD: 6.388.998.545, 11.833, 24.773, 0).
    Chỉ chấp nhận các hướng địa lý hợp lệ.
    """
    if raw_direction is None:
        return ''
    s = str(raw_direction).strip()
    if not s or re.match(r'^(0|-|n/a|none|null)$', s, re.IGNORECASE):
        return ''

    # Nếu chứa số -> đây là giá tiền/diện tích bị trôi cột hoặc số tầng, loại bỏ ngay
    if re.search(r'\d', s):
        return ''

    cleaned = re.sub(r'^(HƯỚNG|HUONG|CỬA|BAN CÔNG|BC)\s*', '', s, flags=re.IGNORECASE).strip().upper()
    cleaned = re.sub(r'\s+', ' ', cleaned)

    if cleaned in DIRECTION_MAP:
        return DIRECTION_MAP[cleaned]

    # Tra cứu từng phần nếu là hướng ghép (VD: ĐB - ĐN, Đông Bắc - Đông Nam)
    parts = re.split(r'[-/,+&]', cleaned)
    if len(parts) == 2:
        p1 = parts[0].strip()
        p2 = parts[1].strip()
        if p1 in DIRECTION_MAP and p2 in DIRECTION_MAP:
            return f"{DIRECTION_MAP[p1]}-{DIRECTION_MAP[p2]}"

    # Kiểm tra xem có chứa từ khóa hướng hay không
    for k, v in DIRECTION_MAP.items():
        if re.search(rf'\b{re.escape(k)}\b', cleaned):
            return v

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

    # Đối tượng datetime / date trực tiếp (từ Excel openpyxl)
    if isinstance(raw_csbh, (datetime, date)):
        return {
            "csbh_date": f"{raw_csbh.day:02d}/{raw_csbh.month:02d}/{raw_csbh.year}",
            "extra_gift": "",
            "extra_bank": "",
            "extra_note": ""
        }

    s = str(raw_csbh).strip().rstrip('.').strip()

    # Kiểm tra định dạng ISO YYYY-MM-DD
    m_iso = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', s)
    if m_iso:
        y = int(m_iso.group(1))
        m = int(m_iso.group(2))
        d = int(m_iso.group(3))
        try:
            val_date = date(y, m, d)
            return {
                "csbh_date": f"{val_date.day:02d}/{val_date.month:02d}/{val_date.year}",
                "extra_gift": "",
                "extra_bank": "",
                "extra_note": ""
            }
        except ValueError:
            pass

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
    if not s:
        return ''
    if ('SONG LẬP' in tcbg or 'SONG LAP' in tcbg) and any(kw in s for kw in ['LIỀN KỀ', 'LIEN KE', 'LIÊN KẾ', 'LK']):
        return 'BTSL'
    if any(kw in s for kw in ['SONG LẬP', 'SONG LAP', 'BTSL', 'SL']):
        return 'BTSL'
    if any(kw in s for kw in ['ĐƠN LẬP', 'DON LAP', 'BTĐL', 'BTDL', 'ĐL', 'DL']):
        return 'BTĐL'
    if any(kw in s for kw in ['TỨ LẬP', 'TU LAP', 'BTTL', 'TL']):
        return 'BTTL'
    if any(kw in s for kw in ['SHOPHOUSE', 'NHÀ PHỐ', 'NHA PHO', 'SH', 'SHOP']):
        return 'SH'
    if any(kw in s for kw in ['TMDV', 'THƯƠNG MẠI', 'THUONG MAI']):
        return 'TMDV'
    if any(kw in s for kw in ['LIỀN KỀ', 'LIEN KE', 'LIÊN KẾ', 'LK']):
        return 'LK'
    if any(kw in s for kw in ['BIỆT THỰ', 'BIET THU', 'BT']):
        return 'BT'
    return s

def normalize_high_rise_type(raw_val: Any) -> str:
    """Chuẩn hóa loại hình cao tầng: STUDIO, 1PN, 1PN+, 2PN, 2PN+, 3PN, 3PN+, 4PN, DUPLEX, PENTHOUSE..."""
    s = str(raw_val or '').strip().upper()
    s = re.sub(r'\s+', ' ', s)
    if not s or s in ['NONE', 'NULL', 'N/A']:
        return ''
    if any(kw in s for kw in ['STUDIO', 'STU']):
        return 'STUDIO'
    if any(kw in s for kw in ['PENTHOUSE', 'PEN']):
        return 'PENTHOUSE'
    if any(kw in s for kw in ['DUPLEX', 'DUP']):
        return 'DUPLEX'
    if any(kw in s for kw in ['TRIPLEX', 'TRI']):
        return 'TRIPLEX'
    m_plus = re.search(r'([1-4])\s*(?:PN|BR|PHÒNG\s*NGỦ|PHONG\s*NGU|P)\s*(?:\+|\+\s*1|\bCỘNG\b)', s)
    if m_plus:
        return f"{m_plus.group(1)}PN+"
    m_std = re.search(r'([1-4])\s*(?:PN|BR|PHÒNG\s*NGỦ|PHONG\s*NGU|P)\b', s)
    if m_std:
        return f"{m_std.group(1)}PN"
    s_clean = s.replace(' ', '').replace('BR', 'PN')
    if re.match(r'^[1-4]PN\+?$', s_clean):
        return s_clean
    return s

def sanitize_and_cross_validate_prices(
    total_price: Any,
    price_before_vat: Any,
    don_gia_m2: Any = None
) -> Tuple[Any, Any, Any]:
    """
    Quy tắc kiểm định giá chuẩn xác:
    1. Loại bỏ giá rác bất thường < 100 triệu VNĐ đối với BĐS (trả về None).
    2. BẢO TỒN 100% Giá tổng (total_price): Nếu nguồn không có VAT hoặc không có giá trước VAT,
       bắt buộc giữ nguyên giá tổng gốc (theo chỉ đạo người dùng).
    3. Nhận diện trôi cột (Column Drift): Khi price_before_vat > 1 tỷ nhưng total_price < 500 triệu
       (do bị gán nhầm đơn giá/m2 hoặc tiền cọc vào cột tổng giá):
       Gán lại don_gia_m2 = don_gia_m2 or total_price và đặt total_price = None.
    """
    tot = total_price
    prev = price_before_vat
    dg = don_gia_m2

    if tot is not None and tot != '':
        try:
            tot_num = float(tot)
            if 0 < tot_num < 100_000_000:
                tot = None
        except (ValueError, TypeError):
            pass

    if prev is not None and tot is not None and prev != '' and tot != '':
        try:
            prev_num = float(prev)
            tot_num = float(tot)
            if prev_num > 1_000_000_000 and tot_num < 500_000_000 and prev_num > tot_num:
                if dg is None or dg == '':
                    dg = tot
                tot = None
        except (ValueError, TypeError):
            pass

    return tot, prev, dg

# Bảng ánh xạ phân khu dựa trên dữ liệu thực tế có sẵn từ các nguồn chính thống của từng dự án
GROUNDED_ZONE_MAP = {
    'OCP2-3': {
        'VX': 'Vịnh Xanh',  # Theo chỉ đạo của người dùng: VX -> Vịnh Xanh
        'KĐ': 'Kinh Đô Ánh Sáng',
        'PB': 'Phố Biển',
        'NT': 'Ngọc Trai',
        'AD': 'Ánh Dương',
        'SH': 'San Hô',
        'ĐD': 'Đảo Dừa',
        'CL': 'Chà Là',
        'SB': 'Sao Biển',
        'VTĐ': 'Vịnh Thiên Đường',
        'HA': 'Hải Âu',
        'TĐ': 'Thời Đại'
    },
    'làng vân': {
        'VM': 'Vịnh Mây',
        'BV': 'Bạch Vân',
        'VU': 'Bạch Vân',
        'TK': 'Bạch Vân',
        'VK': 'Bạch Vân',
        'LN': 'Đảo Ngọc',
        'SV': 'Đảo Ngọc',
        'AN': 'Đảo Ngọc',
        'LV': 'Đảo Ngọc',
        'HC': 'Đảo Ngọc',
        'LP': 'Đảo Ngọc',
        'ĐLMC': 'Đảo Ngọc'
    },
    'HLX': {
        'BM': 'Bình Minh',
        'NĐ': 'Ngọc Đảo',
        'HL': 'Hoàng Lâu'
    },
    'MIK OCP': {
        'P1': 'The Pavilion',
        'P2': 'The Pavilion',
        'P3': 'The Pavilion',
        'P4': 'The Pavilion',
        'Z1': 'The Zurich',
        'Z2': 'The Zurich',
        'M1': 'The Miami',
        'M2': 'The Miami',
        'M3': 'The Miami'
    },
    'MAS CAO TẦNG': {
        'MGC': 'Masteri Grand Coast',
        'MEL': 'Lumiere EverGreen',
        'HSG': 'The Senique',
        'LEP': 'Lumiere SpringBay'
    }
}

def infer_grounded_zone(unit_code: str, project_key: str, existing_zone: str = '', sub_tab: str = '') -> str:
    """
    Suy luận phân khu dựa trên dữ liệu thực tế có sẵn khi nguồn bỏ trống.
    Không tự sáng tạo giá trị mới, bảo toàn 100% dữ liệu gốc nếu đã có.
    """
    zone = str(existing_zone or '').strip()

    # 1. Nếu đã có dữ liệu phân khu, chuẩn hóa trường hợp Vịnh Xuân -> Vịnh Xanh theo chỉ đạo
    if zone:
        if re.search(r'vịnh xuân|vinh xuan', zone, re.IGNORECASE):
            return re.sub(r'vịnh xuân|vinh xuan', 'Vịnh Xanh', zone, flags=re.IGNORECASE)
        return zone

    # 2. Xử lý cho dự án MAS CAO TẦNG dựa trên sub-tab
    if project_key == 'MAS CAO TẦNG' and sub_tab:
        mas_map = GROUNDED_ZONE_MAP.get('MAS CAO TẦNG', {})
        if sub_tab.upper() in mas_map:
            return mas_map[sub_tab.upper()]

    # 3. Tra cứu theo tiền tố mã căn cho các dự án đã có dữ liệu thực tế
    p_map = GROUNDED_ZONE_MAP.get(project_key)
    if not p_map or not unit_code:
        return ''

    clean_code = sanitize_unit_code(unit_code).upper()

    # Với MIK OCP (mã dạng P1.1101, Z1.1502, M2.2005)
    if project_key == 'MIK OCP':
        m_tw = re.match(r'^([PZM]\d+)', clean_code)
        if m_tw and m_tw.group(1) in p_map:
            return p_map[m_tw.group(1)]

    # Tìm tiền tố chữ cái (có thể có dấu tiếng Việt như KĐ, ĐD, VTĐ)
    # Ví dụ: VX2-46 -> VX, KĐ7-117 -> KĐ, VTĐ8-01 -> VTĐ, BM3-08 -> BM
    m_pref = re.match(r'^([A-ZĐĂÂÔƠƯ]+)', clean_code)
    if m_pref:
        pref = m_pref.group(1)
        if pref in p_map:
            return p_map[pref]
        for k in sorted(p_map.keys(), key=len, reverse=True):
            if pref.startswith(k) or pref.endswith(k):
                return p_map[k]

    return ''

def infer_grounded_low_rise_type(unit_code: str, raw_type: str = '', raw_tcbg: str = '') -> str:
    """Suy luận loại hình thấp tầng dựa trên dữ liệu có sẵn từ cột nguồn hoặc tiền tố mã căn."""
    norm = normalize_low_rise_type(raw_type, raw_tcbg)
    if norm:
        return norm
    if not unit_code:
        return ''
    u = unit_code.strip().upper()
    if re.match(r'^(LK|LIENKE|LIỀNKỀ)', u):
        return 'LK'
    if re.match(r'^(SH|SHOP|SHOPHOUSE)', u):
        return 'SH'
    if re.match(r'^(BTĐL|BTDL)', u):
        return 'BTĐL'
    if re.match(r'^(BTSL)', u):
        return 'BTSL'
    if re.match(r'^(BT|BIETTHU|BIỆTTHỰ)', u):
        return 'BT'
    if re.match(r'^(TMDV)', u):
        return 'TMDV'
    return ''

def compute_expiry_warning(
    issue_date_str: str,
    today_date: Optional[date] = None,
    cycle_days: int = 30
) -> Dict[str, Any]:
    """
    Tính toán số ngày còn lại và cảnh báo hết hạn cấp hàng.
    - Chu kỳ chuẩn: 30 ngày kể từ ngày cấp hàng.
    - Cảnh báo tại mốc 29 ngày: ⚠️ Sắp hết hạn (Còn 1 ngày).
    - Quá hạn (>= 30 ngày): ⛔ Đã hết hạn (Quá X ngày).
    - Bình thường (< 29 ngày): Còn X ngày.
    """
    if not issue_date_str or not isinstance(issue_date_str, str):
        return {
            "display": "",
            "days_remaining": None,
            "days_elapsed": None,
            "status": "UNKNOWN"
        }

    clean_str = issue_date_str.strip().rstrip('.')
    m = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', clean_str)
    if not m:
        return {
            "display": "",
            "days_remaining": None,
            "days_elapsed": None,
            "status": "UNKNOWN"
        }

    d = int(m.group(1))
    month = int(m.group(2))
    y = int(m.group(3))

    try:
        parsed_date = date(y, month, d)
    except ValueError:
        return {
            "display": "",
            "days_remaining": None,
            "days_elapsed": None,
            "status": "UNKNOWN"
        }

    if today_date is None:
        today_date = date.today()

    days_elapsed = (today_date - parsed_date).days

    if days_elapsed < 0:
        return {
            "display": f"Còn {cycle_days} ngày",
            "days_remaining": cycle_days,
            "days_elapsed": 0,
            "status": "NORMAL"
        }

    days_remaining = cycle_days - days_elapsed

    if days_elapsed == 29:
        return {
            "display": "⚠️ Sắp hết hạn (Còn 1 ngày)",
            "days_remaining": 1,
            "days_elapsed": 29,
            "status": "EXPIRING_SOON"
        }
    elif days_elapsed >= cycle_days:
        over_days = days_elapsed - cycle_days
        over_str = f"Quá {over_days} ngày" if over_days > 0 else "Hôm nay"
        return {
            "display": f"⛔ Đã hết hạn ({over_str})",
            "days_remaining": days_remaining,
            "days_elapsed": days_elapsed,
            "status": "EXPIRED"
        }
    else:
        return {
            "display": f"Còn {days_remaining} ngày",
            "days_remaining": days_remaining,
            "days_elapsed": days_elapsed,
            "status": "NORMAL"
        }

def realign_legacy_row(row: List[Any], is_low_rise: bool) -> List[Any]:
    """
    Tự động chuẩn hóa và căn chỉnh dòng dữ liệu theo cấu trúc cột mới (Phương án 2 - Low Rise):
    Index 30 (AE): Ghi chú
    Index 31 (AF): Trạng thái
    Index 32 (AG): Nhóm quỹ
    Index 33 (AH): Đại lý
    Index 34 (AI): Ngày cấp hàng
    Index 35 (AJ): Hạn cấp hàng (Còn lại)
    Index 36 (AK): Ảnh chỉ căn
    Index 37 (AL): Ảnh phiếu tính giá
    Index 38 (AM): Ẩnh chỉ căn+ PTG
    """
    if not is_low_rise or len(row) <= 33:
        return row

    def _format_date_val(val: Any) -> str:
        s = str(val or '').strip()
        if not s:
            return ''
        if re.match(r'^\d{5}$', s):
            try:
                return (date(1899, 12, 30) + timedelta(days=int(s))).strftime('%d/%m/%Y')
            except Exception:
                pass
        return s

    status_keywords = {'còn hàng', 'đang lock', 'đã bán'}
    fund_keywords = {'quỹ chung', 'quỹ độc quyền', 'quỹ chéo', 'quỹ ngoại giao'}

    padded = list(row)
    while len(padded) < 39:
        padded.append('')

    val_30 = str(padded[30] or '').strip()
    val_31 = str(padded[31] or '').strip()
    val_32 = str(padded[32] or '').strip()
    val_33 = str(padded[33] or '').strip()
    val_34 = str(padded[34] or '').strip()
    val_35 = str(padded[35] or '').strip()
    val_36 = str(padded[36] or '').strip()
    val_37 = str(padded[37] or '').strip()
    val_38 = str(padded[38] or '').strip()

    is_url_33 = bool('http' in val_33 or 'drive.google' in val_33)
    is_date_34 = bool(re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', val_34) or re.match(r'^\d{5}$', val_34))

    # 1. Đã ở chuẩn mới (Phương án 2):
    # col 31 là Trạng thái, col 32 là Nhóm quỹ, col 33 là Đại lý (có giá trị và không phải URL), col 34 là ngày (hoặc trống)
    if val_31.lower() in status_keywords and (val_32.lower() in fund_keywords or not val_32):
        has_legacy_shifted_tail = bool(not val_33 and not val_34 and (val_36 or val_37) and 'http' not in val_36)
        if not is_url_33 and not has_legacy_shifted_tail and (is_date_34 or not val_34) and ('http' not in val_33 and 'drive' not in val_33):
            if re.match(r'^\d{5}$', val_34):
                padded[34] = _format_date_val(val_34)
            return padded

    # 2. Định dạng từ bước trước (Ảnh ở 33-35, Đại lý ở 36, Ngày ở 37, Hạn ở 38):
    if val_31.lower() in status_keywords and (val_36 or val_37 or is_url_33):
        new_row = list(padded)
        status = val_31
        fund_group = val_32
        agency = val_36
        issue_date = _format_date_val(val_37)
        expiry = val_38
        img1 = val_33
        img2 = val_34
        img3 = val_35

        new_row[30] = val_30
        new_row[31] = status
        new_row[32] = fund_group
        new_row[33] = agency
        new_row[34] = issue_date
        new_row[35] = expiry
        new_row[36] = img1
        new_row[37] = img2
        new_row[38] = img3
        return new_row

    # 3. Định dạng legacy sâu (col 34 là Trạng thái):
    if val_34.lower() in status_keywords:
        new_row = list(padded)
        status = val_34
        fund_group = val_35

        is_date_36 = bool(re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', val_36) or re.match(r'^\d{5}$', val_36))
        is_date_37 = bool(re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', val_37) or re.match(r'^\d{5}$', val_37))

        if not is_url_33 and val_33:
            agency = val_33
            img1 = val_31
            img2 = val_32
            img3 = ''
            issue_date = _format_date_val(val_37) if is_date_37 else _format_date_val(val_36)
            expiry = val_38
        else:
            agency = val_36
            img1 = val_31
            img2 = val_32
            img3 = val_33
            issue_date = _format_date_val(val_37)
            expiry = val_38

        new_row[30] = val_30
        new_row[31] = status
        new_row[32] = fund_group
        new_row[33] = agency
        new_row[34] = issue_date
        new_row[35] = expiry
        new_row[36] = img1
        new_row[37] = img2
        new_row[38] = img3
        return new_row

    return padded
