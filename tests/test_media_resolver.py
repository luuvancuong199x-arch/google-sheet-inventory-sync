"""
Unit tests cho src/media_resolver.py theo quy tắc mới:
- Không tách riêng các ảnh trong folder ra các trường riêng.
- Toàn bộ link file trong folder được lưu vào product_images (cột ảnh chỉ căn).
- Cột PTG chỉ ghi khi có giá trị cụ thể tại cột PTG.
"""

import pytest
from src.media_resolver import (
    extract_drive_folder_id,
    fetch_drive_folder_files,
    expand_and_classify_media_urls,
    _FOLDER_MEDIA_CACHE,
    _CACHE_LOCK
)


def test_extract_drive_folder_id():
    url1 = "https://drive.google.com/drive/folders/1JI2Pc3sb0T0zh0v5ZmrnmIcto1y23GFN"
    assert extract_drive_folder_id(url1) == "1JI2Pc3sb0T0zh0v5ZmrnmIcto1y23GFN"

    url2 = "https://drive.google.com/drive/u/1/folders/1a5NU8h8fXIPUDNrscC1Uo02ASLYILpl2?usp=sharing"
    assert extract_drive_folder_id(url2) == "1a5NU8h8fXIPUDNrscC1Uo02ASLYILpl2"

    url3 = "https://drive.google.com/open?id=1S-Ne_OvDT3SFCnj-VI5BpxO7rebM-9-v"
    assert extract_drive_folder_id(url3) == "1S-Ne_OvDT3SFCnj-VI5BpxO7rebM-9-v"

    url4 = "/folders/1A9d7MZxleTqLlXnEddefRmpvIWPqYsBM"
    assert extract_drive_folder_id(url4) == "1A9d7MZxleTqLlXnEddefRmpvIWPqYsBM"

    file_url = "https://drive.google.com/file/d/1DQXnZj_6CtYSkm80X30Lx0UXnDU1d1wd/view"
    assert extract_drive_folder_id(file_url) is None

    assert extract_drive_folder_id("") is None
    assert extract_drive_folder_id(None) is None


def test_expand_and_classify_media_urls_all_folder_files_to_chican():
    fid = "test_folder_cache_all_files_001"
    file1 = "https://drive.google.com/file/d/img_layout_111/view?usp=drivesdk"
    file2 = "https://drive.google.com/file/d/img_ptg_222/view?usp=drivesdk"
    with _CACHE_LOCK:
        _FOLDER_MEDIA_CACHE[fid] = [file1, file2]

    folder_url = f"https://drive.google.com/drive/folders/{fid}"
    # Đưa folder vào combined_urls (cột PTG/Ảnh chỉ căn gộp)
    c_out, p_out = expand_and_classify_media_urls(
        chican_urls=[],
        ptg_urls=[],
        combined_urls=[folder_url]
    )

    # Toàn bộ ảnh trong folder phải nằm trong c_out (product_images)
    assert len(c_out) == 2
    assert file1 in c_out
    assert file2 in c_out

    # Không tự ý tách file2 sang p_out (cột PTG) khi không có giá trị cụ thể ở cột PTG
    assert len(p_out) == 0


def test_expand_and_classify_media_urls_with_explicit_ptg():
    fid = "test_folder_cache_explicit_002"
    file1 = "https://drive.google.com/file/d/img_layout_aaa/view?usp=drivesdk"
    file2 = "https://drive.google.com/file/d/img_layout_bbb/view?usp=drivesdk"
    with _CACHE_LOCK:
        _FOLDER_MEDIA_CACHE[fid] = [file1, file2]

    folder_url = f"https://drive.google.com/drive/folders/{fid}"
    explicit_ptg = "https://drive.google.com/file/d/explicit_ptg_link_999/view?usp=drive_link"

    c_out, p_out = expand_and_classify_media_urls(
        chican_urls=[],
        ptg_urls=[explicit_ptg],
        combined_urls=[folder_url]
    )

    # Folder files vào c_out
    assert len(c_out) == 2
    assert file1 in c_out
    assert file2 in c_out

    # Explicit PTG được ghi nhận riêng vào p_out
    assert len(p_out) == 1
    assert p_out[0] == explicit_ptg


def test_expand_and_classify_media_urls_backward_compat_cache():
    fid = "test_compat_old_cache_003"
    with _CACHE_LOCK:
        _FOLDER_MEDIA_CACHE[fid] = {
            "chi_can": ["https://drive.google.com/file/d/old_chi_can/view"],
            "ptg": ["https://drive.google.com/file/d/old_ptg/view"]
        }

    folder_url = f"https://drive.google.com/drive/folders/{fid}"
    c_out, p_out = expand_and_classify_media_urls(
        chican_urls=[],
        ptg_urls=[],
        combined_urls=[folder_url]
    )

    # Đọc được cả chi_can và ptg từ cache cũ và gộp toàn bộ vào c_out
    assert len(c_out) == 2
    assert "old_chi_can" in c_out[0]
    assert "old_ptg" in c_out[1]
    assert len(p_out) == 0
