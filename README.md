# VHUB Google Sheet Inventory Sync Engine

Hệ thống tự động thu thập, chuẩn hóa, hợp nhất và đồng bộ bảng hàng bất động sản theo kiến trúc **Đích Kép (Dual-Destination)**:
1. **Google Sheets Chuẩn hóa (Đích 1):** Tổng hợp giỏ hàng sạch từ các đại lý về bảng hàng chuẩn hóa cho từng dự án (Thấp tầng 39 cột / Cao tầng 32 cột) + tab `Danh mục Link Đại lý`.
2. **PostgreSQL Database (Đích 2):** Bulk Upsert trực tiếp vào bảng `products` của hệ thống VHUB Web (`--write-db`), tự động ẩn/chuyển trạng thái căn hết nguồn, xóa cache `project_filter_facets` và phát tín hiệu `NOTIFY`.

> **Tài liệu bàn giao chi tiết:** Xem đầy đủ quy trình kiến trúc, quy tắc nghiệp vụ, ánh xạ dự án, hướng dẫn vận hành PM2 và xử lý sự cố tại [`docs/HANDOVER_GUIDE.md`](docs/HANDOVER_GUIDE.md).

---

## Kiến trúc & Luồng dữ liệu

```
Master Sheet (1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j) + Tab "Danh mục Link Đại lý"
        │
        ▼
[1] master_reader.py   ── Đọc danh sách nguồn Google Sheets / Drive XLSX của từng đại lý
        │
        ▼
[2] fetcher.py         ── Tải dữ liệu đa luồng (Sheets API v4 / Drive XLSX / GViz CSV fallback)
                          Bóc link/Smart Chips (chipRuns), màu nền, dòng ẩn, gạch ngang, chặn "BHC cũ"
        │
        ▼
[3] normalizer.py      ── Chuẩn hóa mã căn, phân khu, hướng, giá VNĐ, loại hình (Closed Taxonomy)
        │
        ▼
[4] merger.py          ── Hợp nhất (smart_upsert_pool), phân loại Quỹ (Độc quyền Vhub / Chung / Chéo),
                          giữ quyền sở hữu 30 ngày, chuyển Đã bán khi biến mất khỏi nguồn
        │
        ├──► [5a] writer.py     ── Kiểm tra diff (has_inventory_changed) & ghi Google Sheet đích
        └──► [5b] db_writer.py  ── Bulk Upsert vào PostgreSQL `products` + xóa cache facet
```

---

## Cài đặt nhanh (Quick Start)

### 1. Yêu cầu hệ thống
- Python >= 3.11 (VPS production hiện đang chạy Python 3.14 trong `venv/`).
- PostgreSQL (khi dùng cờ `--write-db` hoặc chạy daemon).
- Google Service Account JSON key đã được cấp quyền **Editor** trên các Google Sheets đích và tối thiểu **Viewer** trên Sheet Master + các sheet nguồn đại lý.

### 2. Khởi tạo môi trường
```bash
python3 -m venv venv
source venv/bin/activate        # Trên Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Sau đó điền thông tin credentials & DB thực tế vào .env
```

### 3. Chạy kiểm thử (Unit Tests)
```bash
pytest
```

### 4. Các lệnh chạy đồng bộ thông dụng
```bash
# Chạy thử nghiệm 1 dự án (Dry run - không ghi Sheet & không ghi DB)
python -m src.main --project "DƯƠNG KINH" --dry-run

# Đồng bộ 1 dự án cụ thể (cả Google Sheet & PostgreSQL)
python -m src.main --project "DƯƠNG KINH" --write-db

# Đồng bộ và ép ghi lại Google Sheet dù không phát hiện diff
python -m src.main --project "DƯƠNG KINH" --write-db --force-sheet-write

# Đồng bộ toàn bộ dự án đang cấu hình
python -m src.main --all --write-db

# Chạy Micro-Daemon nền 24/7 (Adaptive Polling: 2p / 5p / 30p)
python -m src.daemon
```

---

## Cấu trúc Thư mục chính

| Đường dẫn | Vai trò |
| --- | --- |
| `src/config.py` | Cấu hình `MASTER_SPREADSHEET_ID`, `TARGET_PROJECTS`, header 39 cột Thấp tầng / 32 cột Cao tầng, `RED_HEX_CODES`, `NON_INVENTORY_TAB_REGEX` |
| `src/auth.py` | Xác thực Google API (`GCP_SA_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, `credentials.json`) |
| `src/master_reader.py` | Trích xuất liên kết nguồn & GID đại lý từ Master Sheet / tab `Danh mục Link Đại lý` |
| `src/fetcher.py` | Bộ đọc & bóc tách bảng hàng đại lý đa định dạng (Google Sheets API, XLSX, GViz CSV) |
| `src/normalizer.py` | Bộ chuẩn hóa dữ liệu & Danh mục Đóng loại hình (Closed Canonical Taxonomy) |
| `src/merger.py` | Hợp nhất đa đại lý, xếp hạng ưu tiên và xử lý vòng đời trạng thái căn (`smart_upsert_pool`) |
| `src/writer.py` | Đọc pool hiện tại & ghi đè Google Sheets đích theo batch |
| `src/db_writer.py` | Ánh xạ & Bulk Upsert vào PostgreSQL `products`, reconcile căn ẩn/bán, xóa cache `project_filter_facets` |
| `src/agency_directory.py` | Cập nhật thống kê tổng hợp vào tab `Danh mục Link Đại lý` trên từng Sheet đích |
| `src/main.py` | CLI runner điều phối đồng bộ từng dự án hoặc toàn hệ thống |
| `src/daemon.py` | Micro-Daemon Adaptive Polling chạy 24/7 (PM2 `vhub-inventory-sync`) |
| `src/setup_target_sheets.py` | Script tiện ích khởi tạo mới bộ Google Sheets đích và phân quyền Editor |
| `scripts/generate_standardization_report.py` | Sinh báo cáo kiểm toán/chuẩn hóa dữ liệu |
| `tests/` | Bộ Unit Test `pytest` kiểm soát hồi quy toàn bộ pipeline |
| `docs/HANDOVER_GUIDE.md` | **Tài liệu Hướng dẫn Bàn giao & Vận hành Chi tiết** |
