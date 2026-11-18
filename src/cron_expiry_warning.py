"""
Cron script: Cảnh báo căn sắp đến hạn thu hồi (Còn 1 ngày / Ngày thứ 29).
Chạy định kỳ vào đầu phiên làm việc lúc 08:00 AM mỗi sáng (Giờ Việt Nam).
Áp dụng cho TOÀN BỘ các căn trong mỗi dự án (không phân biệt loại quỹ).
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import zoneinfo

# Đảm bảo import được các module trong src dù script được gọi từ đâu
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.db_writer import get_db_connection
from src.zalo_notifier import enqueue_zalo_notification

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cron_expiry_warning")
VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")


def run_expiry_warning_check(force: bool = False) -> Dict[str, Any]:
    """
    Quét toàn bộ cơ sở dữ liệu để tìm các căn:
    - Chưa bán (state_line != 'sold')
    - Sắp đến hạn thu: 'Còn 1 ngày' HOẶC ngày thứ 29 tính từ allocationDate
    Và gửi thông báo Zalo tới các tài khoản phụ trách dự án đó.
    """
    now_vn = datetime.now(VN_TZ)
    today_str = now_vn.strftime("%Y-%m-%d")
    logger.info(f"🚀 Bắt đầu quét cảnh báo hạn thu căn lúc {now_vn.strftime('%H:%M:%S %d/%m/%Y')} (VN)")

    conn = get_db_connection()
    stats = {"total_projects": 0, "total_units": 0, "enqueued_deliveries": 0}

    try:
        with conn.cursor() as cur:
            # 1. Truy vấn các căn sắp đến hạn thu hồi trên toàn bộ hệ thống
            query = """
                SELECT 
                    p.project_id,
                    COALESCE(t.title, p.project_name, p.project_id) as project_title,
                    p.product_code,
                    COALESCE(p.subdivision_name, '') as subdivision,
                    COALESCE(p.fund_groups_sell_name, 'Quỹ chung') as fund_name,
                    COALESCE(p.metadata->>'partner', '') as partner,
                    p.metadata->>'allocationDate' as alloc_date,
                    p.metadata->>'expiryWarning' as expiry_warning
                FROM products p
                LEFT JOIN tours_data t ON t.id = p.project_id
                WHERE p.state_line != 'sold'
                  AND p.is_not_show = false
                  AND (
                    p.metadata->>'expiryWarning' ILIKE '%Còn 1 ngày%'
                    OR (
                        p.metadata->>'allocationDate' IS NOT NULL 
                        AND (CURRENT_DATE - (p.metadata->>'allocationDate')::date) = 29
                    )
                  )
                ORDER BY p.project_id, p.product_code;
            """
            cur.execute(query)
            rows = cur.fetchall()

            if not rows:
                logger.info("✅ Không có căn nào sắp đến hạn thu (còn 1 ngày) trong ngày hôm nay.")
                return stats

            # 2. Gom nhóm theo dự án
            grouped: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                p_id = r[0]
                p_title = r[1]
                if p_id not in grouped:
                    grouped[p_id] = {
                        "title": p_title,
                        "units": [],
                    }
                grouped[p_id]["units"].append(
                    {
                        "code": r[2],
                        "subdivision": r[3],
                        "fund": r[4],
                        "partner": r[5],
                        "alloc_date": r[6],
                        "expiry": r[7],
                    }
                )

            stats["total_projects"] = len(grouped)
            stats["total_units"] = len(rows)

            # 3. Gửi thông báo cho từng dự án
            for p_id, p_info in grouped.items():
                units = p_info["units"]
                p_title = p_info["title"]
                count = len(units)

                preview_lines = []
                for u in units[:25]:
                    detail_parts = [u["code"]]
                    if u["subdivision"]:
                        detail_parts.append(u["subdivision"])
                    fund_disp = u["partner"] if u["partner"] else u["fund"]
                    if fund_disp:
                        detail_parts.append(fund_disp)
                    if u["alloc_date"]:
                        detail_parts.append(f"Vào ngày: {u['alloc_date']}")
                    preview_lines.append(f"  · {' | '.join(detail_parts)}")

                if count > 25:
                    preview_lines.append(f"  · ... và {count - 25} căn khác")

                text = (
                    f"⏰ Cảnh báo căn sắp đến hạn thu hồi (Còn 1 ngày)\n"
                    f"· Dự án: {p_title}\n"
                    f"· Số lượng: {count} căn sắp đến hạn thu\n"
                    f"· Danh sách căn:\n" + "\n".join(preview_lines) + "\n"
                    f"· Ghi chú: Vui lòng rà soát và xử lý trước khi hệ thống tự động thu hồi căn!\n"
                    f"Truy cập: https://vhub.com.vn/"
                )

                dedupe_key = f"daily-expiry:{p_id}:{today_str}"
                if force:
                    dedupe_key = f"{dedupe_key}:force-{int(now_vn.timestamp())}"

                enqueued = enqueue_zalo_notification(
                    cur=cur,
                    project_id=p_id,
                    event_type="product_exclusive_expiring",
                    text=text,
                    dedupe_key=dedupe_key,
                    extra_payload={
                        "project_title": p_title,
                        "expiring_count": count,
                        "expiring_codes": [u["code"] for u in units],
                    },
                )
                stats["enqueued_deliveries"] += enqueued

            conn.commit()
            logger.info(
                f"🎉 Hoàn tất quét hạn thu căn: {stats['total_projects']} dự án, "
                f"{stats['total_units']} căn, đã nạp {stats['enqueued_deliveries']} tin nhắn Zalo."
            )
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Lỗi khi chạy quét cảnh báo hạn thu căn: {e}", exc_info=True)
        raise
    finally:
        conn.close()

    return stats


if __name__ == "__main__":
    force_run = "--force" in sys.argv
    run_expiry_warning_check(force=force_run)
