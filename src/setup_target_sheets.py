"""
Script tự động khởi tạo 12 file Google Trang tính đích mới và cấp quyền chia sẻ.

Chức năng:
1. Tự động tạo 12 file Google Sheets mới toanh trên tài khoản Google Cloud của bạn.
2. Thiết lập đúng cấu trúc:
   - 9 dự án Thấp tầng: Tab 'Bảng hàng chuẩn hóa' với đầy đủ 38 cột chuẩn.
   - 2 dự án Cao tầng (MIK OCP, Q9): Tab 'Bảng hàng chuẩn hóa' với đầy đủ 31 cột chuẩn.
   - Dự án MAS Cao Tầng: Tự động tạo sẵn 4 tabs (MGC, MEL, HSG, LEP) với 31 cột chuẩn mỗi tab.
3. Cấp quyền chỉnh sửa (Editor/Writer) cho email Google cá nhân của bạn để bạn toàn quyền quản lý, xem và chia sẻ.
4. Tự động cập nhật 12 ID mới này vào file 'src/config.py'.
"""

import sys
import os
import re
import argparse
import logging
from typing import Dict, List, Any

# Cấu hình UTF-8 console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.auth import get_sheets_service, get_drive_service
from src.config import TARGET_PROJECTS, LOW_RISE_HEADERS, HIGH_RISE_HEADERS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def build_sheet_spec(title: str, headers: List[str]) -> Dict[str, Any]:
    """Tạo thông số sheet kèm header."""
    return {
        'properties': {
            'title': title,
            'gridProperties': {
                'frozenRowCount': 1
            }
        },
        'data': [
            {
                'startRow': 0,
                'startColumn': 0,
                'rowData': [
                    {
                        'values': [
                            {
                                'userEnteredValue': {'stringValue': h},
                                'userEnteredFormat': {
                                    'textFormat': {'bold': True},
                                    'backgroundColor': {'red': 0.9, 'green': 0.93, 'blue': 0.98}
                                }
                            }
                            for h in headers
                        ]
                    }
                ]
            }
        ]
    }

def create_target_spreadsheet(
    sheets_service: Any,
    drive_service: Any,
    project_key: str,
    project_info: Dict[str, Any],
    share_email: str = None,
    public_link: bool = True
) -> Dict[str, str]:
    """Tạo 1 Google Spreadsheet mới kèm cấu trúc tab và phân quyền."""
    project_name = project_info['name']
    is_low_rise = (project_info['type'] == 'LOW_RISE')
    headers = LOW_RISE_HEADERS if is_low_rise else HIGH_RISE_HEADERS

    if project_key == 'MAS CAO TẦNG':
        sheets_specs = [
            build_sheet_spec(tab_name, headers)
            for tab_name in project_info.get('sub_tabs', ['MGC', 'MEL', 'HSG', 'LEP'])
        ]
    else:
        sheets_specs = [build_sheet_spec('Bảng hàng chuẩn hóa', headers)]

    create_body = {
        'properties': {
            'title': f"Bảng Hàng Chuẩn Hóa - {project_name}"
        },
        'sheets': sheets_specs
    }

    # 1. Tạo file Google Spreadsheet mới
    resp = sheets_service.spreadsheets().create(body=create_body).execute()
    new_id = resp['spreadsheetId']
    new_url = f"https://docs.google.com/spreadsheets/d/{new_id}/edit"
    logger.info(f"Đã tạo file mới: '{project_name}' -> ID: {new_id}")

    # 2. Cấp quyền chia sẻ cho Email Google cá nhân của bạn (Editor)
    if share_email:
        try:
            drive_service.permissions().create(
                fileId=new_id,
                body={
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': share_email.strip()
                },
                fields='id',
                sendNotificationEmail=False
            ).execute()
            logger.info(f"   + Đã cấp quyền chỉnh sửa (Editor) cho: {share_email}")
        except Exception as e:
            logger.warning(f"   ! Không thể cấp quyền cho email {share_email}: {e}")

    # 3. Mở quyền xem hoặc sửa qua link (nếu bật public_link)
    if public_link:
        try:
            drive_service.permissions().create(
                fileId=new_id,
                body={
                    'type': 'anyone',
                    'role': 'reader'
                },
                fields='id'
            ).execute()
            logger.info(f"   + Đã mở quyền xem công khai qua liên kết")
        except Exception as e:
            logger.warning(f"   ! Lỗi mở quyền xem liên kết: {e}")

    return {
        'key': project_key,
        'name': project_name,
        'id': new_id,
        'url': new_url
    }

def update_config_file_with_new_ids(new_project_ids: Dict[str, str], config_path: str = "src/config.py"):
    """Cập nhật các ID mới vào file src/config.py."""
    if not os.path.exists(config_path):
        logger.error(f"Không tìm thấy file cấu hình {config_path}")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for proj_key, new_id in new_project_ids.items():
        # Tìm pattern dạng: 'làng vân': { 'id': '...',
        pattern = rf"('{re.escape(proj_key)}':\s*\{{\s*'id':\s*')([^']+)'"
        replacement = rf"\g<1>{new_id}'"
        content = re.sub(pattern, replacement, content)

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)

    logger.info(f"✅ Đã tự động cập nhật 12 ID mới vào file '{config_path}'")

def main():
    parser = argparse.ArgumentParser(description="Tự động tạo 12 Google Sheets đích mới và phân quyền")
    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="Email Google cá nhân của bạn để nhận quyền chỉnh sửa (Editor) cho 12 file (ví dụ: yourname@gmail.com)"
    )
    parser.add_argument(
        "--public",
        action="store_true",
        default=True,
        help="Cho phép ai có link cũng có thể xem bảng hàng (mặc định: True)"
    )
    args = parser.parse_args()

    sheets_service = get_sheets_service()
    drive_service = get_drive_service()

    logger.info("==================================================")
    logger.info(f"🚀 BẮT ĐẦU TỰ ĐỘNG KHỞI TẠO 12 FILE GOOGLE TRANG TÍNH ĐÍCH")
    logger.info(f"👤 Cấp quyền quản lý cho Email: {args.email}")
    logger.info("==================================================")

    created_sheets = []
    id_map = {}

    for proj_key, proj_info in TARGET_PROJECTS.items():
        try:
            res = create_target_spreadsheet(
                sheets_service=sheets_service,
                drive_service=drive_service,
                project_key=proj_key,
                project_info=proj_info,
                share_email=args.email,
                public_link=args.public
            )
            created_sheets.append(res)
            id_map[proj_key] = res['id']
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo file cho dự án '{proj_key}': {e}")

    # Cập nhật ID mới vào src/config.py
    if id_map:
        update_config_file_with_new_ids(id_map)

    # In bảng tổng kết
    print("\n" + "=" * 80)
    print("🎉 DANH MỤC 12 FILE GOOGLE TRANG TÍNH ĐÍCH MỚI ĐÃ TẠO THÀNH CÔNG:")
    print("=" * 80)
    for idx, item in enumerate(created_sheets, 1):
        print(f"{idx:2d}. {item['name']:<25} : {item['url']}")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    main()
