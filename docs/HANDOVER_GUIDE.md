# TÀI LIỆU BÀN GIAO HỆ THỐNG ĐỒNG BỘ BẢNG HÀNG BĐS (VHUB INVENTORY SYNC ENGINE)

Tài liệu này cung cấp toàn bộ thông tin về kiến trúc kỹ thuật, cấu trúc mã nguồn, quy tắc nghiệp vụ cốt lõi, quy trình vận hành/triển khai và xử lý sự cố để kỹ sư tiếp nhận có thể trực tiếp quản lý, bảo trì và mở rộng hệ thống `google-sheet-inventory-sync`.

---

## 1. Tổng quan Kiến trúc Hệ thống (Dual-Destination Sync Engine)

Hệ thống được thiết kế theo mô hình **Đích Kép (Dual-Destination)**, hoạt động liên tục 24/7 dưới dạng Micro-Daemon (`src/daemon.py`, quản lý qua PM2 trên VPS) hoặc chạy thủ công qua CLI (`src/main.py`) và GitHub Actions (`.github/workflows/sync-inventory.yml`).

### Luồng xử lý dữ liệu End-to-End

1. **Khám phá danh mục nguồn (`src/master_reader.py`):**
   - Ưu tiên đọc tab `Danh mục Link Đại lý` ngay trong Google Sheet đích của dự án (`get_agency_links_from_target_sheet`).
   - Nếu Sheet đích chưa có danh sách đại lý, hệ thống fallback sang file Google Sheet Master tổng hợp (`MASTER_SPREADSHEET_ID = '1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j'`) thông qua `get_project_agency_links`.
   - Hỗ trợ bóc tách URL chứa nhiều GID (`?gid=111,222`), phân loại bảng tổng hợp thông thường và cụm `MAS CAO TẦNG` (`MGC`, `MEL`, `HSG`, `LEP`), cũng như nhận diện file `.xlsx` trên Google Drive.

2. **Đọc & Bóc tách Bảng hàng Đa luồng (`src/fetcher.py`):**
   - `fetch_all_agencies_for_project` dùng `ThreadPoolExecutor` (`max_workers=5`) tải đồng thời bảng hàng từ các đại lý.
   - Hỗ trợ 3 cơ chế tải & tự động fallback khi gặp giới hạn hoặc khóa tải binary:
     1. **Google Sheets API v4 (`fetch_agency_from_google_sheet`):** Đọc đồng thời giá trị (`formattedValue`), liên kết (`hyperlink`), Google Smart Chips (`chipRuns`), đoạn link trong text (`textFormatRuns`), công thức (`userEnteredValue`), màu nền (`backgroundColor`), chữ gạch ngang (`strikethrough`), và trạng thái ẩn dòng (`rowMetadata.hiddenByUser`, `hiddenByFilter`). Tự chuyển sang `values.get` + format rút gọn nếu gặp lỗi Amplification ratio > 100.
     2. **Drive Excel XLSX (`fetch_agency_from_drive_xlsx`):** Tải file `.xlsx` từ Drive API v3 và parse bằng `openpyxl` (hỗ trợ trích xuất màu cell, hyperlink, GID mapping).
     3. **GViz CSV Endpoint (`fetch_agency_via_gviz_csv`):** Cơ chế dự phòng đọc CSV công khai khi Sheets/Drive API bị `403 cannotDownloadFile` hoặc giới hạn tải file.
   - Tự động nhận diện tiêu đề cột linh hoạt (`detect_header_row`, `map_columns_from_headers`) và bỏ qua các tab rác theo `NON_INVENTORY_TAB_REGEX`.

3. **Chuẩn hóa Dữ liệu (`src/normalizer.py`):**
   - Làm sạch mã căn (`sanitize_unit_code`), chuyển mã căn/tầng/trục thương mại (`to_commercial_code`, `to_commercial_floor_code`, `to_axis_code`, `normalize_high_rise_unit_floor_axis`).
   - Chuẩn hóa diện tích (`sanitize_single_area`), giá bán về đơn vị VNĐ (`normalize_price_to_vnd`) và đối chiếu chéo logic giữa giá chưa VAT, giá full, giá vay, giá TTTĐ, giá TTS (`sanitize_and_cross_validate_prices`).
   - Chuẩn hóa hướng (`normalize_direction`), ngày CSBH (`normalize_csbh_date`), đường dẫn ảnh chỉ căn / phiếu tính giá (`repair_drive_url`, `resolve_unit_media_links`).
   - Chuẩn hóa **Loại hình** theo **Danh mục Đóng (Closed Canonical Taxonomy)** (`normalize_low_rise_type`, `normalize_high_rise_type`, `infer_grounded_low_rise_type`, `infer_parkland_high_rise_type`).

4. **Hợp nhất & Quản lý Vòng đời Sản phẩm (`src/merger.py`):**
   - Đọc bảng hàng cũ hiện có trên Sheet đích (`read_existing_target_pool`) làm `existing_pool`.
   - `smart_upsert_pool` gom nhóm các căn vừa quét theo `unit_key`, áp dụng luật ưu tiên nguồn & phân loại `Nhóm quỹ`, tính ngày cấp hàng / hạn cấp hàng 30 ngày (`compute_expiry_warning`), và cập nhật trạng thái `Đã bán` đối với các căn thuộc đại lý quét thành công nhưng đã biến mất khỏi bảng hàng nguồn.

5. **Ghi Đích Kép (`src/writer.py` & `src/db_writer.py`):**
   - **Đích 1 (`writer.py`):** Kiểm tra sai khác bằng `has_inventory_changed` trước khi ghi. Chỉ ghi đè tab chuẩn hóa (`write_normalized_inventory`) khi dữ liệu thay đổi hoặc truyền `--force-sheet-write` (giảm phình lịch sử Sheet & tiết kiệm Google API quota). Sau đó cập nhật thống kê biến động vào tab `Danh mục Link Đại lý` (`src/agency_directory.py`).
   - **Đích 2 (`db_writer.py`):** Khi bật `--write-db`, `bulk_upsert_products_to_db` ánh xạ dòng chuẩn hóa (`map_merged_row_to_db_record`), đối chiếu phân khu với danh mục DB (`load_subdivision_catalog`), thực hiện Bulk Upsert vào bảng PostgreSQL `products` theo chunk 250 dòng (`execute_values` với `UPSERT_SQL`), tự động ẩn (`is_not_show = true`) và chuyển `state_line = 'sold'` cho các sản phẩm không còn được quan sát từ nguồn, xóa cache `project_filter_facets` và phát tín hiệu `NOTIFY`.

---

## 2. Chi tiết Cấu trúc Mã nguồn

| Thư mục / File | Chức năng & Ký hiệu (Symbols) quan trọng |
| --- | --- |
| `src/config.py` | Định nghĩa `MASTER_SPREADSHEET_ID`, `LOW_RISE_TEMPLATE_GID`, `DEFAULT_POLICY_YEAR = 2026`, từ điển `TARGET_PROJECTS`, bộ cột chuẩn `LOW_RISE_HEADERS` (39 cột) và `HIGH_RISE_HEADERS` (32 cột), tập mã màu đỏ `RED_HEX_CODES`, và `NON_INVENTORY_TAB_REGEX`. |
| `src/auth.py` | Hàm `get_credentials()`, `get_sheets_service()`, `get_drive_service()`, `get_gspread_client()`. Tự nạp `.env`, ưu tiên biến `GCP_SA_KEY` rồi tới `GOOGLE_APPLICATION_CREDENTIALS` / `credentials.json`. |
| `src/master_reader.py` | `parse_spreadsheet_url_and_gids()`, `get_agency_links_from_target_sheet()`, `get_project_agency_links()`, `_execute_api_call()` (có backoff cho lỗi 429). |
| `src/fetcher.py` | `parse_agency_grid_data()`, `fetch_agency_from_google_sheet()`, `fetch_agency_from_drive_xlsx()`, `fetch_agency_via_gviz_csv()`, `fetch_single_agency()`, `fetch_all_agencies_for_project()`, `classify_rgb_color()`, `extract_urls_from_cell_data()`. |
| `src/normalizer.py` | `normalize_low_rise_type()`, `normalize_high_rise_type()`, `infer_grounded_low_rise_type()`, `infer_parkland_high_rise_type()`, `infer_grounded_zone()`, `sanitize_unit_code()`, `sanitize_and_cross_validate_prices()`, `resolve_unit_media_links()`, `realign_legacy_row()`. |
| `src/merger.py` | `smart_upsert_pool()`, `get_candidate_rank()`, `extract_clean_agency_name()`, `natural_sort_key()`, `make_sort_key()`. |
| `src/writer.py` | `get_or_create_sheet()`, `read_existing_target_pool()`, `write_normalized_inventory()`. |
| `src/db_writer.py` | `VHUB_PROJECT_MAP`, `VHUB_MAS_SUBTAB_MAP`, `resolve_vhub_project()`, `map_merged_row_to_db_record()`, `has_inventory_changed()`, `get_db_connection()`, `bulk_upsert_products_to_db()`. |
| `src/agency_directory.py` | `DIRECTORY_TAB_NAME = 'Danh mục Link Đại lý'`, `DIRECTORY_HEADERS`, `update_project_agency_directory()`, `compute_project_stats_from_sheet()`. |
| `src/main.py` | `sync_single_project()`, `ensure_default_local_credentials()`, `main()` (CLI parser). |
| `src/daemon.py` | `get_adaptive_interval_sec()`, `get_process_memory_mb()`, `run_daemon()`, `main()`. |
| `src/setup_target_sheets.py` | Công cụ CLI khởi tạo Google Sheets đích mới, tạo tab chuẩn và cấp quyền Editor cho email quản trị. |
| `scripts/generate_standardization_report.py` | Sinh báo cáo chuẩn hóa & kiểm toán nguồn đại lý ra Google Sheet báo cáo (`TARGET_REPORT_SHEET_ID`). |
| `tests/` | 10 file test (`pytest`, hiện đạt 112/112 test cases pass). |

---

## 3. Danh mục Dự án & Ánh xạ Database

Dưới đây là toàn bộ 15 key cấu hình trong `TARGET_PROJECTS` (`src/config.py`) và ánh xạ `project_id` tương ứng trong `VHUB_PROJECT_MAP` (`src/db_writer.py`):

| Key (`src/config.py`) | Tên dự án | Loại | Google Sheet Đích ID | `project_id` trong PostgreSQL (`products`) |
| --- | --- | --- | --- | --- |
| `làng vân` | Dự án Làng Vân | `LOW_RISE` | `1G7kWbKI1q8O_r2i5eeNCyAhPjr62EIYRIeXp1n4FZBI` | `vinhomes-hai-van-bay` |
| `VRI` | Dự án VRI | `LOW_RISE` | `1fLHY2nvP4pLXDFrY0GMfLLTpOHORhnZ5JePVxqh8kfU` | `vinhomes-royal-island` |
| `MIK OCP` | Dự án MIK OCP | `HIGH_RISE` | `1NhlYJU_eyv4AXYGY3YhJ2RESe32u7QhSevajFXX5b-c` | `the-parkland-imperia-ocean-city` |
| `DƯƠNG KINH` | Dự án Dương Kinh | `LOW_RISE` | `1Xx2PSzX6LzYkiBeu9qM3cK5u2p_BjjVjSktR1_AIt7Q` | `vinhomes-golden-city` |
| `HLX` | Dự án HLX | `LOW_RISE` | `1TAkltHR0O6bvCdJ5s8LY1Ystq95eSuFXyLMscQ5xGJM` | `vinhomes-global-gate-ha-long` |
| `Đan phượng` | Dự án Đan Phượng | `LOW_RISE` | `1VGF3Joh39qIT4hwpjNT_YETsCUoFmBdUsAQvhncbkC4` | `vinhomes-wonder-city` |
| `TRÀNG CÁT` | Dự án Tràng Cát | `LOW_RISE` | `1lPCZGx2ngtFQkL7KBZkQDfVEQHUog91Fr8qfWsLVIlk` | `happy-home-trang-cat` |
| `Cần giờ` | Dự án Cần Giờ | `LOW_RISE` | `1yt1aiAt8ONkU1YKzHoO2zAjB-Oujne0tR3hbYOt2qQc` | `vinhomes-green-paradise` |
| `Hóc Môn` | Dự án Hóc Môn | `LOW_RISE` | `1YzUhxCEqm47yxP7SOpuA8kktflQEAbvNkWIn5UxIM0U` | `vinhomes-sai-gon-park` |
| `Q9` | Dự án Q9 | `HIGH_RISE` | `1HTcHXvk9gKZdE2fGGIkL4utSHZ-as5zZC0FxN2GVlYI` | `vinhomes-grand-park` |
| `MGC` | Masteri Grand Coast | `HIGH_RISE` | `1fV1_ZKQXVzsrdMa8ElSpVu-32cj4vPTzgftN81sDynM` | `masteri-grand-coast` (sub_tab: `MGC`) |
| `MEL` | Masteri Era Landmark | `HIGH_RISE` | `1s3SnBe265ap3SY6x3TXhnYYCC-NwTeBJD_tkez1WEfc` | `masteri-era-landmark` (sub_tab: `MEL`) |
| `HSG` | LUMIÈRE Hanoi Seasons Garden | `HIGH_RISE` | `1wZeM_3wLws_n86fCjOdUIeKDlj6wu5LtOUYDJ86eftk` | `lumiere-hanoi-seasons-garden` (sub_tab: `HSG`) |
| `OCP2-3` | Dự án OCP2-3 | `LOW_RISE` | `1LtzwcF6xP-ZdfuNoschNN3-LhbP1fuHqsiA_ad75jJQ` | `vinhomes-ocean-park-3` |
| `Global Gate` | Dự án Vinhomes Global Gate | `LOW_RISE` | `1Q7DxaK9Z-s1IVt7fNoW5pTfJnkoSJe9RhyICR4QSSdQ` | `vinhomes-global-gate` |

*Ghi chú:* Key đặc biệt `MAS CAO TẦNG` khi truyền vào `--project "MAS CAO TẦNG"` sẽ tự động điều phối chạy lần lượt `MGC`, `MEL`, `HSG`. Ngoài ra `VHUB_PROJECT_MAP` cũng hỗ trợ mapping bổ sung cho `LEP` (`lumiere-essence-peak`).

---

## 4. Các Quy tắc Nghiệp vụ Quan trọng (Business Invariants)

Người tiếp nhận cần nắm chắc 4 quy tắc bất biến sau khi chỉnh sửa logic đồng bộ:

### 4.1. Bốn (4) tiêu chí xác định căn `Đã bán` (`src/fetcher.py` & `src/merger.py`)
1. **Từ khóa / Banner / Gạch ngang:** Cột trạng thái hoặc ghi chú chứa từ khóa đã bán/cọc/thu hồi/ráp căn (lưu ý: KHÔNG bắt `hđmb`, `ttđc`, `vbcn`, hay chữ `cọc` đơn lẻ vì dính `"giải ngân trên cọc"`), HOẶC nằm dưới section `"Đã bán"`, HOẶC ô mã căn / trạng thái có định dạng gạch ngang (`strikethrough`).
2. **Dòng bị ẩn:** `hiddenByUser` / `hiddenByFilter` trong Google Sheets hoặc `ws.row_dimensions[r].hidden` trong Excel $ightarrow$ luôn tính là `Đã bán`.
3. **Biến mất khỏi nguồn:** Trong `smart_upsert_pool`, nếu đại lý đã quét thành công trong chu kỳ hiện tại (`successful_agencies`) mà mã căn từng thuộc đại lý đó không còn xuất hiện $ightarrow$ tự chuyển sang `Đã bán` kèm tag `[Đã bán dd/mm/yyyy] Đã xóa khỏi bảng hàng nguồn.`.
4. **Màu nền đỏ (`color_type == 'red'`):** Chấp nhận ô mã căn, ô trạng thái, ô STT tô nền đỏ rõ nét (`RED_HEX_CODES`) hoặc >= 3 ô đỏ chiếm >= 30% số ô trên dòng. **TUYỆT ĐỐI KHÔNG** tính màu chữ đỏ (`is_fg_red`), màu cam/vàng/be/pastel, và **KHÔNG** tự suy diễn `Đã bán` chỉ vì thiếu cột giá.

### 4.2. Quy tắc 3 cấp phân loại `Nhóm quỹ` (`src/merger.py`)
1. **Cấp 1 — `Quỹ độc quyền`:** CHỈ cấp cho nguồn đến từ đại lý **`Vhub`** (trừ khi ô phân loại ghi rõ `'Quỹ chung'` / `'QC'`). Nếu `Vhub` có căn đó, `Vhub` luôn thắng mọi đại lý khác.
2. **Cấp 2 — `Quỹ chung`:** Áp dụng khi nguồn được khai báo chính thức là `Quỹ chung` / `Quỹ CĐT` (`is_general_pool`), HOẶC căn đó xuất hiện đồng thời từ **>= 2 đại lý phân phối khác nhau** (ưu tiên xét các đại lý còn hoạt động; nếu tất cả đều đã bán thì xét số lượng đại lý từng giữ căn đó). Khi lưu DB `products`, nếu là `Quỹ chung` / `Quỹ CĐT`, trường `partner` trong bảng `products` được để `NULL`.
3. **Cấp 3 — `Quỹ chéo`:** Áp dụng khi chỉ có duy nhất 1 đại lý phân phối thông thường (khác `Vhub`) đang nắm giữ/bán căn đó (kể cả khi tab đại lý tự ghi là "Độc quyền").

*Lưu ý bảo toàn 30 ngày:* Nếu căn thuộc 1 đại lý và đã được cấp hàng trước đó, `smart_upsert_pool` tính hạn 30 ngày từ `Ngày cấp hàng`; trong thời hạn < 30 ngày, chủ sở hữu cũ được ưu tiên xếp hạng cao hơn khi hợp nhất cùng nhóm.

### 4.3. Danh mục Đóng Loại hình (`Closed Canonical Taxonomy` - `src/normalizer.py`)
Để chặn triệt để rác bộ lọc (câu mô tả view, hướng, số phòng tắm, diện tích trôi cột, tên tòa nhà `M1`/`M3`...), cả hai hàm chuẩn hóa chỉ trả về các nhãn nằm trong whitelist hoặc chuỗi rỗng `''` (tuyệt đối không fallback trả nguyên văn chuỗi rác `return s`):
- **Thấp tầng (`normalize_low_rise_type` & `infer_grounded_low_rise_type`):**
  `Liền kề`, `Liền kề góc`, `Liền kề xẻ khe`, `Liền kề shop`, `Biệt thự Song lập`, `Biệt thự Song lập góc`, `Biệt thự Đơn lập`, `Biệt thự Đơn lập góc`, `Biệt thự Tứ lập`, `Biệt thự`, `Shophouse`, `Shophouse góc`, `Shophouse xẻ khe`, `Shophouse chân đế`, `TMDV`.
- **Cao tầng (`normalize_high_rise_type` & `infer_parkland_high_rise_type`):**
  `STUDIO`, `1PN`, `1PN+`, `2PN`, `2PN+`, `3PN`, `3PN+`, `4PN`, `5PN`, `DUPLEX`, `PENTHOUSE`, `TRIPLEX`, `Shophouse chân đế`.

### 4.4. Quy tắc Dừng Quét Bảng hàng cũ & Khoảng trống lớn (`src/fetcher.py`)
Trong `parse_agency_grid_data`:
1. **Khoảng trống lớn:** Sau khi đã quét được ít nhất 1 căn hợp lệ (`len(scanned_units) > 0`), nếu gặp **>= 15 dòng trống liên tiếp**, engine dừng quét (`break`) để không đọc nhầm ghi chú / bảng phụ cuối trang tính.
2. **Banner Bảng hàng cũ:** Nếu gặp dòng tiêu đề chứa `BHC cũ`, `Bảng hàng cũ`, `Hàng cũ`, `Quỹ cũ`, `Bảng cũ` (và không phải dòng mã căn thực tế), engine dừng quét (`break`).
3. **Giới hạn riêng nguồn MDLAND Dương Kinh (`1J3UZdjPZtCQlT-me75mUjeSYgWw7ciHUJYE1ThrTJtg`):** Tự động dừng quét tại dòng **58** (hoặc đủ **54 căn** khi đọc qua GViz CSV), bỏ qua hoàn toàn block `"BHC cũ"` từ dòng 95 trở đi để các căn cũ tự động chuyển thành `Đã bán`.

---

## 5. Hướng dẫn Cài đặt, Vận hành & Xử lý Sự cố (Operations Runbook)

### 5.1. Cài đặt từ đầu trên máy mới / server mới
```bash
git clone <repo-url> google-sheet-inventory-sync
cd google-sheet-inventory-sync

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# Mở .env và điền:
# - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
# - GOOGLE_APPLICATION_CREDENTIALS (trỏ tới credentials.json) hoặc GCP_SA_KEY
```

### 5.2. Chạy đồng bộ thủ công qua CLI (`src/main.py`)
Các tham số hỗ trợ của `python -m src.main`:
- `--project "<KEY>"`: Chạy 1 dự án (ví dụ: `"DƯƠNG KINH"`, `"làng vân"`, `"MIK OCP"`, `"MAS CAO TẦNG"`).
- `--all`: Chạy toàn bộ dự án trong `TARGET_PROJECTS`.
- `--write-db`: Bật ghi vào PostgreSQL bảng `products` (mặc định CLI tắt nếu không truyền cờ này; riêng `daemon.py` mặc định BẬT ghi DB trừ khi truyền `--no-write-db`).
- `--force-sheet-write`: Ép ghi lại Google Sheet đích kể cả khi `has_inventory_changed` báo không thay đổi.
- `--dry-run`: Quét thử nghiệm, không ghi Sheet và không ghi DB.
- `--max-workers <N>`: Số luồng quét song song (mặc định `5`).

### 5.3. Vận hành Daemon nền với PM2 trên VPS
Trên VPS production (`/root/vhub/google-sheet-inventory-sync`), daemon đang chạy bằng PM2 với tên **`vhub-inventory-sync`** (ID hiện tại: `110`):
- Script: `/root/vhub/google-sheet-inventory-sync/venv/bin/python`
- Args: `-m src.daemon` (Adaptive Polling: nghỉ 120s khung 08h–18h, 300s khung 18h–22h, 1800s khung 22h–08h; tự chạy `gc.collect()` giải phóng RAM sau mỗi chu kỳ).

Các lệnh quản trị PM2 thường dùng:
```bash
pm2 status                          # Xem trạng thái các service
pm2 describe vhub-inventory-sync    # Xem chi tiết cấu hình & uptime
pm2 logs vhub-inventory-sync --lines 100   # Theo dõi log realtime
pm2 restart vhub-inventory-sync     # Khởi động lại sau khi sửa code hoặc .env
```

### 5.4. Quy trình Thêm Dự án mới hoặc Nguồn Đại lý mới
1. **Thêm nguồn đại lý vào dự án đã có:**
   - Thêm dòng link đại lý vào tab `Danh mục Link Đại lý` của Google Sheet đích dự án đó (hoặc trong file Master `1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j`).
   - Đảm bảo sheet nguồn đã được chia sẻ quyền xem (hoặc link công khai) cho email của Google Service Account.
2. **Thêm dự án hoàn toàn mới:**
   - Bước 1: Tạo Google Sheet đích mới (hoặc dùng `python -m src.setup_target_sheets --email <admin-email>`), cấp quyền Editor cho Service Account.
   - Bước 2: Khai báo key mới trong `TARGET_PROJECTS` tại `src/config.py`.
   - Bước 3: Khai báo ánh xạ sang `project_id` Web DB trong `VHUB_PROJECT_MAP` tại `src/db_writer.py`.
   - Bước 4: Chạy test `pytest` và chạy thử `python -m src.main --project "<KEY>" --dry-run` trước khi đưa vào `--write-db`.

### 5.5. Kiểm thử & Xử lý Sự cố thường gặp
- **Chạy kiểm thử hồi quy trước mọi thay đổi:**
  ```bash
  /root/vhub/google-sheet-inventory-sync/venv/bin/pytest
  ```
- **Lỗi Google API `429 RATE_LIMIT_EXCEEDED`:**
  - Hệ thống đã có cơ chế backoff tự động trong `_execute_api_call` / `_execute_with_retry` (chờ 15s, 30s, 45s...). Nếu chạy song song nhiều script thủ công trong lúc daemon đang chạy có thể chạm ngưỡng 60 read req/phút/user — nên tạm dừng daemon (`pm2 stop vhub-inventory-sync`) nếu cần chạy script audit nặng, sau đó `pm2 start vhub-inventory-sync`.
- **Lỗi `Amplification ratio exceeds limit 100`:**
  - Đã được `fetcher.py` tự động xử lý chuyển sang `values.get` + đọc format rút gọn, hoặc fallback `fetch_agency_via_gviz_csv`.
- **Bộ lọc Web không cập nhật sau khi sửa DB trực tiếp:**
  - `db_writer.py` tự động thực thi `DELETE FROM project_filter_facets WHERE project_id = %s` sau mỗi lần upsert. Nếu sửa dữ liệu tay bằng SQL bên ngoài script, bắt buộc phải xóa dòng cache tương ứng trong bảng `project_filter_facets` để Backend VHUB tự rebuild facet mới.
- **Bảo mật:** Không bao giờ đưa `.env`, `credentials.json`, hoặc secret JSON vào git commit hoặc file đóng gói chia sẻ công khai.
