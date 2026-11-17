"""
Unit tests cho src/media_resolver.py
"""

import pytest
from src.media_resolver import (
    extract_drive_folder_id,
    classify_folder_files,
    expand_and_classify_media_urls,
    _FOLDER_MEDIA_CACHE,
    _CACHE_LOCK
)


def test_extract_drive_folder_id():
    # URL tiêu chuẩn
    url1 = "https://drive.google.com/drive/folders/1JI2Pc3sb0T0zh0v5ZmrnmIcto1y23GFN"
    assert extract_drive_folder_id(url1) == "1JI2Pc3sb0T0zh0v5ZmrnmIcto1y23GFN"

    # URL có query params và /u/0/
    url2 = "https://drive.google.com/drive/u/1/folders/1a5NU8h8fXIPUDNrscC1Uo02ASLYILpl2?usp=sharing"
    assert extract_drive_folder_id(url2) == "1a5NU8h8fXIPUDNrscC1Uo02ASLYILpl2"

    # URL open?id=
    url3 = "https://drive.google.com/open?id=1S-Ne_OvDT3SFCnj-VI5BpxO7rebM-9-v"
    assert extract_drive_folder_id(url3) == "1S-Ne_OvDT3SFCnj-VI5BpxO7rebM-9-v"

    # Đường dẫn tương đối /folders/...
    url4 = "/folders/1A9d7MZxleTqLlXnEddefRmpvIWPqYsBM"
    assert extract_drive_folder_id(url4) == "1A9d7MZxleTqLlXnEddefRmpvIWPqYsBM"

    # Link file trực tiếp không được nhận diện nhầm là folder
    file_url = "https://drive.google.com/file/d/1DQXnZj_6CtYSkm80X30Lx0UXnDU1d1wd/view"
    assert extract_drive_folder_id(file_url) is None

    # Chuỗi rỗng / None
    assert extract_drive_folder_id("") is None
    assert extract_drive_folder_id(None) is None


def test_classify_folder_files_by_dimensions_and_extension():
    files = [
        {
            "id": "file_ptg_png",
            "name": "BM79-26.png",
            "mimeType": "image/png",
            "imageMediaMetadata": {"width": 2250, "height": 3710}
        },
        {
            "id": "file_layout_jpg",
            "name": "BM79-26.jpg",
            "mimeType": "image/jpeg",
            "imageMediaMetadata": {"width": 2839, "height": 1080}
        }
    ]

    classified = classify_folder_files(files)
    assert len(classified["chi_can"]) == 1
    assert "file_layout_jpg" in classified["chi_can"][0]
    assert len(classified["ptg"]) == 1
    assert "file_ptg_png" in classified["ptg"][0]


def test_classify_folder_files_by_name_and_pdf():
    files = [
        {
            "id": "file_ptg_doc",
            "name": "Phiếu tính giá BM50-04.pdf",
            "mimeType": "application/pdf"
        },
        {
            "id": "file_layout_doc",
            "name": "Mặt bằng vị trí BM50-04.webp",
            "mimeType": "image/webp"
        }
    ]

    classified = classify_folder_files(files)
    assert len(classified["ptg"]) == 1
    assert "file_ptg_doc" in classified["ptg"][0]
    assert len(classified["chi_can"]) == 1
    assert "file_layout_doc" in classified["chi_can"][0]


def test_expand_and_classify_media_urls_with_cache():
    fid = "test_folder_cache_key_999"
    with _CACHE_LOCK:
        _FOLDER_MEDIA_CACHE[fid] = {
            "chi_can": ["https://drive.google.com/file/d/chi_can_123/view?usp=drivesdk"],
            "ptg": ["https://drive.google.com/file/d/ptg_456/view?usp=drivesdk"]
        }

    folder_url = f"https://drive.google.com/drive/folders/{fid}"
    # Đưa vào combined_urls (cột PTG/Ảnh chỉ căn gộp)
    c_out, p_out = expand_and_classify_media_urls(
        chican_urls=[],
        ptg_urls=[],
        combined_urls=[folder_url]
    )

    assert len(c_out) == 1
    assert "chi_can_123" in c_out[0]
    assert len(p_out) == 1
    assert "ptg_456" in p_out[0]


def test_expand_and_classify_media_urls_mixed():
    direct_file = "https://drive.google.com/file/d/direct_file_789/view"
    c_out, p_out = expand_and_classify_media_urls(
        chican_urls=[direct_file],
        ptg_urls=[],
        combined_urls=[]
    )
    assert c_out == [direct_file]
    assert p_out == []
