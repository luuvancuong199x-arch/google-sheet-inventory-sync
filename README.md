# HỆ THỐNG ĐỒNG BỘ BẢNG HÀNG 12 DỰ ÁN BẤT ĐỘNG SẢN (PYTHON + GITHUB ACTIONS)

Hệ thống tự động quét, chuẩn hóa và đồng bộ dữ liệu bảng hàng từ hơn 400 liên kết đại lý về 12 dự án bất động sản lớn, hoạt động tự động định kỳ **mỗi 15 phút một lần** thông qua GitHub Actions.

---

## 🌟 TẠI SAO CHỌN REPOSITORY CÔNG KHAI (PUBLIC)?
* **Miễn phí 100% không giới hạn số phút chạy:** GitHub cấp **Unlimited Actions Minutes** cho tất cả các Repository Public. Bạn có thể cho hệ thống chạy mỗi 15 phút liên tục 24/7 mà không lo hết hạn mức 2.000 phút như tài khoản Private.
* **Bảo mật tuyệt đối:** Mã nguồn chỉ chứa logic xử lý. Toàn bộ thông tin xác thực Google Service Account được lưu trữ an toàn trong **GitHub Secrets (`GCP_SA_KEY`)**. File `.gitignore` đã được cấu hình chặt chẽ để không bao giờ cho phép các file key `.json` hay file môi trường `.env` bị đẩy lên GitHub.

---

## 📋 HƯỚNG DẪN CÀI ĐẶT TỪNG BƯỚC

### BƯỚC 1: TẠO GOOGLE CLOUD SERVICE ACCOUNT
1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Tạo một Project mới (ví dụ: `BDS-Inventory-Sync`).
3. Vào mục **APIs & Services** -> **Library** (Thư viện):
   - Tìm kiếm và bấm **Enable** (Bật) **Google Sheets API**.
   - Tìm kiếm và bấm **Enable** (Bật) **Google Drive API**.
4. Vào mục **APIs & Services** -> **Credentials** -> Bấm **Create Credentials** -> Chọn **Service Account**:
   - Đặt tên Service Account (ví dụ: `sheets-sync-bot`). Bấm **Create and Continue** -> **Done**.
5. Bấm vào Service Account vừa tạo -> Chuyển sang tab **Keys** (Khóa) -> Bấm **Add Key** -> **Create new key** -> Chọn **JSON** -> Bấm **Create**.
   - Máy tính của bạn sẽ tải về một file dạng `xxxx-xxxx.json`. Hãy giữ cẩn thận file này!
6. Sao chép địa chỉ Email của Service Account (có dạng: `sheets-sync-bot@ten-project.iam.gserviceaccount.com`).

---

### BƯỚC 2: PHÂN QUYỀN TRÊN GOOGLE TRANG TÍNH
Mở Google Drive và phân quyền cho Email Service Account ở Bước 1:
1. **File Master Tổng Hợp (`1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j`):**
   - Bấm nút **Chia sẻ** (Share) -> Dán email Service Account -> Chọn quyền **Người xem** (Viewer).
2. **12 File Trang Tính Đích của 12 Dự Án:**
   - Bấm nút **Chia sẻ** (Share) trên từng file -> Dán email Service Account -> Chọn quyền **Người chỉnh sửa** (Editor).
   - *(Mẹo nhanh: Nếu 12 file này nằm chung trong 1 Thư mục Google Drive, bạn chỉ cần chia sẻ quyền Editor cho Thư mục đó là toàn bộ file con sẽ tự động nhận quyền).*

---

### BƯỚC 3: TẠO REPOSITORY PUBLIC TRÊN GITHUB & ĐẨY CODE LÊN
1. Đăng nhập vào [GitHub](https://github.com/) -> Bấm **New repository**.
2. Đặt tên repository (ví dụ: `google-sheets-inventory-sync`).
3. **Chọn chế độ `Public`** (để nhận hạn mức chạy GitHub Actions không giới hạn).
4. Mở cửa sổ dòng lệnh (Terminal/PowerShell) tại thư mục dự án `I:\Google-sheet` và chạy các lệnh:
   ```bash
   git init
   git add .
   git commit -m "feat: initial commit python sync engine"
   git branch -M main
   git remote add origin https://github.com/<tai-khoan-github-cua-ban>/<ten-repo>.git
   git push -u origin main
   ```

---

### BƯỚC 4: THÊM SECRET `GCP_SA_KEY` VÀO GITHUB
1. Trên trang Repository GitHub vừa tạo, vào tab **Settings** -> Mục bên trái chọn **Secrets and variables** -> **Actions**.
2. Bấm nút **New repository secret**.
3. Điền thông tin:
   - **Name:** `GCP_SA_KEY`
   - **Secret:** Mở file JSON key đã tải về ở Bước 1 bằng Notepad, copy toàn bộ nội dung bên trong và dán vào ô này.
4. Bấm **Add secret** để lưu lại.

---

### BƯỚC 5: KIỂM TRA & KÍCH HOẠT ĐỒNG BỘ
1. Vào tab **Actions** trên GitHub:
   - Bạn sẽ thấy workflow **Sync Real Estate Inventory (15 Mins)**.
2. Để chạy thử ngay lập tức mà không cần đợi 15 phút:
   - Bấm vào tên workflow -> Bấm nút **Run workflow** -> Bấm nút màu xanh **Run workflow**.
3. Sau khoảng 60 – 90 giây, tiến trình sẽ báo dấu tích xanh ✅ **Success**. Bảng hàng trên Google Trang tính sẽ được cập nhật đầy đủ và chính xác!

---

## 🛠️ CHẠY THỬ NGHIỆM TRÊN MÁY TÍNH (LOCAL)
Nếu muốn chạy thử nghiệm trực tiếp từ máy tính:
1. Đặt file JSON key vào thư mục gốc dự án và đổi tên thành `credentials.json` (file này đã được `.gitignore` bảo vệ, không lo bị đẩy lên mạng).
2. Cài đặt thư viện:
   ```bash
   pip install -r requirements.txt
   ```
3. Chạy kiểm thử:
   ```bash
   pytest
   ```
4. Chạy đồng bộ thử nghiệm (Dry-run không ghi đè):
   ```bash
   python -m src.main --dry-run
   ```
5. Chạy đồng bộ thật:
   ```bash
   python -m src.main --all
   ```
