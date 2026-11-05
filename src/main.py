"""
CLI Runner điều phối toàn bộ pipeline đồng bộ 12 dự án bất động sản.
Hỗ trợ chạy đồng bộ toàn bộ (--all) hoặc chạy riêng từng dự án (--project "tên dự án").
Áp dụng kiến trúc Đích Kép (Dual-Destination):
- Đích 1: Ghi vào Google Sheets chuẩn hóa (khi có thay đổi dữ liệu).
- Đích 2: Bulk Upsert trực tiếp vào bảng 'products' trong PostgreSQL của VHUB (--write-db).
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

VN_TZ = timezone(timedelta(hours=7))

# Cấu hình UTF-8 cho console để in tiếng Việt chuẩn xác trên mọi OS (Windows/Linux)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.config import TARGET_PROJECTS, LOW_RISE_HEADERS, HIGH_RISE_HEADERS
from src.auth import get_sheets_service
from src.master_reader import get_project_agency_links, get_agency_links_from_target_sheet
from src.fetcher import fetch_all_agencies_for_project
from src.merger import smart_upsert_pool
from src.writer import read_existing_target_pool, write_normalized_inventory
from src.db_writer import bulk_upsert_products_to_db, has_inventory_changed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def ensure_default_local_credentials():
    """Tự động nạp file chứng chỉ mặc định của hệ thống VHUB nếu biến môi trường chưa được gán."""
    if os.environ.get("GCP_SA_KEY") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    candidates = [
        r"C:\Users\admin\.vhub-credentials\vhub-sheet-syn.json",
        "/root/vhub/secrets/vhub-sheet-syn.json",
    ]
    for cp in candidates:
        if os.path.exists(cp):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cp
            break


def sync_single_project(
    sheets_service,
    project_key: str,
    today_str: str,
    dry_run: bool = False,
    max_workers: int = 5,
    write_db: bool = False,
    force_sheet_write: bool = False
) -> dict:
    """Đồng bộ một dự án cụ thể (Đích Kép: Google Sheets + PostgreSQL)."""
    # Nếu gọi MAS CAO TẦNG tổng hợp, tự động điều phối đồng bộ cả 4 dự án thành viên
    if project_key.strip().upper() == 'MAS CAO TẦNG':
        mas_keys = ['MGC', 'MEL', 'HSG', 'LEP']
        total_units = 0
        total_db = 0
        total_dur = 0.0
        for mk in mas_keys:
            res = sync_single_project(
                sheets_service, mk, today_str, dry_run=dry_run,
                max_workers=max_workers, write_db=write_db,
                force_sheet_write=force_sheet_write
            )
            total_units += res.get("units", 0)
            total_db += res.get("db_upserted", 0)
            total_dur += res.get("duration", 0.0)
        return {
            "project": "Dự án MAS - Cao tầng (MGC, MEL, HSG, LEP)",
            "units": total_units,
            "db_upserted": total_db,
            "db_write_duration": 0.0,
            "sheet_skipped_no_diff": False,
            "duration": total_dur,
            "project_stats": overall_project_stats,
        }

    config = TARGET_PROJECTS.get(project_key)
    if not config:
        for k, v in TARGET_PROJECTS.items():
            if k.strip().lower() == project_key.strip().lower() or v.get('name', '').strip().lower() == project_key.strip().lower():
                project_key = k
                config = v
                break
    if not config:
        raise ValueError(f"Không tìm thấy cấu hình cho dự án: '{project_key}'")

    project_name = config['name']
    target_id = config['id']
    is_low_rise = (config['type'] == 'LOW_RISE')
    headers = LOW_RISE_HEADERS if is_low_rise else HIGH_RISE_HEADERS
    sub_tab = config.get('sub_tab')
    target_tab_name = config.get('target_tab', sub_tab or 'Bảng hàng chuẩn hóa')

    logger.info(f"==> BẮT ĐẦU ĐỒNG BỘ: {project_name} (ID: {target_id}, Tab: {target_tab_name})")
    start_time = time.time()
    total_units_updated = 0
    total_db_upserted = 0
    db_write_duration = 0.0
    sheet_skipped_no_diff = False
    overall_agency_stats = {}
    overall_link_sync_stats = {}
    overall_project_stats = {
        "total_units": 0, "new_today": 0, "sold_today": 0,
        "expiring_soon": 0, "avail": 0, "lock": 0, "sold": 0
    }

    existing_pool = read_existing_target_pool(
        sheets_service, target_id, target_tab_name, is_low_rise=is_low_rise
    )
    agency_links = get_agency_links_from_target_sheet(
        sheets_service, target_id, sub_tab=sub_tab
    )
    if not agency_links:
        agency_links = get_project_agency_links(
            sheets_service, project_key, sub_tab=sub_tab
        )
    logger.info(f"Tìm thấy {len(agency_links)} link đại lý cho dự án {project_name}")

    scanned, successful_agencies, link_sync_stats = fetch_all_agencies_for_project(
        sheets_service,
        agency_links,
        project_key,
        is_low_rise=is_low_rise,
        existing_pool_keys=set(existing_pool.keys()),
        today_str=today_str,
        max_workers=max_workers,
        return_link_stats=True
    )
    overall_link_sync_stats.update(link_sync_stats)

    merged_rows, stats = smart_upsert_pool(
        existing_pool, scanned, is_low_rise=is_low_rise, today_str=today_str,
        successful_agencies=successful_agencies, return_stats=True
    )

    overall_agency_stats = stats["agency_stats"]
    overall_project_stats = stats["project_stats"]
    total_units_updated = len(merged_rows)

    changed = has_inventory_changed(existing_pool, merged_rows, is_low_rise=is_low_rise)
    if not dry_run:
        if changed or force_sheet_write:
            write_normalized_inventory(
                sheets_service, target_id, target_tab_name, headers, merged_rows, is_low_rise=is_low_rise
            )
            logger.info(f"Đã cập nhật {total_units_updated} căn vào tab '{target_tab_name}'")
        else:
            sheet_skipped_no_diff = True
            logger.info(
                f"⚡ Dữ liệu '{project_name}' không thay đổi so với Sheet đích -> "
                f"Bỏ qua bước ghi đè Google Sheet (Tiết kiệm Quota & chống phình lịch sử)"
            )

        if write_db:
            t_db = time.time()
            db_res = bulk_upsert_products_to_db(
                rows=merged_rows,
                project_key=project_key,
                is_low_rise=is_low_rise,
                sub_tab=sub_tab,
            )
            db_write_duration += (time.time() - t_db)
            total_db_upserted += db_res.get("upserted", 0)

    logger.info(
        f"📊 Biến động trong ngày: 🟢 Căn mới hôm nay: +{overall_project_stats['new_today']} | "
        f"🔴 Chuyển Đã bán: {overall_project_stats['sold_today']} | "
        f"🟠 Sắp hết hạn (29 ngày): {overall_project_stats['expiring_soon']} | "
        f"📊 Tổng quỹ: {overall_project_stats['total_units']}"
    )

    if not dry_run and (not sheet_skipped_no_diff or force_sheet_write):
        try:
            from src.agency_directory import update_project_agency_directory
            update_project_agency_directory(
                sheets_service=sheets_service,
                project_key=project_key,
                sync_stats_lookup=overall_link_sync_stats,
                project_daily_stats={
                    "agency_stats": overall_agency_stats,
                    "project_stats": overall_project_stats
                },
                today_str=today_str
            )
        except Exception as e_dir:
            logger.warning(f"Lỗi khi cập nhật Danh mục Đại lý cho {project_name}: {e_dir}")

    duration = time.time() - start_time
    logger.info(
        f"✅ Hoàn tất dự án {project_name} trong {duration:.2f} giây! "
        f"(Tổng số căn: {total_units_updated}, DB Upserted: {total_db_upserted} trong {db_write_duration:.3f}s)"
    )
    return {
        "project": project_name,
        "units": total_units_updated,
        "db_upserted": total_db_upserted,
        "db_write_duration": db_write_duration,
        "sheet_skipped_no_diff": sheet_skipped_no_diff,
        "duration": duration,
        "project_stats": overall_project_stats,
    }


def main():
    parser = argparse.ArgumentParser(description="Hệ thống đồng bộ bảng hàng các dự án bất động sản")
    parser.add_argument("--all", action="store_true", help="Đồng bộ toàn bộ dự án")
    parser.add_argument("--project", type=str, help="Đồng bộ riêng 1 dự án (ví dụ: 'làng vân', 'VRI', 'MGC'...)")
    parser.add_argument("--dry-run", action="store_true", help="Chạy quét thử nghiệm, không ghi đè vào Sheet đích")
    parser.add_argument("--max-workers", type=int, default=5, help="Số luồng quét song song (mặc định 5)")
    parser.add_argument("--write-db", action="store_true", help="Ghi trực tiếp dữ liệu vào PostgreSQL bảng products")
    parser.add_argument("--force-sheet-write", action="store_true", help="Bắt buộc ghi lại Google Sheet kể cả khi không có diff")
    args = parser.parse_args()

    ensure_default_local_credentials()
    sheets_service = get_sheets_service()
    today_str = datetime.now(VN_TZ).strftime('%d/%m/%Y')
    overall_start = time.time()

    if args.project:
        sync_single_project(
            sheets_service,
            args.project,
            today_str=today_str,
            dry_run=args.dry_run,
            max_workers=args.max_workers,
            write_db=args.write_db,
            force_sheet_write=args.force_sheet_write
        )
    elif args.all or not args.project:
        logger.info("==================================================")
        logger.info("🚀 BẮT ĐẦU ĐỒNG BỘ TOÀN BỘ CÁC DỰ ÁN BẤT ĐỘNG SẢN")
        logger.info("==================================================")
        summary = []
        for p_key in TARGET_PROJECTS:
            try:
                res = sync_single_project(
                    sheets_service,
                    p_key,
                    today_str=today_str,
                    dry_run=args.dry_run,
                    max_workers=args.max_workers,
                    write_db=args.write_db,
                    force_sheet_write=args.force_sheet_write
                )
                summary.append(res)
            except Exception as e:
                logger.error(f"❌ Thất bại khi đồng bộ dự án '{p_key}': {e}")

        total_time = time.time() - overall_start
        total_units = sum(s['units'] for s in summary)
        total_db = sum(s.get('db_upserted', 0) for s in summary)
        logger.info("==================================================")
        logger.info(f"🎉 TỔNG KẾT: Đã đồng bộ {len(summary)}/{len(TARGET_PROJECTS)} dự án")
        logger.info(f"📊 Tổng số căn: {total_units} (DB Upserted: {total_db})")
        logger.info(f"⏱️ Tổng thời gian: {total_time:.2f} giây (~{total_time/60:.1f} phút)")
        logger.info("==================================================")


if __name__ == '__main__':
    main()
