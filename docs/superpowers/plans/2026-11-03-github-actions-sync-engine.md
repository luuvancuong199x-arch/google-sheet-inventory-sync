# Kế Hoạch Triển Khai Hệ Thống Đồng Bộ & Chuẩn Hóa Bảng Hàng 12 Dự Án Qua GitHub Actions (Python Engine)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

---

## 1. TỔNG QUAN HỆ THỐNG & MỤC TIÊU DỰ ÁN

Hệ thống thay thế hoàn toàn tập lệnh Google Apps Script đang bị treo/timeout 6 phút bằng một **Engine Python đa luồng (Multi-threaded Python Engine)** chạy tự động định kỳ trên **GitHub Actions (hoàn toàn miễn phí)**.

### Mục tiêu kỹ thuật cốt lõi:
1. **Tốc độ:** Quét đồng thời hàng trăm link đại lý bằng cơ chế đa luồng (`ThreadPoolExecutor`), rút ngắn thời gian quét toàn bộ 12 dự án từ > 40 phút xuống còn **60 – 90 giây**.
2. **Không giới hạn thời gian:** GitHub Actions cho phép chạy tối đa 360 phút (6 tiếng), xóa bỏ triệt để bức tường 6 phút của Apps Script.
3. **Đọc danh mục động từ Master Sheet:** Không hardcode 3.000 dòng link tĩnh trong code. Script tự động đọc danh mục đại lý trực tiếp từ Master Sheet [`1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j`](https://docs.google.com/spreadsheets/d/1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j/edit). Khi người dùng thêm/bớt/sửa link trên Master Sheet, lượt chạy tiếp theo sẽ tự động áp dụng.
4. **Bảo toàn dữ liệu (Smart Upsert):** Tuyệt đối không dùng `clearContents()`. Dữ liệu mới được merge vào dữ liệu cũ theo `unitKey`. Nếu một đại lý bị lỗi mạng, căn của họ trong sheet đích vẫn được giữ nguyên.
5. **Khắc phục toàn diện 16 lỗi logic cũ:**
   - Bảo toàn 100% link Google Drive Folder / Open ID.
   - Không áp dụng bảng né số tầng phong thủy vào Trục căn (Axis).
   - Bảo toàn số WC thập phân (2.5 WC).
   - Chuẩn hóa giá an toàn (không xóa giá < 1.5 tỷ, không nhân nhầm đơn vị triệu thành trăm tỷ).
   - Validate ngày tháng chính xác bằng `datetime.date`.
   - Bỏ giới hạn cứng 1.200 dòng / 45 cột.
6. **Chi phí:** **0 VNĐ / tháng** (Tận dụng 2.000 phút chạy miễn phí hàng tháng của GitHub Actions private repo).

---

## 2. CẤU TRÚC THƯ MỤC DỰ ÁN (FILE STRUCTURE)

```
I:\Google-sheet\
├── .github/
│   └── workflows/
│       └── sync-inventory.yml        # Lịch chạy cron tự động trên GitHub Actions
├── src/
│   ├── __init__.py
│   ├── config.py                     # Cấu hình ID Sheet, Header chuẩn thấp/cao tầng
│   ├── auth.py                       # Quản lý xác thực Google Service Account
│   ├── master_reader.py              # Đọc danh mục đại lý động từ Master Sheet
│   ├── fetcher.py                    # Tải dữ liệu bảng hàng đại lý đa luồng (parallel)
│   ├── normalizer.py                 # Bộ chuẩn hóa mã căn, phân khu, diện tích, giá, CSBH
│   ├── merger.py                     # Logic Upsert & Deduplicate theo unitKey
│   ├── writer.py                     # Ghi dữ liệu và định dạng về Sheet đích bằng batchUpdate
│   └── main.py                       # CLI Runner điều phối toàn bộ pipeline
├── tests/
│   ├── __init__.py
│   ├── test_normalizer.py            # Kiểm thử chuẩn hóa mã căn, trục, WC, giá
│   ├── test_merger.py                # Kiểm thử Smart Upsert và bảo toàn dữ liệu
│   └── test_master_reader.py         # Kiểm thử đọc danh mục đại lý
├── requirements.txt                  # Danh mục thư viện Python (gspread, google-api-python-client...)
└── README.md                         # Hướng dẫn tạo Google Service Account & cài đặt Secrets
```

---

## 3. DANH SÁCH CÁC TÁC VỤ TRIỂN KHAI (TASKS)

### Task 1: Khởi tạo Cấu trúc Dự án & File Cấu hình Hệ thống
- [ ] Tạo file `requirements.txt` với các thư viện:
  - `google-auth>=2.28.0`
  - `google-api-python-client>=2.120.0`
  - `gspread>=6.0.0`
  - `requests>=2.31.0`
  - `pytest>=8.0.0`
- [ ] Tạo file `src/config.py`:
  - `MASTER_SPREADSHEET_ID = '1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j'`
  - `LOW_RISE_TEMPLATE_GID = '904198174'` (Tab "Bàng hàng" - 36 cột gốc + 2 cột bổ sung: Cột 37 `Đại lý` và Cột 38 `Ngày cấp hàng`)
  - Dictionary `TARGET_PROJECTS`: Khai báo 12 dự án với `id`, `name`, `type` (`LOW_RISE` hoặc `HIGH_RISE`), và `sub_tabs` (cho MAS Cao Tầng).
  - Khai báo hằng số danh sách 38 cột chuẩn `LOW_RISE_HEADERS` và 31 cột chuẩn `HIGH_RISE_HEADERS`.
- [ ] Xác minh: Chạy `python -c "import src.config as cfg; print(cfg.MASTER_SPREADSHEET_ID)"` thành công.

---

### Task 2: Module Xác thực Google Cloud Service Account (`src/auth.py`)
- [ ] Viết hàm `get_credentials()` hỗ trợ 2 cơ chế:
  - Chạy local: Đọc từ file JSON `credentials.json` hoặc đường dẫn trong biến môi trường `GOOGLE_APPLICATION_CREDENTIALS`.
  - Chạy trên GitHub Actions: Đọc chuỗi JSON lưu trong biến môi trường `GCP_SA_KEY`.
- [ ] Khởi tạo client `gspread` và `build('sheets', 'v4')` với các scope `spreadsheets` và `drive.readonly`.
- [ ] Viết test trong `tests/test_auth.py` để kiểm tra kết nối với mock credentials.

---

### Task 3: Module Đọc Danh mục Đại lý Động từ Master Sheet (`src/master_reader.py`)
- [ ] Viết hàm `get_project_agency_links(service, project_key, sub_tab=None)`:
  - Mở Master Sheet `1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j`.
  - Đọc tab tương ứng với `project_key` (ví dụ `làng vân`, `VRI`, `MAS CAO TẦNG`...).
  - Tự động parse URL, bóc tách `spreadsheet_id` và `gid`.
  - Hỗ trợ format bảng chia theo cột như `MAS CAO TẦNG` (các cột `MGC, MEL, HSG, LEP`).
  - Lọc bỏ các dòng không có URL hoặc đại lý ghi chú ngừng hoạt động.
- [ ] Viết test `tests/test_master_reader.py` kiểm tra phân tích URL Sheet chuẩn.

---

### Task 4: Module Quét Dữ Liệu Đại Lý Đa Luồng (`src/fetcher.py`)
- [ ] Viết hàm `fetch_single_agency(service, agency_info)`:
  - Bỏ qua các file có đuôi `.xlsx` (`rtpof=true`) và ghi log cảnh báo cụ thể.
  - Mở spreadsheet đại lý, chọn đúng sheet theo `gid` (hoặc phân loại theo tên tab nếu không có gid).
  - Đọc toàn bộ giá trị bảng (`values`), công thức (`formulas`), định dạng (`displayValues`) và màu nền (`backgroundColors`) chỉ bằng **1 lần gọi API `spreadsheets.get`** (Batch read metadata & values).
  - Kiểm tra xem tab có Filter hay không qua `sheet.get('basicFilter')`. Không gọi RPC từng dòng.
- [ ] Viết hàm `fetch_all_agencies_parallel(agency_list, max_workers=15)`:
  - Sử dụng `concurrent.futures.ThreadPoolExecutor` để tải đồng thời 10-20 đại lý cùng lúc.
  - Bắt ngoại lệ từng đại lý, ghi log chi tiết lỗi (`PermissionDenied`, `NotFound`, `Timeout`) mà không làm gián đoạn các đại lý khác.
- [ ] Viết unit test giả lập (mock) fetcher đa luồng trong `tests/test_fetcher.py`.

---

### Task 5: Module Chuẩn Hóa Dữ Liệu Toàn Diện (`src/normalizer.py`)
Khắc phục triệt để các lỗi nghiệp vụ từ kịch bản cũ:
- [ ] **Chuẩn hóa Mã căn & Trục căn (High-Rise):**
  - Giữ nguyên mã trục căn (ví dụ `04`, `07`, `13`, `14` giữ nguyên là `04, 07, 13, 14`, **không đổi sang 05A, 08A, 12A**).
  - Chỉ áp dụng bảng né số tầng thương mại cho trường `floor`.
- [ ] **Chuẩn hóa Diện tích (Area):**
  - Nhận diện đúng số thực thập phân `.` và `,`.
  - Cross-check diện tích thông thủy vs tim tường cho cao tầng ($a_1 \le a_2$).
  - Bỏ các bộ lọc heuristics chia 10 mù quáng gây co nhỏ biệt thự lớn.
- [ ] **Chuẩn hóa Giá (Price):**
  - Chấp nhận giá căn hộ nhỏ / NOXH từ 400 triệu trở lên (không xóa giá < 1.5 tỷ).
  - Phân biệt rõ đơn vị Triệu và Tỷ: Nếu giá nhập là `850` ở cột giá tổng, quy đổi hợp lý dựa theo loại hình căn hộ hoặc đơn giá/m².
  - Đảm bảo KPBT đúng tỷ lệ 2% giá trị căn hộ.
- [ ] **Chuẩn hóa Số WC & Mặt tiền / Tầng:**
  - Bảo toàn số thập phân cho WC (giữ nguyên `1.5`, `2.5` WC, không xóa nhầm thành `15`, `25`).
- [ ] **Bóc tách Link Media & Tài liệu:**
  - Bóc tách URL thực từ Smart Chip và công thức `=HYPERLINK()`.
  - Khôi phục link Drive lỗi (thiếu dấu chấm domain `drivegooglecom`).
  - **Giữ lại 100% link Thư mục Google Drive (`/folders/...`)** khi chế độ quét sâu tắt.
- [ ] **Chuẩn hóa Ngày CSBH & Ngày cấp:**
  - Parse ngày tháng và kiểm tra tính hợp lệ bằng `datetime.date(year, month, day)` thực sự (loại bỏ `31/02`).
- [ ] Viết bộ test kiểm thử `tests/test_normalizer.py` bao phủ tất cả các trường hợp biên trên.

---

### Task 6: Module Hợp Nhất & Bảo Toàn Dữ Liệu Thông Minh (`src/merger.py`)
- [ ] Viết hàm `smart_upsert(existing_pool_dict, scanned_units_list, is_low_rise)`:
  - Khóa chính định danh: `unitKey = sanitize_unit_code(unit_code)`.
  - Duyệt danh sách vừa quét:
    - Nếu căn đã có trong pool: Cập nhật thông tin giá, CSBH, link ảnh mới nhất, ưu tiên nguồn Quỹ độc quyền hoặc nguồn có nhiều thông tin giá hơn.
    - Nếu căn phát hiện bị tô đỏ hoặc trạng thái ghi "Đã bán/Thu hàng": Chuyển trạng thái sang `Đã bán`.
    - Nếu căn mới: Bổ sung vào pool (bỏ qua nếu căn mới vốn đã ở trạng thái đã bán từ đầu).
  - **Bảo toàn dữ liệu cũ:** Bất kỳ căn nào đã có trong sheet đích mà đợt này đại lý của nó tạm thời bị lỗi mạng/không truy cập được sẽ **được giữ nguyên vẹn**, không bị xóa.
- [ ] Viết test `tests/test_merger.py` xác minh: Khi giả lập 1 đại lý bị sập mạng, toàn bộ căn của đại lý đó trong Sheet đích vẫn còn nguyên 100%.

---

### Task 7: Module Ghi Dữ Liệu & Định Dạng Hàng Loạt (`src/writer.py`)
- [ ] Viết hàm `write_project_inventory(service, spreadsheet_id, sheet_name, headers, rows, is_low_rise)`:
  - Kiểm tra tab đích (ví dụ `Bảng hàng chuẩn hóa` hoặc các tab con của MAS). Nếu chưa có thì tự động tạo mới, **tuyệt đối không ghi đè lên trang bìa `getSheets()[0]`**.
  - Dùng Google Sheets API `batchUpdate`:
    - Ghi dữ liệu bằng `UpdateCellsRequest` hoặc `values.update`.
    - Thiết lập định dạng số `#,#0` cho Giá, `#,#0.##` cho Diện tích, `@` cho Mã căn và Text chỉ trong **1 request duy nhất**.
    - Cắt tỉa các dòng thừa nếu số dòng mới ít hơn (thay vì dùng `clearContents` nguy hiểm).
- [ ] Viết test `tests/test_writer.py` kiểm tra payload gửi tới Google API.

---

### Task 8: Bộ Điều Phối Chính CLI Runner (`src/main.py`)
- [ ] Viết CLI hỗ trợ các tham số:
  - `python -m src.main --all`: Đồng bộ toàn bộ 12 dự án.
  - `python -m src.main --project "làng vân"`: Đồng bộ riêng 1 dự án cụ thể.
  - `python -m src.main --dry-run`: Chạy thử nghiệm bóc tách và in log mà không ghi đè vào Sheet đích.
- [ ] Tích hợp in bảng báo cáo tổng kết (Summary Report):
  - Số lượng căn quét được, số căn còn hàng, số căn đã bán, số đại lý truy cập thành công / thất bại.
  - Thời gian thực thi chi tiết của từng dự án.

---

### Task 9: Thiết Lập GitHub Actions Workflow (`.github/workflows/sync-inventory.yml`)
- [ ] Viết workflow file:
  - Trigger 1: `schedule` với cron linh hoạt (hỗ trợ `*/30 * * * *` mỗi 30 phút, hoặc `*/15 * * * *` mỗi 15 phút, hoặc `0 * * * *` mỗi giờ).
  - Trigger 2: `workflow_dispatch` (cho phép bấm nút chạy thủ công từ giao diện GitHub web với tùy chọn chọn dự án).
  - Khóa chống chạy đồng thời: `concurrency: { group: sync-sheets, cancel-in-progress: false }`.
  - Môi trường: `ubuntu-latest`, Python 3.11, cache `pip`.
  - Nạp Secret `GCP_SA_KEY` từ GitHub Secrets.
  - Chạy `pytest` trước khi chạy script chính để đảm bảo mã nguồn toàn vẹn.
  - Upload log thực thi thành Artifact của GitHub Actions nếu xảy ra lỗi để kiểm tra.

---

### Task 10: Hướng Dẫn Cấu Hình Google Cloud Service Account & GitHub Secrets
- [ ] Tạo file `README.md` hướng dẫn chi tiết từng bước bằng tiếng Việt:
  1. Hướng dẫn tạo Project miễn phí trên Google Cloud Console.
  2. Bật Google Sheets API và Google Drive API.
  3. Tạo Service Account và tải file JSON Key.
  4. Chia sẻ quyền "Viewer" (Người xem) trên Master Sheet và các Sheet đại lý (hoặc chia sẻ cho cả folder).
  5. Chia sẻ quyền "Editor" (Người chỉnh sửa) trên 12 Sheet đích.
  6. Cách dán nội dung file JSON vào mục `Settings -> Secrets and variables -> Actions` trên GitHub với tên `GCP_SA_KEY`.

---

## 4. TIÊU CHÍ NGHIỆM THU HOÀN THÀNH (ACCEPTANCE CRITERIA)

1. [ ] **Tốc độ:** Tổng thời gian chạy 1 lượt cả 12 dự án trên GitHub Actions không vượt quá **3 phút** (thay vì bị chết ở phút thứ 6).
2. [ ] **Độ ổn định:** 100% các lần chạy tự động trên GitHub Actions có trạng thái `Success` (màu xanh).
3. [ ] **Tính toàn vẹn dữ liệu:**
   - Cột ảnh chỉ căn và PTG giữ lại đầy đủ link Google Drive Folder.
   - Trục căn không bị biến dạng (căn 04 vẫn là 04).
   - WC 2.5 giữ nguyên là 2.5.
   - Khi có đại lý bị ngắt kết nối tạm thời, dữ liệu cũ của đại lý đó trên sheet đích không bị mất.
4. [ ] **Khả năng mở rộng:** Khi thêm đại lý mới vào Master Sheet `1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j`, hệ thống tự động quét đại lý mới đó ở lần chạy kế tiếp mà không cần sửa một dòng code nào.
