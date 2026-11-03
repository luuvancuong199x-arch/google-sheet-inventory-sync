"""
Module hợp nhất dữ liệu thông minh và chống mất trắng dữ liệu.
Áp dụng cơ chế Upsert theo unitKey:
- Căn hộ quét được đợt này sẽ cập nhật giá, trạng thái, CSBH.
- Căn hộ trong dữ liệu cũ nếu đợt này đại lý của nó tạm thời lỗi mạng sẽ ĐƯỢC GIỮ NGUYÊN.
- Ưu tiên trạng thái Đã bán nếu bất kỳ nguồn nào đánh dấu Đã bán.
"""

import re
from typing import Dict, List, Any, Optional
from src.normalizer import sanitize_unit_code

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

def smart_upsert_pool(
    existing_pool_by_key: Dict[str, Dict[str, Any]],
    scanned_units: List[Dict[str, Any]],
    is_low_rise: bool,
    today_str: str = '',
    successful_agencies: Optional[set] = None
) -> List[List[Any]]:
    """
    Hợp nhất danh sách vừa quét (scanned_units) vào kho dữ liệu hiện có (existing_pool_by_key).
    BẢO TOÀN 100% dữ liệu cũ nếu đại lý gặp lỗi mạng/gián đoạn.
    CẬP NHẬT hoặc XÓA các dòng không còn tồn tại từ các đại lý đã quét thành công.
    """
    status_col_idx = 31 if is_low_rise else 27
    issue_date_col_idx = 37 if is_low_rise else 30
    agency_col_idx = 36 if is_low_rise else 29

    # 1. Deduplicate các căn vừa quét trong đợt này
    best_scanned_by_key = {}
    for item in scanned_units:
        key = item["unit_key"]
        if not key:
            continue

        if key not in best_scanned_by_key:
            best_scanned_by_key[key] = item
        else:
            cur = best_scanned_by_key[key]
            # Nếu một trong các đại lý đánh dấu Đã bán -> Ghi nhận Đã bán
            if item.get("status") == "Đã bán":
                cur["status"] = "Đã bán"
                cur["row_values"][status_col_idx] = "Đã bán"
            elif item.get("status") == "Đang lock" and cur.get("status") != "Đã bán":
                cur["status"] = "Đang lock"
                cur["row_values"][status_col_idx] = "Đang lock"

            # Ưu tiên nguồn Quỹ Độc Quyền
            if item.get("is_exclusive") and not cur.get("is_exclusive"):
                if cur.get("status") in ["Đã bán", "Đang lock"]:
                    item["row_values"][status_col_idx] = cur.get("status")
                    item["status"] = cur.get("status")
                best_scanned_by_key[key] = item
            elif item.get("is_exclusive") == cur.get("is_exclusive"):
                # Ưu tiên nguồn có nhiều cột giá chi tiết hơn
                if count_filled_prices(item["row_values"], is_low_rise) > count_filled_prices(cur["row_values"], is_low_rise):
                    if cur.get("status") in ["Đã bán", "Đang lock"]:
                        item["row_values"][status_col_idx] = cur.get("status")
                        item["status"] = cur.get("status")
                    best_scanned_by_key[key] = item

    # 2. Khởi tạo kho dữ liệu tổng hợp dựa trên existing_pool
    # Bảo toàn các căn từ các đại lý gặp sự cố mạng (không nằm trong successful_agencies)
    master_pool = {}
    for key, data in existing_pool_by_key.items():
        row_vals = list(data.get("row_values", []))
        old_agency = str(row_vals[agency_col_idx] if len(row_vals) > agency_col_idx else '').strip()
        if successful_agencies and old_agency in successful_agencies:
            continue
        # Bỏ qua các dòng dữ liệu rác cũ bị lệch cột ngày vào cột đại lý
        if re.match(r'^\d{2}/\d{2}/\d{4}$', old_agency):
            continue
        master_pool[key] = row_vals

    # 3. Cập nhật các căn vừa quét vào master_pool
    for key, item in best_scanned_by_key.items():
        scanned_row = list(item["row_values"])
        if key in master_pool:
            # Nếu căn đã có: Cập nhật thông tin, nhưng giữ nguyên Ngày cấp hàng ban đầu nếu nguồn này để trống
            old_issue_date = master_pool[key][issue_date_col_idx] if len(master_pool[key]) > issue_date_col_idx else ""
            if not scanned_row[issue_date_col_idx] and old_issue_date:
                scanned_row[issue_date_col_idx] = old_issue_date
            master_pool[key] = scanned_row
        else:
            # Căn mới hoàn toàn
            if not scanned_row[issue_date_col_idx] and today_str:
                scanned_row[issue_date_col_idx] = today_str
            master_pool[key] = scanned_row

    # 4. Xuất danh sách dòng và đánh số thứ tự (STT) từ 1 đến N
    final_rows = []
    # Sắp xếp các căn theo mã căn để bảng hàng luôn ngay ngắn
    sorted_keys = sorted(master_pool.keys())
    for idx, key in enumerate(sorted_keys):
        row = master_pool[key]
        if row:
            row[0] = idx + 1
            final_rows.append(row)

    return final_rows
