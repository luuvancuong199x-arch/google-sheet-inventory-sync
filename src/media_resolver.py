"""
Module xử lý mở rộng và phân loại link media từ Google Drive:
1. Phát hiện link thư mục Google Drive (drive.google.com/drive/folders/...).
2. Truy vấn danh sách file trong thư mục qua Google Drive API kèm cơ chế cache bộ nhớ & disk persistence.
3. Phân loại thông minh:
   - File PNG / tỷ lệ dọc (h > w) / tên chứa PTG -> Ảnh Phiếu tính giá (pricing_sheet_images / Cột 37).
   - File JPG / tỷ lệ ngang (w > h) / tên chứa layout / chỉ căn -> Ảnh chỉ căn (product_images / Cột 36).
4. Tạo link view trực tiếp dạng https://drive.google.com/file/d/{file_id}/view?usp=drivesdk.
"""

import os
import re
import time
import json
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Regex nhận diện Google Drive Folder URL hoặc Folder ID
DRIVE_FOLDER_REGEX = re.compile(
    r'(?:drive\.google\.com/(?:drive/(?:u/\d+/)?folders/|open\?id=|folderview\?id=)|(?:^|/)folders/)([a-zA-Z0-9_-]{15,})',
    re.IGNORECASE
)

# Regex phân loại tên file
PTG_NAME_REGEX = re.compile(r'ptg|phiếu\s*tính|phieu\s*tinh|bảng\s*tính|bang\s*tinh', re.IGNORECASE)
CHICAN_NAME_REGEX = re.compile(r'chỉ\s*căn|chi\s*can|mặt\s*bằng|mat\s*bang|layout|sơ\s*đồ|so\s*do|vi_tri', re.IGNORECASE)

_CACHE_LOCK = threading.Lock()
_FOLDER_MEDIA_CACHE: Dict[str, Dict[str, List[str]]] = {}
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


def classify_folder_files(files: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Phân loại danh sách file trong thư mục Drive thành:
    - chi_can: Ảnh chỉ căn (Layout, mặt bằng vị trí căn)
    - ptg: Phiếu tính giá (PTG)
    """
    chi_can_urls = []
    ptg_urls = []

    for f in files:
        file_id = f.get('id')
        if not file_id:
            continue
        name = str(f.get('name', '')).strip()
        mime = str(f.get('mimeType', '')).strip().lower()
        meta = f.get('imageMediaMetadata', {}) or {}
        w = int(meta.get('width', 0) or 0)
        h = int(meta.get('height', 0) or 0)

        view_url = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"

        # Phân loại theo tên file hoặc định dạng PDF
        if PTG_NAME_REGEX.search(name) or name.lower().endswith('.pdf'):
            ptg_urls.append(view_url)
            continue
        if CHICAN_NAME_REGEX.search(name):
            chi_can_urls.append(view_url)
            continue

        # Phân loại theo tỷ lệ khung hình thực tế
        if w > 0 and h > 0:
            if h > w:
                # Ảnh dọc (portrait, tỷ lệ > 1) -> Phiếu tính giá
                ptg_urls.append(view_url)
            else:
                # Ảnh ngang (landscape, tỷ lệ <= 1) -> Mặt bằng chỉ căn
                chi_can_urls.append(view_url)
            continue

        # Phân loại fallback theo đuôi mở rộng phổ biến
        name_lower = name.lower()
        if name_lower.endswith('.png'):
            ptg_urls.append(view_url)
        elif name_lower.endswith(('.jpg', '.jpeg', '.webp')):
            chi_can_urls.append(view_url)
        else:
            chi_can_urls.append(view_url)

    # Nếu chỉ có 1 ảnh duy nhất trong folder mà một bên rỗng -> gán cho bên còn lại
    if len(files) == 1 and files[0].get('id'):
        single_url = f"https://drive.google.com/file/d/{files[0]['id']}/view?usp=drivesdk"
        if not chi_can_urls:
            chi_can_urls.append(single_url)
        if not ptg_urls:
            ptg_urls.append(single_url)

    return {
        "chi_can": chi_can_urls,
        "ptg": ptg_urls
    }


def fetch_drive_folder_media(
    folder_id: str,
    drive_service: Optional[Any] = None
) -> Dict[str, List[str]]:
    """Truy vấn Google Drive API để lấy và phân loại danh sách file trong thư mục."""
    init_cache_if_needed()

    with _CACHE_LOCK:
        if folder_id in _FOLDER_MEDIA_CACHE:
            return _FOLDER_MEDIA_CACHE[folder_id]

    if drive_service is None:
        drive_service = get_thread_drive_service()
    if drive_service is None:
        return {"chi_can": [], "ptg": []}

    try:
        call = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType, imageMediaMetadata)",
            pageSize=50
        )
        resp = _execute_api_call(call)
        files = resp.get("files", [])
        classified = classify_folder_files(files)

        with _CACHE_LOCK:
            _FOLDER_MEDIA_CACHE[folder_id] = classified

        return classified
    except Exception as e:
        logger.warning(f"Lỗi khi đọc thư mục Drive {folder_id}: {e}")
        return {"chi_can": [], "ptg": []}


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
    # Mỗi worker thread trong executor tự sử dụng instance drive_service riêng qua get_thread_drive_service()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_drive_folder_media, fid, None): fid
            for fid in unique_folder_ids
        }
        for future in as_completed(futures):
            try:
                res = future.result()
                if res.get("chi_can") or res.get("ptg"):
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
    Mở rộng tất cả link thư mục Drive thành các file ảnh cụ thể, phân loại thành:
    - final_chican: [link_chi_can_1, ...]
    - final_ptg: [link_ptg_1, ...]
    Nếu gặp URL dạng thư mục: thay thế bằng các file bên trong thư mục.
    Nếu không mở rộng được (lỗi Drive): giữ nguyên link thư mục gốc.
    """
    final_chican: List[str] = []
    final_ptg: List[str] = []

    def process_url(u: str, hint_type: str):
        if not u or not isinstance(u, str):
            return
        u_clean = u.strip()
        fid = extract_drive_folder_id(u_clean)
        if fid:
            media = fetch_drive_folder_media(fid, drive_service=drive_service)
            chi_can_files = media.get("chi_can", [])
            ptg_files = media.get("ptg", [])

            if chi_can_files or ptg_files:
                for c in chi_can_files:
                    if c not in final_chican:
                        final_chican.append(c)
                for p in ptg_files:
                    if p not in final_ptg:
                        final_ptg.append(p)
                return
            # Nếu folder rỗng hoặc không đọc được, fallback giữ link folder gốc
            if hint_type == "chi_can" and u_clean not in final_chican:
                final_chican.append(u_clean)
            elif hint_type == "ptg" and u_clean not in final_ptg:
                final_ptg.append(u_clean)
            elif hint_type == "combined":
                if u_clean not in final_chican:
                    final_chican.append(u_clean)
            return

        # Là link file thông thường
        if hint_type == "chi_can":
            if u_clean not in final_chican:
                final_chican.append(u_clean)
        elif hint_type == "ptg":
            if u_clean not in final_ptg:
                final_ptg.append(u_clean)
        elif hint_type == "combined":
            # Phân loại link file trong cột gộp
            u_lower = u_clean.lower()
            if PTG_NAME_REGEX.search(u_lower) or u_lower.endswith('.pdf') or 'ptg' in u_lower:
                if u_clean not in final_ptg:
                    final_ptg.append(u_clean)
            elif CHICAN_NAME_REGEX.search(u_lower) or 'mat_bang' in u_lower:
                if u_clean not in final_chican:
                    final_chican.append(u_clean)
            else:
                # Không rõ -> đưa vào cả 2 hoặc chỉ căn
                if u_clean not in final_chican:
                    final_chican.append(u_clean)

    for u in (chican_urls or []):
        process_url(u, "chi_can")

    for u in (ptg_urls or []):
        process_url(u, "ptg")

    for u in (combined_urls or []):
        process_url(u, "combined")

    return final_chican, final_ptg
