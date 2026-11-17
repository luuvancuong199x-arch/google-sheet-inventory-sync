"""
Module xử lý mở rộng link media từ Google Drive theo quy tắc chuẩn:
1. Phát hiện link thư mục Google Drive (drive.google.com/drive/folders/...).
2. Truy vấn danh sách file trong thư mục qua Google Drive API kèm cơ chế cache bộ nhớ & disk persistence.
3. Nguyên tắc xử lý ảnh:
   - Không tự ý phân tách riêng các ảnh trong cùng một folder thành các trường riêng biệt.
   - Nếu có giá trị cụ thể ở cột riêng biệt (ví dụ: cột Ảnh PTG có link riêng) thì mới ghi riêng vào cột đó.
   - Trường hợp folder chứa nhiều ảnh (ở cột gộp PTG/Ảnh chỉ căn hoặc media chung): đọc toàn bộ các link file
     bên trong và ghi vào cột Ảnh chỉ căn / product_images dạng nhiều link như bình thường.
4. Tạo link view trực tiếp dạng https://drive.google.com/file/d/{file_id}/view?usp=drivesdk.
"""

import os
import re
import time
import json
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Regex nhận diện Google Drive Folder URL hoặc Folder ID
DRIVE_FOLDER_REGEX = re.compile(
    r'(?:drive\.google\.com/(?:drive/(?:u/\d+/)?folders/|open\?id=|folderview\?id=)|(?:^|/)folders/)([a-zA-Z0-9_-]{15,})',
    re.IGNORECASE
)

_CACHE_LOCK = threading.Lock()
_FOLDER_MEDIA_CACHE: Dict[str, Any] = {}
_CACHE_INITIALIZED = False
_thread_local = threading.local()

CACHE_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "drive_folder_cache.json"
)


def get_thread_drive_service():
    """Mỗi thread sở hữu một instance Google Drive API riêng biệt để tránh OpenSSL data race."""
    if not hasattr(_thread_local, 'drive_service') or _thread_local.drive_service is None:
        try:
            from src.auth import get_drive_service
            _thread_local.drive_service = get_drive_service()
        except Exception as e:
            logger.warning(f"Không thể khởi tạo Drive service cho luồng: {e}")
            _thread_local.drive_service = None
    return _thread_local.drive_service


def _execute_api_call(call, max_retries=3):
    for attempt in range(max_retries):
        try:
            return call.execute()
        except Exception as e:
            err = str(e)
            if ("429" in err or "RATE_LIMIT_EXCEEDED" in err) and attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise e


def extract_drive_folder_id(url_or_id: str) -> Optional[str]:
    """Trích xuất ID thư mục Google Drive từ URL hoặc chuỗi ID."""
    if not url_or_id or not isinstance(url_or_id, str):
        return None
    s = url_or_id.strip()
    m = DRIVE_FOLDER_REGEX.search(s)
    if m:
        return m.group(1)
    if re.match(r'^[a-zA-Z0-9_-]{20,}$', s):
        return s
    return None


def init_cache_if_needed():
    """Tải cache từ file JSON trên đĩa nếu tồn tại."""
    global _CACHE_INITIALIZED, _FOLDER_MEDIA_CACHE
    if _CACHE_INITIALIZED:
        return
    with _CACHE_LOCK:
        if _CACHE_INITIALIZED:
            return
        if os.path.exists(CACHE_FILE_PATH):
            try:
                with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        _FOLDER_MEDIA_CACHE.update(data)
                        logger.info(f"Đã nạp {len(_FOLDER_MEDIA_CACHE)} thư mục Drive từ disk cache: {CACHE_FILE_PATH}")
            except Exception as e:
                logger.warning(f"Không thể đọc file cache {CACHE_FILE_PATH}: {e}")
        _CACHE_INITIALIZED = True


def save_cache_to_disk():
    """Ghi cache hiện tại ra file JSON trên đĩa."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
        tmp_path = f"{CACHE_FILE_PATH}.tmp"
        with _CACHE_LOCK:
            cache_copy = dict(_FOLDER_MEDIA_CACHE)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cache_copy, f, ensure_ascii=False, indent=2)
        if os.path.exists(CACHE_FILE_PATH):
            try:
                os.remove(CACHE_FILE_PATH)
            except OSError:
                pass
        os.rename(tmp_path, CACHE_FILE_PATH)
    except Exception as e:
        logger.warning(f"Không thể lưu cache ra đĩa ({CACHE_FILE_PATH}): {e}")


def fetch_drive_folder_files(
    folder_id: str,
    drive_service: Optional[Any] = None
) -> List[str]:
    """
    Truy vấn Google Drive API để lấy toàn bộ danh sách file trong thư mục.
    Tương thích với cả định dạng cache cũ và mới.
    """
    init_cache_if_needed()

    with _CACHE_LOCK:
        if folder_id in _FOLDER_MEDIA_CACHE:
            entry = _FOLDER_MEDIA_CACHE[folder_id]
            if isinstance(entry, list):
                return list(entry)
            if isinstance(entry, dict):
                urls = []
                for u in entry.get("all_files", []):
                    if u not in urls:
                        urls.append(u)
                for u in entry.get("chi_can", []) + entry.get("ptg", []):
                    if u not in urls:
                        urls.append(u)
                if urls:
                    return urls

    if drive_service is None:
        drive_service = get_thread_drive_service()
    if drive_service is None:
        return []

    try:
        call = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType)",
            pageSize=50
        )
        resp = _execute_api_call(call)
        files = resp.get("files", [])
        urls = [
            f"https://drive.google.com/file/d/{f['id']}/view?usp=drivesdk"
            for f in files if f.get('id')
        ]

        with _CACHE_LOCK:
            _FOLDER_MEDIA_CACHE[folder_id] = urls

        return urls
    except Exception as e:
        logger.warning(f"Lỗi khi đọc thư mục Drive {folder_id}: {e}")
        return []


def prefetch_drive_folders(
    folder_urls_or_ids: List[str],
    drive_service: Optional[Any] = None,
    max_workers: int = 5
):
    """Quét trước danh sách thư mục Drive song song và lưu vào cache."""
    init_cache_if_needed()

    unique_folder_ids = set()
    for item in folder_urls_or_ids:
        fid = extract_drive_folder_id(item)
        if fid:
            with _CACHE_LOCK:
                if fid not in _FOLDER_MEDIA_CACHE:
                    unique_folder_ids.add(fid)

    if not unique_folder_ids:
        return

    logger.info(f"Đang prefetch {len(unique_folder_ids)} thư mục Google Drive song song ({max_workers} luồng)...")

    newly_fetched = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_drive_folder_files, fid, None): fid
            for fid in unique_folder_ids
        }
        for future in as_completed(futures):
            try:
                res = future.result()
                if res:
                    newly_fetched += 1
            except Exception as e:
                fid = futures[future]
                logger.debug(f"Prefetch lỗi cho {fid}: {e}")

    if newly_fetched > 0:
        save_cache_to_disk()
        logger.info(f"Đã cập nhật và lưu {newly_fetched} thư mục Drive mới vào disk cache.")


def expand_and_classify_media_urls(
    chican_urls: Optional[List[str]] = None,
    ptg_urls: Optional[List[str]] = None,
    combined_urls: Optional[List[str]] = None,
    drive_service: Optional[Any] = None
) -> Tuple[List[str], List[str]]:
    """
    Quy tắc chuẩn hóa link media theo yêu cầu:
    1. Không tự tách riêng các ảnh trong folder thành các trường riêng biệt.
    2. Nếu có giá trị cụ thể ở cột riêng (cột Ảnh PTG hoặc cột Ảnh chỉ căn) thì ghi vào cột tương ứng.
    3. Trường hợp folder chứa nhiều ảnh (ở cột gộp PTG/Ảnh chỉ căn hoặc media chung),
       đọc toàn bộ các link trong đó và ghi vào final_chican (cột product_images) dạng nhiều link.
    4. Trả về (final_chican, final_ptg).
    """
    final_chican: List[str] = []
    final_ptg: List[str] = []

    def add_chican(u: str):
        if u and u not in final_chican:
            final_chican.append(u)

    def add_ptg(u: str):
        if u and u not in final_ptg:
            final_ptg.append(u)

    # 1. Xử lý các link từ cột Chỉ căn (nếu có)
    for u in (chican_urls or []):
        if not u or not isinstance(u, str):
            continue
        u_clean = u.strip()
        fid = extract_drive_folder_id(u_clean)
        if fid:
            files = fetch_drive_folder_files(fid, drive_service=drive_service)
            if files:
                for f_url in files:
                    add_chican(f_url)
            else:
                add_chican(u_clean)
        else:
            add_chican(u_clean)

    # 2. Xử lý các link từ cột gộp (PTG/Ảnh chỉ căn hoặc media chung)
    # Toàn bộ file trong folder gộp được đọc và lưu vào final_chican (product_images) dạng nhiều link
    for u in (combined_urls or []):
        if not u or not isinstance(u, str):
            continue
        u_clean = u.strip()
        fid = extract_drive_folder_id(u_clean)
        if fid:
            files = fetch_drive_folder_files(fid, drive_service=drive_service)
            if files:
                for f_url in files:
                    add_chican(f_url)
            else:
                add_chican(u_clean)
        else:
            add_chican(u_clean)

    # 3. Xử lý các link cụ thể từ cột PTG (chỉ ghi khi có giá trị cụ thể tại cột này)
    for u in (ptg_urls or []):
        if not u or not isinstance(u, str):
            continue
        u_clean = u.strip()
        fid = extract_drive_folder_id(u_clean)
        if fid:
            files = fetch_drive_folder_files(fid, drive_service=drive_service)
            if files:
                for f_url in files:
                    add_ptg(f_url)
            else:
                add_ptg(u_clean)
        else:
            add_ptg(u_clean)

    return final_chican, final_ptg
