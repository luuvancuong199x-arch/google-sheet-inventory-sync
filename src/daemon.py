"""
Micro-Daemon chạy nền cho hệ thống đồng bộ bảng hàng VHUB (Phương án B).
Tích hợp cơ chế Quét thích ứng (Adaptive Polling):
- Khung giờ cao điểm (08:00 – 18:00): Nghỉ 120s (chu kỳ ~2–3 phút/lần).
- Khung giờ tối (18:00 – 22:00): Nghỉ 300s (chu kỳ ~5–6 phút/lần).
- Khung giờ đêm (22:00 – 08:00): Nghỉ 1800s (chu kỳ ~30 phút/lần).
Giải phóng bộ nhớ (gc.collect) sau mỗi chu kỳ quét để giữ RAM ở mức tối thiểu.
"""

import gc
import os
import sys
import time
import argparse
import logging
from datetime import datetime, timezone, timedelta

VN_TZ = timezone(timedelta(hours=7))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import TARGET_PROJECTS
from src.auth import get_sheets_service
from src.main import ensure_default_local_credentials, sync_single_project

logger = logging.getLogger(__name__)


def get_adaptive_interval_sec(now_dt: datetime) -> int:
    """Trả về thời gian nghỉ (giây) giữa 2 chu kỳ quét tùy theo khung giờ."""
    hour = now_dt.hour
    if 8 <= hour < 18:
        return 120   # 2 phút (giờ hành chính cao điểm)
    if 18 <= hour < 22:
        return 300   # 5 phút (giờ buổi tối)
    return 1800      # 30 phút (giờ ban đêm)


def get_process_memory_mb() -> float:
    """Đo mức sử dụng RAM hiện tại (Working Set / RSS) của tiến trình Python (MB)."""
    try:
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        get_cur_proc = ctypes.windll.kernel32.GetCurrentProcess
        get_cur_proc.restype = wintypes.HANDLE
        handle = get_cur_proc()
        get_mem_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_mem_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        get_mem_info.restype = wintypes.BOOL
        if get_mem_info(handle, ctypes.byref(pmc), pmc.cb):
            return pmc.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return 0.0


def run_daemon(
    project_key: str = "",
    max_workers: int = 5,
    once: bool = False,
    write_db: bool = True,
):
    ensure_default_local_credentials()
    cycle = 0
    while True:
        cycle += 1
        now_dt = datetime.now(VN_TZ)
        today_str = now_dt.strftime("%d/%m/%Y")
        mem_before = get_process_memory_mb()
        logger.info(
            f"🔄 [Daemon Cycle #{cycle}] Bắt đầu lúc {now_dt.strftime('%H:%M:%S %d/%m/%Y')} "
            f"(RAM trước quét: {mem_before:.1f} MB)"
        )

        try:
            sheets_service = get_sheets_service()
            if project_key:
                sync_single_project(
                    sheets_service=sheets_service,
                    project_key=project_key,
                    today_str=today_str,
                    dry_run=False,
                    max_workers=max_workers,
                    write_db=write_db,
                )
            else:
                for p_key in TARGET_PROJECTS:
                    try:
                        sync_single_project(
                            sheets_service=sheets_service,
                            project_key=p_key,
                            today_str=today_str,
                            dry_run=False,
                            max_workers=max_workers,
                            write_db=write_db,
                        )
                    except Exception as p_err:
                        logger.error(f"❌ Lỗi dự án '{p_key}' trong chu kỳ #{cycle}: {p_err}")
        except Exception as err:
            logger.error(f"❌ Lỗi chu kỳ Daemon #{cycle}: {err}")

        gc.collect()
        mem_after = get_process_memory_mb()
        logger.info(f"🧹 Đã giải phóng bộ nhớ sau chu kỳ #{cycle} (RAM hiện tại: {mem_after:.1f} MB)")

        if once:
            break

        sleep_sec = get_adaptive_interval_sec(datetime.now(VN_TZ))
        logger.info(f"⏳ Chờ {sleep_sec}s trước chu kỳ tiếp theo (Adaptive Polling)...")
        time.sleep(sleep_sec)


def main():
    parser = argparse.ArgumentParser(description="Micro-Daemon đồng bộ bảng hàng VHUB")
    parser.add_argument("--project", type=str, default="", help="Tên dự án cụ thể (để trống = chạy cả 12 dự án)")
    parser.add_argument("--max-workers", type=int, default=5, help="Số luồng quét song song (5-8)")
    parser.add_argument("--once", action="store_true", help="Chỉ chạy đúng 1 chu kỳ rồi thoát")
    parser.add_argument("--no-write-db", action="store_true", help="Tắt ghi DB PostgreSQL")
    args = parser.parse_args()

    run_daemon(
        project_key=args.project,
        max_workers=args.max_workers,
        once=args.once,
        write_db=not args.no_write_db,
    )


if __name__ == "__main__":
    main()
