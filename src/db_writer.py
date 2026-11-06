"""
Module ghi trực tiếp bảng hàng đã chuẩn hóa vào cơ sở dữ liệu PostgreSQL (VHUB Web Database).
Thực hiện cơ chế Đích Kép (Dual-Destination):
- Đích 1: Google Sheets (cho đội ngũ kinh doanh nội bộ).
- Đích 2: Bảng 'products' trong PostgreSQL (cho Web API và bộ lọc tra cứu bảng hàng).
"""

import os
import re
import json
import uuid
import unicodedata
import logging
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import execute_values, Json

from src.normalizer import (
    sanitize_unit_code,
    normalize_direction,
    normalize_low_rise_type,
    normalize_high_rise_type,
    sanitize_and_cross_validate_prices
)
from src.merger import extract_clean_agency_name

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))

# Ánh xạ mã dự án trong Engine Python sang (project_id, project_name) chuẩn của hệ thống VHUB
VHUB_PROJECT_MAP: Dict[str, Tuple[str, str]] = {
    "làng vân": ("vinhomes-hai-van-bay", "VINHOMES HẢI VÂN BAY"),
    "VRI": ("vinhomes-royal-island", "VINHOMES ROYAL ISLAND"),
    "MIK OCP": ("the-parkland-imperia-ocean-city", "THE PARKLAND - IMPERIA OCEAN CITY"),
    "DƯƠNG KINH": ("vinhomes-golden-city", "VINHOMES GOLDEN CITY"),
    "HLX": ("vinhomes-global-gate-ha-long", "VINHOMES GLOBAL GATE HẠ LONG"),
    "Đan phượng": ("vinhomes-wonder-city", "VINHOMES WONDER CITY"),
    "TRÀNG CÁT": ("happy-home-trang-cat", "HAPPY HOME TRÀNG CÁT"),
    "Cần giờ": ("vinhomes-green-paradise", "VINHOMES GREEN PARADISE"),
    "Hóc Môn": ("vinhomes-sai-gon-park", "VINHOMES SÀI GÒN PARK"),
    "Q9": ("vinhomes-grand-park", "VINHOMES GRAND PARK"),
    "OCP2-3": ("vinhomes-ocean-park-3", "VINHOMES OCEAN PARK 2-3"),
    "Global Gate": ("vinhomes-global-gate", "VINHOMES GLOBAL GATE"),
    "Vinhomes Global Gate": ("vinhomes-global-gate", "VINHOMES GLOBAL GATE"),
    "MGC": ("masteri-grand-coast", "MASTERI GRAND COAST"),
    "Masteri Grand Coast": ("masteri-grand-coast", "MASTERI GRAND COAST"),
    "MEL": ("masteri-era-landmark", "MASTERI ERA LANDMARK"),
    "Masteri Era Landmark": ("masteri-era-landmark", "MASTERI ERA LANDMARK"),
    "HSG": ("lumiere-hanoi-seasons-garden", "LUMIÈRE Hanoi Seasons Garden"),
    "LUMIÈRE Hanoi Seasons Garden": ("lumiere-hanoi-seasons-garden", "LUMIÈRE Hanoi Seasons Garden"),
    "LEP": ("lumiere-essence-peak", "LUMIÈRE Essence Peak"),
    "LUMIÈRE Essence Peak": ("lumiere-essence-peak", "LUMIÈRE Essence Peak"),
    "lumiere-essence-peak": ("lumiere-essence-peak", "LUMIÈRE Essence Peak"),
}

VHUB_MAS_SUBTAB_MAP: Dict[str, Tuple[str, str]] = {
    "MGC": ("masteri-grand-coast", "MASTERI GRAND COAST"),
    "HSG": ("lumiere-hanoi-seasons-garden", "LUMIÈRE Hanoi Seasons Garden"),
    "MEL": ("masteri-era-landmark", "MASTERI ERA LANDMARK"),
    "LEP": ("lumiere-essence-peak", "LUMIÈRE Essence Peak"),
}

DIRECTION_ATOMIC_ORDER = [
    "dong",
    "tay",
    "nam",
    "bac",
    "dong_bac",
    "dong_nam",
    "tay_bac",
    "tay_nam",
]

DIRECTION_GLUE_MAP = [
    ("dongbac", "dong_bac"),
    ("dongnam", "dong_nam"),
    ("taybac", "tay_bac"),
    ("taynam", "tay_nam"),
    ("db", "dong_bac"),
    ("dn", "dong_nam"),
    ("tb", "tay_bac"),
    ("tn", "tay_nam"),
    ("dong", "dong"),
    ("tay", "tay"),
    ("nam", "nam"),
    ("bac", "bac"),
    ("d", "dong"),
    ("t", "tay"),
    ("n", "nam"),
    ("b", "bac"),
]


def _strip_diacritics(text: str) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFD", str(text))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def _collapse_text(text: str) -> str:
    s = _strip_diacritics(text).lower()
    s = re.sub(r"[_-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _slug_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _collapse_text(text))


def _acronym_key(text: str) -> str:
    parts = [re.sub(r"[^a-z0-9]", "", p) for p in _collapse_text(text).split(" ")]
    parts = [p for p in parts if p]
    if len(parts) >= 2:
        return "".join(p[0] for p in parts)
    return _slug_key(text)


def _normalize_type_key(raw: str) -> str:
    c = _collapse_text(raw)
    if not c:
        return ""
    if re.search(r"\bstudio\b", c):
        return "studio"
    plus = re.search(r"(\d+)\s*(?:pn|br|p\b|phong\s*ngu|phong)\s*\+", c)
    if plus:
        return f"{plus.group(1)}pn+"
    plus_rev = re.search(r"(?:pn|br)\s*(\d+)\s*\+", c)
    if plus_rev:
        return f"{plus_rev.group(1)}pn+"
    m1 = re.search(r"(\d+)\s*(?:pn|br|p\b|phong\s*ngu|phong\b)", c)
    if m1:
        return f"{m1.group(1)}pn"
    m2 = re.search(r"(?:pn|br)\s*(\d+)", c)
    if m2:
        return f"{m2.group(1)}pn"
    return _slug_key(c)


def _parse_direction_atomic_keys(raw: str) -> List[str]:
    if not raw:
        return []
    parts = re.split(r"[,;/|＋+&]+|\s+va\s+|\s+and\s+", _collapse_text(raw))
    found = set()
    for part in parts:
        glued = re.sub(r"[^a-z]", "", part)
        while glued:
            matched = False
            for token, canon in DIRECTION_GLUE_MAP:
                if glued.startswith(token):
                    found.add(canon)
                    glued = glued[len(token) :]
                    matched = True
                    break
            if not matched:
                break
    return [k for k in DIRECTION_ATOMIC_ORDER if k in found]


def _build_filter_keys(
    apartment_type_name: Optional[str],
    base_direction_name: Optional[str],
    subdivision_name: Optional[str],
    building_name: Optional[str],
    building_code: Optional[str],
) -> Dict[str, Any]:
    dir_keys = _parse_direction_atomic_keys(base_direction_name or "")
    return {
        "typeKey": _normalize_type_key(apartment_type_name or ""),
        "directionKey": "_".join(dir_keys),
        "directionKeys": dir_keys,
        "subdivisionKey": _slug_key(subdivision_name or ""),
        "subdivisionAcronym": _acronym_key(subdivision_name or ""),
        "buildingKey": _slug_key(building_code or building_name or ""),
    }


def resolve_vhub_project(project_key: str, sub_tab: Optional[str] = None) -> Tuple[str, str]:
    """Ánh xạ project_key (và sub_tab nếu có) sang (project_id, project_name) chuẩn."""
    if sub_tab:
        st = sub_tab.strip().upper()
        if st in VHUB_MAS_SUBTAB_MAP:
            return VHUB_MAS_SUBTAB_MAP[st]
    if project_key in VHUB_PROJECT_MAP:
        return VHUB_PROJECT_MAP[project_key]
    for k, val in VHUB_PROJECT_MAP.items():
        if k.strip().lower() == str(project_key or "").strip().lower():
            return val
    slug = re.sub(r"[^a-z0-9]+", "-", _collapse_text(project_key)).strip("-")
    return (slug or "unknown-project", str(project_key).strip())


def _clean_str(val: Any, max_len: Optional[int] = None) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    if max_len is not None and len(s) > max_len:
        return s[:max_len]
    return s


def _parse_decimal(val: Any, is_price: bool = False) -> Optional[Decimal]:
    if val is None or val == "":
        return None
    if isinstance(val, Decimal):
        d = val
    elif isinstance(val, (int, float)):
        if isinstance(val, float) and (val != val or val == float("inf") or val == float("-inf")):
            return None
        d = Decimal(str(val))
    else:
        s = str(val).strip()
        if not s:
            return None
        s = re.sub(r"[^\d.,-]", "", s)
        if not s or s in ("-", ".", ","):
            return None
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            parts = s.split(",")
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) >= 1):
                s = s.replace(",", "")
            else:
                s = s.replace(",", ".")
        try:
            d = Decimal(s)
        except InvalidOperation:
            return None

    if d <= 0 and is_price:
        return None
    if is_price and d > Decimal("1000000000000"):
        d = d / Decimal("1000")
    return d


def _parse_date_str(val: Any) -> Optional[date]:
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    m1 = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", s)
    if m1:
        day, month, year = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            pass
    m2 = re.search(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b", s)
    if m2:
        year, month, day = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            pass
    return None


def _parse_policy(val: Any) -> Tuple[Optional[date], Optional[str]]:
    if val is None or val == "":
        return None, None
    s = str(val).strip()
    if not s:
        return None, None
    dt = _parse_date_str(s)
    if dt and re.fullmatch(r"[\d/\-\s]+", s):
        return dt, None
    if dt:
        return dt, _clean_str(s, 255)
    return None, _clean_str(s, 255)


def _extract_urls(val: Any) -> Tuple[Optional[str], List[str]]:
    if val is None or val == "":
        return None, []
    s = str(val).strip()
    if not s:
        return None, []
    urls = re.findall(r'https?://[^\s"\'<>)\],;]+', s)
    seen = []
    for u in urls:
        if u not in seen:
            seen.append(u)
    if seen:
        return seen[0], seen
    return None, []


def _parse_floor_sort_order(floor_val: Any) -> Optional[int]:
    if floor_val is None or floor_val == "":
        return None
    s = str(floor_val).strip().upper()
    if not s:
        return None
    m_bsm = re.match(r"^B(\d+)$", s)
    if m_bsm:
        return -int(m_bsm.group(1))
    if s in ("G", "GF", "TRET"):
        return 0
    m_num = re.search(r"-?\d+", s)
    if m_num:
        try:
            return int(m_num.group(0))
        except ValueError:
            return None
    return None


def _map_state_line(status_val: Any) -> Tuple[str, str]:
    s = str(status_val or "").strip()
    low = s.lower()
    if "lock" in low:
        return "locked", "Đang lock"
    if "bán" in low or "ban" in low or "sold" in low:
        return "sold", "Đã bán"
    if "còn" in low or "con" in low or not s:
        return "available", "Còn hàng"
    return "available", s


def _map_fund_info(fund_val: Any, agency_val: Any) -> Tuple[str, str, Optional[str]]:
    clean_agency = extract_clean_agency_name(agency_val).strip()
    fund_raw = str(fund_val or "").strip()
    fund_low = fund_raw.lower()
    ag_low = clean_agency.lower()

    if "quỹ chung" in fund_low or "quy chung" in fund_low or "quỹ chung" in ag_low or "quy chung" in ag_low or "cđt" in ag_low:
        return "Quỹ chung", "Quỹ CĐT", None
    if "độc quyền" in fund_low or "doc quyen" in fund_low or "vhub" in ag_low:
        return "Quỹ độc quyền", "Quỹ đối tác", (clean_agency or None)
    return (fund_raw or "Quỹ chéo"), "Quỹ đối tác", (clean_agency or None)


def _get_col(row: List[Any], idx: int) -> Any:
    return row[idx] if idx < len(row) else None


_subdivision_catalog_cache = {}
_subdivision_catalog_loaded_at = 0

def load_subdivision_catalog(conn):
    global _subdivision_catalog_cache, _subdivision_catalog_loaded_at
    import time
    now = time.time()
    if _subdivision_catalog_cache and (now - _subdivision_catalog_loaded_at < 300):
        return _subdivision_catalog_cache

    catalog = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tour_id, id, name, code, normalized_key 
                FROM tour_subdivisions 
                WHERE status = 'active' OR status IS NULL;
            """)
            for tour_id, sub_id, name, code, norm_key in cur.fetchall():
                if not tour_id: continue
                entry = {
                    "id": str(sub_id),
                    "code": code or "",
                    "canonical_name": name,
                    "tour_id": tour_id
                }
                for k in [norm_key, _slug_key(name), _slug_key(code or "")]:
                    if k:
                        catalog[(tour_id, k)] = entry

            cur.execute("""
                SELECT a.tour_id, a.subdivision_id, a.normalized_alias, s.name, s.code
                FROM tour_subdivision_aliases a
                JOIN tour_subdivisions s ON a.subdivision_id = s.id
                WHERE a.status = 'confirmed';
            """)
            for tour_id, sub_id, norm_alias, name, code in cur.fetchall():
                if not tour_id or not norm_alias: continue
                entry = {
                    "id": str(sub_id),
                    "code": code or "",
                    "canonical_name": name,
                    "tour_id": tour_id
                }
                catalog[(tour_id, _slug_key(norm_alias))] = entry

        # High-volume manual shortcuts
        COMMON_ABBREVS = {
            ("vinhomes-ocean-park-3", "kdas"): "kinh-do-anh-sang",
            ("vinhomes-ocean-park-3", "kinh-do"): "kinh-do-anh-sang",
            ("vinhomes-ocean-park-3", "vtd"): "vinh-thien-duong",
            ("vinhomes-ocean-park-3", "vx"): "vinh-xanh",
            ("vinhomes-ocean-park-3", "td"): "thoi-dai",
            ("vinhomes-ocean-park-3", "sh"): "san-ho",
            ("vinhomes-ocean-park-3", "ha"): "hai-au",
            ("vinhomes-ocean-park-3", "sb"): "sao-bien",
            ("vinhomes-ocean-park-3", "cl"): "cha-la",
            ("vinhomes-ocean-park-3", "dd"): "dao-dua",
            ("vinhomes-ocean-park-3", "pb"): "pho-bien",
            ("vinhomes-global-gate-ha-long", "tdnd-1-1"): "thien-duong-nhiet-doi-1",
            ("vinhomes-global-gate-ha-long", "tdnd-1-2"): "thien-duong-nhiet-doi-1",
            ("vinhomes-global-gate-ha-long", "thien-duong-nhiet-doi-1-2"): "thien-duong-nhiet-doi-1",
            ("vinhomes-global-gate-ha-long", "mat-troi"): "mat-troi",
            ("happy-home-trang-cat", "thinh-vuong"): "trang-cat",
        }
        for (proj, abbr), target_slug in COMMON_ABBREVS.items():
            target_entry = catalog.get((proj, target_slug))
            if target_entry:
                catalog[(proj, abbr)] = target_entry

        _subdivision_catalog_cache = catalog
        _subdivision_catalog_loaded_at = now
    except Exception as e:
        logger.warning(f"Không thể nạp danh mục phân khu tour_subdivisions: {e}")

    return catalog

def map_merged_row_to_db_record(
    row: List[Any],
    project_key: str,
    is_low_rise: bool,
    sub_tab: Optional[str] = None,
    subdivision_catalog: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None,
    now_ts: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """
    Chuyển đổi 1 dòng đã chuẩn hóa (39 cột Thấp tầng hoặc 32 cột Cao tầng)
    sang dictionary khớp với cấu trúc bảng 'products' trong PostgreSQL.
    """
    unit_col_idx = 2 if is_low_rise else 1
    raw_code_raw = _clean_str(_get_col(row, unit_col_idx), 128)
    if not raw_code_raw:
        return None
    raw_code = sanitize_unit_code(raw_code_raw).upper()
    if not raw_code or len(raw_code) < 2:
        return None
    if re.match(r"^\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}$", raw_code) or not (
        re.search(r"[A-Za-zÀ-ỹ]", raw_code) and re.search(r"\d", raw_code)
    ):
        return None

    project_id, project_name = resolve_vhub_project(project_key, sub_tab=sub_tab)
    now_ts = now_ts or datetime.now(VN_TZ)

    if is_low_rise:
        subdivision_name = _clean_str(_get_col(row, 1), 255)
        delivery_standards = _clean_str(_get_col(row, 3))
        apartment_type_name = normalize_low_rise_type(_clean_str(_get_col(row, 4), 255), delivery_standards)
        land_area = _parse_decimal(_get_col(row, 5), is_price=False)
        construction_area = _parse_decimal(_get_col(row, 6), is_price=False)
        price_before_vat = _parse_decimal(_get_col(row, 7), is_price=True)
        vat_amount = _parse_decimal(_get_col(row, 8), is_price=True)
        maintenance_fee_amount = _parse_decimal(_get_col(row, 9), is_price=True)
        total_price = _parse_decimal(_get_col(row, 10), is_price=True)
        construction_price_before_vat = _parse_decimal(_get_col(row, 11), is_price=True)
        construction_vat_amount = _parse_decimal(_get_col(row, 12), is_price=True)
        construction_maintenance_fee_amount = _parse_decimal(_get_col(row, 13), is_price=True)
        construction_total = _parse_decimal(_get_col(row, 14), is_price=True)
        land_price_before_vat = _parse_decimal(_get_col(row, 15), is_price=True)
        land_vat_amount = _parse_decimal(_get_col(row, 16), is_price=True)
        land_maintenance_fee_amount = _parse_decimal(_get_col(row, 17), is_price=True)
        land_total = _parse_decimal(_get_col(row, 18), is_price=True)
        price_per_meter = _parse_decimal(_get_col(row, 19), is_price=True)
        loan_price = _parse_decimal(_get_col(row, 20), is_price=True)
        progress_payment_price = _parse_decimal(_get_col(row, 21), is_price=True)
        early_payment_price = _parse_decimal(_get_col(row, 22), is_price=True)
        base_direction_name = normalize_direction(_clean_str(_get_col(row, 23), 255)) or None
        front_width = _parse_decimal(_get_col(row, 24), is_price=False)
        floor_count = _clean_str(_get_col(row, 25), 32)
        gift = _clean_str(_get_col(row, 26))
        x_sale_description = _clean_str(_get_col(row, 27))
        policy_date, policy_code = _parse_policy(_get_col(row, 28))
        supporting_banks = _clean_str(_get_col(row, 29), 1024)
        notes_real_estate = _clean_str(_get_col(row, 30))
        state_line, state_line_name = _map_state_line(_get_col(row, 31))
        fund_groups_sell_name, fund_type, partner = _map_fund_info(_get_col(row, 32), _get_col(row, 33))
        issue_date_raw = _get_col(row, 34)
        expiry_raw = _clean_str(_get_col(row, 35))
        x_sale_link_summary, product_images = _extract_urls(_get_col(row, 36))
        x_sale_link_full, pricing_sheet_images = _extract_urls(_get_col(row, 37))
        x_link_layout_design, _ = _extract_urls(_get_col(row, 38))
        if not x_link_layout_design:
            x_link_layout_design = _clean_str(_get_col(row, 38))

        building_name = None
        building_code = None
        number_of_floor = None
        floor_sort_order = None
        apartment_axis_code = None
        carpet_area = None
        built_up_area = None
        number_of_room = None
        number_of_wc = None
        product_type = "thap_tang"
    else:
        subdivision_name = _clean_str(_get_col(row, 2), 255)
        apartment_type_name = normalize_high_rise_type(_clean_str(_get_col(row, 3), 255))
        base_direction_name = normalize_direction(_clean_str(_get_col(row, 4), 255)) or None
        building_name = _clean_str(_get_col(row, 5), 255)
        building_code = building_name
        number_of_floor = _clean_str(_get_col(row, 6), 32)
        floor_sort_order = _parse_floor_sort_order(number_of_floor)
        apartment_axis_code = _clean_str(_get_col(row, 7), 255)
        carpet_area = _parse_decimal(_get_col(row, 8), is_price=False)
        built_up_area = _parse_decimal(_get_col(row, 9), is_price=False)
        number_of_room = _clean_str(_get_col(row, 10), 32)
        number_of_wc = _clean_str(_get_col(row, 11), 32)
        maintenance_fee_amount = _parse_decimal(_get_col(row, 12), is_price=True)
        price_before_vat = _parse_decimal(_get_col(row, 13), is_price=True)
        total_price = _parse_decimal(_get_col(row, 14), is_price=True)
        loan_price = _parse_decimal(_get_col(row, 15), is_price=True)
        progress_payment_price = _parse_decimal(_get_col(row, 16), is_price=True)
        early_payment_price = _parse_decimal(_get_col(row, 17), is_price=True)
        price_per_meter = _parse_decimal(_get_col(row, 18), is_price=True)
        delivery_standards = _clean_str(_get_col(row, 19))
        gift = _clean_str(_get_col(row, 20))
        x_sale_description = _clean_str(_get_col(row, 21))
        policy_date, policy_code = _parse_policy(_get_col(row, 22))
        supporting_banks = _clean_str(_get_col(row, 23), 1024)
        x_sale_link_summary, product_images = _extract_urls(_get_col(row, 24))
        x_sale_link_full, pricing_sheet_images = _extract_urls(_get_col(row, 25))
        x_link_layout_design = None
        notes_real_estate = _clean_str(_get_col(row, 26))
        state_line, state_line_name = _map_state_line(_get_col(row, 27))
        fund_groups_sell_name, fund_type, partner = _map_fund_info(_get_col(row, 28), _get_col(row, 29))
        issue_date_raw = _get_col(row, 30)
        expiry_raw = _clean_str(_get_col(row, 31))

        land_area = None
        construction_area = None
        vat_amount = None
        construction_price_before_vat = None
        construction_vat_amount = None
        construction_maintenance_fee_amount = None
        construction_total = None
        land_price_before_vat = None
        land_vat_amount = None
        land_maintenance_fee_amount = None
        land_total = None
        front_width = None
        floor_count = None
        product_type = "cao_tang"

    # Architectural integrity: carpet_area (thông thủy) <= built_up_area (tim tường)
    if carpet_area and built_up_area and carpet_area > built_up_area:
        carpet_area, built_up_area = built_up_area, carpet_area

    # Pricing cross-validation (bảo tồn giá tổng theo chỉ đạo người dùng)
    total_price, price_before_vat, don_gia_m2 = sanitize_and_cross_validate_prices(
        total_price=total_price,
        price_before_vat=price_before_vat,
        don_gia_m2=price_per_meter
    )
    if don_gia_m2:
        price_per_meter = don_gia_m2
    if not total_price:
        total_price = progress_payment_price or early_payment_price or loan_price or price_before_vat

    # Canonical subdivision resolution
    subdivision_id = None
    subdivision_code = None
    subdivision_resolution_status = None
    subdivision_resolution_version = 1
    if subdivision_catalog and subdivision_name:
        sub_key = _slug_key(subdivision_name)
        cat_entry = subdivision_catalog.get((project_id, sub_key))
        if cat_entry:
            subdivision_id = cat_entry["id"]
            subdivision_code = cat_entry["code"]
            subdivision_name = cat_entry["canonical_name"]
            subdivision_resolution_status = "resolved"
        else:
            subdivision_resolution_status = "unmatched"
    elif subdivision_name:
        subdivision_resolution_status = "unmatched"

    filter_keys = _build_filter_keys(
        apartment_type_name=apartment_type_name,
        base_direction_name=base_direction_name,
        subdivision_name=subdivision_name,
        building_name=building_name,
        building_code=building_code,
    )

    alloc_dt = _parse_date_str(issue_date_raw)
    metadata: Dict[str, Any] = {
        "typeKey": filter_keys["typeKey"],
        "directionKey": filter_keys["directionKey"],
        "subdivisionKey": filter_keys["subdivisionKey"],
        "filterKeys": filter_keys,
    }
    if partner:
        metadata["partner"] = partner
    if fund_type:
        metadata["fundType"] = fund_type
    if alloc_dt:
        metadata["allocationDate"] = alloc_dt.isoformat()
    if expiry_raw:
        metadata["expiryWarning"] = expiry_raw

    return {
        "id": str(uuid.uuid4()),
        "product_code": raw_code,
        "project_id": project_id,
        "project_name": project_name,
        "product_type": product_type,
        "product_name": None,
        "subdivision_name": subdivision_name,
        "subdivision_id": subdivision_id,
        "subdivision_code": subdivision_code,
        "subdivision_resolution_status": subdivision_resolution_status,
        "subdivision_resolution_version": subdivision_resolution_version,
        "building_code": building_code,
        "building_name": building_name,
        "apartment_type_name": apartment_type_name,
        "base_direction_name": base_direction_name,
        "apartment_axis_code": apartment_axis_code,
        "number_of_room": number_of_room,
        "number_of_wc": number_of_wc,
        "number_of_floor": number_of_floor,
        "floor_count": floor_count,
        "floor_sort_order": floor_sort_order,
        "front_width": front_width,
        "land_area": land_area,
        "construction_area": construction_area,
        "carpet_area": carpet_area,
        "built_up_area": built_up_area,
        "early_payment_price": early_payment_price,
        "progress_payment_price": progress_payment_price,
        "loan_price": loan_price,
        "total_price": total_price,
        "price_per_meter": price_per_meter,
        "price_before_vat": price_before_vat,
        "vat_amount": vat_amount,
        "maintenance_fee_amount": maintenance_fee_amount,
        "construction_price_before_vat": construction_price_before_vat,
        "construction_vat_amount": construction_vat_amount,
        "construction_maintenance_fee_amount": construction_maintenance_fee_amount,
        "construction_total": construction_total,
        "land_price_before_vat": land_price_before_vat,
        "land_vat_amount": land_vat_amount,
        "land_maintenance_fee_amount": land_maintenance_fee_amount,
        "land_total": land_total,
        "supporting_banks": supporting_banks,
        "delivery_standards": delivery_standards,
        "x_sale_description": x_sale_description,
        "gift": gift,
        "notes_real_estate": notes_real_estate,
        "policy_date": policy_date,
        "policy_code": policy_code,
        "state_line": state_line,
        "state_line_name": state_line_name,
        "fund_groups_sell_name": fund_groups_sell_name,
        "fund_type": fund_type,
        "partner": partner,
        "x_sale_link_summary": x_sale_link_summary,
        "x_sale_link_full": x_sale_link_full,
        "x_link_layout_design": x_link_layout_design,
        "product_images": product_images,
        "pricing_sheet_images": pricing_sheet_images,
        "computed_prices": {},
        "metadata": metadata,
        "is_not_show": False,
        "is_hot": False,
        "view_count": 0,
        "favorite_count": 0,
        "last_source_observed_at": now_ts,
        "created_at": now_ts,
        "updated_at": now_ts,
    }


def _normalize_cell_for_diff(val: Any) -> str:
    if val is None or val == "":
        return ""
    if isinstance(val, (int, float, Decimal)):
        try:
            d = Decimal(str(val)).normalize()
            return str(d)
        except Exception:
            return str(val).strip()
    s = extract_clean_agency_name(val)
    # Nếu là chuỗi số có dấu phẩy ngăn cách hàng nghìn (VD: "14,948,829,217")
    if re.fullmatch(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?", s):
        s_num = s.replace(",", "")
        try:
            return str(Decimal(s_num).normalize())
        except Exception:
            pass
    if re.fullmatch(r"-?\d+(?:\.\d+)?", s):
        try:
            return str(Decimal(s).normalize())
        except Exception:
            pass
    return s


def has_inventory_changed(
    existing_pool_by_key: Dict[str, Dict[str, Any]],
    merged_rows: List[List[Any]],
    is_low_rise: bool,
) -> bool:
    """
    Kiểm tra xem danh sách căn sau khi hợp nhất (merged_rows) có thay đổi
    so với dữ liệu hiện có trên Google Sheet đích (existing_pool_by_key) hay không.
    Nếu không thay đổi (False) -> Có thể bỏ qua bước ghi đè Google Sheet để tiết kiệm Quota.
    """
    if len(existing_pool_by_key) != len(merged_rows):
        return True

    unit_col_idx = 2 if is_low_rise else 1
    target_len = 39 if is_low_rise else 32

    for row in merged_rows:
        if len(row) <= unit_col_idx:
            return True
        key = sanitize_unit_code(str(row[unit_col_idx] or ""))
        if not key or key not in existing_pool_by_key:
            return True
        old_row = existing_pool_by_key[key].get("row_values", [])
        # So sánh tất cả các cột nghiệp vụ từ cột 1 đến cột target_len - 2 (bỏ qua cột 0 STT)
        for col_idx in range(1, target_len - 1):
            new_v = _normalize_cell_for_diff(row[col_idx] if col_idx < len(row) else "")
            old_v = _normalize_cell_for_diff(old_row[col_idx] if col_idx < len(old_row) else "")
            if new_v != old_v:
                return True

    return False


def _load_env_if_needed():
    for p in [".env", os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass

def get_db_connection():
    """Tạo kết nối tới PostgreSQL của VHUB."""
    _load_env_if_needed()
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "5432")),
        user=os.environ.get("DB_USER", "lockcan"),
        password=os.environ.get("DB_PASSWORD", "LockCan_Pg_2026!Secure"),
        dbname=os.environ.get("DB_NAME", "vhub_hr_review_20261021"),
    )


DB_COLUMNS = [
    "id",
    "product_code",
    "project_id",
    "project_name",
    "product_type",
    "product_name",
    "subdivision_name",
    "building_code",
    "building_name",
    "apartment_type_name",
    "base_direction_name",
    "apartment_axis_code",
    "number_of_room",
    "number_of_wc",
    "number_of_floor",
    "floor_count",
    "floor_sort_order",
    "front_width",
    "land_area",
    "construction_area",
    "carpet_area",
    "built_up_area",
    "early_payment_price",
    "progress_payment_price",
    "loan_price",
    "total_price",
    "price_per_meter",
    "price_before_vat",
    "vat_amount",
    "maintenance_fee_amount",
    "construction_price_before_vat",
    "construction_vat_amount",
    "construction_maintenance_fee_amount",
    "construction_total",
    "land_price_before_vat",
    "land_vat_amount",
    "land_maintenance_fee_amount",
    "land_total",
    "supporting_banks",
    "delivery_standards",
    "x_sale_description",
    "gift",
    "notes_real_estate",
    "policy_date",
    "policy_code",
    "subdivision_id",
    "subdivision_code",
    "subdivision_resolution_status",
    "subdivision_resolution_version",
    "state_line",
    "state_line_name",
    "fund_groups_sell_name",
    "fund_type",
    "partner",
    "x_sale_link_summary",
    "x_sale_link_full",
    "x_link_layout_design",
    "product_images",
    "pricing_sheet_images",
    "computed_prices",
    "metadata",
    "is_not_show",
    "is_hot",
    "view_count",
    "favorite_count",
    "last_source_observed_at",
    "created_at",
    "updated_at",
]

UPSERT_SQL = f"""
INSERT INTO products ({", ".join(DB_COLUMNS)})
VALUES %s
ON CONFLICT (product_code, project_id) DO UPDATE SET
    project_name = EXCLUDED.project_name,
    product_type = EXCLUDED.product_type,
    subdivision_name = EXCLUDED.subdivision_name,
    subdivision_id = COALESCE(EXCLUDED.subdivision_id, products.subdivision_id),
    subdivision_code = COALESCE(EXCLUDED.subdivision_code, products.subdivision_code),
    subdivision_resolution_status = COALESCE(EXCLUDED.subdivision_resolution_status, products.subdivision_resolution_status),
    subdivision_resolution_version = COALESCE(EXCLUDED.subdivision_resolution_version, products.subdivision_resolution_version),
    building_code = EXCLUDED.building_code,
    building_name = EXCLUDED.building_name,
    apartment_type_name = EXCLUDED.apartment_type_name,
    base_direction_name = EXCLUDED.base_direction_name,
    apartment_axis_code = EXCLUDED.apartment_axis_code,
    number_of_room = EXCLUDED.number_of_room,
    number_of_wc = EXCLUDED.number_of_wc,
    number_of_floor = EXCLUDED.number_of_floor,
    floor_count = EXCLUDED.floor_count,
    floor_sort_order = EXCLUDED.floor_sort_order,
    front_width = EXCLUDED.front_width,
    land_area = EXCLUDED.land_area,
    construction_area = EXCLUDED.construction_area,
    carpet_area = EXCLUDED.carpet_area,
    built_up_area = EXCLUDED.built_up_area,
    early_payment_price = EXCLUDED.early_payment_price,
    progress_payment_price = EXCLUDED.progress_payment_price,
    loan_price = EXCLUDED.loan_price,
    total_price = EXCLUDED.total_price,
    price_per_meter = EXCLUDED.price_per_meter,
    price_before_vat = EXCLUDED.price_before_vat,
    vat_amount = EXCLUDED.vat_amount,
    maintenance_fee_amount = EXCLUDED.maintenance_fee_amount,
    construction_price_before_vat = EXCLUDED.construction_price_before_vat,
    construction_vat_amount = EXCLUDED.construction_vat_amount,
    construction_maintenance_fee_amount = EXCLUDED.construction_maintenance_fee_amount,
    construction_total = EXCLUDED.construction_total,
    land_price_before_vat = EXCLUDED.land_price_before_vat,
    land_vat_amount = EXCLUDED.land_vat_amount,
    land_maintenance_fee_amount = EXCLUDED.land_maintenance_fee_amount,
    land_total = EXCLUDED.land_total,
    supporting_banks = EXCLUDED.supporting_banks,
    delivery_standards = EXCLUDED.delivery_standards,
    x_sale_description = EXCLUDED.x_sale_description,
    gift = EXCLUDED.gift,
    notes_real_estate = EXCLUDED.notes_real_estate,
    policy_date = EXCLUDED.policy_date,
    policy_code = COALESCE(EXCLUDED.policy_code, products.policy_code),
    state_line = CASE
        WHEN products.lock_info IS NOT NULL AND EXCLUDED.state_line <> 'sold' THEN products.state_line
        ELSE EXCLUDED.state_line
    END,
    state_line_name = CASE
        WHEN products.lock_info IS NOT NULL AND EXCLUDED.state_line <> 'sold' THEN products.state_line_name
        ELSE EXCLUDED.state_line_name
    END,
    fund_groups_sell_name = EXCLUDED.fund_groups_sell_name,
    fund_type = EXCLUDED.fund_type,
    partner = EXCLUDED.partner,
    x_sale_link_summary = EXCLUDED.x_sale_link_summary,
    x_sale_link_full = EXCLUDED.x_sale_link_full,
    x_link_layout_design = EXCLUDED.x_link_layout_design,
    product_images = CASE
        WHEN jsonb_array_length(EXCLUDED.product_images) > 0 THEN EXCLUDED.product_images
        ELSE products.product_images
    END,
    pricing_sheet_images = CASE
        WHEN jsonb_array_length(EXCLUDED.pricing_sheet_images) > 0 THEN EXCLUDED.pricing_sheet_images
        ELSE products.pricing_sheet_images
    END,
    is_not_show = EXCLUDED.is_not_show,
    metadata = COALESCE(products.metadata, '{{}}'::jsonb) || EXCLUDED.metadata,
    last_source_observed_at = EXCLUDED.last_source_observed_at,
    updated_at = EXCLUDED.updated_at;
"""


def bulk_upsert_products_to_db(
    rows: List[List[Any]],
    project_key: str,
    is_low_rise: bool,
    sub_tab: Optional[str] = None,
    chunk_size: int = 250,
) -> Dict[str, Any]:
    """
    Thực hiện Bulk Upsert danh sách căn đã chuẩn hóa vào bảng 'products' trong PostgreSQL
    theo từng lô (chunking), xóa cache facet và phát tín hiệu NOTIFY.
    """
    project_id, project_name = resolve_vhub_project(project_key, sub_tab=sub_tab)
    conn = get_db_connection()
    try:
        catalog = load_subdivision_catalog(conn)
    except Exception:
        catalog = {}

    sync_start_time = datetime.now(VN_TZ)
    dedup_records: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        rec = map_merged_row_to_db_record(
            row=r,
            project_key=project_key,
            is_low_rise=is_low_rise,
            sub_tab=sub_tab,
            subdivision_catalog=catalog,
            now_ts=sync_start_time,
        )
        if not rec:
            continue
        code_key = rec["product_code"].strip().upper()
        dedup_records[code_key] = rec

    records = list(dedup_records.values())
    if not records:
        return {"project_id": project_id, "project_name": project_name, "upserted": 0, "reconciled": 0}

    json_cols = {"product_images", "pricing_sheet_images", "computed_prices", "metadata"}

    reconciled_count = 0
    try:
        with conn.cursor() as cur:
            for i in range(0, len(records), chunk_size):
                chunk = records[i : i + chunk_size]
                tuples = []
                for rec in chunk:
                    row_tuple = tuple(
                        Json(rec[col]) if col in json_cols else rec[col]
                        for col in DB_COLUMNS
                    )
                    tuples.append(row_tuple)
                execute_values(cur, UPSERT_SQL, tuples, page_size=chunk_size)

            # Ẩn / chuyển trạng thái các căn không còn tồn tại trong bảng hàng nguồn của dự án này
            if len(records) > 0:
                cur.execute(
                    """
                    UPDATE products
                    SET is_not_show = true,
                        state_line = CASE WHEN state_line = 'available' THEN 'sold' ELSE state_line END,
                        state_line_name = CASE WHEN state_line_name ILIKE %s THEN 'Đã bán' ELSE state_line_name END,
                        updated_at = %s
                    WHERE project_id = %s
                      AND (last_source_observed_at IS NULL OR last_source_observed_at < %s)
                      AND is_not_show = false;
                    """,
                    ("%còn hàng%", sync_start_time, project_id, sync_start_time),
                )
                reconciled_count = cur.rowcount if isinstance(cur.rowcount, int) else 0
                if reconciled_count > 0:
                    logger.info(
                        f"🧹 [DB Reconcile] Đã ẩn và cập nhật trạng thái {reconciled_count} căn không còn tồn tại "
                        f"trong bảng hàng nguồn (project_id='{project_id}')"
                    )

            # Xóa cache filter facet cũ của dự án để Backend tự động rebuild khi FE gọi
            cur.execute(
                "DELETE FROM project_filter_facets WHERE project_id = %s;",
                (project_id,),
            )

            # Phát tín hiệu PostgreSQL NOTIFY để Web API nhận biết cập nhật bảng hàng tức thì
            notify_payload = json.dumps(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "upserted": len(records),
                    "reconciled": reconciled_count,
                    "timestamp": datetime.now(VN_TZ).isoformat(),
                },
                ensure_ascii=False,
            )
            cur.execute("SELECT pg_notify('inventory_sync', %s);", (notify_payload,))

        conn.commit()
        logger.info(
            f"💾 [DB Direct Upsert] Đã đồng bộ {len(records)} căn (ẩn {reconciled_count} căn cũ) vào bảng 'products' "
            f"(project_id='{project_id}', chunk_size={chunk_size})"
        )
        return {
            "project_id": project_id,
            "project_name": project_name,
            "upserted": len(records),
            "reconciled": reconciled_count,
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Lỗi khi Bulk Upsert DB cho dự án '{project_id}': {e}", exc_info=True)
        raise
    finally:
        conn.close()
