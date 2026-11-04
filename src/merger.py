"""
Module hợp nhất dữ liệu thông minh và chống mất trắng dữ liệu.
Áp dụng cơ chế Upsert theo unitKey:
- Căn hộ quét được đợt này sẽ cập nhật giá, trạng thái, CSBH.
- Căn hộ trong dữ liệu cũ nếu đợt này đại lý của nó tạm thời lỗi mạng sẽ ĐƯỢC GIỮ NGUYÊN.
- Ưu tiên trạng thái Đã bán nếu bất kỳ nguồn nào đánh dấu Đã bán.
"""

import re
from typing import Dict, List, Any, Optional, Tuple, Union
from src.normalizer import sanitize_unit_code, compute_expiry_warning

def extract_clean_agency_name(val: Any) -> str:
    """Trích xuất tên đại lý thuần từ chuỗi thông thường hoặc từ công thức =HYPERLINK('url', 'Tên đại lý')."""
    if val is None:
        return ""
    val_str = str(val).strip()
    m = re.search(r'HYPERLINK\([^,;]+[,;]\s*["\']([^"\']+)["\']\)', val_str, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return val_str

def natural_sort_key(s: str) -> list:
    """Tách chuỗi và số để sắp xếp tự nhiên A-Z (VD: LK-2 đứng trước LK-10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s or ''))]

def make_sort_key(row: List[Any], is_low_rise: bool) -> tuple:
    """
    Tạo khóa sắp xếp đa cấp:
    - Cấp 1: Gom theo nhóm Quỹ (0: Quỹ chung - hiển thị đầu bảng, 1: Đại lý phân phối A-Z)
    - Cấp 2: Tên Đại lý (A-Z)
    - Cấp 3: Trong từng Đại lý/Quỹ chung: Trạng thái (1: Còn hàng, 2: Đang lock, 3: Đã bán)
    - Cấp 4: Trong cùng trạng thái: Mã căn A-Z (natural sort)
    """
    agency_col_idx = 36 if is_low_rise else 29
    status_col_idx = 31 if is_low_rise else 27
    unit_code_col_idx = 2 if is_low_rise else 1

    agency_raw = str(row[agency_col_idx] if len(row) > agency_col_idx else '')
    clean_agency = extract_clean_agency_name(agency_raw).strip().upper()

    is_qc = bool(re.search(r'quỹ chung|quy chung|quỹ cđt|quy cdt', clean_agency, re.IGNORECASE))
    group_rank = 0 if is_qc else 1

    status_raw = str(row[status_col_idx] if len(row) > status_col_idx else '').strip().lower()
    if 'còn' in status_raw or 'con' in status_raw:
        status_rank = 1
    elif 'lock' in status_raw:
        status_rank = 2
    elif 'bán' in status_raw or 'ban' in status_raw or 'sold' in status_raw:
        status_rank = 3
    else:
        status_rank = 4

    unit_code_raw = str(row[unit_code_col_idx] if len(row) > unit_code_col_idx else '').strip()

    return (group_rank, clean_agency, status_rank, natural_sort_key(unit_code_raw))

def count_filled_prices(row_values: List[Any], is_low_rise: bool) -> int:
    """Đếm số trường giá đã được điền thông tin."""
    start_idx = 7 if is_low_rise else 12
    end_idx = 22 if is_low_rise else 18
    count = 0
    for i in range(start_idx, min(end_idx + 1, len(row_values))):
        val = row_values[i]
        if val is not None and val != '':
            count += 1
    return count

def get_candidate_rank(
    item: Dict[str, Any],
    is_low_rise: bool,
    existing_owner: str = "",
    is_within_exclusive_period: bool = False
) -> tuple:
    """
    Xác định mức độ ưu tiên giữa các nguồn khi deduplicate cùng 1 mã căn:
    1. Có giá hợp lệ (Giá chưa VAT hoặc Giá full) -> Luôn ưu tiên hơn nguồn không có giá.
    2. Nguồn Quỹ chung chính thức (từ file Quỹ chung dự án) -> Thẩm quyền cao nhất với các căn thuộc giỏ chung.
    3. Nguồn Độc quyền -> Ưu tiên hơn các nguồn đại lý thông thường.
    4. Đại lý đang nắm giữ độc quyền hợp lệ (< 30 ngày) -> Ưu tiên bảo vệ không bị đại lý khác ghi đè.
    5. Nguồn có trạng thái Khả dụng ('Còn hàng' hoặc 'Đang lock') -> Ưu tiên hơn nguồn đánh dấu 'Đã bán'.
    6. Số lượng trường giá được điền đầy đủ hơn (độ chi tiết dữ liệu).
    """
    chua_idx = 7 if is_low_rise else 13
    full_idx = 10 if is_low_rise else 14
    has_valid_price = bool(str(item["row_values"][chua_idx] or '').strip() or str(item["row_values"][full_idx] or '').strip())
    is_exclusive = bool(item.get("is_exclusive"))

    item_agency = extract_clean_agency_name(item.get("agency_name") or '').strip().upper()
    is_official_qc = bool(re.search(r'quỹ chung|quy chung|quỹ cđt|quy cdt', item_agency, re.IGNORECASE))
    is_current_protected_owner = bool(is_within_exclusive_period and existing_owner and item_agency == existing_owner)

    is_active = (item.get("status") in ["Còn hàng", "Đang lock"])
    price_count = count_filled_prices(item["row_values"], is_low_rise)
    return (has_valid_price, is_official_qc, is_exclusive, is_current_protected_owner, is_active, price_count)

def smart_upsert_pool(
    existing_pool_by_key: Dict[str, Dict[str, Any]],
    scanned_units: List[Dict[str, Any]],
    is_low_rise: bool,
    today_str: str = '',
    successful_agencies: Optional[set] = None,
    return_stats: bool = False
) -> Union[List[List[Any]], Tuple[List[List[Any]], Dict[str, Any]]]:
    """
    Hợp nhất danh sách vừa quét (scanned_units) vào kho dữ liệu hiện có (existing_pool_by_key).
    BẢO TOÀN 100% dữ liệu cũ nếu đại lý gặp lỗi mạng/gián đoạn.
    CẬP NHẬT hoặc XÓA các dòng không còn tồn tại từ các đại lý đã quét thành công.
    Hỗ trợ trả về thống kê biến động ngày (return_stats=True).
    """
    target_len = 39 if is_low_rise else 32
    status_col_idx = 31 if is_low_rise else 27
    issue_date_col_idx = 37 if is_low_rise else 30
    expiry_col_idx = 38 if is_low_rise else 31
    agency_col_idx = 36 if is_low_rise else 29

    # 1. Deduplicate các căn vừa quét trong đợt này theo xếp hạng thẩm quyền
    best_scanned_by_key = {}
    for item in scanned_units:
        key = item["unit_key"]
        if not key:
            continue

        # Kiểm tra thông tin chủ sở hữu cũ trong existing_pool
        existing_owner = ""
        is_within_exclusive_period = False
        if key in existing_pool_by_key:
            old_row = existing_pool_by_key[key].get("row_values", [])
            old_ag_raw = old_row[agency_col_idx] if len(old_row) > agency_col_idx else ""
            existing_owner = extract_clean_agency_name(old_ag_raw).strip().upper()
            old_issue = old_row[issue_date_col_idx] if len(old_row) > issue_date_col_idx else ""
            if old_issue:
                exp_info = compute_expiry_warning(old_issue)
                days_el = exp_info.get("days_elapsed")
                if days_el is not None and days_el < 30:
                    is_within_exclusive_period = True

        if key not in best_scanned_by_key:
            best_scanned_by_key[key] = item
        else:
            cur = best_scanned_by_key[key]
            item_rank = get_candidate_rank(item, is_low_rise, existing_owner, is_within_exclusive_period)
            cur_rank = get_candidate_rank(cur, is_low_rise, existing_owner, is_within_exclusive_period)

            if item_rank > cur_rank:
                best_scanned_by_key[key] = item

    # Cập nhật trạng thái cho nguồn chiến thắng
    for key, target in best_scanned_by_key.items():
        chua_idx = 7 if is_low_rise else 13
        full_idx = 10 if is_low_rise else 14
        has_price = bool(str(target["row_values"][chua_idx] or '').strip() or str(target["row_values"][full_idx] or '').strip())
        if not has_price:
            target["status"] = "Đã bán"
            target["row_values"][status_col_idx] = "Đã bán"
        else:
            target["row_values"][status_col_idx] = target["status"]

    # 2. Khởi tạo kho dữ liệu tổng hợp dựa trên existing_pool
    # Bảo toàn các căn từ các đại lý gặp sự cố mạng (không nằm trong successful_agencies)
    master_pool = {}
    for key, data in existing_pool_by_key.items():
        row_vals = list(data.get("row_values", []))
        old_agency_raw = str(row_vals[agency_col_idx] if len(row_vals) > agency_col_idx else '').strip()
        clean_old_agency = extract_clean_agency_name(old_agency_raw)
        if successful_agencies and clean_old_agency in successful_agencies:
            continue
        # Bỏ qua các dòng dữ liệu rác cũ bị lệch cột ngày vào cột đại lý
        if re.match(r'^\d{2}/\d{2}/\d{4}$', clean_old_agency):
            continue

        # Đảm bảo đủ độ dài chuẩn
        while len(row_vals) < target_len:
            row_vals.append("")

        # Tính toán lại hạn cấp hàng cho các căn được bảo toàn
        old_issue = str(row_vals[issue_date_col_idx] or '').strip()
        if old_issue:
            exp_info = compute_expiry_warning(old_issue)
            row_vals[expiry_col_idx] = exp_info["display"]

        master_pool[key] = row_vals

    # 3. Cập nhật các căn vừa quét vào master_pool
    for key, item in best_scanned_by_key.items():
        scanned_row = list(item["row_values"])
        while len(scanned_row) < target_len:
            scanned_row.append("")

        if key in existing_pool_by_key:
            old_row = existing_pool_by_key[key].get("row_values", [])
            old_agency = extract_clean_agency_name(old_row[agency_col_idx] if len(old_row) > agency_col_idx else "").strip().upper()
            new_agency = extract_clean_agency_name(scanned_row[agency_col_idx] if len(scanned_row) > agency_col_idx else "").strip().upper()
            old_issue_date = old_row[issue_date_col_idx] if len(old_row) > issue_date_col_idx else ""

            if old_agency and new_agency and old_agency != new_agency:
                # Điều chuyển giỏ hàng sang đại lý mới hoặc Quỹ chung:
                # Reset ngày cấp hàng = ngày hiện tại để tính chu kỳ 30 ngày mới cho chủ sở hữu mới
                if today_str:
                    scanned_row[issue_date_col_idx] = today_str
            else:
                if not scanned_row[issue_date_col_idx] and old_issue_date:
                    scanned_row[issue_date_col_idx] = old_issue_date
        elif key in master_pool:
            old_issue_date = master_pool[key][issue_date_col_idx] if len(master_pool[key]) > issue_date_col_idx else ""
            if not scanned_row[issue_date_col_idx] and old_issue_date:
                scanned_row[issue_date_col_idx] = old_issue_date
        else:
            # Căn mới hoàn toàn
            if not scanned_row[issue_date_col_idx] and today_str:
                scanned_row[issue_date_col_idx] = today_str

        # Tính toán hạn cấp hàng
        cur_issue = str(scanned_row[issue_date_col_idx] or '').strip()
        if cur_issue:
            exp_info = compute_expiry_warning(cur_issue)
            scanned_row[expiry_col_idx] = exp_info["display"]

        master_pool[key] = scanned_row

    # 4. Thống kê biến động trong ngày (nếu return_stats=True)
    agency_stats = {}
    project_stats = {
        "total_units": 0,
        "new_today": 0,
        "sold_today": 0,
        "expiring_soon": 0,
        "avail": 0,
        "lock": 0,
        "sold": 0
    }

    if return_stats:
        for key, row in master_pool.items():
            st = str(row[status_col_idx] or '').strip()
            ag_raw = str(row[agency_col_idx] or '').strip()
            ag_name = extract_clean_agency_name(ag_raw).strip().upper()
            if not ag_name:
                ag_name = "KHÁC"

            if ag_name not in agency_stats:
                agency_stats[ag_name] = {
                    "total_units": 0,
                    "new_today": 0,
                    "sold_today": 0,
                    "expiring_soon": 0,
                    "avail": 0,
                    "lock": 0,
                    "sold": 0
                }

            agency_stats[ag_name]["total_units"] += 1
            project_stats["total_units"] += 1

            if st == "Còn hàng":
                agency_stats[ag_name]["avail"] += 1
                project_stats["avail"] += 1
            elif st == "Đang lock":
                agency_stats[ag_name]["lock"] += 1
                project_stats["lock"] += 1
            elif st == "Đã bán":
                agency_stats[ag_name]["sold"] += 1
                project_stats["sold"] += 1

            # Căn mới hôm nay
            issue_d = str(row[issue_date_col_idx] or '').strip()
            if (today_str and issue_d == today_str) or (key not in existing_pool_by_key):
                agency_stats[ag_name]["new_today"] += 1
                project_stats["new_today"] += 1

            # Chuyển Đã bán hôm nay
            if key in existing_pool_by_key:
                old_row = existing_pool_by_key[key].get("row_values", [])
                old_st = str(old_row[status_col_idx] or '').strip() if len(old_row) > status_col_idx else ""
                if old_st and old_st != "Đã bán" and st == "Đã bán":
                    agency_stats[ag_name]["sold_today"] += 1
                    project_stats["sold_today"] += 1

            # Sắp hết hạn (mốc 29 ngày)
            expiry_val = str(row[expiry_col_idx] or '')
            if st in ["Còn hàng", "Đang lock"] and "⚠️ Sắp hết hạn" in expiry_val:
                agency_stats[ag_name]["expiring_soon"] += 1
                project_stats["expiring_soon"] += 1

    # 5. Xuất danh sách dòng, sắp xếp đa cấp (Đại lý -> Trạng thái -> Mã căn A-Z) và đánh STT 1..N
    final_rows = [row for row in master_pool.values() if row]
    final_rows.sort(key=lambda r: make_sort_key(r, is_low_rise))

    for idx, row in enumerate(final_rows):
        row[0] = idx + 1

    if return_stats:
        return final_rows, {"agency_stats": agency_stats, "project_stats": project_stats}
    return final_rows
