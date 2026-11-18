from unittest.mock import MagicMock, patch
import pytest

from src.zalo_notifier import get_assigned_zalo_recipients, enqueue_zalo_notification


def test_get_assigned_zalo_recipients():
    mock_cur = MagicMock()
    # Mock tours_data row
    mock_cur.fetchall.side_effect = [
        # First call: tours_data query
        [
            ("vhb", "Vinhomes Hai Van Bay", {"assignedNotificationUsers": ["user1@test.com", "user2@test.com"]}, {}, None)
        ],
        # Second call: users & zalo_account_links query
        [
            ("u-1", "user1@test.com", "User One", "chat-111"),
            ("u-2", "user2@test.com", "User Two", "chat-222"),
        ]
    ]

    recipients = get_assigned_zalo_recipients(mock_cur, "vhb")
    assert len(recipients) == 2
    assert recipients[0]["chat_id"] == "chat-111"
    assert recipients[1]["email"] == "user2@test.com"


def test_enqueue_zalo_notification_skips_duplicate():
    mock_cur = MagicMock()
    # dedupe_key exists
    mock_cur.fetchone.return_value = ("existing-id",)

    count = enqueue_zalo_notification(
        mock_cur,
        project_id="vhb",
        event_type="sheet_sold_confirmed",
        text="Test message",
        dedupe_key="dedupe-123",
    )
    assert count == 0
    # Should not insert
    assert not any("INSERT INTO notification_events" in str(call) for call in mock_cur.execute.call_args_list)


def test_enqueue_zalo_notification_creates_deliveries():
    mock_cur = MagicMock()
    # dedupe_key does not exist
    mock_cur.fetchone.return_value = None

    with patch("src.zalo_notifier.get_assigned_zalo_recipients") as mock_recipients:
        mock_recipients.return_value = [
            {"user_id": "u-1", "chat_id": "chat-111", "email": "u1@test.com", "display_name": "U1"},
            {"user_id": "u-2", "chat_id": "chat-222", "email": "u2@test.com", "display_name": "U2"},
        ]

        count = enqueue_zalo_notification(
            mock_cur,
            project_id="vhb",
            event_type="sheet_sold_confirmed",
            text="🔴 Căn đã bán",
            dedupe_key="dedupe-new-123",
        )

        assert count == 2
        insert_event_calls = [c for c in mock_cur.execute.call_args_list if "INSERT INTO notification_events" in str(c)]
        assert len(insert_event_calls) == 1
        insert_deliv_calls = [c for c in mock_cur.execute.call_args_list if "INSERT INTO notification_deliveries" in str(c)]
        assert len(insert_deliv_calls) == 2
