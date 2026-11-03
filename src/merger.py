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
            cur_price_count = count_filled_prices(cur["row_values"], is_low_rise)
            item_price_count = count_filled_prices(item["row_values"], is_low_rise)

            # Kiểm tra xem từng nguồn có giá hợp lệ (Giá chưa VAT hoặc Giá full) hay không
            chua_idx = 7 if is_low_rise else 13
            full_idx = 10 if is_low_rise else 14
            cur_has_valid_price = bool(str(cur["row_values"][chua_idx] or '').strip() or str(cur["row_values"][full_idx] or '').strip())
            item_has_valid_price = bool(str(item["row_values"][chua_idx] or '').strip() or str(item["row_values"][full_idx] or '').strip())

            # 1. Nguồn có giá hợp lệ LUÔN được ưu tiên hơn nguồn không có giá
            if item_has_valid_price and not cur_has_valid_price:
                best_scanned_by_key[key] = item
            elif cur_has_valid_price and not item_has_valid_price:
                pass  # Giữ nguyên nguồn có giá
            else:
                # Cả 2 đều có giá (hoặc cả 2 đều không có giá)
                if item.get("is_exclusive") and not cur.get("is_exclusive"):
                    best_scanned_by_key[key] = item
                elif not item.get("is_exclusive") and cur.get("is_exclusive"):
                    pass
                elif item_price_count > cur_price_count:
                    best_scanned_by_key[key] = item

            # 2. Xử lý trạng thái hợp nhất:
            target = best_scanned_by_key[key]
            target_has_price = (item_has_valid_price or cur_has_valid_price)

            if not target_has_price:
                # Không có bất kỳ nguồn nào có giá -> Đã bán
                target["status"] = "Đã bán"
                target["row_values"][status_col_idx] = "Đã bán"
            else:
                # Có giá: Chỉ nhận 'Đã bán' nếu nguồn CÓ GIÁ đánh dấu Đã bán (đỏ/sold text)
                sold_from_priced = (
                    (item.get("status") == "Đã bán" and item_has_valid_price) or
                    (cur.get("status") == "Đã bán" and cur_has_valid_price)
                )
                if sold_from_priced:
                    target["status"] = "Đã bán"
                    target["row_values"][status_col_idx] = "Đã bán"
                elif (item.get("status") == "Đang lock" or cur.get("status") == "Đang lock"):
                    target["status"] = "Đang lock"
                    target["row_values"][status_col_idx] = "Đang lock"
                else:
                    target["status"] = "Còn hàng"
                    target["row_values"][status_col_idx] = "Còn hàng"

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
