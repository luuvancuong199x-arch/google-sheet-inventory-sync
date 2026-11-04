"""
CLI Runner điều phối toàn bộ pipeline đồng bộ 12 dự án bất động sản.
Hỗ trợ chạy đồng bộ toàn bộ (--all) hoặc chạy riêng từng dự án (--project "tên dự án").
"""

import sys
import time
import argparse
import logging
from datetime import datetime
from typing import Optional

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def sync_single_project(
    sheets_service,
    project_key: str,
    today_str: str,
    dry_run: bool = False,
    max_workers: int = 5
) -> dict:
    """Đồng bộ một dự án cụ thể."""
    config = TARGET_PROJECTS.get(project_key)
    if not config:
        raise ValueError(f"Không tìm thấy cấu hình cho dự án: '{project_key}'")

    project_name = config['name']
    target_id = config['id']
    is_low_rise = (config['type'] == 'LOW_RISE')
    headers = LOW_RISE_HEADERS if is_low_rise else HIGH_RISE_HEADERS

    logger.info(f"==> BẮT ĐẦU ĐỒNG BỘ: {project_name} (ID: {target_id})")
    start_time = time.time()
    total_units_updated = 0
    overall_agency_stats = {}
    overall_project_stats = {
        "total_units": 0, "new_today": 0, "sold_today": 0,
        "expiring_soon": 0, "avail": 0, "lock": 0, "sold": 0
    }

    if project_key == 'MAS CAO TẦNG' and config.get('sub_tabs'):
        for sub_tab in config['sub_tabs']:
            logger.info(f"--- Đang xử lý phân khu MAS: {sub_tab} ---")
            existing_pool = read_existing_target_pool(
                sheets_service, target_id, sub_tab, is_low_rise=False
            )
            agency_links = get_agency_links_from_target_sheet(
                sheets_service, target_id, sub_tab=sub_tab
            )
            if not agency_links:
                agency_links = get_project_agency_links(
                    sheets_service, project_key, sub_tab=sub_tab
                )
            logger.info(f"Tìm thấy {len(agency_links)} link đại lý cho phân khu {sub_tab}")

            scanned, successful_agencies = fetch_all_agencies_for_project(
                sheets_service,
                agency_links,
                project_key,
                is_low_rise=False,
                existing_pool_keys=set(existing_pool.keys()),
                today_str=today_str,
                max_workers=max_workers
            )

            merged_rows, stats = smart_upsert_pool(
                existing_pool, scanned, is_low_rise=False, today_str=today_str,
                successful_agencies=successful_agencies, return_stats=True
            )

            for ag, a_s in stats["agency_stats"].items():
                if ag not in overall_agency_stats:
                    overall_agency_stats[ag] = {
                        "total_units": 0, "new_today": 0, "sold_today": 0,
                        "expiring_soon": 0, "avail": 0, "lock": 0, "sold": 0
                    }
                for k in overall_agency_stats[ag]:
                    overall_agency_stats[ag][k] += a_s.get(k, 0)
                overall_agency_stats[(ag, sub_tab.strip().upper())] = a_s

            for k in overall_project_stats:
                overall_project_stats[k] += stats["project_stats"].get(k, 0)

            if not dry_run:
                write_normalized_inventory(
                    sheets_service, target_id, sub_tab, headers, merged_rows, is_low_rise=False
                )
            total_units_updated += len(merged_rows)
            logger.info(f"Đã cập nhật {len(merged_rows)} căn vào tab '{sub_tab}'")
    else:
        target_tab_name = 'Bảng hàng chuẩn hóa'
        existing_pool = read_existing_target_pool(
            sheets_service, target_id, target_tab_name, is_low_rise=is_low_rise
        )
        agency_links = get_agency_links_from_target_sheet(
            sheets_service, target_id, sub_tab=None
        )
        if not agency_links:
            agency_links = get_project_agency_links(
                sheets_service, project_key, sub_tab=None
            )
        logger.info(f"Tìm thấy {len(agency_links)} link đại lý cho dự án {project_name}")

        scanned, successful_agencies = fetch_all_agencies_for_project(
            sheets_service,
            agency_links,
            project_key,
            is_low_rise=is_low_rise,
            existing_pool_keys=set(existing_pool.keys()),
            today_str=today_str,
            max_workers=max_workers
        )

        merged_rows, stats = smart_upsert_pool(
            existing_pool, scanned, is_low_rise=is_low_rise, today_str=today_str,
            successful_agencies=successful_agencies, return_stats=True
        )

        overall_agency_stats = stats["agency_stats"]
        overall_project_stats = stats["project_stats"]

        if not dry_run:
            write_normalized_inventory(
                sheets_service, target_id, target_tab_name, headers, merged_rows, is_low_rise=is_low_rise
            )
        total_units_updated = len(merged_rows)
        logger.info(f"Đã cập nhật {total_units_updated} căn vào tab '{target_tab_name}'")

    logger.info(
        f"📊 Biến động trong ngày: 🟢 Căn mới hôm nay: +{overall_project_stats['new_today']} | "
        f"🔴 Chuyển Đã bán: {overall_project_stats['sold_today']} | "
        f"🟠 Sắp hết hạn (29 ngày): {overall_project_stats['expiring_soon']} | "
        f"📊 Tổng quỹ: {overall_project_stats['total_units']}"
    )

    if not dry_run:
        try:
            from src.agency_directory import update_project_agency_directory
            update_project_agency_directory(
                sheets_service=sheets_service,
                project_key=project_key,
                project_daily_stats={
                    "agency_stats": overall_agency_stats,
                    "project_stats": overall_project_stats
                },
                today_str=today_str
            )
        except Exception as e_dir:
            logger.warning(f"Lỗi khi cập nhật Danh mục Đại lý cho {project_name}: {e_dir}")

    duration = time.time() - start_time
    logger.info(f"✅ Hoàn tất dự án {project_name} trong {duration:.2f} giây! (Tổng số căn: {total_units_updated})")
    return {
        "project": project_name,
        "units": total_units_updated,
        "duration": duration
    }

def main():
    parser = argparse.ArgumentParser(description="Hệ thống đồng bộ bảng hàng 12 dự án bất động sản")
    parser.add_argument("--all", action="store_true", help="Đồng bộ toàn bộ 12 dự án")
    parser.add_argument("--project", type=str, help="Đồng bộ riêng 1 dự án (ví dụ: 'làng vân', 'VRI'...)")
    parser.add_argument("--dry-run", action="store_true", help="Chạy quét thử nghiệm, không ghi đè vào Sheet đích")
    parser.add_argument("--max-workers", type=int, default=5, help="Số luồng quét song song (mặc định 5)")
    args = parser.parse_args()

    sheets_service = get_sheets_service()
    today_str = datetime.now().strftime('%d/%m/%Y')
    overall_start = time.time()

    if args.project:
        sync_single_project(
            sheets_service,
            args.project,
            today_str=today_str,
            dry_run=args.dry_run,
            max_workers=args.max_workers
        )
    elif args.all or not args.project:
        logger.info("==================================================")
        logger.info("🚀 BẮT ĐẦU ĐỒNG BỘ TOÀN BỘ 12 DỰ ÁN BẤT ĐỘNG SẢN")
        logger.info("==================================================")
        summary = []
        for p_key in TARGET_PROJECTS:
            try:
                res = sync_single_project(
                    sheets_service,
                    p_key,
                    today_str=today_str,
                    dry_run=args.dry_run,
                    max_workers=args.max_workers
                )
                summary.append(res)
            except Exception as e:
                logger.error(f"❌ Thất bại khi đồng bộ dự án '{p_key}': {e}")

        total_time = time.time() - overall_start
        total_units = sum(s['units'] for s in summary)
        logger.info("==================================================")
        logger.info(f"🎉 TỔNG KẾT: Đã đồng bộ {len(summary)}/{len(TARGET_PROJECTS)} dự án")
        logger.info(f"📊 Tổng số căn: {total_units}")
        logger.info(f"⏱️ Tổng thời gian: {total_time:.2f} giây (~{total_time/60:.1f} phút)")
        logger.info("==================================================")

if __name__ == '__main__':
    main()
