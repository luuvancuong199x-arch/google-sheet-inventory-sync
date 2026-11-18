"""
Module gửi thông báo biến động sản phẩm qua Zalo Bot.
Tích hợp với hạ tầng Zalo notification sẵn có trong PostgreSQL:
- Bảng `notification_events` (sự kiện thông báo)
- Bảng `notification_deliveries` (hàng đợi gửi tin Zalo Bot)
- Bảng `tours_data` (lấy danh sách assignedNotificationUsers theo dự án)
- Bảng `zalo_account_links` (map user_id sang chat_id Zalo đang active)
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import zoneinfo

logger = logging.getLogger("zalo_notifier")
VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")


def get_assigned_zalo_recipients(cur, project_id: str) -> List[Dict[str, Any]]:
    """
    Truy vấn danh sách tài khoản Zalo active được phân quyền nhận thông báo theo dự án.
    Đọc từ `tours_data.ui_settings.assignedNotificationUsers` và map sang `zalo_account_links`.
    """
    try:
        cur.execute(
            """
            SELECT id, title, ui_settings, metadata, source_project_ids
            FROM tours_data
            WHERE id = %s OR (source_project_ids IS NOT NULL AND source_project_ids ? %s)
            """,
            (project_id, project_id),
        )
        rows = cur.fetchall()
        emails = set()
        for r in rows:
            _, _, ui_settings, _, _ = r
            ui = ui_settings or {}
            assigned = (
                ui.get("assignedNotificationUsers")
                or ui.get("assigned_notification_users")
                or []
            )
            for e in assigned:
                if e and isinstance(e, str):
                    emails.add(e.strip().lower())

        if not emails:
            return []

        cur.execute(
            """
            SELECT u.id, u.email, u.display_name, zal.chat_id
            FROM users u
            JOIN zalo_account_links zal ON zal.user_id = u.id
            WHERE lower(u.email) = ANY(%s) AND zal.status = 'active'
            """,
            (list(emails),),
        )
        recipients = []
        for r in cur.fetchall():
            recipients.append(
                {
                    "user_id": str(r[0]),
                    "email": r[1],
                    "display_name": r[2],
                    "chat_id": str(r[3]),
                }
            )
        return recipients
    except Exception as e:
        logger.error(f"Lỗi khi tra cứu người nhận Zalo cho dự án '{project_id}': {e}", exc_info=True)
        return []


def enqueue_zalo_notification(
    cur,
    project_id: str,
    event_type: str,
    text: str,
    dedupe_key: str,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Nạp thông báo vào `notification_events` và `notification_deliveries`.
    Backend vhub-be (@Cron 15s) sẽ tự động lấy từ bảng `notification_deliveries`
    để gửi tin nhắn Zalo tới các chat_id tương ứng.

    Trả về số lượng delivery jobs đã được tạo.
    """
    if not text or not project_id:
        return 0

    try:
        # 1. Kiểm tra trùng lặp dedupe_key
        cur.execute(
            "SELECT id FROM notification_events WHERE dedupe_key = %s LIMIT 1;",
            (dedupe_key,),
        )
        if cur.fetchone():
            logger.debug(f"Bỏ qua thông báo trùng dedupeKey: {dedupe_key}")
            return 0

        # 2. Lấy danh sách người nhận Zalo cho dự án
        recipients = get_assigned_zalo_recipients(cur, project_id)
        if not recipients:
            logger.info(
                f"ℹ️ Không có tài khoản Zalo active nào được gán quyền nhận thông báo cho dự án '{project_id}'"
            )
            return 0

        # 3. Tạo payload cho event
        payload = {
            "text": text[:1900],  # Giới hạn an toàn Zalo bot text (< 2000 chars)
            "projectScopedOnly": True,
            "groupKey": dedupe_key,
            "dedupeKeys": [dedupe_key],
        }
        if extra_payload:
            payload.update(extra_payload)

        event_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO notification_events (id, dedupe_key, event_type, project_id, payload, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW());
            """,
            (event_id, dedupe_key, event_type, project_id, json.dumps(payload, ensure_ascii=False)),
        )

        # 4. Tạo delivery jobs cho từng recipient
        enqueued_count = 0
        for rec in recipients:
            delivery_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO notification_deliveries
                    (id, event_id, user_id, chat_id, status, attempt_count, next_attempt_at, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'queued', 0, NOW(), NOW(), NOW());
                """,
                (delivery_id, event_id, rec["user_id"], rec["chat_id"]),
            )
            enqueued_count += 1

        logger.info(
            f"📢 [Zalo Notifier] Đã tạo event '{event_type}' ({enqueued_count} deliveries) "
            f"cho dự án '{project_id}' (dedupe: {dedupe_key})"
        )
        return enqueued_count
    except Exception as e:
        logger.error(
            f"❌ Lỗi khi nạp thông báo Zalo '{event_type}' cho dự án '{project_id}': {e}",
            exc_info=True,
        )
        return 0
