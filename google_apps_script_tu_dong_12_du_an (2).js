/**
 * ============================================================================
 * HỆ THỐNG GOOGLE APPS SCRIPT TỰ ĐỘNG QUÉT, CHUẨN HÓA, XỬ LÝ BẤT THƯỜNG,
 * BÓC TÁCH SMART CHIP / HYPERLINK & ĐỒNG BỘ BẢNG HÀNG 12 DỰ ÁN (V4.5 FULL - CHUẨN KIỂM TOÁN TRUNG THỰC NGUỒN 100% - ĐÃ NHÚNG SẴN 419 LINK ĐẠI LÝ & TỐI ƯU TỐC ĐỘ 20X)
 * ============================================================================
 * Cách cài đặt nhanh trên Google Trang tính:
 * 1. Mở file Google Trang tính tổng hợp link nguồn (hoặc bất kỳ file nào trong 12 dự án).
 * 2. Vào Tiện ích mở rộng (Extensions) -> Apps Script.
 * 3. Xóa mã mặc định trong file Code.gs, dán toàn bộ nội dung file này vào và nhấn Lưu (Ctrl+S).
 * 4. Tải lại trang Google Sheet -> trên thanh công cụ sẽ xuất hiện menu:
 *    "⚡ Đồng Bộ 12 Dự Án (v4.5)"
 * 5. Chọn "🚀 Chạy đồng bộ toàn bộ 12 dự án ngay" hoặc "⏰ Cài đặt Trigger tự động mỗi giờ".
 *
 * Toàn bộ quy tắc chuẩn hóa V4.0 + 10 quy tắc cải tiến V4.1 (từ kiểm toán 347 nguồn đại lý):
 * - Quy tắc 1 (Dòng ẩn, Tô nền đỏ & Dòng phân nhóm ĐANG BÁN / ĐÃ BÁN):
 *   + Căn mới nằm trên dòng bị ẩn, có nền màu đỏ, nằm dưới banner "ĐÃ BÁN", hoặc có ghi chú
 *     "thu" / "thu hàng" / "đã có cọc" -> Bỏ qua hoàn toàn, không đưa vào Pool.
 *   + Căn ĐÃ CÓ trong Pool ở lần quét trước, nếu lần quét sau phát hiện bị ẩn dòng, tô nền đỏ,
 *     hoặc chuyển sang vùng "ĐÃ BÁN" / "thu" -> Tự động cập nhật cột Trạng thái thành "Đã bán".
 * - Quy tắc 2 (Trạng thái Đã bán / Đã có cọc / Thu hàng):
 *   + Căn mới có trạng thái "Đã bán" / "Sold" / "Hết hàng" / "Đã cọc" / "Đã có cọc" / "Thu" -> Bỏ qua.
 * - Quy tắc 3 (Định dạng số đồng nhất - xử lý triệt để lỗi lúc chấm lúc phẩy):
 *   + Ép kiểu số thực (NUMBER) cho toàn bộ cột Diện tích với định dạng hiển thị "#,##0.##".
 *   + Ép kiểu số nguyên (NUMBER) cho toàn bộ cột Giá / VAT / KPBT / Đơn giá với định dạng "#,##0".
 *   + Tự động khôi phục diện tích bị nhảy Date-Serial (46233 -> 30.7 m²) hoặc mất dấu chấm (3437 -> 343.7 m²).
 * - Quy tắc 4 (Giá trị số = 0 & Lọc Vốn tự có 30% / Tiền cọc bị điền nhầm vào cột Giá):
 *   + Mọi trường số có giá trị = 0 đều tự động trả về rỗng (null / "") để không ghi số 0 vào bảng.
 *   + Tự động phát hiện và loại bỏ giá trị Vốn tự có 20%-30% (như 2,15 tỷ trong cột HTLS KH tự trả lãi
 *     khi Giá Full là 9,4 tỷ) hoặc tiền cọc 450 triệu bị nhập nhầm vào cột Giá vay / Giá TTTĐ.
 * - Quy tắc 5 (Xử lý Smart Chip / Hyperlink tài liệu & tự sửa link Drive lỗi thiếu dấu chấm):
 *   + Bóc tách URL thực từ RichTextValue (Smart Chip) và công thức =HYPERLINK(...).
 *   + Tự động sửa lỗi URL "https://drivegooglecom/..." -> "https://drive.google.com/...".
 *   + Tuyệt đối không ghi tên hiển thị của Smart Chip (như VN66-65, TV4-19, BHOMES) vào cột ảnh.
 * - Quy tắc 6 (Chuẩn hóa CSBH áp dụng về dd/mm/yyyy & phân loại mã V15/V26/Tháng 4.2026):
 *   + Mọi biến thể ngày chính sách ("CSBH 04/05/2026", "04/05", "4/5", "23/12/2025.") -> "dd/mm/yyyy".
 *   + Các mã phiên bản CSBH không có ngày cụ thể ("V15", "V26", "V38", "Tháng 4.2026") được chuyển
 *     sang cột "Ghi chú", mã ngân hàng ("MBV", "VBCN-BIOCARE-TCB") sang "Ngân hàng hỗ trợ giải ngân".
 * - Quy tắc 7 (Mã tầng & Mã căn Cao tầng - mở rộng cho mã kép Q9):
 *   + Chuẩn hóa về hệ mã thương mại 2 ký tự String ('@'): 01, 02, 03, 05A, 05, 06, 08A, 08, 09,
 *     10, 11, 12, 12A, 15A, 15, 16, 17, 18...
 *   + Hỗ trợ cả mã căn 2 dấu chấm của Q9 ("S6.0619.06", "S10.0213.19") và mã TòaTầng.Trục ("BE130.04",
 *     "BS1114.15", "OS207.03", "GH224.18").
 * - Quy tắc 8 (Tự động lọc bỏ Tab thông số/lưu trữ & kiểm tra tương thích Thấp tầng / Cao tầng):
 *   + Bỏ qua các tab thông tin/lưu trữ ("STK", "Giỏ bank", "Thông số OCP2/OCP3", "Giải chấp", "Đã bán",
 *     "Quỹ cũ", "Check ẩn") và lọc bỏ tab Nhà ở xã hội cao tầng (The Link 1/2/5) lẫn trong dự án Thấp tầng.
 * - Quy tắc 9 (Nhận diện bảng ghép nhiều Header dọc trong cùng 1 Sheet & mã Quỹ riêng "QR"/"QC"):
 *   + Tự động nhận diện dòng tiêu đề phụ ở giữa sheet (như bảng Five Star Tràng Cát) để cập nhật lại vị trí cột.
 *   + Nhận diện ký hiệu "QR" (Quỹ riêng) / "ĐQ" ở cả cột STT, cột Quỹ và tên Sheet để gán "Độc quyền".
 * ============================================================================
 */

const MASTER_LINK_SHEET_ID = '1pYfZPbHwmhQzusYdupjoLo-EP280isvo2Pza-6Z22wo';
// Tắt quét đệ quy Folder Drive mặc định khi đồng bộ hàng loạt để tốc độ chạy đạt 10-20 giây/dự án (không bị treo "Đang chạy tập lệnh")
const EXPAND_DRIVE_FOLDERS_DEEP = false;

// Danh mục toàn bộ 419 link đại lý của 12 dự án được nhúng trực tiếp (khắc phục triệt để lỗi file Master gốc là định dạng Excel .xlsx)
const EMBEDDED_MASTER_LINKS = {
  "làng vân": [
    {
      "agency": "VHS",
      "sub": null,
      "file_id": "1ONPUJuewSw1xu_I5SSgnr1YUqIEyGcUJ",
      "gid": "841746683",
      "url": "https://docs.google.com/spreadsheets/d/1ONPUJuewSw1xu_I5SSgnr1YUqIEyGcUJ/edit?gid=841746683"
    },
    {
      "agency": "BHS PARTNERS",
      "sub": null,
      "file_id": "1s27ks61cq_4vloR7C49hRS2Skt6HSWiVBN7qFl_cZyo",
      "gid": "920510806",
      "url": "https://docs.google.com/spreadsheets/d/1s27ks61cq_4vloR7C49hRS2Skt6HSWiVBN7qFl_cZyo/edit?gid=920510806"
    },
    {
      "agency": "SSM",
      "sub": null,
      "file_id": "1H5HWGQKpOBZOJQGSgJTfXPxHHyM07Qx5fC4N6mx-DYI",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1H5HWGQKpOBZOJQGSgJTfXPxHHyM07Qx5fC4N6mx-DYI/edit?gid=0"
    },
    {
      "agency": "CALI HOMES",
      "sub": null,
      "file_id": "1km6CMmYgN7iDZGZDFSSKRtNRl-z2CHtdggBLo6qibms",
      "gid": "1921330874",
      "url": "https://docs.google.com/spreadsheets/d/1km6CMmYgN7iDZGZDFSSKRtNRl-z2CHtdggBLo6qibms/edit?gid=1921330874#gid=1921330874"
    },
    {
      "agency": "DTL",
      "sub": null,
      "file_id": "1oupajTSRUJ1Xo3KYDaASoe6U4fy9IM5T",
      "gid": "1791795539",
      "url": "https://docs.google.com/spreadsheets/d/1oupajTSRUJ1Xo3KYDaASoe6U4fy9IM5T/edit?gid=1791795539#gid=1791795539"
    },
    {
      "agency": "STH",
      "sub": null,
      "file_id": "1vEcUpw72lzy4fkgbMqRoh2F_Wj7ySbJt",
      "gid": "374342281",
      "url": "https://docs.google.com/spreadsheets/d/1vEcUpw72lzy4fkgbMqRoh2F_Wj7ySbJt/edit?gid=374342281#gid=374342281"
    },
    {
      "agency": "MDLAND",
      "sub": null,
      "file_id": "11lTr9yvJAxZToOPJdLJGSKc5D0LKEKHP",
      "gid": "1962974863",
      "url": "https://docs.google.com/spreadsheets/d/11lTr9yvJAxZToOPJdLJGSKc5D0LKEKHP/edit?gid=1962974863"
    },
    {
      "agency": "MAYHOMES",
      "sub": null,
      "file_id": "1ZaeHKdYjiiBdTcVmcUW_heXk_pmfSgk5W_IuLUlTwmU",
      "gid": "200492768",
      "url": "https://docs.google.com/spreadsheets/d/1ZaeHKdYjiiBdTcVmcUW_heXk_pmfSgk5W_IuLUlTwmU/edit?gid=200492768#gid=200492768"
    },
    {
      "agency": "TÂN THỜI ĐẠI",
      "sub": null,
      "file_id": "18rYNcKvrXPeUJd3hd-gSjGhKYLbebhx2mtNBT2DMm_E",
      "gid": "1909584477",
      "url": "https://docs.google.com/spreadsheets/d/18rYNcKvrXPeUJd3hd-gSjGhKYLbebhx2mtNBT2DMm_E/edit?gid=1909584477#gid=1909584477"
    },
    {
      "agency": "TÂN HƯƠNG PHÁT",
      "sub": null,
      "file_id": "19RUkYgoupE-zWrfMVSg1hph0-kPWvaAxK9YLSkiOkVY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/19RUkYgoupE-zWrfMVSg1hph0-kPWvaAxK9YLSkiOkVY/edit?gid=0#gid=0"
    },
    {
      "agency": "FIVESTAR",
      "sub": null,
      "file_id": "1f1hUqqsevOdb0o8JVCwzRNSIebdbG3GwmbdICPOeaDc",
      "gid": "216400787",
      "url": "https://docs.google.com/spreadsheets/d/1f1hUqqsevOdb0o8JVCwzRNSIebdbG3GwmbdICPOeaDc/edit?gid=216400787#gid=216400787"
    },
    {
      "agency": "NOVASKY",
      "sub": null,
      "file_id": "1yeHEV9F-cbz-GojsXEGSWG8ZLvBroQubg3VghlJb09M",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1yeHEV9F-cbz-GojsXEGSWG8ZLvBroQubg3VghlJb09M/edit?gid=0#gid=0"
    },
    {
      "agency": "QUEENLAND",
      "sub": null,
      "file_id": "1brunQ7tVsoFxjdlGT2kWMBU-fvg38Addwf7jPUPOsyc",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1brunQ7tVsoFxjdlGT2kWMBU-fvg38Addwf7jPUPOsyc/edit?gid=0#gid=0"
    },
    {
      "agency": "QTC",
      "sub": null,
      "file_id": "1cUsP-K-a_6fPPwxmNM1Fj1tj_sy70lOt",
      "gid": "1824384072",
      "url": "https://docs.google.com/spreadsheets/d/1cUsP-K-a_6fPPwxmNM1Fj1tj_sy70lOt/edit?gid=1824384072#gid=1824384072"
    },
    {
      "agency": "BIGHOMES",
      "sub": null,
      "file_id": "1vPEpYKUF8yTTJ-Va11nhRCcunHzEr24X",
      "gid": "887728941",
      "url": "https://docs.google.com/spreadsheets/d/1vPEpYKUF8yTTJ-Va11nhRCcunHzEr24X/edit?gid=887728941#gid=887728941"
    },
    {
      "agency": "HDHOMES",
      "sub": null,
      "file_id": "1JZP19hMY8CQhQnayuBrR03K4iht7hSle",
      "gid": "25756137",
      "url": "https://docs.google.com/spreadsheets/d/1JZP19hMY8CQhQnayuBrR03K4iht7hSle/edit?gid=25756137#gid=25756137"
    },
    {
      "agency": "ROMAN PROPERTY",
      "sub": null,
      "file_id": "1aemuGsPQD8FkFJwsWekMTbBd6y2ovrCqy3aQyuHoR6c",
      "gid": "552207001",
      "url": "https://docs.google.com/spreadsheets/d/1aemuGsPQD8FkFJwsWekMTbBd6y2ovrCqy3aQyuHoR6c/edit?gid=552207001#gid=552207001"
    },
    {
      "agency": "ELITE CAPITAL",
      "sub": null,
      "file_id": "1v_8JWknyzg9xbbKLcM_wmXntsxc2Xxna2JTf-UlPP8Y",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1v_8JWknyzg9xbbKLcM_wmXntsxc2Xxna2JTf-UlPP8Y/edit?gid=0#gid=0"
    },
    {
      "agency": "ĐẤT VIỆT",
      "sub": null,
      "file_id": "1L1tjYVgvkh5lh-xO5Di2ltjLPm6wtYqWLWNW1nzW1QA",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1L1tjYVgvkh5lh-xO5Di2ltjLPm6wtYqWLWNW1nzW1QA/edit?gid=0#gid=0"
    },
    {
      "agency": "MICC GROUP",
      "sub": null,
      "file_id": "1TzaXMF2ahE9zF01H-rHIhtYBvOl5l8C-m8hZmClCgVA",
      "gid": "382995227",
      "url": "https://docs.google.com/spreadsheets/d/1TzaXMF2ahE9zF01H-rHIhtYBvOl5l8C-m8hZmClCgVA/edit?gid=382995227#gid=382995227"
    },
    {
      "agency": "HOMEP LUS",
      "sub": null,
      "file_id": "18isaflvFAVOiDlOk9EcgyvEOFzHmA2Obit9qSb55gjk",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/18isaflvFAVOiDlOk9EcgyvEOFzHmA2Obit9qSb55gjk/edit?gid=0#gid=0"
    },
    {
      "agency": "VIETSTARLAND",
      "sub": null,
      "file_id": "1bgaV3sCjkmo_1RxolUxgLuLe05LlL-ZD",
      "gid": "135739879",
      "url": "https://docs.google.com/spreadsheets/d/1bgaV3sCjkmo_1RxolUxgLuLe05LlL-ZD/edit?gid=135739879#gid=135739879"
    },
    {
      "agency": "TRƯỜNG PHÁT",
      "sub": null,
      "file_id": "1-4SnXyMwiCY2Js3tC4Ri1Eprjw76vfnQNS8S6nt3R1Q",
      "gid": "470138048",
      "url": "https://docs.google.com/spreadsheets/d/1-4SnXyMwiCY2Js3tC4Ri1Eprjw76vfnQNS8S6nt3R1Q/edit?gid=470138048#gid=470138048"
    },
    {
      "agency": "SAO VÀNG",
      "sub": null,
      "file_id": "1OckLBpX2hdI5F02Ifudz_p1YHFULsr0qYRUFK8XQ6qk",
      "gid": "79820384",
      "url": "https://docs.google.com/spreadsheets/d/1OckLBpX2hdI5F02Ifudz_p1YHFULsr0qYRUFK8XQ6qk/edit?gid=79820384#gid=79820384"
    },
    {
      "agency": "MAI VIỆT",
      "sub": null,
      "file_id": "1dlSh8qVW-MPebXK32xmXRnBYPi4bRn7ejfeG94BAdH4",
      "gid": "1811442815",
      "url": "https://docs.google.com/spreadsheets/d/1dlSh8qVW-MPebXK32xmXRnBYPi4bRn7ejfeG94BAdH4/edit?gid=1811442815#gid=1811442815"
    },
    {
      "agency": "NEWSTARLAND",
      "sub": null,
      "file_id": "1jloUHzmzqcawj9Nc9TGt5gsdKSYaGzgx",
      "gid": "2026370603",
      "url": "https://docs.google.com/spreadsheets/d/1jloUHzmzqcawj9Nc9TGt5gsdKSYaGzgx/edit?gid=2026370603#gid=2026370603"
    },
    {
      "agency": "MGLAND",
      "sub": null,
      "file_id": "1XzgCi3pbW1jYR-hi4lIVmp31e17o2KK9",
      "gid": "1616276294",
      "url": "https://docs.google.com/spreadsheets/d/1XzgCi3pbW1jYR-hi4lIVmp31e17o2KK9/edit?gid=1616276294#gid=1616276294"
    },
    {
      "agency": "ANN HOME",
      "sub": null,
      "file_id": "1MmkTCn2_mT29oMPL5DHoEIhwvMpfsGBBrTfOoSwZFZY",
      "gid": "648542232",
      "url": "https://docs.google.com/spreadsheets/d/1MmkTCn2_mT29oMPL5DHoEIhwvMpfsGBBrTfOoSwZFZY/edit?gid=648542232#gid=648542232"
    },
    {
      "agency": "PHÚ GIA",
      "sub": null,
      "file_id": "1bO62GuHncXvrvhrRkpbRX6jwbzk67xVs",
      "gid": "1556258896",
      "url": "https://docs.google.com/spreadsheets/d/1bO62GuHncXvrvhrRkpbRX6jwbzk67xVs/edit?gid=1556258896#gid=1556258896"
    },
    {
      "agency": "Lâm thuỷ mộc",
      "sub": null,
      "file_id": "1ZQTJihY7N5PGzx2lpr0zoLgC_Rc-sEzyXGayvOJDyaA",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1ZQTJihY7N5PGzx2lpr0zoLgC_Rc-sEzyXGayvOJDyaA/edit?gid=0#gid=0"
    },
    {
      "agency": "360LAND",
      "sub": null,
      "file_id": "1Si3XMFiXZpX0Zyvd-vipUc3EY2FiytwRkdICwGfEIuY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1Si3XMFiXZpX0Zyvd-vipUc3EY2FiytwRkdICwGfEIuY/edit?gid=0#gid=0"
    },
    {
      "agency": "Hợp Long",
      "sub": null,
      "file_id": "18pQ1_1GQ8wRCiK0XZG-rw8mzSedjwtIcJikHkCWGpSY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/18pQ1_1GQ8wRCiK0XZG-rw8mzSedjwtIcJikHkCWGpSY/edit?gid=0#gid=0"
    },
    {
      "agency": "Minh Minh",
      "sub": null,
      "file_id": "1wY1r5nsy1WYRN3mO6BqsZWh7V3RsadJZzwuObkxSSm0",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1wY1r5nsy1WYRN3mO6BqsZWh7V3RsadJZzwuObkxSSm0/edit?gid=0#gid=0"
    },
    {
      "agency": "Đất xanh MT",
      "sub": null,
      "file_id": "15mLWBzjkjf8Co-S5CvrAIpJMhn8hK_LNgm8ZmgTuQJI",
      "gid": "1725370903",
      "url": "https://docs.google.com/spreadsheets/d/15mLWBzjkjf8Co-S5CvrAIpJMhn8hK_LNgm8ZmgTuQJI/edit?gid=1725370903#gid=1725370903"
    }
  ],
  "VRI": [
    {
      "agency": "VHS",
      "sub": null,
      "file_id": "102gRVeWzpcQudKSsBTkrAzQOVBzSota4SsMGKRQPBUg",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/102gRVeWzpcQudKSsBTkrAzQOVBzSota4SsMGKRQPBUg/edit?gid=0"
    },
    {
      "agency": "HOMEPLUS",
      "sub": null,
      "file_id": "1b18ldGi9TTwZslSPFHUktmuaC7dl83IV0t0wT3M_IeY",
      "gid": "1546400229",
      "url": "https://docs.google.com/spreadsheets/d/1b18ldGi9TTwZslSPFHUktmuaC7dl83IV0t0wT3M_IeY/edit?gid=1546400229"
    },
    {
      "agency": "MAYHOME",
      "sub": null,
      "file_id": "1g0EFga75RR7eJobTwXXEpKXUQhMZ-Q8b",
      "gid": "1713323816",
      "url": "https://docs.google.com/spreadsheets/d/1g0EFga75RR7eJobTwXXEpKXUQhMZ-Q8b/edit?gid=1713323816"
    },
    {
      "agency": "MICC",
      "sub": null,
      "file_id": "1DOyrc710aKh5yXc0hmIhDv7s-gKA6303LGpOBBvfi6c",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1DOyrc710aKh5yXc0hmIhDv7s-gKA6303LGpOBBvfi6c/edit?gid=0"
    },
    {
      "agency": "NSL",
      "sub": null,
      "file_id": "1URzz4HypBxJHB-92svgfwYq0fP0LJdKK146gSA3RDmw",
      "gid": "565167621",
      "url": "https://docs.google.com/spreadsheets/d/1URzz4HypBxJHB-92svgfwYq0fP0LJdKK146gSA3RDmw/edit?gid=565167621"
    },
    {
      "agency": "VSL",
      "sub": null,
      "file_id": "1VuMsfpZsIVgmuoINZvvjyRO7oJIQkXN4",
      "gid": "300577265",
      "url": "https://docs.google.com/spreadsheets/d/1VuMsfpZsIVgmuoINZvvjyRO7oJIQkXN4/edit?gid=300577265"
    },
    {
      "agency": "HDH",
      "sub": null,
      "file_id": "1fk8Roj9C0O8hdQfSN38ZAKlNnr2mXXDgXEUtZ1gIDkw",
      "gid": "1379889512",
      "url": "https://docs.google.com/spreadsheets/d/1fk8Roj9C0O8hdQfSN38ZAKlNnr2mXXDgXEUtZ1gIDkw/edit?gid=1379889512"
    },
    {
      "agency": "SSM",
      "sub": null,
      "file_id": "1-_QI8fOzVNwW0bSjCtaxeyxH5DPKfZUzlo7sWJgr-AU",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1-_QI8fOzVNwW0bSjCtaxeyxH5DPKfZUzlo7sWJgr-AU/edit?gid=0"
    },
    {
      "agency": "DML",
      "sub": null,
      "file_id": "1L8PE2ekauz5iXrIMVWAb9kelspWt-7rg",
      "gid": "285157603",
      "url": "https://docs.google.com/spreadsheets/d/1L8PE2ekauz5iXrIMVWAb9kelspWt-7rg/edit?gid=285157603"
    },
    {
      "agency": "THP",
      "sub": null,
      "file_id": "1VBKF44c6LEcu7se3PKs7FI2ChFA-E6BI",
      "gid": "791514673",
      "url": "https://docs.google.com/spreadsheets/d/1VBKF44c6LEcu7se3PKs7FI2ChFA-E6BI/edit?gid=791514673"
    },
    {
      "agency": "BIGHOME",
      "sub": null,
      "file_id": "1vD8GReErngMV3yXXn3Zmkny_VJ2AqvXE",
      "gid": "1513138523",
      "url": "https://docs.google.com/spreadsheets/d/1vD8GReErngMV3yXXn3Zmkny_VJ2AqvXE/edit?gid=1513138523"
    },
    {
      "agency": "MDLAND",
      "sub": null,
      "file_id": "14P5_72NveFnpfrHuDXNXzisI79AZrlWfemtfcT3Cuhg",
      "gid": "1150387387",
      "url": "https://docs.google.com/spreadsheets/d/14P5_72NveFnpfrHuDXNXzisI79AZrlWfemtfcT3Cuhg/edit?gid=1150387387"
    },
    {
      "agency": "NVS",
      "sub": null,
      "file_id": "1zJJWl34HmJyJ3bfgRoFsGMrLHibpztQX",
      "gid": "1052333379",
      "url": "https://docs.google.com/spreadsheets/d/1zJJWl34HmJyJ3bfgRoFsGMrLHibpztQX/edit?gid=1052333379"
    },
    {
      "agency": "QUEENLAND",
      "sub": null,
      "file_id": "1fyGMLuvhMnWZFmEQPCYF_NxdWjEfCqoeWsWMzDC9Wm0",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1fyGMLuvhMnWZFmEQPCYF_NxdWjEfCqoeWsWMzDC9Wm0/edit?gid=0"
    },
    {
      "agency": "TTĐ",
      "sub": null,
      "file_id": "1DHvgxyWajuwN8BGiOUHwhXBbe6QkiQkc",
      "gid": "16231567",
      "url": "https://docs.google.com/spreadsheets/d/1DHvgxyWajuwN8BGiOUHwhXBbe6QkiQkc/edit?gid=16231567"
    },
    {
      "agency": "VSR",
      "sub": null,
      "file_id": "1D1qgbiSb66d9BpQ8GCgP1l-zZptacrfI-BaVZy5eI5o",
      "gid": "9759577",
      "url": "https://docs.google.com/spreadsheets/d/1D1qgbiSb66d9BpQ8GCgP1l-zZptacrfI-BaVZy5eI5o/edit?gid=9759577"
    },
    {
      "agency": "ĐẤT VIỆT",
      "sub": null,
      "file_id": "1qXzqEo5iWR4Rs8j-Lz3HdaHtPHefT2MKIMZhYzKn9xM",
      "gid": "733671245",
      "url": "https://docs.google.com/spreadsheets/d/1qXzqEo5iWR4Rs8j-Lz3HdaHtPHefT2MKIMZhYzKn9xM/edit?gid=733671245"
    },
    {
      "agency": "MMG",
      "sub": null,
      "file_id": "1W1xHWRoFdzxI1EbmgjOi1MWsZkrNvX8ObmC_xcLJ2eI",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1W1xHWRoFdzxI1EbmgjOi1MWsZkrNvX8ObmC_xcLJ2eI/edit?gid=0"
    },
    {
      "agency": "QCBEST",
      "sub": null,
      "file_id": "1GJVqcUQaFZBxARfDmtUWretYTpp7RZHv",
      "gid": "1602580462",
      "url": "https://docs.google.com/spreadsheets/d/1GJVqcUQaFZBxARfDmtUWretYTpp7RZHv/edit?gid=1602580462"
    },
    {
      "agency": "HOÀNG GIA",
      "sub": null,
      "file_id": "1oSe3A3bi1p1f-FzI9-OOw7FwnqSfrMtM",
      "gid": "504097482",
      "url": "https://docs.google.com/spreadsheets/d/1oSe3A3bi1p1f-FzI9-OOw7FwnqSfrMtM/edit?gid=504097482"
    },
    {
      "agency": "TÂN LONG",
      "sub": null,
      "file_id": "1fs0r55fNlP_adGjTh3mMAPdgW6PBD3le",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1fs0r55fNlP_adGjTh3mMAPdgW6PBD3le/edit?usp=drivesdk&ouid=110818127186721498938&rtpof=true&sd=tru"
    },
    {
      "agency": "IHD",
      "sub": null,
      "file_id": "1OSjBCUkkCdfBD008Gzl0hoPxG-SISmCf6yVMhY6uMFo",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1OSjBCUkkCdfBD008Gzl0hoPxG-SISmCf6yVMhY6uMFo/edit?gid=0"
    },
    {
      "agency": "THIÊN PHÚC",
      "sub": null,
      "file_id": "1-QL2xd1JPTE-89d9N9JuafNJcGDoH1hn",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/u/0/d/1-QL2xd1JPTE-89d9N9JuafNJcGDoH1hn/htmlview"
    },
    {
      "agency": "KHP",
      "sub": null,
      "file_id": "1jatG45vrv2PxsKNPf3Hrn-_q5IjG3h_qPwATDU-Tua4",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1jatG45vrv2PxsKNPf3Hrn-_q5IjG3h_qPwATDU-Tua4/edit?gid=0"
    },
    {
      "agency": "TRƯỜNG PHÁT",
      "sub": null,
      "file_id": "1FYw_MCLCu_oPEdA_v93QFZMgkya3M7kQw2a4L7MbZPg",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1FYw_MCLCu_oPEdA_v93QFZMgkya3M7kQw2a4L7MbZPg/edit?gid=0"
    },
    {
      "agency": "NEWBLUE",
      "sub": null,
      "file_id": "1QfWh_5RbmoNTIozr6QHbrPv4weS-uZpQ",
      "gid": "1770250163",
      "url": "https://docs.google.com/spreadsheets/d/1QfWh_5RbmoNTIozr6QHbrPv4weS-uZpQ/edit?gid=1770250163"
    },
    {
      "agency": "MEGAHOME",
      "sub": null,
      "file_id": "1mQ4FADcUxsiTuCajXQPgG9xE79RoJPPq1D6-dcOiApY",
      "gid": "718372191",
      "url": "https://docs.google.com/spreadsheets/d/1mQ4FADcUxsiTuCajXQPgG9xE79RoJPPq1D6-dcOiApY/edit?gid=718372191"
    },
    {
      "agency": "QHOME",
      "sub": null,
      "file_id": "1AbRv0JMzA7MBo0sZgLR-HhH-z8PEid1W14fAYBpSM6Y",
      "gid": "1074495421",
      "url": "https://docs.google.com/spreadsheets/d/1AbRv0JMzA7MBo0sZgLR-HhH-z8PEid1W14fAYBpSM6Y/edit?gid=1074495421"
    }
  ],
  "MIK OCP": [
    {
      "agency": "VHS",
      "sub": null,
      "file_id": "1qgQcVHgeErbj6TjlxO-HXvOCzEeW5sqOe5DQcCjDkUU",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1qgQcVHgeErbj6TjlxO-HXvOCzEeW5sqOe5DQcCjDkUU/edit?usp=drivesdk"
    },
    {
      "agency": "AN PHÁT",
      "sub": null,
      "file_id": "12bjiMkd6DzAy1FpY9v-dhvHkxgnUx3rRMGKgUpSyuCY",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/12bjiMkd6DzAy1FpY9v-dhvHkxgnUx3rRMGKgUpSyuCY/edit?usp=sharing"
    },
    {
      "agency": "VISION (neway)",
      "sub": null,
      "file_id": "1yUTMDpNZSzrut2LX8hnsr6D6FoZLcDUw",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1yUTMDpNZSzrut2LX8hnsr6D6FoZLcDUw/edit?usp=drivesdk&ouid=118160950773836280307&rtpof=true&sd=true"
    },
    {
      "agency": "G.EMPIRE",
      "sub": null,
      "file_id": "1BDUpGDYVF9L65YWrBKCJ_15U2sCvqQcGoMAVyL6dJRA",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1BDUpGDYVF9L65YWrBKCJ_15U2sCvqQcGoMAVyL6dJRA/edit?usp=drivesdk"
    },
    {
      "agency": "CENLAND",
      "sub": null,
      "file_id": "1T-T5lpmvTw2yg2kEdvm07Q9tQL3Sw3vA95_q4HyDDnk",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1T-T5lpmvTw2yg2kEdvm07Q9tQL3Sw3vA95_q4HyDDnk/edit?gid=0"
    },
    {
      "agency": "PHÚ LÂM",
      "sub": null,
      "file_id": "14hSrs7TF9hVxgTPq2OJRiUgT36-yQdPl",
      "gid": "133185477",
      "url": "https://docs.google.com/spreadsheets/d/14hSrs7TF9hVxgTPq2OJRiUgT36-yQdPl/edit?gid=133185477"
    },
    {
      "agency": "MV",
      "sub": null,
      "file_id": "1oUd5NGaS6d9liQTPWKLFxpFFzbZOAVAx2QKAzFjSeQc",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1oUd5NGaS6d9liQTPWKLFxpFFzbZOAVAx2QKAzFjSeQc/edit?usp=drivesdk"
    },
    {
      "agency": "ĐTL",
      "sub": null,
      "file_id": "1n-dYWWuuQ0nOlEmaEC8CuAL1bZAzZ-Rc",
      "gid": "1844896858",
      "url": "https://docs.google.com/spreadsheets/d/1n-dYWWuuQ0nOlEmaEC8CuAL1bZAzZ-Rc/edit?gid=1844896858"
    },
    {
      "agency": "THIÊN PHÚC",
      "sub": null,
      "file_id": "1xRp7nbT0gwG_JGqtwqBPrZeC_fpPot-U",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1xRp7nbT0gwG_JGqtwqBPrZeC_fpPot-U/edit?usp=sharing&ouid=109383521046517321815&rtpof=true&sd=true"
    },
    {
      "agency": "MAYHOMES",
      "sub": null,
      "file_id": "1mN2yKQNjddl7fgF8BIJINGJPmSltFOdurE9D80WiU3I",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1mN2yKQNjddl7fgF8BIJINGJPmSltFOdurE9D80WiU3I/edit?usp=drivesdk"
    },
    {
      "agency": "RBS (RETI)",
      "sub": null,
      "file_id": "1YhWt5k38p3ZSRQZIj-i5w69YZTDxStLHWzr_Ar226M4",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1YhWt5k38p3ZSRQZIj-i5w69YZTDxStLHWzr_Ar226M4/edit?usp=sharing"
    },
    {
      "agency": "JOY HOMES",
      "sub": null,
      "file_id": "1-S0b8jdNj-v4xPEPEk8bh8sZi3sUxdV5Mto10_1obVM",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1-S0b8jdNj-v4xPEPEk8bh8sZi3sUxdV5Mto10_1obVM/edit?usp=drive_link"
    },
    {
      "agency": "SSM",
      "sub": null,
      "file_id": "1FLGFKEfJUlu9QbL3rUwugX5NBVXnFb4NpbMVu8IVD60",
      "gid": "807187799",
      "url": "https://docs.google.com/spreadsheets/d/1FLGFKEfJUlu9QbL3rUwugX5NBVXnFb4NpbMVu8IVD60/edit?gid=807187799"
    },
    {
      "agency": "NSL",
      "sub": null,
      "file_id": "13yYOWrdcFTdQILKdN5ChJXrQgzBZSgfEE6vAJE9vTiE",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/13yYOWrdcFTdQILKdN5ChJXrQgzBZSgfEE6vAJE9vTiE/edit?gid=0"
    },
    {
      "agency": "Elite Capital",
      "sub": null,
      "file_id": "1LubFTwDtaA1Edti5hg567HWqA6JHb-7CWrFswrMdUDo",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1LubFTwDtaA1Edti5hg567HWqA6JHb-7CWrFswrMdUDo/edit?usp=sharing"
    },
    {
      "agency": "Đông Phương",
      "sub": null,
      "file_id": "1sezewFIhbBJjps1C1MYbEbWYnPOIbVbnyXIVOYB4z0E",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1sezewFIhbBJjps1C1MYbEbWYnPOIbVbnyXIVOYB4z0E/edit?gid=0"
    },
    {
      "agency": "TDL",
      "sub": null,
      "file_id": "1mpa89O2ZDe18UgJ_ubsvO4v7N5G-XtuE",
      "gid": "328690419",
      "url": "https://docs.google.com/spreadsheets/d/1mpa89O2ZDe18UgJ_ubsvO4v7N5G-XtuE/edit?gid=328690419"
    },
    {
      "agency": "VINSLAND",
      "sub": null,
      "file_id": "1MuxXcZPOEOCOeGgJwMtm5Ysasm9bi9r_RPpIRo0227g",
      "gid": "1179540253",
      "url": "https://docs.google.com/spreadsheets/d/1MuxXcZPOEOCOeGgJwMtm5Ysasm9bi9r_RPpIRo0227g/edit?gid=1179540253"
    },
    {
      "agency": "ATD",
      "sub": null,
      "file_id": "1tpe89VULNVNJz_vZCZx8rpuRi9K7Hssiy-Y3M82DFic",
      "gid": "388737391",
      "url": "https://docs.google.com/spreadsheets/d/1tpe89VULNVNJz_vZCZx8rpuRi9K7Hssiy-Y3M82DFic/edit?gid=388737391"
    },
    {
      "agency": "TÂN LONG",
      "sub": null,
      "file_id": "1NrfeGlTsBVkj8vF0BMYsHsgolkQJplOKWX-C3NEcR9s",
      "gid": "1969275945",
      "url": "https://docs.google.com/spreadsheets/d/1NrfeGlTsBVkj8vF0BMYsHsgolkQJplOKWX-C3NEcR9s/edit?gid=1969275945"
    },
    {
      "agency": "M-Holdings",
      "sub": null,
      "file_id": "1dhI8pdkh2y7oankQ4o9J3vb_oB7-V06E-DGlKsa_2n8",
      "gid": "929441220",
      "url": "https://docs.google.com/spreadsheets/d/1dhI8pdkh2y7oankQ4o9J3vb_oB7-V06E-DGlKsa_2n8/edit?gid=929441220"
    },
    {
      "agency": "Aura",
      "sub": null,
      "file_id": "1cJbI0aHnMElQICLiy1S2_siKPXFSnqfy",
      "gid": "2066003543",
      "url": "https://docs.google.com/spreadsheets/d/1cJbI0aHnMElQICLiy1S2_siKPXFSnqfy/edit?gid=2066003543"
    },
    {
      "agency": "Tiến Phát",
      "sub": null,
      "file_id": "1eCGOfSE-v6IFV-7t0x_H3yNJzBW_F90kDDjawHq7ZZ4",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1eCGOfSE-v6IFV-7t0x_H3yNJzBW_F90kDDjawHq7ZZ4/edit?gid=0"
    },
    {
      "agency": "VSL",
      "sub": null,
      "file_id": "1oCI5eYs6-smIpGC4QkzETutfSdJZfQU-6eEsEY58rus",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1oCI5eYs6-smIpGC4QkzETutfSdJZfQU-6eEsEY58rus/edit?usp=drivesdk"
    },
    {
      "agency": "DIAMOE HOLDING",
      "sub": null,
      "file_id": "15UxyOoV4epEDMrSkZi9o_Q0SCMnjay-H",
      "gid": "1623028031",
      "url": "https://docs.google.com/spreadsheets/d/15UxyOoV4epEDMrSkZi9o_Q0SCMnjay-H/edit?gid=1623028031"
    },
    {
      "agency": "BIGHOME",
      "sub": null,
      "file_id": "1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8",
      "gid": "771636370",
      "url": "https://docs.google.com/spreadsheets/d/1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8/edit?gid=771636370"
    },
    {
      "agency": "NOVASKY",
      "sub": null,
      "file_id": "1cxfixi2rT_eUTlHszWEQsg26Urw796-8TrRqHbf3GEs",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1cxfixi2rT_eUTlHszWEQsg26Urw796-8TrRqHbf3GEs/edit?usp=drivesdk"
    },
    {
      "agency": "ROMAN",
      "sub": null,
      "file_id": "1n3d1Bvj-XuhLjKwwdwVCETgWuGmtripgT9j9tWkLKlI",
      "gid": "1391720637",
      "url": "https://docs.google.com/spreadsheets/d/1n3d1Bvj-XuhLjKwwdwVCETgWuGmtripgT9j9tWkLKlI/edit?gid=1391720637"
    },
    {
      "agency": "HDH",
      "sub": null,
      "file_id": "1EfBh80lKRmVdk0oyYIOAnxUi6QYQwiPA",
      "gid": "175022391",
      "url": "https://docs.google.com/spreadsheets/d/1EfBh80lKRmVdk0oyYIOAnxUi6QYQwiPA/edit?gid=175022391"
    },
    {
      "agency": "PHÚC LỘC",
      "sub": null,
      "file_id": "13kth15x7s-YFy6Di-gi4Usm6rfTYdZ2UyhmlwK-K8Nc",
      "gid": "1813751609",
      "url": "https://docs.google.com/spreadsheets/d/13kth15x7s-YFy6Di-gi4Usm6rfTYdZ2UyhmlwK-K8Nc/edit?gid=1813751609"
    },
    {
      "agency": "METALAND",
      "sub": null,
      "file_id": "1lezEjJNrTcCIMsWHnE7dM8rh6JfTppGlnnKl6007oKM",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1lezEjJNrTcCIMsWHnE7dM8rh6JfTppGlnnKl6007oKM/edit?gid=0"
    },
    {
      "agency": "HP",
      "sub": null,
      "file_id": "1j6mQNMg-OpKL_pniAJHE5N3JsB4IQEJLIyauOmQdHnc",
      "gid": "579635785",
      "url": "https://docs.google.com/spreadsheets/d/1j6mQNMg-OpKL_pniAJHE5N3JsB4IQEJLIyauOmQdHnc/edit?gid=579635785"
    },
    {
      "agency": "ĐẤT VIỆT",
      "sub": null,
      "file_id": "1fU-U4_-jqXPd871c4yLPImjajnZ7Q3N_",
      "gid": "1985337590",
      "url": "https://docs.google.com/spreadsheets/d/1fU-U4_-jqXPd871c4yLPImjajnZ7Q3N_/edit?gid=1985337590"
    },
    {
      "agency": "FIVESTAR",
      "sub": null,
      "file_id": "1QRT3BZu5q_ljJpa2k3Z_vpb0cZQL9wX8KR8vHuMHg_w",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1QRT3BZu5q_ljJpa2k3Z_vpb0cZQL9wX8KR8vHuMHg_w/edit?usp=drivesdk"
    },
    {
      "agency": "ASTAR",
      "sub": null,
      "file_id": "1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8",
      "gid": "771636370",
      "url": "https://docs.google.com/spreadsheets/d/1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8/edit?gid=771636370"
    },
    {
      "agency": "Trường phát (metro)",
      "sub": null,
      "file_id": "1aQm0W77KOmOaEuowX6pRzLJZxzSEHNS3",
      "gid": "1161122128",
      "url": "https://docs.google.com/spreadsheets/d/1aQm0W77KOmOaEuowX6pRzLJZxzSEHNS3/edit?rtpof=true&gid=1161122128"
    },
    {
      "agency": "AHS",
      "sub": null,
      "file_id": "1PGlHt6Ho3THHT-o87XHUbDDilO7Ktln8vwHdOFbGujk",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1PGlHt6Ho3THHT-o87XHUbDDilO7Ktln8vwHdOFbGujk/edit?gid=0"
    },
    {
      "agency": "Vinsland",
      "sub": null,
      "file_id": "1MuxXcZPOEOCOeGgJwMtm5Ysasm9bi9r_RPpIRo0227g",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1MuxXcZPOEOCOeGgJwMtm5Ysasm9bi9r_RPpIRo0227g/edit?gid=0"
    },
    {
      "agency": "queenland",
      "sub": null,
      "file_id": "1qV3tQ_KG5bd3ZCHPvVUgHkeL2ofrAL7k",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1qV3tQ_KG5bd3ZCHPvVUgHkeL2ofrAL7k/edit?usp=drivesdk&ouid=103024372198281112107&rtpof=true&sd=true"
    }
  ],
  "DƯƠNG KINH": [
    {
      "agency": "MAYHOMES",
      "sub": null,
      "file_id": "1SvPEmQFTHgEFPq9G-H_W38PGEtMpksYFe5dILVAhmqA",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1SvPEmQFTHgEFPq9G-H_W38PGEtMpksYFe5dILVAhmqA/edit?gid=0"
    },
    {
      "agency": "TÂN THỜI ĐẠI",
      "sub": null,
      "file_id": "1FAOmYrPEK-PQOxVDLXHJ1_Y28r_RzhfL",
      "gid": "737137173",
      "url": "https://docs.google.com/spreadsheets/d/1FAOmYrPEK-PQOxVDLXHJ1_Y28r_RzhfL/edit?gid=737137173"
    },
    {
      "agency": "MICC",
      "sub": null,
      "file_id": "1dL9TSYc6CYxFE7kR_ZCLUGI0vz-I_nd4g4iTka07VmE",
      "gid": "1016242186",
      "url": "https://docs.google.com/spreadsheets/d/1dL9TSYc6CYxFE7kR_ZCLUGI0vz-I_nd4g4iTka07VmE/edit?gid=1016242186"
    },
    {
      "agency": "DIAMOND LAND",
      "sub": null,
      "file_id": "1pQAsSK80nmmwCLnjvBo67rGlYMpDGwoj",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1pQAsSK80nmmwCLnjvBo67rGlYMpDGwoj/edit?rtpof=true&sd=true"
    },
    {
      "agency": "SSM",
      "sub": null,
      "file_id": "1U8ovi-zmpY0oE8mHsJnR5mSwmgO0xq_rn5d5kkRk5Pg",
      "gid": "1770519065",
      "url": "https://docs.google.com/spreadsheets/d/1U8ovi-zmpY0oE8mHsJnR5mSwmgO0xq_rn5d5kkRk5Pg/edit?gid=1770519065"
    },
    {
      "agency": "NEWSTARLAND",
      "sub": null,
      "file_id": "1lWiCcmnOG7qGpKKIJqHFShKbYk_g0vavkQFc0Ysd-38",
      "gid": "1543985326",
      "url": "https://docs.google.com/spreadsheets/d/1lWiCcmnOG7qGpKKIJqHFShKbYk_g0vavkQFc0Ysd-38/edit?gid=1543985326"
    },
    {
      "agency": "MINH MINH",
      "sub": null,
      "file_id": "1RUtPV74Khls1uc5zJRxcZyEB1ABpp5eH",
      "gid": "502116423",
      "url": "https://docs.google.com/spreadsheets/d/1RUtPV74Khls1uc5zJRxcZyEB1ABpp5eH/edit?rtpof=true&sd=true&gid=502116423"
    },
    {
      "agency": "MDLAND",
      "sub": null,
      "file_id": "1J3UZdjPZtCQlT-me75mUjeSYgWw7ciHUJYE1ThrTJtg",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1J3UZdjPZtCQlT-me75mUjeSYgWw7ciHUJYE1ThrTJtg/edit?gid=0"
    },
    {
      "agency": "TÂN HƯƠNG PHÁT",
      "sub": null,
      "file_id": "1x5EQSSFUMerAHPkCYTpC34xhTKaXeEEzXv8oKnBYyck",
      "gid": "1079713439",
      "url": "https://docs.google.com/spreadsheets/d/1x5EQSSFUMerAHPkCYTpC34xhTKaXeEEzXv8oKnBYyck/edit?gid=1079713439"
    },
    {
      "agency": "HDHOMES",
      "sub": null,
      "file_id": "1Tk_GdLy-B7GbybKCSjcTzlHAa4Rcg2DwHyREpAjZcaU",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1Tk_GdLy-B7GbybKCSjcTzlHAa4Rcg2DwHyREpAjZcaU/edit?gid=0"
    },
    {
      "agency": "BIGHOMES",
      "sub": null,
      "file_id": "1aes6oJ5L8RCjeK4zw77FJCaPfElHTAch",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1aes6oJ5L8RCjeK4zw77FJCaPfElHTAch/edit?dls=true"
    },
    {
      "agency": "ĐẤT VIỆT",
      "sub": null,
      "file_id": "14T25ZRhzO5nW54CNTixPoZqc9iVbEVwtg_HNcRoEwEM",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/14T25ZRhzO5nW54CNTixPoZqc9iVbEVwtg_HNcRoEwEM/edit?gid=0"
    },
    {
      "agency": "FIVESTAR",
      "sub": null,
      "file_id": "1RNUeNC1uOI1QKxCdOLVscalJBf353Zeqv2dAb21CDVM",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1RNUeNC1uOI1QKxCdOLVscalJBf353Zeqv2dAb21CDVM/edit?gid=0"
    },
    {
      "agency": "QUEENLAND",
      "sub": null,
      "file_id": "1fi4BGkHTt5VxLKe-vRfTytNohQxOQQlctscaMZQ_O_k",
      "gid": "1691869383",
      "url": "https://docs.google.com/spreadsheets/d/1fi4BGkHTt5VxLKe-vRfTytNohQxOQQlctscaMZQ_O_k/edit?gid=1691869383"
    },
    {
      "agency": "VIETSTARLAND",
      "sub": null,
      "file_id": "1gmANVel_Rp08lhuiFJYdAT8ch_3gXXfj",
      "gid": "152091165",
      "url": "https://docs.google.com/spreadsheets/d/1gmANVel_Rp08lhuiFJYdAT8ch_3gXXfj/edit?gid=152091165"
    },
    {
      "agency": "THIÊN PHÚC",
      "sub": null,
      "file_id": "1DNkMCqpLAPUVJJ9dJCfn7YqhFl_FDZ4nuptSegjIUrc",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1DNkMCqpLAPUVJJ9dJCfn7YqhFl_FDZ4nuptSegjIUrc/edit?gid=0"
    },
    {
      "agency": "ĐÔNG PHƯƠNG",
      "sub": null,
      "file_id": "1yf0MNreT0MR-4mXoqYLjWRtotHG4XwBF3eMFvT1HGis",
      "gid": "1427006936",
      "url": "https://docs.google.com/spreadsheets/d/1yf0MNreT0MR-4mXoqYLjWRtotHG4XwBF3eMFvT1HGis/edit?gid=1427006936"
    },
    {
      "agency": "NOVASKY",
      "sub": null,
      "file_id": "1joXFB6XY7yNyAjb5jpcuW2B5sX65iRCp",
      "gid": "1052333379",
      "url": "https://docs.google.com/spreadsheets/d/1joXFB6XY7yNyAjb5jpcuW2B5sX65iRCp/edit?gid=1052333379"
    },
    {
      "agency": "VISION REALTY",
      "sub": null,
      "file_id": "1cVVi8tPEqra833qqVXuPb-Gju80-ExOHrHbcNT6BW48",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1cVVi8tPEqra833qqVXuPb-Gju80-ExOHrHbcNT6BW48/edit?gid=0"
    },
    {
      "agency": "KHP",
      "sub": null,
      "file_id": "1EtKn7zxiy-Fs2qLfq9qouI1NO4xW0L7MT5HeGwEscYg",
      "gid": "1194505456",
      "url": "https://docs.google.com/spreadsheets/d/1EtKn7zxiy-Fs2qLfq9qouI1NO4xW0L7MT5HeGwEscYg/edit?gid=1194505456"
    },
    {
      "agency": "ROMAN",
      "sub": null,
      "file_id": "19ThDox5BUUmIk2CqPlhX8LcOtNgF9GhH-aLEaqbKSHQ",
      "gid": "495161037",
      "url": "https://docs.google.com/spreadsheets/d/19ThDox5BUUmIk2CqPlhX8LcOtNgF9GhH-aLEaqbKSHQ/edit?gid=495161037"
    },
    {
      "agency": "TRƯỜNG PHÁT",
      "sub": null,
      "file_id": "1mP8o1HPAda2SwyosbZO3peB4OvYOaNZ8BJybgK5TAZo",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1mP8o1HPAda2SwyosbZO3peB4OvYOaNZ8BJybgK5TAZo/edit?gid=0"
    },
    {
      "agency": "HOMEPLUS",
      "sub": null,
      "file_id": "1-4DIiWTn2T6tlCcSAZiqeEN0Rewt-UE7jyMl-o8W4o4",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1-4DIiWTn2T6tlCcSAZiqeEN0Rewt-UE7jyMl-o8W4o4/edit?gid=0"
    },
    {
      "agency": "QC BEST",
      "sub": null,
      "file_id": "1B01LerG29HD89lsPrixHWWx2t-nbzklg",
      "gid": "645850692",
      "url": "https://docs.google.com/spreadsheets/d/1B01LerG29HD89lsPrixHWWx2t-nbzklg/edit?gid=645850692"
    }
  ],
  "HLX": [
    {
      "agency": "BHOMES",
      "sub": null,
      "file_id": "1X22IimjtzIKyAtqhatPenSWaiuR8bdm-GSqxUuFQIY0",
      "gid": "731272395",
      "url": "https://docs.google.com/spreadsheets/d/1X22IimjtzIKyAtqhatPenSWaiuR8bdm-GSqxUuFQIY0/edit?gid=731272395#gid=731272395"
    },
    {
      "agency": "ELITE CAPITAL",
      "sub": null,
      "file_id": "1vrt8OcTYEfJKRTh2kJLussiGW1p-Jb_KTCt6bH2r-Js",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1vrt8OcTYEfJKRTh2kJLussiGW1p-Jb_KTCt6bH2r-Js/edit?gid=0#gid=0"
    },
    {
      "agency": "MAYHOMES",
      "sub": null,
      "file_id": "1TCCyj4npP0VJjwLCN7i1Z7RSpsWdtDyi-lUp1GO-TvI",
      "gid": "324247473",
      "url": "https://docs.google.com/spreadsheets/d/1TCCyj4npP0VJjwLCN7i1Z7RSpsWdtDyi-lUp1GO-TvI/edit?gid=324247473#gid=324247473"
    },
    {
      "agency": "IHOLDINGS",
      "sub": null,
      "file_id": "19FDj5zzl2ZwPftOdoXSMJGnlcVrHqE3zAfyAfn-JYsM",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/19FDj5zzl2ZwPftOdoXSMJGnlcVrHqE3zAfyAfn-JYsM/edit?gid=0#gid=0"
    },
    {
      "agency": "VIETSTARLAND",
      "sub": null,
      "file_id": "10GyTEH439hI0nnU4pYSwOjQSVOERWTI1-rmXcGraUYQ",
      "gid": "1764864771",
      "url": "https://docs.google.com/spreadsheets/d/10GyTEH439hI0nnU4pYSwOjQSVOERWTI1-rmXcGraUYQ/edit?gid=1764864771#gid=1764864771"
    },
    {
      "agency": "TÂN LONG",
      "sub": null,
      "file_id": "1mAVabKzwcRusXplslTcaKvrBCwoVglqb",
      "gid": "967385513",
      "url": "https://docs.google.com/spreadsheets/d/1mAVabKzwcRusXplslTcaKvrBCwoVglqb/edit?gid=967385513#gid=967385513"
    },
    {
      "agency": "ĐẤT VIỆT GROUP",
      "sub": null,
      "file_id": "1mVPatqNC0N4psvzb62314cxQHUG-9eLeKjRGmudjEKw",
      "gid": "846364326",
      "url": "https://docs.google.com/spreadsheets/d/1mVPatqNC0N4psvzb62314cxQHUG-9eLeKjRGmudjEKw/edit?gid=846364326#gid=846364326"
    },
    {
      "agency": "HDHOMES",
      "sub": null,
      "file_id": "1ZZc7eZrLS8LG6SYUlCCycG97iOF-69kg",
      "gid": "2063234797",
      "url": "https://docs.google.com/spreadsheets/d/1ZZc7eZrLS8LG6SYUlCCycG97iOF-69kg/edit?gid=2063234797#gid=2063234797"
    },
    {
      "agency": "TIẾN PHÁT SUNRISE",
      "sub": null,
      "file_id": "14_pog9zgklJSLzpVvpU0Laww84hY8q-2rO0ofzvdpuo",
      "gid": "92245854",
      "url": "https://docs.google.com/spreadsheets/d/14_pog9zgklJSLzpVvpU0Laww84hY8q-2rO0ofzvdpuo/edit?gid=92245854#gid=92245854"
    },
    {
      "agency": "MINH MINH GROUP",
      "sub": null,
      "file_id": "1OpoFKk8RtCDSdukzwUK9ISZ385XovCnSKeZ8Bj1hWrA",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1OpoFKk8RtCDSdukzwUK9ISZ385XovCnSKeZ8Bj1hWrA/edit?gid=0#gid=0"
    },
    {
      "agency": "MGLAND",
      "sub": null,
      "file_id": "1wlDcocTRC6fHaiChBUzpjXjqPfuStvDH",
      "gid": "1628124256",
      "url": "https://docs.google.com/spreadsheets/d/1wlDcocTRC6fHaiChBUzpjXjqPfuStvDH/edit?gid=1628124256#gid=1628124256"
    },
    {
      "agency": "NOVASKY",
      "sub": null,
      "file_id": "1fPDhR13jq3uANbv35PKXjbUWlvSnw-vo",
      "gid": "1995423151",
      "url": "https://docs.google.com/spreadsheets/d/1fPDhR13jq3uANbv35PKXjbUWlvSnw-vo/edit?gid=1995423151#gid=1995423151"
    },
    {
      "agency": "QHOMES",
      "sub": null,
      "file_id": "1lGbBy7c80j_gNETL4uZIS32D4ZruudcpaOa09NrJc-o",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1lGbBy7c80j_gNETL4uZIS32D4ZruudcpaOa09NrJc-o/edit?gid=0#gid=0"
    },
    {
      "agency": "BHS PARTNERS",
      "sub": null,
      "file_id": "1nm4QGW836mv0Dm4iMG-zHr9KkrrPq2GtXJzEAaLjmOw",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1nm4QGW836mv0Dm4iMG-zHr9KkrrPq2GtXJzEAaLjmOw/edit?gid=0#gid=0"
    },
    {
      "agency": "TÂN THỜI ĐẠI",
      "sub": null,
      "file_id": "1gKlLw9zzdXkmUPObC0T4TZTx5mQoVMN1achL_AuQNC8",
      "gid": "2018602417",
      "url": "https://docs.google.com/spreadsheets/d/1gKlLw9zzdXkmUPObC0T4TZTx5mQoVMN1achL_AuQNC8/edit?gid=2018602417#gid=2018602417"
    },
    {
      "agency": "QCBEST",
      "sub": null,
      "file_id": "1aFjohF749aXcoVMd7oD1H1ERq27vjBD866GujF-mWlY",
      "gid": "1174805011",
      "url": "https://docs.google.com/spreadsheets/d/1aFjohF749aXcoVMd7oD1H1ERq27vjBD866GujF-mWlY/edit?gid=1174805011#gid=1174805011"
    },
    {
      "agency": "TRƯỜNG PHÁT",
      "sub": null,
      "file_id": "1et1iWGw7-G4jCNPVXqAwmWwZn1dphbAhZrrLBqxQ9bI",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1et1iWGw7-G4jCNPVXqAwmWwZn1dphbAhZrrLBqxQ9bI/edit?gid=0#gid=0"
    },
    {
      "agency": "MICC GROUP",
      "sub": null,
      "file_id": "1LckFlBpCEhPDEg3qPRgkIHiDDsLxEw4ckpvWujCyK1A",
      "gid": "1394544682",
      "url": "https://docs.google.com/spreadsheets/d/1LckFlBpCEhPDEg3qPRgkIHiDDsLxEw4ckpvWujCyK1A/edit?gid=1394544682#gid=1394544682"
    },
    {
      "agency": "FOUR HOME",
      "sub": null,
      "file_id": "1sV4qW4GtfKwzIksQhqIgjb_I6vY7JxDj",
      "gid": "97023775",
      "url": "https://docs.google.com/spreadsheets/d/1sV4qW4GtfKwzIksQhqIgjb_I6vY7JxDj/edit?gid=97023775#gid=97023775"
    },
    {
      "agency": "CEN HÀ NỘI",
      "sub": null,
      "file_id": "15nncTnzejMD27ojp4INzM9FfgtjzwujbxIG9OsMb18U",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/15nncTnzejMD27ojp4INzM9FfgtjzwujbxIG9OsMb18U/edit?gid=0#gid=0"
    },
    {
      "agency": "VICTORY HOLDINGS",
      "sub": null,
      "file_id": "1Fhu26_g-NyhEqK9Ovei29kJ61u9YiAQW1641EiJTWPg",
      "gid": "1569229129",
      "url": "https://docs.google.com/spreadsheets/d/1Fhu26_g-NyhEqK9Ovei29kJ61u9YiAQW1641EiJTWPg/edit?gid=1569229129#gid=1569229129"
    },
    {
      "agency": "HOME PLUS",
      "sub": null,
      "file_id": "19lZEW0RTC8C6hOT2RSH2Em_4C9gTvbiA7bicUJFzEYI",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/19lZEW0RTC8C6hOT2RSH2Em_4C9gTvbiA7bicUJFzEYI/edit?gid=0#gid=0"
    },
    {
      "agency": "MDLAND",
      "sub": null,
      "file_id": "1KIcOPA3jULXIWGsfnXaNotcflkkfKmJbZCZhp_hi6ng",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1KIcOPA3jULXIWGsfnXaNotcflkkfKmJbZCZhp_hi6ng/edit?gid=0#gid=0"
    },
    {
      "agency": "NEWSTARLAND",
      "sub": null,
      "file_id": "1dkfhzSFUyxB9tKR3IimhQp-r07wLdUoMywFZhX9NZrw",
      "gid": "100008478",
      "url": "https://docs.google.com/spreadsheets/d/1dkfhzSFUyxB9tKR3IimhQp-r07wLdUoMywFZhX9NZrw/edit?gid=100008478#gid=100008478"
    },
    {
      "agency": "TICA LAND",
      "sub": null,
      "file_id": "1Ui8DI-BUJGcizv8rCgVJBUG-9eZ7H3vE",
      "gid": "1432943488",
      "url": "https://docs.google.com/spreadsheets/d/1Ui8DI-BUJGcizv8rCgVJBUG-9eZ7H3vE/edit?gid=1432943488#gid=1432943488"
    },
    {
      "agency": "QUEENLAND",
      "sub": null,
      "file_id": "1aUxxwDIQXf23nS07idycvYpx9lFLnDm2BuphHoYz6f0",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1aUxxwDIQXf23nS07idycvYpx9lFLnDm2BuphHoYz6f0/edit?gid=0#gid=0"
    },
    {
      "agency": "BIGHOMES GROUP",
      "sub": null,
      "file_id": "1m5kpK-giWB5xlE-M77f7uk5IRRh6gMyv",
      "gid": "1412089424",
      "url": "https://docs.google.com/spreadsheets/d/1m5kpK-giWB5xlE-M77f7uk5IRRh6gMyv/edit?gid=1412089424#gid=1412089424"
    },
    {
      "agency": "HOÀNG GIA",
      "sub": null,
      "file_id": "1wGHBIq_lC0mTuZxh9DlTnd0CwJYyazKa",
      "gid": "786390698",
      "url": "https://docs.google.com/spreadsheets/d/1wGHBIq_lC0mTuZxh9DlTnd0CwJYyazKa/edit?pli=1&gid=786390698#gid=786390698"
    },
    {
      "agency": "VHS GROUP",
      "sub": null,
      "file_id": "1J4266FAPcSNpEkbE2C2CRjWamrzheZkXctBqqO4LOUk",
      "gid": "1315973653",
      "url": "https://docs.google.com/spreadsheets/d/1J4266FAPcSNpEkbE2C2CRjWamrzheZkXctBqqO4LOUk/edit?gid=1315973653#gid=1315973653"
    },
    {
      "agency": "VISION REALTY",
      "sub": null,
      "file_id": "1aUyuNZcnc7QS1QxZW2oLeOShXaNcR1Is16qt9a4r7E0",
      "gid": "1122142689",
      "url": "https://docs.google.com/spreadsheets/d/1aUyuNZcnc7QS1QxZW2oLeOShXaNcR1Is16qt9a4r7E0/edit?gid=1122142689#gid=1122142689"
    },
    {
      "agency": "QTC",
      "sub": null,
      "file_id": "1Ug-PXldGLw1LRkR_5Y_0WDqetgx9svlv",
      "gid": "841568026",
      "url": "https://docs.google.com/spreadsheets/d/1Ug-PXldGLw1LRkR_5Y_0WDqetgx9svlv/edit?gid=841568026#gid=841568026"
    },
    {
      "agency": "FIVE STAR",
      "sub": null,
      "file_id": "16TJiktr75fGci6uWmE3MOXi1qFJ4NotpU2sOBSiIe4U",
      "gid": "2106624498",
      "url": "https://docs.google.com/spreadsheets/d/16TJiktr75fGci6uWmE3MOXi1qFJ4NotpU2sOBSiIe4U/edit?gid=2106624498#gid=2106624498"
    },
    {
      "agency": "BHOMES",
      "sub": null,
      "file_id": "1X22IimjtzIKyAtqhatPenSWaiuR8bdm-GSqxUuFQIY0",
      "gid": "731272395",
      "url": "https://docs.google.com/spreadsheets/d/1X22IimjtzIKyAtqhatPenSWaiuR8bdm-GSqxUuFQIY0/edit?gid=731272395#gid=731272395"
    },
    {
      "agency": "ĐÔNG PHƯƠNG",
      "sub": null,
      "file_id": "1-cF3xNHotgAmH5E7Lpl17OWrZ58Ck9AW2RKK7Iw1bLc",
      "gid": "1496835381",
      "url": "https://docs.google.com/spreadsheets/d/1-cF3xNHotgAmH5E7Lpl17OWrZ58Ck9AW2RKK7Iw1bLc/edit?gid=1496835381#gid=1496835381"
    },
    {
      "agency": "MAI VIỆT LAND",
      "sub": null,
      "file_id": "1jPk-DuPmdKXbBG891_tQwXcFLNn-hkre",
      "gid": "431347636",
      "url": "https://docs.google.com/spreadsheets/d/1jPk-DuPmdKXbBG891_tQwXcFLNn-hkre/edit?gid=431347636#gid=431347636"
    },
    {
      "agency": "ROMAN PROPERTY",
      "sub": null,
      "file_id": "1L8TbslXM_ByR8PUbmN-LH3cwBjAXnqEJ1WfhgODppbs",
      "gid": "1424934000",
      "url": "https://docs.google.com/spreadsheets/d/1L8TbslXM_ByR8PUbmN-LH3cwBjAXnqEJ1WfhgODppbs/edit?gid=1424934000#gid=1424934000"
    },
    {
      "agency": "SAO VÀNG HOLDINGS",
      "sub": null,
      "file_id": "1-7W1y5WQpTaqQnDZ0vESPJHPl7DhVueWDcRl9D_qwbE",
      "gid": "928005377",
      "url": "https://docs.google.com/spreadsheets/d/1-7W1y5WQpTaqQnDZ0vESPJHPl7DhVueWDcRl9D_qwbE/edit?gid=928005377#gid=928005377"
    },
    {
      "agency": "SUPERLAND",
      "sub": null,
      "file_id": "1sqp5ZJQ6zNYZ0d3MDUwruf-Vse0LLqea",
      "gid": "1537305799",
      "url": "https://docs.google.com/spreadsheets/d/1sqp5ZJQ6zNYZ0d3MDUwruf-Vse0LLqea/edit?gid=1537305799#gid=1537305799"
    },
    {
      "agency": "SSM GROUP",
      "sub": null,
      "file_id": "1PCyUFKPJsfPUKQx5hexziQosIvQ0CsX2c0iiZBiriak",
      "gid": "1093064709",
      "url": "https://docs.google.com/spreadsheets/d/1PCyUFKPJsfPUKQx5hexziQosIvQ0CsX2c0iiZBiriak/edit?gid=1093064709#gid=1093064709"
    },
    {
      "agency": "TÂN HƯƠNG PHÁT",
      "sub": null,
      "file_id": "1rCKAkRiRMYo3WWx9hYrgEexRrrW6Kk6ER2yuSn4Q1yE",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1rCKAkRiRMYo3WWx9hYrgEexRrrW6Kk6ER2yuSn4Q1yE/edit?gid=0#gid=0"
    },
    {
      "agency": "SUPERLAND",
      "sub": null,
      "file_id": "1sqp5ZJQ6zNYZ0d3MDUwruf-Vse0LLqea",
      "gid": "1537305799",
      "url": "https://docs.google.com/spreadsheets/d/1sqp5ZJQ6zNYZ0d3MDUwruf-Vse0LLqea/edit?gid=1537305799#gid=1537305799"
    },
    {
      "agency": "SSM GROUP",
      "sub": null,
      "file_id": "1PCyUFKPJsfPUKQx5hexziQosIvQ0CsX2c0iiZBiriak",
      "gid": "1093064709",
      "url": "https://docs.google.com/spreadsheets/d/1PCyUFKPJsfPUKQx5hexziQosIvQ0CsX2c0iiZBiriak/edit?gid=1093064709#gid=1093064709"
    },
    {
      "agency": "TÂN HƯƠNG PHÁT",
      "sub": null,
      "file_id": "1rCKAkRiRMYo3WWx9hYrgEexRrrW6Kk6ER2yuSn4Q1yE",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1rCKAkRiRMYo3WWx9hYrgEexRrrW6Kk6ER2yuSn4Q1yE/edit?gid=0#gid=0"
    }
  ],
  "Đan phượng": [
    {
      "agency": "HOMEPLUS",
      "sub": null,
      "file_id": "1WrwoBUpcqB0SyfPIy5hVuZnEj3-amlSyZc24ZQC7XFU",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1WrwoBUpcqB0SyfPIy5hVuZnEj3-amlSyZc24ZQC7XFU/edit?gid=0"
    },
    {
      "agency": "MICC",
      "sub": null,
      "file_id": "1-UhfQKkCOtldOOyXSfS5Ay6c79jr059Y",
      "gid": "943453673",
      "url": "https://docs.google.com/spreadsheets/d/1-UhfQKkCOtldOOyXSfS5Ay6c79jr059Y/edit?gid=943453673"
    },
    {
      "agency": "NSL",
      "sub": null,
      "file_id": "1ADT-9MPmusDG46WtstqXcwRXnLQvsPzCapYQygx9irw",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1ADT-9MPmusDG46WtstqXcwRXnLQvsPzCapYQygx9irw/edit?usp=drivesdk"
    },
    {
      "agency": "VSL",
      "sub": null,
      "file_id": "1Ry6DKk0h-vUhK-6Hob78LN04NIxTnSTbqPvXjRm-2WE",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1Ry6DKk0h-vUhK-6Hob78LN04NIxTnSTbqPvXjRm-2WE/edit?usp=embed_facebook"
    },
    {
      "agency": "SSM",
      "sub": null,
      "file_id": "1ZhYsKA3N5sT0hHOmfb29d92FWzAdeE-TXiGk2GmosIs",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1ZhYsKA3N5sT0hHOmfb29d92FWzAdeE-TXiGk2GmosIs/edit?usp=sharing"
    },
    {
      "agency": "MDLAND",
      "sub": null,
      "file_id": "1ssUVWOeDH-jrU5oWwX2O5YZzunB7ygNCxdNobLdotiA",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1ssUVWOeDH-jrU5oWwX2O5YZzunB7ygNCxdNobLdotiA/edit?gid=0"
    },
    {
      "agency": "QUEENLAND",
      "sub": null,
      "file_id": "1FYCyAnafUmspix1PbuumjPKpRlYJb8brqP1h9Rhy2yU",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1FYCyAnafUmspix1PbuumjPKpRlYJb8brqP1h9Rhy2yU/edit?usp=embed_facebook"
    }
  ],
  "TRÀNG CÁT": [
    {
      "agency": "MDL",
      "sub": null,
      "file_id": "1JgF_DrREt_-sFrGwaLNBAoUGyAiGLkGmfWy2JBSCbaY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1JgF_DrREt_-sFrGwaLNBAoUGyAiGLkGmfWy2JBSCbaY/edit?gid=0"
    },
    {
      "agency": "HDH",
      "sub": null,
      "file_id": "1JRoWgxg3qVkcSMqQyKoqtgFEVoiye-gCtTubhvWu_IU",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1JRoWgxg3qVkcSMqQyKoqtgFEVoiye-gCtTubhvWu_IU/edit?usp=sharing"
    },
    {
      "agency": "MICC",
      "sub": null,
      "file_id": "1SceupRAgl8ZUm3A06zFi56cW5nCd6LuJ",
      "gid": "456271118",
      "url": "https://docs.google.com/spreadsheets/d/1SceupRAgl8ZUm3A06zFi56cW5nCd6LuJ/edit?gid=456271118"
    },
    {
      "agency": "Đất Việt",
      "sub": null,
      "file_id": "1s4CmeXjbIsUmxN9h5bczvdACzQO4I8TLPB3bFti8MyY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1s4CmeXjbIsUmxN9h5bczvdACzQO4I8TLPB3bFti8MyY/edit?gid=0"
    },
    {
      "agency": "NSL",
      "sub": null,
      "file_id": "1Wki5tO_KzVeJ9KXizV_lglfHzf_StAS1GQC518U1INI",
      "gid": "922066635",
      "url": "https://docs.google.com/spreadsheets/d/1Wki5tO_KzVeJ9KXizV_lglfHzf_StAS1GQC518U1INI/edit?gid=922066635"
    },
    {
      "agency": "EC",
      "sub": null,
      "file_id": "1bmDORW7KOCEKHDgQsYQBsL4jTk28IIwaZlJdARswO94",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1bmDORW7KOCEKHDgQsYQBsL4jTk28IIwaZlJdARswO94/edit?usp=sharing"
    },
    {
      "agency": "Mai Việt",
      "sub": null,
      "file_id": "1F3ZZ3oEAesnxSG-humwGI3XxhhLNSIWDkpSUEtlTBKs",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1F3ZZ3oEAesnxSG-humwGI3XxhhLNSIWDkpSUEtlTBKs/edit?gid=0"
    },
    {
      "agency": "Five Star",
      "sub": null,
      "file_id": "1oZqiXuxHTzP8LSsREpHzJHM2cKJcgcXpql37dAxOJRo",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1oZqiXuxHTzP8LSsREpHzJHM2cKJcgcXpql37dAxOJRo/edit?gid=0"
    },
    {
      "agency": "Bighomes",
      "sub": null,
      "file_id": "1lwIwddoGrdUdYzLnpswZU-XvGzm4hx39",
      "gid": "1130250934",
      "url": "https://docs.google.com/spreadsheets/d/1lwIwddoGrdUdYzLnpswZU-XvGzm4hx39/edit?gid=1130250934"
    }
  ],
  "Cần giờ": [
    {
      "agency": "SSM",
      "sub": null,
      "file_id": "1-_kdVqk-A-Ru267KkzQJQdgLuHB_LzYomljMvR66D2w",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1-_kdVqk-A-Ru267KkzQJQdgLuHB_LzYomljMvR66D2w/edit?gid=0"
    },
    {
      "agency": "SVH",
      "sub": null,
      "file_id": "1wDN_gtwOrOdpRnLvRDrko3P91STVpOEb-axRRObDDe4",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1wDN_gtwOrOdpRnLvRDrko3P91STVpOEb-axRRObDDe4/edit?usp=sharing"
    },
    {
      "agency": "VHS",
      "sub": null,
      "file_id": "1vKopAAb2S_felAl4VGyk7aevmUrtZsh_H4FlwQJPkiM",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1vKopAAb2S_felAl4VGyk7aevmUrtZsh_H4FlwQJPkiM/edit?usp=embed_facebook"
    },
    {
      "agency": "QLG",
      "sub": null,
      "file_id": "1n0xa80QBIlBVdqWD2ibjJ9rhSDUPfMt_rarg7GMy_rA",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1n0xa80QBIlBVdqWD2ibjJ9rhSDUPfMt_rarg7GMy_rA/edit?gid=0"
    },
    {
      "agency": "LM BH - HG",
      "sub": null,
      "file_id": "1rvsswbWUfwxLvLhxntaN-BC25hMLxMKLvC4i7PEUHCw",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1rvsswbWUfwxLvLhxntaN-BC25hMLxMKLvC4i7PEUHCw/edit?gid=0"
    },
    {
      "agency": "Elite Capital",
      "sub": null,
      "file_id": "1xzhykxaCIrt3Q-XXl5ZeybyuepsA1kjdBBmz6n-EwF0",
      "gid": "744108558",
      "url": "https://docs.google.com/spreadsheets/d/1xzhykxaCIrt3Q-XXl5ZeybyuepsA1kjdBBmz6n-EwF0/edit?gid=744108558"
    },
    {
      "agency": "MDLand",
      "sub": null,
      "file_id": "19xhdVPkVTHuuilz8c8cgCUkJV5lpDovHdCjxOxjhozE",
      "gid": "1644799694",
      "url": "https://docs.google.com/spreadsheets/d/19xhdVPkVTHuuilz8c8cgCUkJV5lpDovHdCjxOxjhozE/edit?gid=1644799694"
    },
    {
      "agency": "NOVASKY",
      "sub": null,
      "file_id": "1s6zVuw2fT7-fZ92M6DhYs0CRnEi1C2dbDADGB11m4II",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1s6zVuw2fT7-fZ92M6DhYs0CRnEi1C2dbDADGB11m4II/edit?gid=0"
    },
    {
      "agency": "VSR",
      "sub": null,
      "file_id": "1ogucOY4Go0xy52Y_RBAcEvuEH2uOOWPOAdAzQCj6ZLg",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1ogucOY4Go0xy52Y_RBAcEvuEH2uOOWPOAdAzQCj6ZLg/edit?gid=0"
    },
    {
      "agency": "Minh Minh",
      "sub": null,
      "file_id": "10uKQL42gohOOBVA23EyU53BaJmJgBDwQjJWKscWEMJs",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/10uKQL42gohOOBVA23EyU53BaJmJgBDwQjJWKscWEMJs/edit?gid=0"
    },
    {
      "agency": "Micc Group.",
      "sub": null,
      "file_id": "1LRP6w6OnRN9gQWcgZDvChgm4gmFAjwm6MEL4mP5lLeI",
      "gid": "791758303",
      "url": "https://docs.google.com/spreadsheets/d/1LRP6w6OnRN9gQWcgZDvChgm4gmFAjwm6MEL4mP5lLeI/edit?gid=791758303"
    },
    {
      "agency": "Phúc Lộc",
      "sub": null,
      "file_id": "1oouCiVCSeNg9aGyq8RK_KVNO_SNSbvmY9P6QV__VZkQ",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1oouCiVCSeNg9aGyq8RK_KVNO_SNSbvmY9P6QV__VZkQ/edit?gid=0"
    },
    {
      "agency": "TTĐ.",
      "sub": null,
      "file_id": "1TU9lPTCc2AHi0bXqPOubBssaWJsanPbJPvMLjtTRNeM",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1TU9lPTCc2AHi0bXqPOubBssaWJsanPbJPvMLjtTRNeM/edit?gid=0"
    },
    {
      "agency": "Đất Việt.",
      "sub": null,
      "file_id": "1MVpJ6_dLa0gnPZflZDcAB4psgwgVfu4roghg6DKo8AI",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1MVpJ6_dLa0gnPZflZDcAB4psgwgVfu4roghg6DKo8AI/edit?gid=0"
    },
    {
      "agency": "QHOMES",
      "sub": null,
      "file_id": "1RnUln8hrV6QALvmcucGmHcLjD6Zl7BEIWzPjqB59XxE",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1RnUln8hrV6QALvmcucGmHcLjD6Zl7BEIWzPjqB59XxE/edit?gid=0"
    },
    {
      "agency": "AKA",
      "sub": null,
      "file_id": "1c3MK7DEWw8jqLDeXong2_x_IkDxH0nYfJPfFNlecg14",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1c3MK7DEWw8jqLDeXong2_x_IkDxH0nYfJPfFNlecg14/edit?gid=0"
    },
    {
      "agency": "QCBEST",
      "sub": null,
      "file_id": "1NdfgEzr8Y-vI2JnmCWFkcViWLm-bzL37nmubNi6XGco",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1NdfgEzr8Y-vI2JnmCWFkcViWLm-bzL37nmubNi6XGco/edit?usp=drivesdk"
    },
    {
      "agency": "FS",
      "sub": null,
      "file_id": "13_UghdWS7hl20PHiWCbK4jNfxQ6qehvh",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/13_UghdWS7hl20PHiWCbK4jNfxQ6qehvh/edit?usp=sharing&ouid=100181520087004912992&rtpof=true&sd=true"
    },
    {
      "agency": "CENHN",
      "sub": null,
      "file_id": "1HizrzPrAV0Ob39494xniXPz9FzAh7_4m_dRYEklg2yc",
      "gid": "173596454",
      "url": "https://docs.google.com/spreadsheets/d/1HizrzPrAV0Ob39494xniXPz9FzAh7_4m_dRYEklg2yc/edit?gid=173596454"
    },
    {
      "agency": "JOY HOMES",
      "sub": null,
      "file_id": "1LaPtq8BXQq8e67DLyIPwLMtd1Sg7rgVJ5k5fdXLZOYk",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1LaPtq8BXQq8e67DLyIPwLMtd1Sg7rgVJ5k5fdXLZOYk/edit?gid=0"
    },
    {
      "agency": "Thiên Phúc.",
      "sub": null,
      "file_id": "1ZzySG2cPtSBuDyIabDicXqdN-HI6kMqMRB39FlQhHro",
      "gid": "1041300003",
      "url": "https://docs.google.com/spreadsheets/d/1ZzySG2cPtSBuDyIabDicXqdN-HI6kMqMRB39FlQhHro/edit?gid=1041300003"
    },
    {
      "agency": "KINGLAND",
      "sub": null,
      "file_id": "1q5RX5CYGO6ND5uGyzLJTT5pB3T7wxBwYdYnPOAEmzvI",
      "gid": "1221329960",
      "url": "https://docs.google.com/spreadsheets/d/1q5RX5CYGO6ND5uGyzLJTT5pB3T7wxBwYdYnPOAEmzvI/edit?gid=1221329960"
    },
    {
      "agency": "MAYHOMES",
      "sub": null,
      "file_id": "1AuN7y8h2Ts4ipRmQKZ2cmsPnqrga_cOHbSTt7lJkQHc",
      "gid": "1743901026",
      "url": "https://docs.google.com/spreadsheets/d/1AuN7y8h2Ts4ipRmQKZ2cmsPnqrga_cOHbSTt7lJkQHc/edit?gid=1743901026"
    },
    {
      "agency": "CBest.",
      "sub": null,
      "file_id": "1zCyMFlEh5yba9U1bjLbyTXxBIa4ewRgV3HLEv5DRAoo",
      "gid": "2132757580",
      "url": "https://docs.google.com/spreadsheets/d/1zCyMFlEh5yba9U1bjLbyTXxBIa4ewRgV3HLEv5DRAoo/edit?gid=2132757580"
    },
    {
      "agency": "THP",
      "sub": null,
      "file_id": "1DjOymL95bAgZxaBmM339WRhV6bUpEETXeF4IvnoXUms",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1DjOymL95bAgZxaBmM339WRhV6bUpEETXeF4IvnoXUms/edit?gid=0"
    },
    {
      "agency": "VSL",
      "sub": null,
      "file_id": "1AmLA6V3GAeW9-TeJf3gkExaMQLvcG2O5Ri1ckPJMOK4",
      "gid": "1172840356",
      "url": "https://docs.google.com/spreadsheets/d/1AmLA6V3GAeW9-TeJf3gkExaMQLvcG2O5Ri1ckPJMOK4/edit?gid=1172840356"
    },
    {
      "agency": "Newgen.",
      "sub": null,
      "file_id": "1lBgtsbk0dGmNCbLlAg5KpkYSsiLynxOAidlKho9NslE",
      "gid": "1892030597",
      "url": "https://docs.google.com/spreadsheets/d/1lBgtsbk0dGmNCbLlAg5KpkYSsiLynxOAidlKho9NslE/edit?gid=1892030597"
    },
    {
      "agency": "HD Homes",
      "sub": null,
      "file_id": "1OLy1_fOYRc0KvQ5lXK3dGGEx8MtZAHhw",
      "gid": "290494863",
      "url": "https://docs.google.com/spreadsheets/d/1OLy1_fOYRc0KvQ5lXK3dGGEx8MtZAHhw/edit?gid=290494863"
    },
    {
      "agency": "NEWSTARLAND",
      "sub": null,
      "file_id": "1s3sw0GLewiACYtkhsiYMFsAPy_ln2YlRuCPvMGpyvCE",
      "gid": "2101526670",
      "url": "https://docs.google.com/spreadsheets/d/1s3sw0GLewiACYtkhsiYMFsAPy_ln2YlRuCPvMGpyvCE/edit?gid=2101526670"
    },
    {
      "agency": "BHS",
      "sub": null,
      "file_id": "1GIXAaBXypqTVmrjoNiBcvm_FjAJHc-dr",
      "gid": "1491214331",
      "url": "https://docs.google.com/spreadsheets/d/1GIXAaBXypqTVmrjoNiBcvm_FjAJHc-dr/edit?gid=1491214331"
    },
    {
      "agency": "vnx.",
      "sub": null,
      "file_id": "1cDiukYdJeOOVNbs53hl-P2r2Tn0cGLI-OnF-eR3ugrI",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1cDiukYdJeOOVNbs53hl-P2r2Tn0cGLI-OnF-eR3ugrI/edit?gid=0"
    },
    {
      "agency": "Cali Homes",
      "sub": null,
      "file_id": "164fBtXBGyLMIirNRNKu56iDTDgHxyQwL_4uKnQrCTyM",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/164fBtXBGyLMIirNRNKu56iDTDgHxyQwL_4uKnQrCTyM/edit?usp=drivesdk"
    },
    {
      "agency": "Homeplus",
      "sub": null,
      "file_id": "1mTxvsNNxFzGPl0vlIYYMtHGRDIXoXtluVIz81v-1VVM",
      "gid": "211589432",
      "url": "https://docs.google.com/spreadsheets/d/1mTxvsNNxFzGPl0vlIYYMtHGRDIXoXtluVIz81v-1VVM/edit?gid=211589432"
    },
    {
      "agency": "Alpha",
      "sub": null,
      "file_id": "1sac91VKGEoLYUQ9Kvo2WUwezIwA3PQ7cUiCmqqld4e0",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1sac91VKGEoLYUQ9Kvo2WUwezIwA3PQ7cUiCmqqld4e0/edit?usp=drivesdk"
    },
    {
      "agency": "ADL",
      "sub": null,
      "file_id": "1F7AQQ9vbz4oPSUIVA2UQIQMUyFZxjOMbZS9HokU1eRM",
      "gid": "910381764",
      "url": "https://docs.google.com/spreadsheets/d/1F7AQQ9vbz4oPSUIVA2UQIQMUyFZxjOMbZS9HokU1eRM/edit?gid=910381764"
    }
  ],
  "Hóc Môn": [
    {
      "agency": "VHS GROUP",
      "sub": null,
      "file_id": "1CVP7KorjsxgaU3dRdVe0ke-ju5MPOcXtUyt7K5xWZzg",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1CVP7KorjsxgaU3dRdVe0ke-ju5MPOcXtUyt7K5xWZzg/edit"
    },
    {
      "agency": "REVER",
      "sub": null,
      "file_id": "1qFN-_7peNkxF5PSYPtPV12p7pivjGu8ovU3cvLGXvdI",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1qFN-_7peNkxF5PSYPtPV12p7pivjGu8ovU3cvLGXvdI/edit?gid=0"
    },
    {
      "agency": "NEWSTARLAND",
      "sub": null,
      "file_id": "1TEd-2RQE-rrTuEpSvq_foiC4W1Xo0NUdfqnfdZ4669Y",
      "gid": "562140111",
      "url": "https://docs.google.com/spreadsheets/d/1TEd-2RQE-rrTuEpSvq_foiC4W1Xo0NUdfqnfdZ4669Y/edit?gid=562140111"
    },
    {
      "agency": "SOUTHERNHOMES",
      "sub": null,
      "file_id": "151pxMRBIdtDYWrrusU-GIIAh1eGzn-7HUjCm-SdeK-M",
      "gid": "1549485584",
      "url": "https://docs.google.com/spreadsheets/d/151pxMRBIdtDYWrrusU-GIIAh1eGzn-7HUjCm-SdeK-M/edit?gid=1549485584"
    },
    {
      "agency": "QUEENLAND",
      "sub": null,
      "file_id": "1GFWNU1WWKVOAMUxgz_D3hXW0-M_m9YHPPzjoTtT2El0",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1GFWNU1WWKVOAMUxgz_D3hXW0-M_m9YHPPzjoTtT2El0/edit?gid=0"
    },
    {
      "agency": "TÂN THỜI ĐẠI",
      "sub": null,
      "file_id": "1nAUYOfs0sJ7JJ14ovE5dfFlbyO7U_DZz",
      "gid": "708701789",
      "url": "https://docs.google.com/spreadsheets/d/1nAUYOfs0sJ7JJ14ovE5dfFlbyO7U_DZz/edit?gid=708701789"
    },
    {
      "agency": "FIVE STAR",
      "sub": null,
      "file_id": "1iZgHPcBtbl0PhLjmSy7Up0tAf9lvMgz5",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1iZgHPcBtbl0PhLjmSy7Up0tAf9lvMgz5/edit?usp=sharing&ouid=101575300421862670547&rtpof=true&sd=true"
    },
    {
      "agency": "VISION REALTY",
      "sub": null,
      "file_id": "1G5zKp8gsCxRedLFKMELaS4DSyi4HD-62E1FDFK-R4II",
      "gid": "1694985051",
      "url": "https://docs.google.com/spreadsheets/d/1G5zKp8gsCxRedLFKMELaS4DSyi4HD-62E1FDFK-R4II/edit?gid=1694985051"
    },
    {
      "agency": "VNX",
      "sub": null,
      "file_id": "1wI-M4NzTkVuv8EScD7x4Cd7Vcz6Hbo4k",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1wI-M4NzTkVuv8EScD7x4Cd7Vcz6Hbo4k/edit?usp=drive_link&ouid=111461024308443223992&rtpof=true&sd=true"
    },
    {
      "agency": "HỢP LONG",
      "sub": null,
      "file_id": "1f6jPfJB1zeTVquS_Scfaky6RcCawKkBJ",
      "gid": "219322745",
      "url": "https://docs.google.com/spreadsheets/d/1f6jPfJB1zeTVquS_Scfaky6RcCawKkBJ/edit?gid=219322745"
    },
    {
      "agency": "SSM",
      "sub": null,
      "file_id": "1Lns9m3JEDHHnQOBTCpYENkHxOmVkseJ-hzUiScCQZUk",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1Lns9m3JEDHHnQOBTCpYENkHxOmVkseJ-hzUiScCQZUk/edit?gid=0"
    },
    {
      "agency": "VIETSTARLAND",
      "sub": null,
      "file_id": "1jBDAYvi715xMYU7LxPCoWFhSb1cj7x3UKGOHzT9uSuw",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1jBDAYvi715xMYU7LxPCoWFhSb1cj7x3UKGOHzT9uSuw/edit?gid=0"
    },
    {
      "agency": "MDLAND",
      "sub": null,
      "file_id": "1kfudje41IO8_yRcbiqszPjStd6ts5ewAAgJtmLXTEMU",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1kfudje41IO8_yRcbiqszPjStd6ts5ewAAgJtmLXTEMU/edit?usp=sharing"
    },
    {
      "agency": "TÂN HƯƠNG PHÁT",
      "sub": null,
      "file_id": "1jNreMHusEWyFcmHtu2ChtP2WViElSKGm",
      "gid": "1943396847",
      "url": "https://docs.google.com/spreadsheets/d/1jNreMHusEWyFcmHtu2ChtP2WViElSKGm/edit?gid=1943396847"
    },
    {
      "agency": "SAO VÀNG HOLDINGS",
      "sub": null,
      "file_id": "1fb5SM-Cp-7MUGyHhQEl82gcGJf2T_Q5RCj-hxFI1-vg",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1fb5SM-Cp-7MUGyHhQEl82gcGJf2T_Q5RCj-hxFI1-vg/edit?gid=0"
    },
    {
      "agency": "QCBEST",
      "sub": null,
      "file_id": "1OYNVWQ0ve_xGmSCmSq5YacUO-CaNf6Xt",
      "gid": "645850692",
      "url": "https://docs.google.com/spreadsheets/d/1OYNVWQ0ve_xGmSCmSq5YacUO-CaNf6Xt/edit?gid=645850692"
    },
    {
      "agency": "Á ĐÔNG LAND",
      "sub": null,
      "file_id": "1xUA-B3RgED5RuSDrDgSB4JDYuhHfNhks--Ga8ZdswVc",
      "gid": "825439978",
      "url": "https://docs.google.com/spreadsheets/d/1xUA-B3RgED5RuSDrDgSB4JDYuhHfNhks--Ga8ZdswVc/edit?gid=825439978"
    },
    {
      "agency": "SÀI GÒN GROUP",
      "sub": null,
      "file_id": "1nhkhMb8pXLfZ1Y6K16JZ1W77ndMBOIER",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1nhkhMb8pXLfZ1Y6K16JZ1W77ndMBOIER/edit?usp=sharing&ouid=104602936046424626787&rtpof=true&sd=true"
    },
    {
      "agency": "REDLAND",
      "sub": null,
      "file_id": "1ptWlsWjYP0HQaFDFGlIvFyMDyc1gVTlh",
      "gid": "1446348589",
      "url": "https://docs.google.com/spreadsheets/d/1ptWlsWjYP0HQaFDFGlIvFyMDyc1gVTlh/edit?gid=1446348589"
    },
    {
      "agency": "ĐÔNG TAY LAND",
      "sub": null,
      "file_id": "1ZxtrrKspd2b9-7EwpH3DnYuw5mIHVePq",
      "gid": "1020645914",
      "url": "https://docs.google.com/spreadsheets/d/1ZxtrrKspd2b9-7EwpH3DnYuw5mIHVePq/edit?gid=1020645914"
    },
    {
      "agency": "ALPHA",
      "sub": null,
      "file_id": "1etFv64ZE5Ss666G2Y0Zwqf52tEmdNoTRbDMP113ZauE",
      "gid": "1945361180",
      "url": "https://docs.google.com/spreadsheets/d/1etFv64ZE5Ss666G2Y0Zwqf52tEmdNoTRbDMP113ZauE/edit?gid=1945361180"
    },
    {
      "agency": "QTC",
      "sub": null,
      "file_id": "1OSM9MQdbOEd2kgqIQWalOLuO2U4U75nJKGbaOMtgc5Q",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1OSM9MQdbOEd2kgqIQWalOLuO2U4U75nJKGbaOMtgc5Q/edit?gid=0"
    },
    {
      "agency": "TICALAND",
      "sub": null,
      "file_id": "1nrcjYoYj7or5U3yCxhbk8rgWSnmm8f6QzGA4sygcFxI",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1nrcjYoYj7or5U3yCxhbk8rgWSnmm8f6QzGA4sygcFxI/edit?usp=sharing"
    },
    {
      "agency": "LM MK LAND - LEGACY HOLDING -  LUXURY LAND",
      "sub": null,
      "file_id": "1UdeyInI6GBrDXEy-YtF1M6o0voXXNCxoXFSfBBkrAyc",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1UdeyInI6GBrDXEy-YtF1M6o0voXXNCxoXFSfBBkrAyc/edit?gid=0"
    },
    {
      "agency": "CT HOLDING",
      "sub": null,
      "file_id": "1r-douHpL7NgsUevS7mx68gTy4Ujq-az7",
      "gid": "1137265853",
      "url": "https://docs.google.com/spreadsheets/d/1r-douHpL7NgsUevS7mx68gTy4Ujq-az7/edit?gid=1137265853"
    },
    {
      "agency": "MEGA REALTHY",
      "sub": null,
      "file_id": "12ClJSgx7sC_o9mirLGMRjtKVsmtDpDUB",
      "gid": "74406936",
      "url": "https://docs.google.com/spreadsheets/d/12ClJSgx7sC_o9mirLGMRjtKVsmtDpDUB/edit?gid=74406936"
    },
    {
      "agency": "MINH TÂM LAND",
      "sub": null,
      "file_id": "1-avXJ4rHV_KunN1GLn4N-HxfYn5rmVoV6nExFfePBG8",
      "gid": "37752694",
      "url": "https://docs.google.com/spreadsheets/d/1-avXJ4rHV_KunN1GLn4N-HxfYn5rmVoV6nExFfePBG8/edit?gid=37752694"
    },
    {
      "agency": "CBEST",
      "sub": null,
      "file_id": "1yDp-449MHVDyF-m1U_rv_vJj7xOCaZ96bWQeJ6HbM_I",
      "gid": "669398118",
      "url": "https://docs.google.com/spreadsheets/d/1yDp-449MHVDyF-m1U_rv_vJj7xOCaZ96bWQeJ6HbM_I/edit?gid=669398118"
    },
    {
      "agency": "GOLDEN LAND",
      "sub": null,
      "file_id": "1RkvnJOxtPwVcf2RYXYmUkjY0dudQH9_J",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1RkvnJOxtPwVcf2RYXYmUkjY0dudQH9_J/edit?usp=sharing&ouid=111699325359642440298&rtpof=true&sd=true"
    },
    {
      "agency": "GIR",
      "sub": null,
      "file_id": "12d46VLMoL7m-0iZ2p0JlM0n6L7UdSySo",
      "gid": "354960191",
      "url": "https://docs.google.com/spreadsheets/d/12d46VLMoL7m-0iZ2p0JlM0n6L7UdSySo/edit?gid=354960191"
    },
    {
      "agency": "MAINLAND",
      "sub": null,
      "file_id": "1_4gar27dc0WU0m14bW5AvQ4Txkh-kHxZ",
      "gid": "1913824391",
      "url": "https://docs.google.com/spreadsheets/d/1_4gar27dc0WU0m14bW5AvQ4Txkh-kHxZ/edit?gid=1913824391"
    },
    {
      "agency": "NHÀ LIÊN MINH",
      "sub": null,
      "file_id": "1g_C3hqwJ2t7wTdrqFVUvcvXPkVZQ3TYN6CgPsU8q6w8",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1g_C3hqwJ2t7wTdrqFVUvcvXPkVZQ3TYN6CgPsU8q6w8/edit?gid=0"
    },
    {
      "agency": "LUX HOLDINGS",
      "sub": null,
      "file_id": "1uT49fklM0378dCDLlVxXKnHNEnh8QI-djOfc-gwrMdI",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1uT49fklM0378dCDLlVxXKnHNEnh8QI-djOfc-gwrMdI/edit?gid=0"
    },
    {
      "agency": "MAYHOMES",
      "sub": null,
      "file_id": "1BqmGoff9zIJYxsbBYWnepysPVrWMr71sXyCdFSFLvIc",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1BqmGoff9zIJYxsbBYWnepysPVrWMr71sXyCdFSFLvIc/edit?usp=drivesdk"
    },
    {
      "agency": "NOVASKY",
      "sub": null,
      "file_id": "1IbBt2OHd1tAqyR5lR4tqNvtOlXTwQuR40aKE_ulmE9U",
      "gid": "1981687210",
      "url": "https://docs.google.com/spreadsheets/d/1IbBt2OHd1tAqyR5lR4tqNvtOlXTwQuR40aKE_ulmE9U/edit?gid=1981687210"
    },
    {
      "agency": "MINH MINH GROUP",
      "sub": null,
      "file_id": "1m1gRczHTmlP7Ul5LzkA63YR1S8ZhpYO2FN-CrXGFz10",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1m1gRczHTmlP7Ul5LzkA63YR1S8ZhpYO2FN-CrXGFz10/edit?gid=0"
    },
    {
      "agency": "GROLY LAND - SAIGON STAR",
      "sub": null,
      "file_id": "1InCWsX81wWXR00Z3qhQWFb2aUf-paE7TaGSpjvWM83A",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1InCWsX81wWXR00Z3qhQWFb2aUf-paE7TaGSpjvWM83A/edit?usp=drivesdk"
    },
    {
      "agency": "Liên minh: S9LAND, SG STAR LAND",
      "sub": null,
      "file_id": "1InCWsX81wWXR00Z3qhQWFb2aUf-paE7TaGSpjvWM83A",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1InCWsX81wWXR00Z3qhQWFb2aUf-paE7TaGSpjvWM83A/edit?gid=0"
    },
    {
      "agency": "SALEREAL",
      "sub": null,
      "file_id": "1OcQQeQ8n_C3rmzB3Hl_hwPHbvHojTui1zwkrXUEiVkU",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1OcQQeQ8n_C3rmzB3Hl_hwPHbvHojTui1zwkrXUEiVkU/edit?gid=0"
    },
    {
      "agency": "HOMEPLUS",
      "sub": null,
      "file_id": "1p5x0WkynjGFLYMX7kf2wYPDaGMmsDUV82jrGD8yKRpY",
      "gid": "1438419760",
      "url": "https://docs.google.com/spreadsheets/d/1p5x0WkynjGFLYMX7kf2wYPDaGMmsDUV82jrGD8yKRpY/edit?gid=1438419760"
    },
    {
      "agency": "PRIME",
      "sub": null,
      "file_id": "19Ts-XYk7sjw0DQrgWuAzmyk905NWNL2z",
      "gid": "1259851980",
      "url": "https://docs.google.com/spreadsheets/d/19Ts-XYk7sjw0DQrgWuAzmyk905NWNL2z/edit?gid=1259851980"
    },
    {
      "agency": "MINH AN HOMES",
      "sub": null,
      "file_id": "13AYeoUiqQT1yv7JX1DmnWvH4SAOsFKqpLyV-gx5COn4",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/13AYeoUiqQT1yv7JX1DmnWvH4SAOsFKqpLyV-gx5COn4/edit?usp=drivesdk"
    },
    {
      "agency": "ĐÔNG DƯƠNG REALTY",
      "sub": null,
      "file_id": "1pPtI3eIcG2SSOTl9xdnxfNLarKr2sAF9PuY67hyUuDc",
      "gid": "322956393",
      "url": "https://docs.google.com/spreadsheets/d/1pPtI3eIcG2SSOTl9xdnxfNLarKr2sAF9PuY67hyUuDc/edit?gid=322956393"
    },
    {
      "agency": "BAM GROUP",
      "sub": null,
      "file_id": "1-EhzLibbgY4O-D-ZIEGh8886pHmfS590",
      "gid": "1807940533",
      "url": "https://docs.google.com/spreadsheets/d/1-EhzLibbgY4O-D-ZIEGh8886pHmfS590/edit?gid=1807940533"
    },
    {
      "agency": "ACB HOMES",
      "sub": null,
      "file_id": "1-CI4-oqZBJL84cQgosoU3_3k1sDXWYnQmBbt7nhWct4",
      "gid": "1161341563",
      "url": "https://docs.google.com/spreadsheets/d/1-CI4-oqZBJL84cQgosoU3_3k1sDXWYnQmBbt7nhWct4/edit?gid=1161341563"
    },
    {
      "agency": "VIETNAM GROOVE",
      "sub": null,
      "file_id": "140FhM46YV8DvYH62yLM8og1mvMpuZm4n",
      "gid": "227469381",
      "url": "https://docs.google.com/spreadsheets/d/140FhM46YV8DvYH62yLM8og1mvMpuZm4n/edit?gid=227469381"
    },
    {
      "agency": "AKA HOMES",
      "sub": null,
      "file_id": "1N9mn_vxUfrwGz9DWtsStqdn4aTSo5DKxiTHjjTQVHLs",
      "gid": "195499164",
      "url": "https://docs.google.com/spreadsheets/d/1N9mn_vxUfrwGz9DWtsStqdn4aTSo5DKxiTHjjTQVHLs/edit?gid=195499164"
    },
    {
      "agency": "VIỆT Á",
      "sub": null,
      "file_id": "1F8Hhfvo27i5ohOSvPPZf9al7i5KgfmaPRxwgtpxO1Dc",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1F8Hhfvo27i5ohOSvPPZf9al7i5KgfmaPRxwgtpxO1Dc/edit?gid=0"
    },
    {
      "agency": "THẾ GIỚI BĐS",
      "sub": null,
      "file_id": "1KImC6OZvw36OMEYrVRpUDpI_CCbXnTJ5",
      "gid": "942734233",
      "url": "https://docs.google.com/spreadsheets/d/1KImC6OZvw36OMEYrVRpUDpI_CCbXnTJ5/edit?gid=942734233"
    },
    {
      "agency": "VICTORY HOLDINGS",
      "sub": null,
      "file_id": "1sNOanty5ywXlq2WDTfTE435jEFpl75c9LHdnk-CWmGE",
      "gid": "1093464785",
      "url": "https://docs.google.com/spreadsheets/d/1sNOanty5ywXlq2WDTfTE435jEFpl75c9LHdnk-CWmGE/edit?gid=1093464785"
    },
    {
      "agency": "MICC",
      "sub": null,
      "file_id": "1PPAPR65BblhwEojLLBJcTYuyftdCKcG6S0htFEZ4x2I",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1PPAPR65BblhwEojLLBJcTYuyftdCKcG6S0htFEZ4x2I/edit?gid=0"
    },
    {
      "agency": "PTI HOME",
      "sub": null,
      "file_id": "1rThWamFZO8spFx632fpzZ3nLkBAEqV2ExD1xyWG4I7c",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1rThWamFZO8spFx632fpzZ3nLkBAEqV2ExD1xyWG4I7c/edit?gid=0"
    },
    {
      "agency": "NEWGEN INVEST",
      "sub": null,
      "file_id": "1dKEi_VL33Z83yawA_iSDJlkIkN4Uj3CQVP35YtRa0MA",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1dKEi_VL33Z83yawA_iSDJlkIkN4Uj3CQVP35YtRa0MA/edit?gid=0"
    },
    {
      "agency": "NHÀ KIM CƯƠNG",
      "sub": null,
      "file_id": "1cl7fEhiL8edzoK8ok3lXxZ8kWBbf7lip",
      "gid": "717544480",
      "url": "https://docs.google.com/spreadsheets/d/1cl7fEhiL8edzoK8ok3lXxZ8kWBbf7lip/edit?gid=717544480"
    },
    {
      "agency": "NGỌC PHƯƠNG ĐÔNG",
      "sub": null,
      "file_id": "1ETX0nxA8uNKhFYdqqUiSp6q3Cno5doOZ9-hB8IBGl3g",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1ETX0nxA8uNKhFYdqqUiSp6q3Cno5doOZ9-hB8IBGl3g/edit?usp=sharing"
    },
    {
      "agency": "CALI HOMES",
      "sub": null,
      "file_id": "1B65n5gJI-fQJAqXmA1_URuoTWyAOco2gt-v_HXLuRKg",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1B65n5gJI-fQJAqXmA1_URuoTWyAOco2gt-v_HXLuRKg/edit?usp=drivesdk"
    },
    {
      "agency": "HDHOMES",
      "sub": null,
      "file_id": "1I6XLHfeQPSzhwRd6c4dRf_wWHx9k98kS",
      "gid": "2063234797",
      "url": "https://docs.google.com/spreadsheets/d/1I6XLHfeQPSzhwRd6c4dRf_wWHx9k98kS/edit?gid=2063234797"
    },
    {
      "agency": "SUNNY LAND",
      "sub": null,
      "file_id": "1d66mEIFu7cZ8UsAkJ4mXel9LWwjbZrdhvzt4mJ-vXTs",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1d66mEIFu7cZ8UsAkJ4mXel9LWwjbZrdhvzt4mJ-vXTs/edit?gid=0"
    },
    {
      "agency": "KHẢI MINH LAND",
      "sub": null,
      "file_id": "151pxMRBIdtDYWrrusU-GIIAh1eGzn-7HUjCm-SdeK-M",
      "gid": "1549485584",
      "url": "https://docs.google.com/spreadsheets/d/151pxMRBIdtDYWrrusU-GIIAh1eGzn-7HUjCm-SdeK-M/edit?gid=1549485584"
    },
    {
      "agency": "ĐẤT VIỆT GROUP",
      "sub": null,
      "file_id": "1B2HZ6PmYp9uluzL01h8DvADPVcUBG6aXdZsYVNkYMcw",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1B2HZ6PmYp9uluzL01h8DvADPVcUBG6aXdZsYVNkYMcw/edit?gid=0"
    },
    {
      "agency": "ROMAN PROPERTY",
      "sub": null,
      "file_id": "1BdhZ4PLExD8OkTS0wt5QXkkCXGq8GKSw",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1BdhZ4PLExD8OkTS0wt5QXkkCXGq8GKSw/edit?utm_source=chatgpt.com"
    },
    {
      "agency": "NGỌC PHƯƠNG ĐÔNG",
      "sub": null,
      "file_id": "1ETX0nxA8uNKhFYdqqUiSp6q3Cno5doOZ9-hB8IBGl3g",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1ETX0nxA8uNKhFYdqqUiSp6q3Cno5doOZ9-hB8IBGl3g/edit?usp=drive_link"
    }
  ],
  "Q9": [
    {
      "agency": "MAY",
      "sub": null,
      "file_id": "1rIzoKoN_ip5THsAsjpqoXJyv3IeGZ-LYYAZGNqzglJc",
      "gid": "829003858",
      "url": "https://docs.google.com/spreadsheets/d/1rIzoKoN_ip5THsAsjpqoXJyv3IeGZ-LYYAZGNqzglJc/edit?gid=829003858"
    },
    {
      "agency": "SSM",
      "sub": null,
      "file_id": "190iiNXpZz4UpUcEweMW-V3UEWyHBxbGu",
      "gid": "315056831",
      "url": "https://docs.google.com/spreadsheets/d/190iiNXpZz4UpUcEweMW-V3UEWyHBxbGu/edit?gid=315056831"
    },
    {
      "agency": "NSL",
      "sub": null,
      "file_id": "1iF_daPRf2AHIwlQte2l5TLRWBCZb57Vm",
      "gid": "658169596",
      "url": "https://docs.google.com/spreadsheets/d/1iF_daPRf2AHIwlQte2l5TLRWBCZb57Vm/edit?gid=658169596"
    },
    {
      "agency": "HP",
      "sub": null,
      "file_id": "1DsWFIBRVCq5D6UqoMdoIDehUA6SOhqJcT3WDYGfDq-o",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1DsWFIBRVCq5D6UqoMdoIDehUA6SOhqJcT3WDYGfDq-o/edit?usp=sharing"
    },
    {
      "agency": "VNG",
      "sub": null,
      "file_id": "19Wcy_dr926z09CQmKTO3cIE7hg0RItK-NK2-YYVHOAQ",
      "gid": "1811378476",
      "url": "https://docs.google.com/spreadsheets/d/19Wcy_dr926z09CQmKTO3cIE7hg0RItK-NK2-YYVHOAQ/edit?gid=1811378476"
    },
    {
      "agency": "STH",
      "sub": null,
      "file_id": "1OXtK80xXXkxNVzbtmgFM4TSYNfSg4Qde",
      "gid": "1339322068",
      "url": "https://docs.google.com/spreadsheets/d/1OXtK80xXXkxNVzbtmgFM4TSYNfSg4Qde/edit?gid=1339322068"
    },
    {
      "agency": "Mega",
      "sub": null,
      "file_id": "1Bbjid3EPkXcszt-y86dIyc_lqP40eRf8retrQQiW_SI",
      "gid": "914278040",
      "url": "https://docs.google.com/spreadsheets/d/1Bbjid3EPkXcszt-y86dIyc_lqP40eRf8retrQQiW_SI/edit?gid=914278040"
    },
    {
      "agency": "Sunny",
      "sub": null,
      "file_id": "1iipqP82rHeEfw1dmFPltXVsY9NJAZUyZ5K4awb1Yqb4",
      "gid": "610788937",
      "url": "https://docs.google.com/spreadsheets/d/1iipqP82rHeEfw1dmFPltXVsY9NJAZUyZ5K4awb1Yqb4/edit?gid=610788937"
    },
    {
      "agency": "MAH",
      "sub": null,
      "file_id": "13AYeoUiqQT1yv7JX1DmnWvH4SAOsFKqpLyV-gx5COn4",
      "gid": "2000635791",
      "url": "https://docs.google.com/spreadsheets/d/13AYeoUiqQT1yv7JX1DmnWvH4SAOsFKqpLyV-gx5COn4/edit?gid=2000635791"
    },
    {
      "agency": "SGG",
      "sub": null,
      "file_id": "1opZTy7fmlSBmAOdhcl-1HVV-SolNMRMd",
      "gid": "959968839",
      "url": "https://docs.google.com/spreadsheets/d/1opZTy7fmlSBmAOdhcl-1HVV-SolNMRMd/edit?gid=959968839"
    },
    {
      "agency": "Newgen",
      "sub": null,
      "file_id": "1ZUV9BlTQC4w7n5zMaaJrq9lf0wevEU3emDHikbqlDj8",
      "gid": "297258585",
      "url": "https://docs.google.com/spreadsheets/d/1ZUV9BlTQC4w7n5zMaaJrq9lf0wevEU3emDHikbqlDj8/edit?gid=297258585"
    },
    {
      "agency": "THP",
      "sub": null,
      "file_id": "1RAx55NoLIL7NB4cKQL_c3l_AED1-AjvUxfUp-83NpTE",
      "gid": "1336361437",
      "url": "https://docs.google.com/spreadsheets/d/1RAx55NoLIL7NB4cKQL_c3l_AED1-AjvUxfUp-83NpTE/edit?gid=1336361437"
    },
    {
      "agency": "VSR",
      "sub": null,
      "file_id": "1FgD8eEFISsKa1X-R22akJjMZKVSFMFI7gfnSayQIudQ",
      "gid": "43775456",
      "url": "https://docs.google.com/spreadsheets/d/1FgD8eEFISsKa1X-R22akJjMZKVSFMFI7gfnSayQIudQ/edit?gid=43775456"
    }
  ],
  "MAS CAO TẦNG": [
    {
      "agency": "ATD",
      "sub": "MGC",
      "file_id": "15WpuPJeolLrLEokEelQcPgqy7aORuVV-SpAXb9L2Pgg",
      "gid": "1831326906",
      "url": "https://docs.google.com/spreadsheets/d/15WpuPJeolLrLEokEelQcPgqy7aORuVV-SpAXb9L2Pgg/edit?gid=1831326906"
    },
    {
      "agency": "ATD",
      "sub": "MEL",
      "file_id": "1zVxwzcSi3xzybh0PLLgFb35vrnRzPOl8cPAy0ANaqvs",
      "gid": "1831326906",
      "url": "https://docs.google.com/spreadsheets/d/1zVxwzcSi3xzybh0PLLgFb35vrnRzPOl8cPAy0ANaqvs/edit?gid=1831326906"
    },
    {
      "agency": "ATD",
      "sub": "HSG",
      "file_id": "1laixztepdl8RTlAgiLAxyKiLcXS8TJfcVS8toPwtD5M",
      "gid": "626204350",
      "url": "https://docs.google.com/spreadsheets/d/1laixztepdl8RTlAgiLAxyKiLcXS8TJfcVS8toPwtD5M/edit?gid=626204350"
    },
    {
      "agency": "ATD",
      "sub": "LEP",
      "file_id": "1UJM7hfboFTZ7_gvTtsoWzRO4UCxcYUZhJNKS5paoqcM",
      "gid": "996950621",
      "url": "https://docs.google.com/spreadsheets/d/1UJM7hfboFTZ7_gvTtsoWzRO4UCxcYUZhJNKS5paoqcM/edit?gid=996950621"
    },
    {
      "agency": "DDL",
      "sub": "MGC",
      "file_id": "1twefTWN7o9qILJkG5PsqJXQ9XccKR9IC",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1twefTWN7o9qILJkG5PsqJXQ9XccKR9IC/edit?usp=sharing&ouid=106158638514325987385&rtpof=true&sd=true"
    },
    {
      "agency": "DDL",
      "sub": "MEL",
      "file_id": "1twefTWN7o9qILJkG5PsqJXQ9XccKR9IC",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1twefTWN7o9qILJkG5PsqJXQ9XccKR9IC/edit?usp=sharing&ouid=106158638514325987385&rtpof=true&sd=true"
    },
    {
      "agency": "ĐV",
      "sub": "MGC",
      "file_id": "1BOMAasR8V-NkxPOk0KzGTNzouH50xOCzBUY28phz-1o",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1BOMAasR8V-NkxPOk0KzGTNzouH50xOCzBUY28phz-1o/edit?usp=sharing"
    },
    {
      "agency": "ĐV",
      "sub": "MEL",
      "file_id": "1BOMAasR8V-NkxPOk0KzGTNzouH50xOCzBUY28phz-1o",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1BOMAasR8V-NkxPOk0KzGTNzouH50xOCzBUY28phz-1o/edit?usp=sharing"
    },
    {
      "agency": "ĐV",
      "sub": "HSG",
      "file_id": "1kov34NCmSSnNOauDMaf-lT-D-AauLoLDezX4ayoYyOk",
      "gid": "49858544",
      "url": "https://docs.google.com/spreadsheets/d/1kov34NCmSSnNOauDMaf-lT-D-AauLoLDezX4ayoYyOk/edit?gid=49858544"
    },
    {
      "agency": "ĐV",
      "sub": "LEP",
      "file_id": "1ufc-I-cTJ5DiOAPMA7U5PwUQm46s7fKArR8pIqn6BBY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1ufc-I-cTJ5DiOAPMA7U5PwUQm46s7fKArR8pIqn6BBY/edit?sharingaction=ownershiptransfer&gid=0"
    },
    {
      "agency": "Elite Capital",
      "sub": "MGC",
      "file_id": "1OSgmuneY--MvAT2hKvtXYeN0MFY0cYxlGnlN0AWS624",
      "gid": "908288444",
      "url": "https://docs.google.com/spreadsheets/d/1OSgmuneY--MvAT2hKvtXYeN0MFY0cYxlGnlN0AWS624/edit?gid=908288444"
    },
    {
      "agency": "Elite Capital",
      "sub": "MEL",
      "file_id": "1OSgmuneY--MvAT2hKvtXYeN0MFY0cYxlGnlN0AWS624",
      "gid": "908288444",
      "url": "https://docs.google.com/spreadsheets/d/1OSgmuneY--MvAT2hKvtXYeN0MFY0cYxlGnlN0AWS624/edit?gid=908288444"
    },
    {
      "agency": "Elite Capital",
      "sub": "HSG",
      "file_id": "1OSgmuneY--MvAT2hKvtXYeN0MFY0cYxlGnlN0AWS624",
      "gid": "2096087663",
      "url": "https://docs.google.com/spreadsheets/d/1OSgmuneY--MvAT2hKvtXYeN0MFY0cYxlGnlN0AWS624/edit?gid=2096087663"
    },
    {
      "agency": "Elite Capital",
      "sub": "LEP",
      "file_id": "1OSgmuneY--MvAT2hKvtXYeN0MFY0cYxlGnlN0AWS624",
      "gid": "2096087663",
      "url": "https://docs.google.com/spreadsheets/d/1OSgmuneY--MvAT2hKvtXYeN0MFY0cYxlGnlN0AWS624/edit?gid=2096087663"
    },
    {
      "agency": "Enternity Group",
      "sub": "MGC",
      "file_id": "1RrJ-ptyhOkTKRqYOlcqf8AE7jCkypzQ4QMm-GR4V7gY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1RrJ-ptyhOkTKRqYOlcqf8AE7jCkypzQ4QMm-GR4V7gY/edit?gid=0"
    },
    {
      "agency": "Enternity Group",
      "sub": "MEL",
      "file_id": "1RrJ-ptyhOkTKRqYOlcqf8AE7jCkypzQ4QMm-GR4V7gY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1RrJ-ptyhOkTKRqYOlcqf8AE7jCkypzQ4QMm-GR4V7gY/edit?gid=0"
    },
    {
      "agency": "Enternity Group",
      "sub": "HSG",
      "file_id": "1GOslNCzOJlivbOoRyvgn50A6l8KmGm1M",
      "gid": "1656529496",
      "url": "https://docs.google.com/spreadsheets/d/1GOslNCzOJlivbOoRyvgn50A6l8KmGm1M/edit?gid=1656529496"
    },
    {
      "agency": "Enternity Group",
      "sub": "LEP",
      "file_id": "1RrJ-ptyhOkTKRqYOlcqf8AE7jCkypzQ4QMm-GR4V7gY",
      "gid": "575083780",
      "url": "https://docs.google.com/spreadsheets/d/1RrJ-ptyhOkTKRqYOlcqf8AE7jCkypzQ4QMm-GR4V7gY/edit?gid=575083780"
    },
    {
      "agency": "Ellie Homes",
      "sub": "MGC",
      "file_id": "1nzq8vxtaOWur8qT1aYbq8xMICgT5CYRc",
      "gid": "1803860808",
      "url": "https://docs.google.com/spreadsheets/d/1nzq8vxtaOWur8qT1aYbq8xMICgT5CYRc/edit?gid=1803860808"
    },
    {
      "agency": "Ellie Homes",
      "sub": "MEL",
      "file_id": "11-iulvFSNlJoszww5qe4vflfE77IrPkRWWbyyPhoSdQ",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/11-iulvFSNlJoszww5qe4vflfE77IrPkRWWbyyPhoSdQ/edit?gid=0"
    },
    {
      "agency": "Ellie Homes",
      "sub": "HSG",
      "file_id": "1WPqykEU0UoLpD8bCnGeFEPqxD8Q5ExgGjevL03TaL-Y",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1WPqykEU0UoLpD8bCnGeFEPqxD8Q5ExgGjevL03TaL-Y/edit?gid=0"
    },
    {
      "agency": "Ellie Homes",
      "sub": "LEP",
      "file_id": "1LL5exiR1vS6tAEUgeOXSZAINHJ4qpDVs",
      "gid": "1713545352",
      "url": "https://docs.google.com/spreadsheets/d/1LL5exiR1vS6tAEUgeOXSZAINHJ4qpDVs/edit?gid=1713545352"
    },
    {
      "agency": "HDH",
      "sub": "MGC",
      "file_id": "1T1aDS2Os2yFEuxS8SaXunNSnkZn5B3Fc",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1T1aDS2Os2yFEuxS8SaXunNSnkZn5B3Fc/edit?usp=drivesdk&ouid=103752806038256224225&rtpof=true&sd=true"
    },
    {
      "agency": "HDH",
      "sub": "MEL",
      "file_id": "1T1aDS2Os2yFEuxS8SaXunNSnkZn5B3Fc",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1T1aDS2Os2yFEuxS8SaXunNSnkZn5B3Fc/edit?usp=drivesdk&ouid=103752806038256224225&rtpof=true&sd=true"
    },
    {
      "agency": "HDH",
      "sub": "HSG",
      "file_id": "1T1aDS2Os2yFEuxS8SaXunNSnkZn5B3Fc",
      "gid": "401558571",
      "url": "https://docs.google.com/spreadsheets/d/1T1aDS2Os2yFEuxS8SaXunNSnkZn5B3Fc/edit?gid=401558571"
    },
    {
      "agency": "Home Plus",
      "sub": "MGC",
      "file_id": "1JcPb_YG_84qXsxk0rR9OqpjY4bnlDmI_",
      "gid": "1038233578",
      "url": "https://docs.google.com/spreadsheets/d/1JcPb_YG_84qXsxk0rR9OqpjY4bnlDmI_/edit?sharingaction=ownershiptransfer&gid=1038233578"
    },
    {
      "agency": "Home Plus",
      "sub": "MEL",
      "file_id": "1JcPb_YG_84qXsxk0rR9OqpjY4bnlDmI_",
      "gid": "1038233578",
      "url": "https://docs.google.com/spreadsheets/d/1JcPb_YG_84qXsxk0rR9OqpjY4bnlDmI_/edit?sharingaction=ownershiptransfer&gid=1038233578"
    },
    {
      "agency": "Home Plus",
      "sub": "HSG",
      "file_id": "1JcPb_YG_84qXsxk0rR9OqpjY4bnlDmI_",
      "gid": "2094528670",
      "url": "https://docs.google.com/spreadsheets/d/1JcPb_YG_84qXsxk0rR9OqpjY4bnlDmI_/edit?sharingaction=ownershiptransfer&gid=2094528670"
    },
    {
      "agency": "Mayhomes",
      "sub": "MGC",
      "file_id": "1mcuBF_wCDVREfPHmIs1c2_bOStVueq3L5__XgohqJP8",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1mcuBF_wCDVREfPHmIs1c2_bOStVueq3L5__XgohqJP8/edit?gid=0"
    },
    {
      "agency": "Mayhomes",
      "sub": "MEL",
      "file_id": "1mN2yKQNjddl7fgF8BIJINGJPmSltFOdurE9D80WiU3I",
      "gid": "367025070",
      "url": "https://docs.google.com/spreadsheets/d/1mN2yKQNjddl7fgF8BIJINGJPmSltFOdurE9D80WiU3I/edit?gid=367025070"
    },
    {
      "agency": "Mayhomes",
      "sub": "HSG",
      "file_id": "1iEppDBYHNzVQHIV_cp-4D1oBXU4OvWEs",
      "gid": "328474852",
      "url": "https://docs.google.com/spreadsheets/d/1iEppDBYHNzVQHIV_cp-4D1oBXU4OvWEs/edit?gid=328474852"
    },
    {
      "agency": "MICC",
      "sub": "MGC",
      "file_id": "1hs_YdwRgu3xcFvFC7HBufBd87jtKTbk1",
      "gid": "1359825389",
      "url": "https://docs.google.com/spreadsheets/d/1hs_YdwRgu3xcFvFC7HBufBd87jtKTbk1/edit?gid=1359825389"
    },
    {
      "agency": "MICC",
      "sub": "MEL",
      "file_id": "1hs_YdwRgu3xcFvFC7HBufBd87jtKTbk1",
      "gid": "1459929022",
      "url": "https://docs.google.com/spreadsheets/d/1hs_YdwRgu3xcFvFC7HBufBd87jtKTbk1/edit?gid=1459929022"
    },
    {
      "agency": "MICC",
      "sub": "HSG",
      "file_id": "1WndaJ6VojVIcnPhTYL6lf878dQl9Z0Pv_7yuzH5P6OY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1WndaJ6VojVIcnPhTYL6lf878dQl9Z0Pv_7yuzH5P6OY/edit?gid=0"
    },
    {
      "agency": "NOVASKY",
      "sub": "MGC",
      "file_id": "1yMXwMkOXAt9nly1L3OWQEo-DZ1cwxsbP",
      "gid": "1306885330",
      "url": "https://docs.google.com/spreadsheets/d/1yMXwMkOXAt9nly1L3OWQEo-DZ1cwxsbP/edit?gid=1306885330"
    },
    {
      "agency": "NOVASKY",
      "sub": "HSG",
      "file_id": "1iHz-eTGoNlVes9mps4gk5vLN8sL0PktA",
      "gid": "171824251",
      "url": "https://docs.google.com/spreadsheets/d/1iHz-eTGoNlVes9mps4gk5vLN8sL0PktA/edit?gid=171824251"
    },
    {
      "agency": "NOVASKY",
      "sub": "LEP",
      "file_id": "1wxSFdMeIwHcijdeqOj0oFQcFGqi_8RFT",
      "gid": "236150331",
      "url": "https://docs.google.com/spreadsheets/d/1wxSFdMeIwHcijdeqOj0oFQcFGqi_8RFT/edit?gid=236150331#gid=236150331"
    },
    {
      "agency": "Newway",
      "sub": "MGC",
      "file_id": "10z8PXGU0qaSeiEQDWUxY6Q7Y3y2x2SZM",
      "gid": "1248261107",
      "url": "https://docs.google.com/spreadsheets/d/10z8PXGU0qaSeiEQDWUxY6Q7Y3y2x2SZM/edit?gid=1248261107"
    },
    {
      "agency": "Newway",
      "sub": "MEL",
      "file_id": "10z8PXGU0qaSeiEQDWUxY6Q7Y3y2x2SZM",
      "gid": "892276689",
      "url": "https://docs.google.com/spreadsheets/d/10z8PXGU0qaSeiEQDWUxY6Q7Y3y2x2SZM/edit?gid=892276689"
    },
    {
      "agency": "Newway",
      "sub": "HSG",
      "file_id": "1xviCqYQ94GrJbfIJFc2dJY2s5_vVFa2z5ftB0RzcFYY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1xviCqYQ94GrJbfIJFc2dJY2s5_vVFa2z5ftB0RzcFYY/edit?gid=0"
    },
    {
      "agency": "PHÚC LỘC",
      "sub": "MGC",
      "file_id": "10krC-E4a3Ydv4KbWN7g-Q1V6xZq_opOsqpHf9TmnI5M",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/10krC-E4a3Ydv4KbWN7g-Q1V6xZq_opOsqpHf9TmnI5M/edit?gid=0"
    },
    {
      "agency": "PHÚC LỘC",
      "sub": "MEL",
      "file_id": "10krC-E4a3Ydv4KbWN7g-Q1V6xZq_opOsqpHf9TmnI5M",
      "gid": "441435294",
      "url": "https://docs.google.com/spreadsheets/d/10krC-E4a3Ydv4KbWN7g-Q1V6xZq_opOsqpHf9TmnI5M/edit?gid=441435294"
    },
    {
      "agency": "PHÚC LỘC",
      "sub": "HSG",
      "file_id": "10krC-E4a3Ydv4KbWN7g-Q1V6xZq_opOsqpHf9TmnI5M",
      "gid": "987789710",
      "url": "https://docs.google.com/spreadsheets/d/10krC-E4a3Ydv4KbWN7g-Q1V6xZq_opOsqpHf9TmnI5M/edit?gid=987789710"
    },
    {
      "agency": "SSM",
      "sub": "MGC",
      "file_id": "1SceXJ5ahSlWqT-Rb4asJ_F6EVE0o5PnJ",
      "gid": "2110354503",
      "url": "https://docs.google.com/spreadsheets/d/1SceXJ5ahSlWqT-Rb4asJ_F6EVE0o5PnJ/edit?gid=2110354503"
    },
    {
      "agency": "SSM",
      "sub": "MEL",
      "file_id": "1gz_pC8cmNX6lW98JMq7gRj3UtFFODWSD",
      "gid": "608170782",
      "url": "https://docs.google.com/spreadsheets/d/1gz_pC8cmNX6lW98JMq7gRj3UtFFODWSD/edit?gid=608170782"
    },
    {
      "agency": "SSM",
      "sub": "HSG",
      "file_id": "1YXgwYIubtb4xG9DCqnZlYEa0JGhMDjbH",
      "gid": "1525221167",
      "url": "https://docs.google.com/spreadsheets/d/1YXgwYIubtb4xG9DCqnZlYEa0JGhMDjbH/edit?gid=1525221167"
    },
    {
      "agency": "Tân Long",
      "sub": "MGC",
      "file_id": "1OLlUEBz2zE8lJzVpclDTn3BGllNlKfs4",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1OLlUEBz2zE8lJzVpclDTn3BGllNlKfs4/edit?usp=drivesdk&ouid=108513348932455394481&rtpof=true&sd=true"
    },
    {
      "agency": "Tân Long",
      "sub": "MEL",
      "file_id": "1OLlUEBz2zE8lJzVpclDTn3BGllNlKfs4",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1OLlUEBz2zE8lJzVpclDTn3BGllNlKfs4/edit?usp=drivesdk&ouid=108513348932455394481&rtpof=true&sd=true"
    },
    {
      "agency": "Tân Long",
      "sub": "HSG",
      "file_id": "1ERJhhejVdwv-iLH_QtNQYXhnyATtQ7r1",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1ERJhhejVdwv-iLH_QtNQYXhnyATtQ7r1/edit?usp=sharing&ouid=106576258457376516181&rtpof=true&sd=true"
    },
    {
      "agency": "Thành Phát",
      "sub": "MGC",
      "file_id": "1TXdAH40mUrMK-kPUSNAbQHDjKojquOYiYPwJr-ebQtI",
      "gid": "1078087438",
      "url": "https://docs.google.com/spreadsheets/d/1TXdAH40mUrMK-kPUSNAbQHDjKojquOYiYPwJr-ebQtI/edit?gid=1078087438"
    },
    {
      "agency": "Thành Phát",
      "sub": "MEL",
      "file_id": "1TXdAH40mUrMK-kPUSNAbQHDjKojquOYiYPwJr-ebQtI",
      "gid": "1078087438",
      "url": "https://docs.google.com/spreadsheets/d/1TXdAH40mUrMK-kPUSNAbQHDjKojquOYiYPwJr-ebQtI/edit?gid=1078087438"
    },
    {
      "agency": "Thành Phát",
      "sub": "HSG",
      "file_id": "1TXdAH40mUrMK-kPUSNAbQHDjKojquOYiYPwJr-ebQtI",
      "gid": "1078087438",
      "url": "https://docs.google.com/spreadsheets/d/1TXdAH40mUrMK-kPUSNAbQHDjKojquOYiYPwJr-ebQtI/edit?gid=1078087438"
    },
    {
      "agency": "Thiên Phúc",
      "sub": "MGC",
      "file_id": "17WqdkCPBgH8-M640I8JvnBqI_L29wMvZr_o4w6sqIRY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/17WqdkCPBgH8-M640I8JvnBqI_L29wMvZr_o4w6sqIRY/edit?gid=0"
    },
    {
      "agency": "Thiên Phúc",
      "sub": "MEL",
      "file_id": "17WqdkCPBgH8-M640I8JvnBqI_L29wMvZr_o4w6sqIRY",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/17WqdkCPBgH8-M640I8JvnBqI_L29wMvZr_o4w6sqIRY/edit?gid=0"
    },
    {
      "agency": "TP.LAND",
      "sub": "MGC",
      "file_id": "1EFlDgh419SRQWMWNENsfq-KOQlj0yHYoc7NgvpUe2O0",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1EFlDgh419SRQWMWNENsfq-KOQlj0yHYoc7NgvpUe2O0/edit?pli=1&gid=0"
    },
    {
      "agency": "TP.LAND",
      "sub": "MEL",
      "file_id": "1EFlDgh419SRQWMWNENsfq-KOQlj0yHYoc7NgvpUe2O0",
      "gid": "1347254532",
      "url": "https://docs.google.com/spreadsheets/d/1EFlDgh419SRQWMWNENsfq-KOQlj0yHYoc7NgvpUe2O0/edit?pli=1&gid=1347254532"
    },
    {
      "agency": "TP.LAND",
      "sub": "HSG",
      "file_id": "1upXs0ByPnu-5RZq7b_xxBj4_Eeba8JBBmNsjusD7PEM",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1upXs0ByPnu-5RZq7b_xxBj4_Eeba8JBBmNsjusD7PEM/edit?gid=0"
    },
    {
      "agency": "Trường Phát Land",
      "sub": "MGC",
      "file_id": "1jG3J9czlqXUd7k78CAgVHRJ4-EWfbNqcvy7cnqb9taI",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1jG3J9czlqXUd7k78CAgVHRJ4-EWfbNqcvy7cnqb9taI/edit?usp=drivesdk"
    },
    {
      "agency": "Trường Phát Land",
      "sub": "MEL",
      "file_id": "1jG3J9czlqXUd7k78CAgVHRJ4-EWfbNqcvy7cnqb9taI",
      "gid": "1182586744",
      "url": "https://docs.google.com/spreadsheets/d/1jG3J9czlqXUd7k78CAgVHRJ4-EWfbNqcvy7cnqb9taI/edit?gid=1182586744"
    },
    {
      "agency": "Trường Phát Land",
      "sub": "HSG",
      "file_id": "1jG3J9czlqXUd7k78CAgVHRJ4-EWfbNqcvy7cnqb9taI",
      "gid": "1740185155",
      "url": "https://docs.google.com/spreadsheets/d/1jG3J9czlqXUd7k78CAgVHRJ4-EWfbNqcvy7cnqb9taI/edit?gid=1740185155"
    },
    {
      "agency": "VHS",
      "sub": "MGC",
      "file_id": "1_8KWuwV8M3gSKlRBHJfCoW2uXnz21R13eiC2Po73hho",
      "gid": "26944869",
      "url": "https://docs.google.com/spreadsheets/d/1_8KWuwV8M3gSKlRBHJfCoW2uXnz21R13eiC2Po73hho/edit?gid=26944869"
    },
    {
      "agency": "VHS",
      "sub": "MEL",
      "file_id": "1_8KWuwV8M3gSKlRBHJfCoW2uXnz21R13eiC2Po73hho",
      "gid": "26944869",
      "url": "https://docs.google.com/spreadsheets/d/1_8KWuwV8M3gSKlRBHJfCoW2uXnz21R13eiC2Po73hho/edit?gid=26944869"
    },
    {
      "agency": "VHS",
      "sub": "HSG",
      "file_id": "1Oc4bJEh5yLEwaQFmbaZUiWTjQDkqyJmT1soCUbhXb9E",
      "gid": "1730070749",
      "url": "https://docs.google.com/spreadsheets/d/1Oc4bJEh5yLEwaQFmbaZUiWTjQDkqyJmT1soCUbhXb9E/edit?gid=1730070749"
    },
    {
      "agency": "VHS",
      "sub": "LEP",
      "file_id": "1wnn5QnRPelR23yZKGrH0uemNFVfEGpZuEx9lTAoYiDY",
      "gid": "142054600",
      "url": "https://docs.google.com/spreadsheets/d/1wnn5QnRPelR23yZKGrH0uemNFVfEGpZuEx9lTAoYiDY/edit?gid=142054600"
    },
    {
      "agency": "MVL - F2",
      "sub": "MGC",
      "file_id": "1PU1Gvo6-rQpxDjiXs9QmpMgX3GCqitiK",
      "gid": "760006275",
      "url": "https://docs.google.com/spreadsheets/d/1PU1Gvo6-rQpxDjiXs9QmpMgX3GCqitiK/edit?gid=760006275"
    },
    {
      "agency": "MVL - F2",
      "sub": "MEL",
      "file_id": "1PU1Gvo6-rQpxDjiXs9QmpMgX3GCqitiK",
      "gid": "760006275",
      "url": "https://docs.google.com/spreadsheets/d/1PU1Gvo6-rQpxDjiXs9QmpMgX3GCqitiK/edit?gid=760006275"
    },
    {
      "agency": "PG - F2",
      "sub": "MGC",
      "file_id": "1BHdx1CcJUwiM4gU-EHIeDmWMbAvcY1K8",
      "gid": "242497827",
      "url": "https://docs.google.com/spreadsheets/d/1BHdx1CcJUwiM4gU-EHIeDmWMbAvcY1K8/edit?gid=242497827"
    },
    {
      "agency": "PG - F2",
      "sub": "MEL",
      "file_id": "1TLcf033AXVbuaw45Aj54fqvGs2RGh9am",
      "gid": "2029879128",
      "url": "https://docs.google.com/spreadsheets/d/1TLcf033AXVbuaw45Aj54fqvGs2RGh9am/edit?gid=2029879128"
    },
    {
      "agency": "PG - F2",
      "sub": "HSG",
      "file_id": "15K8X2SonzFkkwfOANXk3bSsvCfYd4q7zMMNekepFy3Q",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/15K8X2SonzFkkwfOANXk3bSsvCfYd4q7zMMNekepFy3Q/edit?gid=0"
    },
    {
      "agency": "JH",
      "sub": "MGC",
      "file_id": "1315ACmRZtKQ8M4GHblgK6QmjyIHAkYZHcq0bqwZhmmI",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1315ACmRZtKQ8M4GHblgK6QmjyIHAkYZHcq0bqwZhmmI/edit?usp=drivesdk"
    },
    {
      "agency": "JH",
      "sub": "MEL",
      "file_id": "15DMO-15wmWGz_yGBfmOU0NSzSyXzvl2ed7LLR_DtGmw",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/15DMO-15wmWGz_yGBfmOU0NSzSyXzvl2ed7LLR_DtGmw/edit?usp=drivesdk"
    },
    {
      "agency": "JH",
      "sub": "HSG",
      "file_id": "1J6acx6bWNtfTMP5hKCPrjwySri3-9Wmo8OL5gIztyKg",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1J6acx6bWNtfTMP5hKCPrjwySri3-9Wmo8OL5gIztyKg/edit?gid=0"
    },
    {
      "agency": "JH",
      "sub": "LEP",
      "file_id": "12_DHhdT2sUeC2QNuLxXWy4DFS6eMCeIOzZBKyF1-2IA",
      "gid": "206934518",
      "url": "https://docs.google.com/spreadsheets/d/12_DHhdT2sUeC2QNuLxXWy4DFS6eMCeIOzZBKyF1-2IA/edit?gid=206934518"
    },
    {
      "agency": "VINSLAND",
      "sub": "MGC",
      "file_id": "1a0u0r-VKjrFmxFJMuLlORyoavP1s4bNPk8JRNNYaUaw",
      "gid": "359077054",
      "url": "https://docs.google.com/spreadsheets/d/1a0u0r-VKjrFmxFJMuLlORyoavP1s4bNPk8JRNNYaUaw/edit?gid=359077054"
    },
    {
      "agency": "VINSLAND",
      "sub": "MEL",
      "file_id": "110ezJiMZdryFplESDwI9ykkOVT_hjjFk",
      "gid": "906884481",
      "url": "https://docs.google.com/spreadsheets/d/110ezJiMZdryFplESDwI9ykkOVT_hjjFk/edit?gid=906884481"
    },
    {
      "agency": "VINSLAND",
      "sub": "HSG",
      "file_id": "1k4aLELmVStbF48qmbBwpydp2cpElNWnw",
      "gid": "2047393054",
      "url": "https://docs.google.com/spreadsheets/d/1k4aLELmVStbF48qmbBwpydp2cpElNWnw/edit?gid=2047393054"
    },
    {
      "agency": "VSL",
      "sub": "MGC",
      "file_id": "1zc4S1zELshpf3kL5OfVZIe2KMo3z9wkrk3zt8Ux3zE4",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1zc4S1zELshpf3kL5OfVZIe2KMo3z9wkrk3zt8Ux3zE4/edit?usp=drivesdk"
    },
    {
      "agency": "VSL",
      "sub": "MEL",
      "file_id": "1zc4S1zELshpf3kL5OfVZIe2KMo3z9wkrk3zt8Ux3zE4",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1zc4S1zELshpf3kL5OfVZIe2KMo3z9wkrk3zt8Ux3zE4/edit?usp=drivesdk"
    },
    {
      "agency": "VSL",
      "sub": "HSG",
      "file_id": "19ol17sm6OanUZZXwg3p6y7nxcMi8zrxX1oOMWY-81FQ",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/19ol17sm6OanUZZXwg3p6y7nxcMi8zrxX1oOMWY-81FQ/edit?gid=0"
    },
    {
      "agency": "WDH",
      "sub": "MGC",
      "file_id": "1kAYcL8mVzZfKvdm1IL34sTP8o1xSTSCE0Hk7fb7vB88",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1kAYcL8mVzZfKvdm1IL34sTP8o1xSTSCE0Hk7fb7vB88/edit?usp=sharing"
    },
    {
      "agency": "WDH",
      "sub": "MEL",
      "file_id": "16PIc_v7Rj4qG-JDBlFVN_jcO0nYmRvDNZjXv5PkdLNM",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/16PIc_v7Rj4qG-JDBlFVN_jcO0nYmRvDNZjXv5PkdLNM/edit?usp=sharing"
    },
    {
      "agency": "WDH",
      "sub": "HSG",
      "file_id": "14uV65eDoZijEld1MpNTsC2R73HLkfJTK4Q3-TLnhuAA",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/14uV65eDoZijEld1MpNTsC2R73HLkfJTK4Q3-TLnhuAA/edit?gid=0"
    },
    {
      "agency": "MDL - F2",
      "sub": "MGC",
      "file_id": "1X8QiskRQwiv6Ho8izxWj0Sg9UWWCMW90",
      "gid": "908703485",
      "url": "https://docs.google.com/spreadsheets/d/1X8QiskRQwiv6Ho8izxWj0Sg9UWWCMW90/edit?gid=908703485"
    },
    {
      "agency": "MDL - F2",
      "sub": "MEL",
      "file_id": "1X8QiskRQwiv6Ho8izxWj0Sg9UWWCMW90",
      "gid": "568881025",
      "url": "https://docs.google.com/spreadsheets/d/1X8QiskRQwiv6Ho8izxWj0Sg9UWWCMW90/edit?gid=568881025"
    },
    {
      "agency": "QLG - F2",
      "sub": "MGC",
      "file_id": "1BuARb6PK0_OXgjj4fkt3ffNzpQddhs_0",
      "gid": "843999775",
      "url": "https://docs.google.com/spreadsheets/d/1BuARb6PK0_OXgjj4fkt3ffNzpQddhs_0/edit?gid=843999775"
    },
    {
      "agency": "QLG - F2",
      "sub": "MEL",
      "file_id": "1BuARb6PK0_OXgjj4fkt3ffNzpQddhs_0",
      "gid": "843999775",
      "url": "https://docs.google.com/spreadsheets/d/1BuARb6PK0_OXgjj4fkt3ffNzpQddhs_0/edit?gid=843999775"
    },
    {
      "agency": "NSL - F2",
      "sub": "MGC",
      "file_id": "1rDDRoreTDP5m71uxt6_Ff_lsvzlwqfuq1Uz72bZrBY8",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1rDDRoreTDP5m71uxt6_Ff_lsvzlwqfuq1Uz72bZrBY8/edit?gid=0"
    },
    {
      "agency": "NSL - F2",
      "sub": "MEL",
      "file_id": "1RMNlDdfmpHp3SWKMslO6r4A28CllJLj3ci46Ightk7U",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1RMNlDdfmpHp3SWKMslO6r4A28CllJLj3ci46Ightk7U/edit?usp=drive_link"
    },
    {
      "agency": "Tân Hương Phát",
      "sub": "MGC",
      "file_id": "1e4xBRLfMn9gRmr1Q3Ov7TZZsBK4AaAci",
      "gid": "324040422",
      "url": "https://docs.google.com/spreadsheets/d/1e4xBRLfMn9gRmr1Q3Ov7TZZsBK4AaAci/edit?gid=324040422"
    },
    {
      "agency": "Tân Hương Phát",
      "sub": "MEL",
      "file_id": "1e4xBRLfMn9gRmr1Q3Ov7TZZsBK4AaAci",
      "gid": "324040422",
      "url": "https://docs.google.com/spreadsheets/d/1e4xBRLfMn9gRmr1Q3Ov7TZZsBK4AaAci/edit?gid=324040422"
    },
    {
      "agency": "Tân Hương Phát",
      "sub": "HSG",
      "file_id": "1a54HIuxsrbbcTAuV30CYtqGYQweNdzySfoxHRpiw7S8",
      "gid": "677934803",
      "url": "https://docs.google.com/spreadsheets/d/1a54HIuxsrbbcTAuV30CYtqGYQweNdzySfoxHRpiw7S8/edit?gid=677934803"
    },
    {
      "agency": "Warriot F2",
      "sub": "MGC",
      "file_id": "1g45iduRRGbQvxBEtAEHffs4mQ2ju8jviy9MALYfvoeU",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1g45iduRRGbQvxBEtAEHffs4mQ2ju8jviy9MALYfvoeU/edit?gid=0"
    },
    {
      "agency": "Warriot F2",
      "sub": "MEL",
      "file_id": "1PZgywpd-_GPaOMeX4pc7y32k77pt4KYkhVI8rFnPvXE",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1PZgywpd-_GPaOMeX4pc7y32k77pt4KYkhVI8rFnPvXE/edit?gid=0"
    },
    {
      "agency": "Cella",
      "sub": "MGC",
      "file_id": "1eZisr46qomH5mGi6jOKA-OOboyJhuaF4",
      "gid": "513947930",
      "url": "https://docs.google.com/spreadsheets/d/1eZisr46qomH5mGi6jOKA-OOboyJhuaF4/edit?gid=513947930"
    },
    {
      "agency": "BH",
      "sub": "MGC",
      "file_id": "1vfD6WxnQkS_IK6CY7Rjtiai6cL8uqogg",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1vfD6WxnQkS_IK6CY7Rjtiai6cL8uqogg/edit?usp=drivesdk&ouid=112968815832014100445&rtpof=true&sd=true"
    },
    {
      "agency": "BH",
      "sub": "MEL",
      "file_id": "1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8",
      "gid": "0",
      "url": "https://docs.google.com/spreadsheets/d/1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8/edit?gid=0"
    },
    {
      "agency": "BH",
      "sub": "HSG",
      "file_id": "1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8",
      "gid": "349207916",
      "url": "https://docs.google.com/spreadsheets/d/1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8/edit?gid=349207916"
    },
    {
      "agency": "BH",
      "sub": "LEP",
      "file_id": "1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8",
      "gid": "349207916",
      "url": "https://docs.google.com/spreadsheets/d/1x-rHW0l2_WenJkK69EIQE5ya7pUl7_eDHLy36xafov8/edit?gid=349207916"
    },
    {
      "agency": "An Holding",
      "sub": "MGC",
      "file_id": "1Gdd-6Mxmxt37gc38dUEpVa-4sK4LFQgovoU2l7nmBBw",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1Gdd-6Mxmxt37gc38dUEpVa-4sK4LFQgovoU2l7nmBBw/edit?usp=drivesdk"
    },
    {
      "agency": "An Holding",
      "sub": "MEL",
      "file_id": "1Gdd-6Mxmxt37gc38dUEpVa-4sK4LFQgovoU2l7nmBBw",
      "gid": "1619487891",
      "url": "https://docs.google.com/spreadsheets/d/1Gdd-6Mxmxt37gc38dUEpVa-4sK4LFQgovoU2l7nmBBw/edit?gid=1619487891"
    },
    {
      "agency": "An Holding",
      "sub": "HSG",
      "file_id": "1Gdd-6Mxmxt37gc38dUEpVa-4sK4LFQgovoU2l7nmBBw",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1Gdd-6Mxmxt37gc38dUEpVa-4sK4LFQgovoU2l7nmBBw/edit?usp=drivesdk"
    },
    {
      "agency": "CLH - F2",
      "sub": "MGC",
      "file_id": "1eZisr46qomH5mGi6jOKA-OOboyJhuaF4",
      "gid": "1443191283",
      "url": "https://docs.google.com/spreadsheets/d/1eZisr46qomH5mGi6jOKA-OOboyJhuaF4/edit?gid=1443191283"
    },
    {
      "agency": "CLH - F2",
      "sub": "MEL",
      "file_id": "1eZisr46qomH5mGi6jOKA-OOboyJhuaF4",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1eZisr46qomH5mGi6jOKA-OOboyJhuaF4/edit?usp=drivesdk&ouid=100088197594858947146&rtpof=true&sd=true"
    },
    {
      "agency": "CLH - F2",
      "sub": "HSG",
      "file_id": "1eZisr46qomH5mGi6jOKA-OOboyJhuaF4",
      "gid": "1443191283",
      "url": "https://docs.google.com/spreadsheets/d/1eZisr46qomH5mGi6jOKA-OOboyJhuaF4/edit?gid=1443191283"
    },
    {
      "agency": "CLH - F2",
      "sub": "LEP",
      "file_id": "1eZisr46qomH5mGi6jOKA-OOboyJhuaF4",
      "gid": "1443191283",
      "url": "https://docs.google.com/spreadsheets/d/1eZisr46qomH5mGi6jOKA-OOboyJhuaF4/edit?gid=1443191283"
    }
  ],
  "OCP2-3": [
    {
      "agency": "BIGHOMES GROUP",
      "sub": null,
      "file_id": "1qtuk53-uI18GmyMDtQhj2mIEq-Bde1X7",
      "gid": "1282456652",
      "url": "https://docs.google.com/spreadsheets/d/1qtuk53-uI18GmyMDtQhj2mIEq-Bde1X7/edit?gid=1282456652"
    },
    {
      "agency": "ĐẤT VIỆT GROUP",
      "sub": null,
      "file_id": "18myJM1bcuRYM0f3s8siAysu5CGOCJREHqpGgGhTOdqQ",
      "gid": "1672281233",
      "url": "https://docs.google.com/spreadsheets/d/18myJM1bcuRYM0f3s8siAysu5CGOCJREHqpGgGhTOdqQ/edit?gid=1672281233"
    },
    {
      "agency": "HDHOMES",
      "sub": null,
      "file_id": "1xhhzfH6ftqxoNHrLGQx_xnWV_Hr9oy8b",
      "gid": "1914621288",
      "url": "https://docs.google.com/spreadsheets/d/1xhhzfH6ftqxoNHrLGQx_xnWV_Hr9oy8b/edit?pli=1&gid=1914621288"
    },
    {
      "agency": "HOÀNG GIA + PHÚC LỘC",
      "sub": null,
      "file_id": "1fjsSdxl4vjIYsZV-qHhegCjuYUVAzSdD",
      "gid": "341896574",
      "url": "https://docs.google.com/spreadsheets/d/1fjsSdxl4vjIYsZV-qHhegCjuYUVAzSdD/edit?gid=341896574"
    },
    {
      "agency": "HOME PLUS",
      "sub": null,
      "file_id": "1wZh2DCh0i79XFXcsPGFkpNzT5YO6FnzqdKsqUlDaR9I",
      "gid": "1196287177",
      "url": "https://docs.google.com/spreadsheets/d/1wZh2DCh0i79XFXcsPGFkpNzT5YO6FnzqdKsqUlDaR9I/edit?gid=1196287177"
    },
    {
      "agency": "MAYHOMES",
      "sub": null,
      "file_id": "1-KcwSLpuSQGhqOZ8BycoRLeE3DUrawan",
      "gid": "1592630955",
      "url": "https://docs.google.com/spreadsheets/d/1-KcwSLpuSQGhqOZ8BycoRLeE3DUrawan/edit?gid=1592630955"
    },
    {
      "agency": "MD LAND",
      "sub": null,
      "file_id": "1Ug7YKmct2VdKEmP5y4osGpZKJkcsfzZux_KyUrmHBCQ",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/u/1/d/1Ug7YKmct2VdKEmP5y4osGpZKJkcsfzZux_KyUrmHBCQ/edit"
    },
    {
      "agency": "MICC",
      "sub": null,
      "file_id": "1stAchuTAuKDwJg3adUdAWXJQI1m9GFilcASiOnUlM6o",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1stAchuTAuKDwJg3adUdAWXJQI1m9GFilcASiOnUlM6o/edit?usp=sharing"
    },
    {
      "agency": "NEWSTARLAND",
      "sub": null,
      "file_id": "1FDnt60-5OeQdy0tFfzrsLhYGAge2i-AjtX0vr1LZMa4",
      "gid": "1185479706",
      "url": "https://docs.google.com/spreadsheets/d/1FDnt60-5OeQdy0tFfzrsLhYGAge2i-AjtX0vr1LZMa4/edit?gid=1185479706"
    },
    {
      "agency": "NOVASKY",
      "sub": null,
      "file_id": "11Q_auyPRRzQodhGvg4SRzG3dkt3dXTos",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/11Q_auyPRRzQodhGvg4SRzG3dkt3dXTos/edit"
    },
    {
      "agency": "QUEENLAND GROUP",
      "sub": null,
      "file_id": "1G_YuvJGvJ8DS8ROe3zEfe2a8bd6AbocwYwOwx3gOM-E",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/u/1/d/1G_YuvJGvJ8DS8ROe3zEfe2a8bd6AbocwYwOwx3gOM-E/edit"
    },
    {
      "agency": "TÂN HƯƠNG PHÁT",
      "sub": null,
      "file_id": "1ncfMRR8aFJyD3ypW4MEvnACrwgbQg0A2",
      "gid": "1640787262",
      "url": "https://docs.google.com/spreadsheets/d/1ncfMRR8aFJyD3ypW4MEvnACrwgbQg0A2/edit?gid=1640787262"
    },
    {
      "agency": "TÂN THỜI ĐẠI",
      "sub": null,
      "file_id": "1nzVz7pn_2B3VZbYEmMsG0kH5si3Ok_2CJwkSC8eCjTw",
      "gid": "1761455020",
      "url": "https://docs.google.com/spreadsheets/d/1nzVz7pn_2B3VZbYEmMsG0kH5si3Ok_2CJwkSC8eCjTw/edit?gid=1761455020"
    },
    {
      "agency": "THIÊN PHÚC",
      "sub": null,
      "file_id": "18g1cyDtMd-ce_ci9FjOvLJZiWbryO-GO",
      "gid": "709290990",
      "url": "https://docs.google.com/spreadsheets/d/18g1cyDtMd-ce_ci9FjOvLJZiWbryO-GO/edit?gid=709290990"
    },
    {
      "agency": "TRƯỜNG PHÁT LAND",
      "sub": null,
      "file_id": "1VQrIy73LgZ7NHPOV7TcKyVNJz9SS5_laiWN_XlCcATM",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/d/1VQrIy73LgZ7NHPOV7TcKyVNJz9SS5_laiWN_XlCcATM/edit?usp=drivesdk"
    },
    {
      "agency": "VHS LAND",
      "sub": null,
      "file_id": "1PrNk0qj3YXuyQ_YqMkKavihHKLAaJhycD2Hgz7dV9qg",
      "gid": "1280098514",
      "url": "https://docs.google.com/spreadsheets/d/1PrNk0qj3YXuyQ_YqMkKavihHKLAaJhycD2Hgz7dV9qg/edit?gid=1280098514"
    },
    {
      "agency": "VIETSTARLAND",
      "sub": null,
      "file_id": "11v84wb5ZbBvlfr6CHVZYWsriG7hohx7ud7NuKDNrJ1s",
      "gid": null,
      "url": "https://docs.google.com/spreadsheets/u/0/d/11v84wb5ZbBvlfr6CHVZYWsriG7hohx7ud7NuKDNrJ1s/htmlview?zarsrc=30&utm_source=zalo&utm_medium=zalo&utm_campaign=zalo&gidzl=FvdZKsCLuc0vWkTGPGBYP3g9vbHv1-Om8D_a12u7vc5wZES48r7ZONZRuLyYKhTkV8hY3JPjkJG7OnBcOm"
    },
    {
      "agency": "VISION REALTY + NW",
      "sub": null,
      "file_id": "13sTDgBX3igxBL69Mua1V4IdeT_zXKE1g",
      "gid": "203109880",
      "url": "https://docs.google.com/spreadsheets/d/13sTDgBX3igxBL69Mua1V4IdeT_zXKE1g/edit?gid=203109880"
    },
    {
      "agency": "FIVE STAR",
      "sub": null,
      "file_id": "16zz1yyED1Mz7R_fxlQOObSCSCSRtQ6cpZU1DJVc26b8",
      "gid": "1505826301",
      "url": "https://docs.google.com/spreadsheets/d/16zz1yyED1Mz7R_fxlQOObSCSCSRtQ6cpZU1DJVc26b8/edit?gid=1505826301"
    },
    {
      "agency": "RM",
      "sub": null,
      "file_id": "1E32xZqcFF3lHcDmYmQANuh97hrNP7BOYpOcHCd6VPlM",
      "gid": "2133880828",
      "url": "https://docs.google.com/spreadsheets/d/1E32xZqcFF3lHcDmYmQANuh97hrNP7BOYpOcHCd6VPlM/edit?gid=2133880828"
    }
  ]
};
const DEFAULT_POLICY_YEAR = 2026;

const TARGET_PROJECT_FILES = {
  'làng vân':     { id: '1G7kWbKI1q8O_r2i5eeNCyAhPjr62EIYRIeXp1n4FZBI', type: 'LOW_RISE',  name: 'Dự án Làng Vân' },
  'VRI':          { id: '1fLHY2nvP4pLXDFrY0GMfLLTpOHORhnZ5JePVxqh8kfU', type: 'LOW_RISE',  name: 'Dự án VRI' },
  'MIK OCP':      { id: '1NhlYJU_eyv4AXYGY3YhJ2RESe32u7QhSevajFXX5b-c', type: 'HIGH_RISE', name: 'Dự án MIK OCP' },
  'DƯƠNG KINH':   { id: '1Xx2PSzX6LzYkiBeu9qM3cK5u2p_BjjVjSktR1_AIt7Q', type: 'LOW_RISE',  name: 'Dự án Dương Kinh' },
  'HLX':          { id: '1TAkltHR0O6bvCdJ5s8LY1Ystq95eSuFXyLMscQ5xGJM', type: 'LOW_RISE',  name: 'Dự án HLX' },
  'Đan phượng':   { id: '1VGF3Joh39qIT4hwpjNT_YETsCUoFmBdUsAQvhncbkC4', type: 'LOW_RISE',  name: 'Dự án Đan Phượng' },
  'TRÀNG CÁT':    { id: '1lPCZGx2ngtFQkL7KBZkQDfVEQHUog91Fr8qfWsLVIlk', type: 'LOW_RISE',  name: 'Dự án Tràng Cát' },
  'Cần giờ':      { id: '1yt1aiAt8ONkU1YKzHoO2zAjB-Oujne0tR3hbYOt2qQc', type: 'LOW_RISE',  name: 'Dự án Cần Giờ' },
  'Hóc Môn':      { id: '1YzUhxCEqm47yxP7SOpuA8kktflQEAbvNkWIn5UxIM0U', type: 'LOW_RISE',  name: 'Dự án Hóc Môn' },
  'Q9':           { id: '1HTcHXvk9gKZdE2fGGIkL4utSHZ-as5zZC0FxN2GVlYI', type: 'HIGH_RISE', name: 'Dự án Q9' },
  'MAS CAO TẦNG': { id: '1fV1_ZKQXVzsrdMa8ElSpVu-32cj4vPTzgftN81sDynM', type: 'HIGH_RISE', name: 'Dự án MAS - Cao tầng', tabs: ['MGC', 'MEL', 'HSG', 'LEP'] },
  'OCP2-3':       { id: '1LtzwcF6xP-ZdfuNoschNN3-LhbP1fuHqsiA_ad75jJQ', type: 'LOW_RISE',  name: 'Dự án OCP2-3' }
};

const LOW_RISE_HEADERS = [
  'STT', 'Phân khu', 'Mã căn', 'TCBG', 'Loại hình', 'Diện tích đất', 'Diện tích xây dựng',
  'Giá chưa gồm VAT', 'VAT (Tổng)', 'KPBT (Tổng)', 'Giá gồm VAT và KPBT',
  'Xây trc VAT', 'VAT (Xây)', 'KPBT (Xây)', 'Tổng Xây',
  'Đất trc VAT', 'VAT (Đất)', 'KPBT (Đất)', 'Tổng Đất',
  'Đơn giá / m²', 'Giá vay', 'Giá thanh toán theo tiến độ', 'Giá thanh toán sớm',
  'Hướng', 'Chiều rộng mặt tiền', 'Số tầng', 'Quà tặng', 'Mô tả', 'CSBH áp dụng',
  'Ngân hàng hỗ trợ giải ngân', 'Ghi chú', 'Trạng thái', 'Nhóm quỹ',
  'Ảnh chỉ căn', 'Ảnh phiếu tính giá', 'Đại lý', 'Ngày cấp hàng'
];

const HIGH_RISE_HEADERS = [
  'STT', 'Mã căn', 'Phân khu', 'Loại hình', 'Hướng', 'Tên tòa', 'Tầng', 'Mã trục căn',
  'Diện tích thông thủy', 'Diện tích tim tường', 'Số phòng ngủ', 'Số WC',
  'KPBT (kinh phí bảo trì)', 'Giá chưa gồm VAT + KPBT', 'Giá niêm yết Gồm VAT + KPBT',
  'Giá vay', 'Giá thanh toán theo tiến độ', 'Giá thanh toán sớm', 'Đơn giá / m²',
  'Tiêu chuẩn bàn giao', 'Quà tặng', 'Mô tả', 'CSBH áp dụng',
  'Ngân hàng hỗ trợ giải ngân', 'Ảnh chỉ căn', 'Ảnh phiếu tính giá',
  'Ghi chú', 'Trạng thái', 'Nhóm quỹ', 'Đại lý', 'Ngày cấp hàng'
];

const RED_BG_COLORS = [
  '#ff0000', '#ea4335', '#e06666', '#f4cccc',
  '#cc0000', '#990000', '#ea9999', '#d9534f',
  '#ff3333', '#ff4d4d', '#ff6666', '#ff9999', '#fce8e6'
];

const NON_INVENTORY_TAB_REGEX = /(stk|tài khoản|tai khoan|giỏ bank|gio bank|đầu mối|dau moi|thông số|thong so|giải chấp|giai chap|bàn giao|ban giao|csbh|đã bán|da ban|check ẩn|check an|quỹ ẩn|quy an|quỹ cũ|quy cu|lưu|game|tạo tk|quy định|quy dinh|hướng dẫn|huong dan)/i;

const DRIVE_FOLDER_CACHE = {};

/**
 * ============================================================================
 * MENU ĐIỀU KHIỂN TRỰC TIẾP TRÊN GOOGLE SHEETS & CÀI ĐẶT TRIGGER TỰ ĐỘNG
 * ============================================================================
 */
function onOpen() {
  try {
    const ui = SpreadsheetApp.getUi();
    ui.createMenu('⚡ Đồng Bộ 12 Dự Án (v4.5)')
      .addItem('🚀 Chạy đồng bộ toàn bộ 12 dự án ngay', 'syncAll12Projects')
      .addSeparator()
      .addItem('⏰ Cài đặt Trigger tự động chạy mỗi giờ', 'setupHourlyTrigger')
      .addItem('🛑 Hủy toàn bộ Trigger tự động', 'removeAllTriggers')
      .addSeparator()
      .addSubMenu(
        ui.createMenu('📂 Chạy riêng từng dự án')
          .addItem('1. Dự án Làng Vân', 'syncLangVan')
          .addItem('2. Dự án VRI', 'syncVri')
          .addItem('3. Dự án MIK OCP', 'syncMikOcp')
          .addItem('4. Dự án Dương Kinh', 'syncDuongKinh')
          .addItem('5. Dự án HLX', 'syncHlx')
          .addItem('6. Dự án Đan Phượng', 'syncDanPhuong')
          .addItem('7. Dự án Tràng Cát', 'syncTrangCat')
          .addItem('8. Dự án Cần Giờ', 'syncCanGio')
          .addItem('9. Dự án Hóc Môn', 'syncHocMon')
          .addItem('10. Dự án Q9', 'syncQ9')
          .addItem('11. Dự án MAS - Cao tầng (4 tab)', 'syncMasCaoTang')
          .addItem('12. Dự án OCP2-3', 'syncOcp23')
      )
      .addToUi();
  } catch (e) {
    Logger.log('onOpen chạy ngoài ngữ cảnh UI: ' + e.message);
  }
}

function setupHourlyTrigger() {
  removeAllTriggers();
  ScriptApp.newTrigger('syncAll12Projects')
    .timeBased()
    .everyHours(1)
    .create();
  Logger.log('Đã cài đặt Trigger tự động chạy hàm syncAll12Projects mỗi giờ.');
}

function removeAllTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  for (let i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'syncAll12Projects') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

function syncLangVan()    { syncSingleProject('làng vân'); }
function syncVri()        { syncSingleProject('VRI'); }
function syncMikOcp()     { syncSingleProject('MIK OCP'); }
function syncDuongKinh()  { syncSingleProject('DƯƠNG KINH'); }
function syncHlx()        { syncSingleProject('HLX'); }
function syncDanPhuong()  { syncSingleProject('Đan phượng'); }
function syncTrangCat()   { syncSingleProject('TRÀNG CÁT'); }
function syncCanGio()     { syncSingleProject('Cần giờ'); }
function syncHocMon()     { syncSingleProject('Hóc Môn'); }
function syncQ9()         { syncSingleProject('Q9'); }
function syncMasCaoTang() { syncSingleProject('MAS CAO TẦNG'); }
function syncOcp23()      { syncSingleProject('OCP2-3'); }

/**
 * ============================================================================
 * 1. CHUẨN HÓA MÃ TẦNG, MÃ TRỤC CĂN & MÃ CĂN CAO TẦNG (MỞ RỘNG V4.1 CHO Q9)
 * ============================================================================
 */
const COMMERCIAL_CODE_MAP = {
  '1': '01', '01': '01',
  '2': '02', '02': '02',
  '3': '03', '03': '03',
  '4': '05A', '04': '05A', '5A': '05A', '05A': '05A', '3A': '03A', '03A': '03A',
  '5': '05', '05': '05',
  '6': '06', '06': '06', '6A': '06A', '06A': '06A',
  '7': '08A', '07': '08A', '8A': '08A', '08A': '08A',
  '8': '08', '08': '08',
  '9': '09', '09': '09',
  '10': '10',
  '11': '11',
  '12': '12',
  '13': '12A', '12A': '12A',
  '14': '15A', '15A': '15A',
  '15': '15',
  '16': '16',
  '17': '17',
  '18': '18'
};

function toCommercialFloorOrAxisCode(rawToken) {
  if (rawToken === null || rawToken === undefined || rawToken === '') return '';
  let s = String(rawToken).trim().toUpperCase();
  s = s.replace(/^(TẦNG|TANG|TRỤC|TRUC|CĂN|CAN|SỐ|SO)\s*/i, '').trim();
  if (!s) return '';
  if (COMMERCIAL_CODE_MAP[s]) return COMMERCIAL_CODE_MAP[s];
  if (/^\d[A-Z]$/.test(s)) return '0' + s;
  if (/^\d$/.test(s)) {
    const padded = '0' + s;
    return COMMERCIAL_CODE_MAP[padded] || padded;
  }
  if (/^\d{2}[A-Z]?$/.test(s)) return s;
  return s;
}

function normalizeHighRiseUnitFloorAxis(rawUnitCode, rawTower, rawFloor, rawAxis) {
  let unit = String(rawUnitCode || '').trim().toUpperCase().replace(/\s+/g, '');
  let tower = String(rawTower || '').trim().toUpperCase();
  let floor = toCommercialFloorOrAxisCode(rawFloor);
  let axis = toCommercialFloorOrAxisCode(rawAxis);

  // 1. Dạng có dấu gạch ngang: 'A1-29-05', 'B2-06A-01', 'HH-A-23-04', 'S2-13-14'
  const hyphenParts = unit.split('-');
  if (hyphenParts.length >= 3) {
    const rawAxPart = hyphenParts[hyphenParts.length - 1];
    const rawFlPart = hyphenParts[hyphenParts.length - 2];
    const rawTwPart = hyphenParts.slice(0, hyphenParts.length - 2).join('-');
    const normFl = toCommercialFloorOrAxisCode(rawFlPart);
    const normAx = toCommercialFloorOrAxisCode(rawAxPart);
    if (!tower) tower = rawTwPart;
    if (!floor) floor = normFl;
    if (!axis) axis = normAx;
    unit = rawTwPart + '-' + normFl + '-' + normAx;
    return { unitCode: unit, tower: tower, floor: floor, axis: axis };
  }

  // 2. (V4.1) Dạng 2 dấu chấm ở Q9 (Vinhomes Grand Park): 'S6.0619.06', 'S10.0213.19'
  const twoDotMatch = unit.match(/^([A-Z]\d{1,2})\.(\d{2})(\d{2}[A-Z]?)\.(\d{2}[A-Z]?)$/);
  if (twoDotMatch) {
    const tw = twoDotMatch[1] + '.' + twoDotMatch[2];
    const normFl = toCommercialFloorOrAxisCode(twoDotMatch[3]);
    const normAx = toCommercialFloorOrAxisCode(twoDotMatch[4]);
    if (!tower) tower = tw;
    if (!floor) floor = normFl;
    if (!axis) axis = normAx;
    unit = tw + '.' + normFl + '.' + normAx;
    return { unitCode: unit, tower: tower, floor: floor, axis: axis };
  }

  // 3. (V4.1) Dạng TòaTầng.Trục ở Q9: 'BE130.04', 'BS1114.15', 'OS207.03', 'GH224.18'
  const towerFloorDotAxis = unit.match(/^([A-Z]{2,3}\d{1,2})(\d{2}[A-Z]?)\.(\d{2}[A-Z]?)$/);
  if (towerFloorDotAxis) {
    const tw = towerFloorDotAxis[1];
    const normFl = toCommercialFloorOrAxisCode(towerFloorDotAxis[2]);
    const normAx = toCommercialFloorOrAxisCode(towerFloorDotAxis[3]);
    if (!tower) tower = tw;
    if (!floor) floor = normFl;
    if (!axis) axis = normAx;
    unit = tw + normFl + '.' + normAx;
    return { unitCode: unit, tower: tower, floor: floor, axis: axis };
  }

  // 4. Dạng Tòa.TầngTrục: 'P2.2602', 'M1.1508A', 'P1.08A05', 'M3.1304'
  const dotMatch = unit.match(/^([A-Z0-9]+)\.(\d{2}[A-Z]?)(\d{2}[A-Z]?)$/);
  if (dotMatch) {
    const tw = dotMatch[1];
    const normFl = toCommercialFloorOrAxisCode(dotMatch[2]);
    const normAx = toCommercialFloorOrAxisCode(dotMatch[3]);
    if (!tower) tower = tw;
    if (!floor) floor = normFl;
    if (!axis) axis = normAx;
    unit = tw + '.' + normFl + normAx;
    return { unitCode: unit, tower: tower, floor: floor, axis: axis };
  }

  // 5. Dạng viết liền: 'U2812A', 'Z3005A', 'C108A08', 'B11407'
  const compactMatch = unit.match(/^([A-Z]\d?|[A-Z]{1,2})(\d{2}[A-Z]?)(\d{2}[A-Z]?)$/);
  if (compactMatch) {
    const tw = compactMatch[1];
    const normFl = toCommercialFloorOrAxisCode(compactMatch[2]);
    const normAx = toCommercialFloorOrAxisCode(compactMatch[3]);
    if (!tower) tower = tw;
    if (!floor) floor = normFl;
    if (!axis) axis = normAx;
    unit = tw + normFl + normAx;
    return { unitCode: unit, tower: tower, floor: floor, axis: axis };
  }

  return { unitCode: unit, tower: tower, floor: floor, axis: axis };
}

/**
 * ============================================================================
 * 2. BỘ PHÁT HIỆN & XỬ LÝ SỐ BẤT THƯỜNG, ĐỊNH DẠNG CHẤM/PHẨY & GIÁ TRỊ = 0
 * ============================================================================
 */
function recoverDateSerialArea(numVal) {
  if (typeof numVal !== 'number' || isNaN(numVal)) return numVal;
  if (numVal >= 40000 && numVal <= 50000 && Math.floor(numVal) === numVal) {
    const excelEpoch = new Date(Date.UTC(1899, 11, 30));
    const dt = new Date(excelEpoch.getTime() + numVal * 86400000);
    const day = dt.getUTCDate();
    const month = dt.getUTCMonth() + 1;
    return parseFloat(day + '.' + month);
  }
  return numVal;
}

function sanitizeSingleArea(rawVal, isLowRise, isConstructionArea) {
  if (rawVal === null || rawVal === undefined || rawVal === '') return '';
  let num;
  if (typeof rawVal === 'number') {
    num = rawVal;
  } else {
    let s = String(rawVal).trim().replace(/m2|m²|m/gi, '').trim();
    s = s.replace(/^[.,-]+|[.,-]+$/g, '').trim();
    if (!s || /^(-|0|n\/a|#ref!|#value!|#error!)$/i.test(s)) return '';
    if (s.includes(',') && !s.includes('.')) {
      s = s.replace(',', '.');
    } else if (s.includes('.') && !s.includes(',')) {
      const parts = s.split('.');
      if (parts.length > 2) s = s.replace(/\./g, '');
    } else if (s.includes('.') && s.includes(',')) {
      if (s.lastIndexOf(',') > s.lastIndexOf('.')) {
        s = s.replace(/\./g, '').replace(',', '.');
      } else {
        s = s.replace(/,/g, '');
      }
    }
    num = parseFloat(s);
  }
  if (isNaN(num) || num <= 0) return '';

  num = recoverDateSerialArea(num);

  if (isLowRise) {
    const maxReasonable = isConstructionArea ? 1200 : 800;
    if (num > maxReasonable && num < 10000) {
      num = Number((num / 10).toFixed(2));
    } else if (num >= 10000) {
      num = Number((num / 100).toFixed(2));
    }
  } else {
    if (num > 600 && num < 6000) {
      num = Number((num / 10).toFixed(2));
    }
  }

  return Number(num.toFixed(2));
}

function sanitizeAndCrossCheckAreas(area1Raw, area2Raw, isLowRise, unitTypeCode) {
  let a1 = sanitizeSingleArea(area1Raw, isLowRise, false);
  let a2 = sanitizeSingleArea(area2Raw, isLowRise, true);

  if (a1 !== '' && a2 !== '') {
    if (!isLowRise) {
      if (a1 > a2) {
        const tmp = a1;
        a1 = a2;
        a2 = tmp;
      }
    } else {
      if ((unitTypeCode === 'LK' || unitTypeCode === 'SH') && a1 > 180 && a2 < 130) {
        const tmp = a1;
        a1 = a2;
        a2 = tmp;
      }
    }
  }
  return { area1: a1, area2: a2 };
}

function normalizePriceToVND(rawVal, unitHint) {
  if (rawVal === null || rawVal === undefined || rawVal === '') return '';
  if (typeof rawVal === 'number') {
    if (isNaN(rawVal) || Math.abs(rawVal) < 1e-9 || rawVal < 0) return '';
    if (unitHint === 'M2') {
      if (rawVal < 5) return '';
      if (rawVal < 1000) return Math.round(rawVal * 1e6);
      if (rawVal < 1000000) return Math.round(rawVal * 1e3);
      return Math.round(rawVal);
    }
    if (rawVal < 1.5 && unitHint !== 'VAT_KPBT') return '';
    if (rawVal < 1000) return Math.round(rawVal * 1e9);
    if (rawVal < 1000000) return Math.round(rawVal * 1e6);
    return Math.round(rawVal);
  }

  let s = String(rawVal).trim();
  if (!s || /^(0|0,0|0\.0|-|n\/a|đã bán|còn hàng|lock|check|thu|ko áp dụng|không áp dụng|#ref!|#value!|#error!|#n\/a)$/i.test(s)) {
    return '';
  }

  if (s.includes('\n')) {
    s = s.split('\n')[0].trim();
  }
  s = s.replace(/\([^)]*\)/g, '').trim();

  const isTy = /tỷ|ty/i.test(s);
  const isTr = /triệu|tr/i.test(s);

  s = s.replace(/vnđ|vnd|đồng|₫/gi, '').trim();
  s = s.replace(/^[.,-]+|[.,-]+$/g, '').trim();
  if (s.startsWith('-')) return '';

  const dotParts = s.split('.');
  if (dotParts.length === 5 && dotParts[1].length === 3 && dotParts[2].length === 3 && dotParts[3].length === 3 && dotParts[4].length <= 2) {
    s = dotParts.slice(0, 4).join('');
    const v = Math.round(parseFloat(s));
    return v > 0 ? v : '';
  }

  s = s.replace(/[^\d.,]/g, '');
  if (!s) return '';

  if ((s.match(/\./g) || []).length >= 2) {
    s = s.replace(/\./g, '').replace(',', '.');
  } else if ((s.match(/,/g) || []).length >= 2) {
    s = s.replace(/,/g, '');
  } else if (s.includes('.') && s.includes(',')) {
    if (s.lastIndexOf(',') > s.lastIndexOf('.')) s = s.replace(/\./g, '').replace(',', '.');
    else s = s.replace(/,/g, '');
  } else if (s.includes(',')) {
    const parts = s.split(',');
    if (parts[1] && parts[1].length === 3 && Number(parts[0]) > 100) s = s.replace(/,/g, '');
    else s = s.replace(',', '.');
  } else if (s.includes('.')) {
    const parts = s.split('.');
    if (parts[1] && parts[1].length === 3 && Number(parts[0]) >= 100 && unitHint !== 'TY_DECIMAL') {
      s = s.replace(/\./g, '');
    }
  }

  const num = parseFloat(s);
  if (isNaN(num) || num <= 0) return '';
  if (isTy) return Math.round(num * 1e9);
  if (isTr) return Math.round(num * 1e6);
  return normalizePriceToVND(num, unitHint);
}

/**
 * Kiểm tra chéo các cột Giá trong cùng 1 dòng (Nâng cấp V4.1):
 * - Phát hiện Đơn giá/m² (30M-350M) bị đặt nhầm vào cột Giá vay/TTTĐ/TTS (ví dụ MIK OCP Phúc Lộc: Tiến độ = 69.633.706).
 * - Phát hiện Vốn tự có 20%-30% hoặc tiền cọc (nhỏ hơn 45% Giá Full nhưng không phải lỗi thiếu 1 chữ số 10x,
 *   ví dụ Dương Kinh HDH: HTLS tự trả lãi = 2.150.305.672 khi Giá Full = 9.405.703.811, hoặc MIK OCP Vay = 450.000.000) -> Xóa bỏ.
 * - Phát hiện trường hợp đại lý không tách Giá xây (TCBG = Thô) mà copy nguyên Giá Full vào Tổng Đất -> Xóa Tổng Đất trùng lặp.
 */
function crossValidateRowPrices(rowPrices, areaForUnitPrice, isLowRise) {
  const p = Object.assign({}, rowPrices);
  const isUnitPriceScale = (val) => typeof val === 'number' && val >= 30000000 && val <= 350000000;

  ['datTrcVat', 'tongDat', 'giaTts', 'giaTttd', 'giaVay'].forEach(colKey => {
    if (isUnitPriceScale(p[colKey])) {
      if (!p.donGiaM2) p.donGiaM2 = p[colKey];
      p[colKey] = '';
    }
  });

  const mainCandidates = [p.giaFull, p.giaChuaVat, p.giaVay, p.giaTttd, p.giaTts].filter(
    v => typeof v === 'number' && v >= 1200000000
  );
  if (mainCandidates.length > 0) {
    mainCandidates.sort((a, b) => b - a);
    const anchor = mainCandidates[0];
    ['giaFull', 'giaChuaVat', 'giaVay', 'giaTttd', 'giaTts'].forEach(colKey => {
      const val = p[colKey];
      if (typeof val === 'number' && val > 0) {
        const ratio = anchor / val;
        if (ratio >= 7.0 && ratio <= 13.5) {
          // Lỗi thiếu 1 chữ số hàng tỷ (nhỏ hơn ~10 lần) -> khôi phục x10
          p[colKey] = Math.round(val * 10);
        } else if ((colKey === 'giaVay' || colKey === 'giaTttd' || colKey === 'giaTts') && ratio > 2.2) {
          // (V4.1) Giá trị < 45% Giá chuẩn (ví dụ Vốn tự có 30% = 2.15 tỷ hoặc Tiền cọc 450tr) -> loại bỏ
          p[colKey] = '';
        }
      }
    });
  }

  if (isLowRise) {
    // (V4.1) Nếu Tổng Đất == Giá Full mà không có Tổng Xây (do đại lý không tách giá đất/xây) -> xóa Tổng Đất trùng
    if (typeof p.tongDat === 'number' && typeof p.giaFull === 'number' && p.tongDat === p.giaFull && !p.tongXay) {
      p.tongDat = '';
    }
    if (typeof p.tongXay === 'number' && typeof p.tongDat === 'number' && p.tongXay > p.tongDat) {
      const tmp = p.tongXay;
      p.tongXay = p.tongDat;
      p.tongDat = tmp;
    }
    // (V4.5) Tuyệt đối không tự suy luận Tổng Đất hay Đất trc VAT từ phép trừ
  }

  // (V4.5) Chặn triệt để lỗi KPBT == Giá Full / Giá chưa VAT hoặc > 5% Giá Full
  if (typeof p.kpbt === 'number') {
    if (p.kpbt === p.giaFull || p.kpbt === p.giaChuaVat || (typeof p.giaFull === 'number' && p.kpbt > p.giaFull * 0.05) || p.kpbt > 600000000) {
      p.kpbt = '';
    }
  }

  // (V4.5) Chặn triệt để lỗi Giá chưa gồm VAT >= Giá gồm VAT & KPBT (H == K hoặc H >= K)
  if (typeof p.giaChuaVat === 'number' && typeof p.giaFull === 'number' && p.giaChuaVat >= p.giaFull) {
    if (typeof p.vatTong === 'number' && p.vatTong > 0 && typeof p.kpbt === 'number' && p.kpbt > 0 && (p.vatTong + p.kpbt) < p.giaFull * 0.25) {
      p.giaChuaVat = Math.round(p.giaFull - p.vatTong - p.kpbt);
    } else {
      p.giaChuaVat = '';
    }
  }

  if (typeof p.giaFull === 'number' && typeof areaForUnitPrice === 'number' && areaForUnitPrice > 0) {
    const calcUnitPrice = Math.round(p.giaFull / areaForUnitPrice);
    if (!p.donGiaM2 || p.donGiaM2 < 20000000 || p.donGiaM2 > 1000000000) {
      p.donGiaM2 = calcUnitPrice;
    }
  }

  Object.keys(p).forEach(k => {
    if (p[k] === 0 || p[k] === '0') p[k] = '';
  });

  return p;
}

function sanitizeFrontageAndFloors(rawFrontage, rawFloors, landArea, unitTypeCode) {
  let frontage = '';
  if (rawFrontage !== null && rawFrontage !== undefined && rawFrontage !== '') {
    const s = String(rawFrontage).trim().replace(/m$/i, '').replace(',', '.');
    const num = parseFloat(s);
    if (!isNaN(num) && num >= 3.0 && num <= 35.0) {
      frontage = Number(num.toFixed(1));
    }
  }
  // (V4.5) Tuyệt đối không tự suy luận Chiều rộng mặt tiền hay Số tầng khi nguồn để trống
  let floors = '';
  if (rawFloors !== null && rawFloors !== undefined && rawFloors !== '') {
    const s = String(rawFloors).trim().replace(/tầng|tang|t/gi, '').replace(',', '.');
    const num = parseFloat(s);
    if (!isNaN(num) && num >= 2.0 && num <= 7.0) {
      floors = Number(num.toFixed(1));
    }
  }

  return { frontage: frontage, floors: floors };
}

/**
 * ============================================================================
 * 3. XỬ LÝ DÒNG ẨN, DÒNG TÔ ĐỎ, CĂN ĐÃ BÁN / THU HÀNG & CHUẨN HÓA CSBH (V4.1)
 * ============================================================================
 */
function isRowHiddenOrRed_(sheet, rowIndex1Based, rowBgColors) {
  let isHidden = false;
  try {
    isHidden = Boolean(sheet.isRowHiddenByUser(rowIndex1Based) || sheet.isRowHiddenByFilter(rowIndex1Based));
  } catch (e) {}
  const isRed = (rowBgColors || []).some(c => {
    const hex = String(c || '').toLowerCase().trim();
    return RED_BG_COLORS.indexOf(hex) !== -1;
  });
  return { isHidden: isHidden, isRed: isRed };
}

function resolveUnitStatusWithPool_(unitKey, rawStatus, isHidden, isRed, inSoldSectionBanner, existingPoolKeySet) {
  const s = String(rawStatus || '').toLowerCase().trim();
  const isSoldText = Boolean(
    inSoldSectionBanner ||
    s.includes('đã bán') || s.includes('da ban') || s.includes('sold') ||
    s.includes('đã cọc') || s.includes('da coc') || s.includes('đã có cọc') ||
    s.includes('hết hàng') || s.includes('het hang') ||
    /^(thu|thu hàng|thu hang|thu hồi|thu hoi|đã thu)$/i.test(s)
  );
  if (existingPoolKeySet && existingPoolKeySet.has(unitKey)) {
    if (isHidden || isRed || isSoldText) return 'Đã bán';
    return (s.includes('lock') || s.includes('giữ chỗ')) ? 'Đang lock' : 'Còn hàng';
  } else {
    if (isHidden || isRed || isSoldText) return null; // Căn mới nằm trên dòng ẩn/tô đỏ/đã bán/thu hàng -> bỏ qua
    return (s.includes('lock') || s.includes('giữ chỗ')) ? 'Đang lock' : 'Còn hàng';
  }
}

/**
 * Chuẩn hóa CSBH áp dụng về dạng dd/mm/yyyy (Nâng cấp V4.1):
 * - Cắt dấu chấm thừa ở cuối ngày (ví dụ "23/12/2025." -> "23/12/2025").
 * - Không biến chuỗi "Tháng 4.2026" / "Tháng 10.2026" thành ngày 04/20/2026 sai lệch; đẩy sang Ghi chú.
 * - Mã phiên bản chính sách "V15", "V26", "V38" (Q9 Newgen) đẩy sang Ghi chú.
 */
function normalizeAndRouteCsbhField_(rawCsbh, defaultYear) {
  const yr = defaultYear || DEFAULT_POLICY_YEAR;
  if (rawCsbh instanceof Date && !isNaN(rawCsbh.getTime())) {
    const d = String(rawCsbh.getDate()).padStart(2, '0');
    const m = String(rawCsbh.getMonth() + 1).padStart(2, '0');
    const y = rawCsbh.getFullYear();
    return { csbhDate: d + '/' + m + '/' + y, extraGift: '', extraBank: '', extraNote: '' };
  }

  let s = String(rawCsbh || '').trim().replace(/\.+$/, '').trim();
  if (!s) return { csbhDate: '', extraGift: '', extraBank: '', extraNote: '' };

  // (V4.1) Nếu là chuỗi "Tháng 4.2026" / "Tháng 10/2026" hoặc mã "V15", "V26", "V38" -> chuyển sang Ghi chú
  if (/^(tháng|thang)\s*\d{1,2}[\/.\-]\d{2,4}$/i.test(s) || /^V\d{1,3}$/i.test(s)) {
    return { csbhDate: '', extraGift: '', extraBank: '', extraNote: 'CSBH ' + s };
  }

  // 1. Có ngày đầy đủ dd/mm/yyyy hoặc dd.mm.yyyy hoặc dd-mm-yyyy
  const mFull = s.match(/(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{2,4})/);
  if (mFull) {
    const d = parseInt(mFull[1], 10);
    const m = parseInt(mFull[2], 10);
    let y = parseInt(mFull[3], 10);
    if (y < 100) y += 2000;
    if (d >= 1 && d <= 31 && m >= 1 && m <= 12) {
      return {
        csbhDate: String(d).padStart(2, '0') + '/' + String(m).padStart(2, '0') + '/' + String(y),
        extraGift: '',
        extraBank: '',
        extraNote: ''
      };
    }
  }

  // 2. Có ngày ngắn dd/mm hoặc d/m (không chứa dấu % và không đứng sau chữ "Tháng")
  if (!/\d+\s*%/.test(s) && !/(tháng|thang)\s*\d/i.test(s)) {
    const mShort = s.match(/(?:^|\b)(\d{1,2})[\/.\-](\d{1,2})(?:\b|$)/);
    if (mShort) {
      const d = parseInt(mShort[1], 10);
      const m = parseInt(mShort[2], 10);
      if (d >= 1 && d <= 31 && m >= 1 && m <= 12) {
        return {
          csbhDate: String(d).padStart(2, '0') + '/' + String(m).padStart(2, '0') + '/' + String(yr),
          extraGift: '',
          extraBank: '',
          extraNote: ''
        };
      }
    }
  }

  // 3. Nếu là mã Quà tặng / Chiết khấu
  if (/(VOS|QUÀ|QUA TANG|CHIẾT KHẤU|CK\s*\d|VOUCHER|CÂY VÀNG|LƯỢNG VÀNG)/i.test(s)) {
    return { csbhDate: '', extraGift: s, extraBank: '', extraNote: '' };
  }

  // 4. Nếu là mã Ngân hàng (MBV, VBCN, VCB, BIDV, TCB, VPB, MBB...)
  if (/(MBV|VBCN|VIETCOMBANK|VCB|TECHCOMBANK|TCB|BIDV|VIETINBANK|CTG|VPBANK|MBBANK|ACB|TPBANK|HDBANK)/i.test(s)) {
    return { csbhDate: '', extraGift: '', extraBank: s, extraNote: '' };
  }

  return { csbhDate: '', extraGift: '', extraBank: '', extraNote: s };
}

/**
 * ============================================================================
 * 4. BÓC TÁCH HYPERLINK ẨN / SMART CHIP & TỰ SỬA LINK DRIVE LỖI (V4.1)
 * ============================================================================
 */
function repairMalformedDriveUrl_(rawUrl) {
  if (!rawUrl) return '';
  let s = String(rawUrl).trim();
  // (V4.1) Sửa lỗi thiếu dấu chấm ở domain (ví dụ QLG VRI: https://drivegooglecom/drive/...)
  s = s.replace(/^https?:\/\/drivegooglecom\//i, 'https://drive.google.com/');
  s = s.replace(/^https?:\/\/docsgooglecom\//i, 'https://docs.google.com/');
  return s;
}

function extractCellUrls(displayVal, richTextVal, formulaVal) {
  const urls = [];
  const addUrl = (u) => {
    if (!u) return;
    const clean = repairMalformedDriveUrl_(u);
    if (/^https?:\/\//i.test(clean) && !urls.includes(clean)) {
      urls.push(clean);
    }
  };

  if (formulaVal && /^=\s*HYPERLINK/i.test(formulaVal)) {
    const match = formulaVal.match(/HYPERLINK\s*\(\s*["']([^"']+)["']/i);
    if (match && match[1]) addUrl(match[1]);
  }

  if (richTextVal) {
    try {
      const wholeLink = richTextVal.getLinkUrl();
      if (wholeLink) addUrl(wholeLink);
      const runs = richTextVal.getRuns();
      if (runs && runs.length > 0) {
        for (let i = 0; i < runs.length; i++) {
          const runUrl = runs[i].getLinkUrl();
          if (runUrl) addUrl(runUrl);
        }
      }
    } catch (e) {}
  }

  if (displayVal) {
    const repairedDisplay = repairMalformedDriveUrl_(displayVal);
    const rawMatches = String(repairedDisplay).match(/https?:\/\/[^\s;"',<>]+/gi);
    if (rawMatches) rawMatches.forEach(addUrl);
  }

  return urls;
}

function parseDriveUrl(url) {
  if (!url) return { type: 'NONE', id: null, url: '' };
  const s = repairMalformedDriveUrl_(url);
  const folderMatch = s.match(/\/folders\/([a-zA-Z0-9_-]{15,})/);
  if (folderMatch) return { type: 'FOLDER', id: folderMatch[1], url: s };
  const sheetMatch = s.match(/\/spreadsheets\/d\/([a-zA-Z0-9_-]{15,})/);
  if (sheetMatch) return { type: 'SHEET_FILE', id: sheetMatch[1], url: s };
  const fileMatch = s.match(/\/file\/d\/([a-zA-Z0-9_-]{15,})/);
  if (fileMatch) return { type: 'FILE', id: fileMatch[1], url: s };
  const openMatch = s.match(/[?&]id=([a-zA-Z0-9_-]{15,})/);
  if (openMatch) return { type: 'OPEN_ID', id: openMatch[1], url: s };
  return { type: 'OTHER_URL', id: null, url: s };
}

function classifyDriveFile(fileName, mimeType) {
  const nameUpper = String(fileName || '').toUpperCase();
  const mimeLower = String(mimeType || '').toLowerCase();
  const isPtgKeyword = /(PTG|PHIẾU TÍNH GIÁ|PHIEU TINH GIA|BẢNG TÍNH|BANG TINH|TÍNH GIÁ|TINH GIA|CSBH|TIẾN ĐỘ|TIEN DO|VAY|TTS|TTTĐ|TTTD)/i.test(nameUpper);
  const isLayoutKeyword = /(CHỈ CĂN|CHI CAN|PCC|VẼ CĂN|VE CAN|MẶT BẰNG|MAT BANG|LAYOUT|MB|VỊ TRÍ|VI TRI|SƠ ĐỒ|SO DO|ẢNH CĂN|ANH CAN|CLIP|VIDEO)/i.test(nameUpper);
  const isSpreadsheetOrPdfOrDoc = mimeLower.includes('spreadsheet') || mimeLower.includes('excel') || mimeLower.includes('pdf') || /\.(xlsx|xls|pdf|csv)$/i.test(nameUpper);
  const isImageOrVideo = mimeLower.includes('image/') || mimeLower.includes('video/') || /\.(jpg|jpeg|png|webp|gif|bmp|mp4|mov)$/i.test(nameUpper);

  if (isPtgKeyword && !isLayoutKeyword) return 'PTG';
  if (isLayoutKeyword && !isPtgKeyword) return 'CHI_CAN';
  if (isSpreadsheetOrPdfOrDoc && !isImageOrVideo) return 'PTG';
  if (isImageOrVideo) return 'CHI_CAN';
  return 'BOTH';
}

function expandDriveFolderAndClassify(folderId, unitCode, fallbackFolderUrl) {
  const cacheKey = folderId + '__' + String(unitCode || '').toUpperCase();
  if (DRIVE_FOLDER_CACHE[cacheKey]) return DRIVE_FOLDER_CACHE[cacheKey];

  const result = { chiCanUrls: [], ptgUrls: [], allFileUrls: [] };
  try {
    const folder = DriveApp.getFolderById(folderId);
    const cleanUnit = String(unitCode || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '');

    const collectFilesFromFolder = (targetFolder, filterByUnit) => {
      const files = targetFolder.getFiles();
      while (files.hasNext()) {
        const f = files.next();
        const fName = f.getName();
        const fMime = f.getMimeType();
        const fUrl = f.getUrl();
        if (filterByUnit && cleanUnit.length >= 3) {
          const cleanFileName = fName.toUpperCase().replace(/[^A-Z0-9]/g, '');
          if (!cleanFileName.includes(cleanUnit)) continue;
        }
        result.allFileUrls.push(fUrl);
        const category = classifyDriveFile(fName, fMime);
        if (category === 'CHI_CAN') result.chiCanUrls.push(fUrl);
        else if (category === 'PTG') result.ptgUrls.push(fUrl);
        else {
          result.chiCanUrls.push(fUrl);
          result.ptgUrls.push(fUrl);
        }
      }
    };

    collectFilesFromFolder(folder, false);
    const subFolders = folder.getFolders();
    while (subFolders.hasNext()) {
      const sub = subFolders.next();
      const subName = sub.getName().toUpperCase();
      const cleanSubName = subName.replace(/[^A-Z0-9]/g, '');
      if (/(PTG|PHIẾU TÍNH GIÁ|PHIEU TINH GIA)/i.test(subName)) {
        const subFiles = sub.getFiles();
        while (subFiles.hasNext()) {
          const sfUrl = subFiles.next().getUrl();
          result.allFileUrls.push(sfUrl);
          result.ptgUrls.push(sfUrl);
        }
      } else if (/(CHỈ CĂN|CHI CAN|MẶT BẰNG|MAT BANG|LAYOUT|VẼ CĂN)/i.test(subName)) {
        const subFiles = sub.getFiles();
        while (subFiles.hasNext()) {
          const sfUrl = subFiles.next().getUrl();
          result.allFileUrls.push(sfUrl);
          result.chiCanUrls.push(sfUrl);
        }
      } else if (cleanUnit.length >= 3 && cleanSubName.includes(cleanUnit)) {
        collectFilesFromFolder(sub, false);
      }
    }

    if (result.chiCanUrls.length === 0 && result.allFileUrls.length > 0) result.chiCanUrls = result.allFileUrls.slice();
    if (result.ptgUrls.length === 0 && result.allFileUrls.length > 0) result.ptgUrls = result.allFileUrls.slice();
  } catch (err) {
    try {
      const file = DriveApp.getFileById(folderId);
      const fUrl = file.getUrl();
      const cat = classifyDriveFile(file.getName(), file.getMimeType());
      result.allFileUrls.push(fUrl);
      if (cat === 'PTG') result.ptgUrls.push(fUrl);
      else if (cat === 'CHI_CAN') result.chiCanUrls.push(fUrl);
      else {
        result.chiCanUrls.push(fUrl);
        result.ptgUrls.push(fUrl);
      }
    } catch (e2) {
      if (fallbackFolderUrl && /^https?:\/\//i.test(fallbackFolderUrl)) {
        result.chiCanUrls.push(fallbackFolderUrl);
        result.ptgUrls.push(fallbackFolderUrl);
      }
    }
  }

  DRIVE_FOLDER_CACHE[cacheKey] = result;
  return result;
}

function resolveUnitMediaAndPtgLinks(unitCode, unitColUrls, chiCanColUrls, ptgColUrls) {
  const finalChiCan = [];
  const finalPtg = [];
  const addUnique = (arr, item) => {
    const repaired = repairMalformedDriveUrl_(item);
    if (repaired && /^https?:\/\//i.test(repaired) && !arr.includes(repaired)) {
      arr.push(repaired);
    }
  };

  const processUrl = (rawUrl, sourceRole) => {
    const cleanUrl = repairMalformedDriveUrl_(rawUrl);
    if (!cleanUrl || !/^https?:\/\//i.test(cleanUrl)) return;
    const parsed = parseDriveUrl(cleanUrl);
    if ((parsed.type === 'FOLDER' || parsed.type === 'OPEN_ID') && EXPAND_DRIVE_FOLDERS_DEEP) {
      const expanded = expandDriveFolderAndClassify(parsed.id, unitCode, cleanUrl);
      if (sourceRole === 'CHI_CAN_COL') {
        (expanded.chiCanUrls.length > 0 ? expanded.chiCanUrls : [cleanUrl]).forEach(u => addUnique(finalChiCan, u));
      } else if (sourceRole === 'PTG_COL') {
        (expanded.ptgUrls.length > 0 ? expanded.ptgUrls : [cleanUrl]).forEach(u => addUnique(finalPtg, u));
        if (expanded.chiCanUrls.length > 0) expanded.chiCanUrls.forEach(u => addUnique(finalChiCan, u));
      } else {
        (expanded.chiCanUrls.length > 0 ? expanded.chiCanUrls : [cleanUrl]).forEach(u => addUnique(finalChiCan, u));
        (expanded.ptgUrls.length > 0 ? expanded.ptgUrls : [cleanUrl]).forEach(u => addUnique(finalPtg, u));
      }
    } else if (parsed.type === 'SHEET_FILE') {
      addUnique(finalPtg, cleanUrl);
    } else if (parsed.type === 'FILE' || parsed.type === 'OTHER_URL') {
      if (sourceRole === 'CHI_CAN_COL') addUnique(finalChiCan, cleanUrl);
      else if (sourceRole === 'PTG_COL') addUnique(finalPtg, cleanUrl);
      else {
        addUnique(finalChiCan, cleanUrl);
        addUnique(finalPtg, cleanUrl);
      }
    }
  };

  (chiCanColUrls || []).forEach(u => processUrl(u, 'CHI_CAN_COL'));
  (ptgColUrls || []).forEach(u => processUrl(u, 'PTG_COL'));
  (unitColUrls || []).forEach(u => processUrl(u, 'UNIT_COL'));

  return {
    anhChiCan: finalChiCan.join(' ; '),
    anhPtg: finalPtg.join(' ; ')
  };
}

/**
 * ============================================================================
 * 5. CHUẨN HÓA LOẠI HÌNH, PHÂN KHU, LỌC TAB RÁC & NHẬN DIỆN HEADER ĐỘNG (V4.1)
 * ============================================================================
 */
function normalizeLowRiseType(rawVal, rawTcbgVal) {
  let s = String(rawVal || '').trim().toUpperCase();
  const tcbg = String(rawTcbgVal || '').trim().toUpperCase();
  if ((s === 'LIỀN KỀ' || s === 'LK') && tcbg.includes('SONG LẬP')) {
    return 'BTSL';
  }
  if (!s) return '';
  if (s.includes('SONG LẬP') && s.includes('SHOP')) return 'BTSL';
  if (s.includes('LIỀN KỀ') && s.includes('SHOP')) return 'SH';
  if (s.includes('ĐƠN LẬP') || s === 'ĐL' || s === 'DL' || s === 'BTĐL' || s === 'BTDL') return 'BTĐL';
  if (s.includes('SONG LẬP') || s === 'SL' || s === 'BTSL') return 'BTSL';
  if (s.includes('TỨ LẬP') || s === 'TL' || s === 'BTTL') return 'BTTL';
  if (s.includes('SHOPHOUSE') || s === 'SH' || s.includes('NHÀ PHỐ') || s === 'SHOP') return 'SH';
  if (s.includes('TMDV') || s.includes('THƯƠNG MẠI')) return 'TMDV';
  if (s.includes('LIỀN KỀ') || s.includes('LIỀN KỀ') || s === 'LK') return 'LK';
  return s;
}

function normalizeHighRiseType(rawVal) {
  let s = String(rawVal || '').trim().toUpperCase();
  if (!s) return '';
  s = s.replace(/BR/g, 'PN').replace(/\s+/g, '');
  if (s.includes('STUDIO') || s === 'STU') return 'STUDIO';
  if (s.includes('PENTHOUSE') || s === 'PEN') return 'PENTHOUSE';
  if (s.includes('DUPLEX') || s === 'DUP') return 'DUPLEX';
  if (/^1PN\+1MR|1PN\+1/.test(s)) return s.includes('MR') ? '1PN+1MR' : '1PN+';
  if (/^2PN\+1MR|2PN\+1/.test(s)) return s.includes('MR') ? '2PN+1MR' : '2PN+';
  if (/^3PN\+1MR|3PN\+1/.test(s)) return s.includes('MR') ? '3PN+1MR' : '3PN+';
  return s;
}

function sanitizeUnitCodeV45_(rawCode) {
  let s = String(rawCode || '').trim().toUpperCase();
  s = s.replace(/[✨🔥💥💎⭐🌟⚡📌📍🎯🏷️✅❌⚠️]/g, '');
  s = s.replace(/\*+/g, '');
  s = s.split(':')[0].split('(')[0].trim();
  s = s.replace(/\s+(GÓC|GOC|XẺ KHE|XE KHE|THƯỜNG|THUONG)$/i, '').trim();
  s = s.replace(/\s+/g, '').replace(/^[-._]+|[-._]+$/g, '');
  return s;
}

function normalizeZoneName(rawZone, projectKey, unitCode, sheetName) {
  const u = sanitizeUnitCodeV45_(unitCode);
  const pk = String(projectKey || '').toLowerCase();
  // (V4.5) Ánh xạ Phân khu chuẩn theo Từ điển Tiền tố Mã căn (tuyệt đối không lấy tên tab quản lý Giỏ Độc quyền, HÀNG ĐQ, QĐQ...)
  if (pk.includes('làng vân')) {
    if (/^(VM)/i.test(u)) return 'Vịnh Mây';
    if (/^(BV|ĐLHV|DLHV|TK|VK|VU)/i.test(u)) return 'Bạch Vân';
    return 'Đảo Ngọc';
  }
  if (pk.includes('dương kinh')) {
    if (/^(TH|ĐLSB|DLSB)/i.test(u)) return 'Thiên Hà';
    if (/^(MT|ĐLHH|DLHH)/i.test(u)) return 'Mặt Trời';
    if (/^(BM)/i.test(u)) return 'Bình Minh';
    return 'Ánh Sao';
  }
  if (pk.includes('hlx')) {
    if (/^(BM|VBM)/i.test(u)) return 'Vịnh Bình Minh';
    return 'Thiên Đường Nhiệt Đới';
  }
  if (pk.includes('đan phượng')) {
    if (/^(BM)/i.test(u)) return 'Bình Minh';
    if (/^(TĐ|TD)/i.test(u)) return 'Thời Đại';
    return 'Hừng Đông';
  }
  if (pk.includes('tràng cát')) {
    return 'Thịnh Vượng';
  }
  if (pk.includes('cần giờ')) {
    if (/^(VN|ĐLCH|DLCH)/i.test(u)) return 'Vịnh Ngọc';
    if (/^(VT)/i.test(u)) return 'Vịnh Tiên';
    return 'Vịnh Sóng Xanh';
  }
  if (pk.includes('hóc môn')) {
    if (/^(AS|TL)/i.test(u)) return 'Công Viên Tri Thức';
    return 'Công Viên Quốc Tế';
  }
  let z = String(rawZone || '').trim();
  if (/(độc quyền|doc quyen|hàng đq|hang dq|qđq|qdq|quỹ|quy|giỏ|gio|check|bảng hàng|bang hang|mới|moi)/i.test(z)) {
    z = '';
  }
  return z;
}

/**
 * (V4.1) Kiểm tra xem 1 tab có phải là tab thông số / lưu trữ / sai loại hình dự án hay không
 */
function shouldSkipAgencyTab_(sheet, isLowRise) {
  if (!sheet) return true;
  const tabName = String(sheet.getName() || '').trim();
  if (NON_INVENTORY_TAB_REGEX.test(tabName)) return true;
  if (isLowRise && /(cao tầng|cao tang|chung cư|chung cu|noxh|happy home)/i.test(tabName)) return true;
  if (!isLowRise && /(thấp tầng|thap tang|biệt thự|biet thu|liền kề|lien ke|vịnh tiên|vinh tien)/i.test(tabName)) return true;
  return false;
}

function mapColumnsFromHeaderRow_(headerCells) {
  const headers = headerCells.map(v => String(v || '').toLowerCase().replace(/\s+/g, ' ').trim());
  const colMap = {};
  const findCol = (regexList) => {
    for (let i = 0; i < regexList.length; i++) {
      const rx = regexList[i];
      for (let c = 0; c < headers.length; c++) {
        if (rx.test(headers[c])) return c;
      }
    }
    return -1;
  };

  colMap.stt        = findCol([/^stt$/]);
  colMap.unitCode   = findCol([/^(mã căn|ma can|mã sp|ký hiệu căn|mã căn hộ|căn số)$/, /(mã căn|ma can|ký hiệu)/]);
  colMap.zone       = findCol([/(phân khu|phan khu|khu|tiểu khu|đường|duong)/]);
  colMap.unitType   = findCol([/(loại hình|loai hinh|loại căn|loai can|loại bđs)/]);
  colMap.tcbg       = findCol([/(tcbg|tiêu chuẩn bàn giao|bàn giao)/]);
  colMap.direction  = findCol([/^(hướng|huong|hướng cửa|hướng ban công)$/, /(hướng|huong)/]);
  colMap.tower      = findCol([/^(tòa|tên tòa|toa|block)$/, /(tên tòa|tòa)/]);
  colMap.floor      = findCol([/^(tầng|tang)$/, /(tầng|tang)/]);
  colMap.axis       = findCol([/(trục|mã trục|căn số)/]);
  colMap.landArea   = findCol([/(dt đất|diện tích đất|dt dat|diện tích lô đất|dtđ)/, /^(diện tích|dt)$/]);
  colMap.buildArea  = findCol([/(dtxd|dt xây dựng|diện tích xây dựng|tổng dtsxd|dt sàn)/]);
  colMap.netArea    = findCol([/(thông thủy|thong thuy|dt thông thủy|diện tích thông thủy)/, /^(diện tích|dt)$/]);
  colMap.grossArea  = findCol([/(tim tường|tim tuong|dt tim tường|diện tích tim tường)/]);
  colMap.bedrooms   = findCol([/(số pn|phòng ngủ|so phong ngu)/]);
  colMap.wc         = findCol([/(số wc|wc)/]);
  colMap.frontage   = findCol([/(mặt tiền|mat tien|rộng mặt tiền)/]);
  colMap.floors     = findCol([/(số tầng|so tang|tầng cao)/]);
  colMap.giaChuaVat = findCol([/(chưa gồm vat|chưa vat|trước vat|giá gốc chưa vat)/]);
  colMap.vatTong    = findCol([/^vat(\s*\(tổng\))?$/, /tiền vat/]);
  colMap.kpbt       = findCol([/^(kpbt|kinh phí bảo trì|kpbt\s*\(tổng\)|kinh phí bảo trì\s*\(kpbt\))$/, /^(?!.*(giá|tổng cộng|chưa gồm|gồm vat)).*(kpbt|kinh phí bảo trì)/]);
  colMap.giaFull    = findCol([/(gồm vat|giá full|tổng giá|giá niêm yết|giá bán gồm vat)/, /^(giá bán|giá|tổng giá)$/]);
  colMap.giaVay     = findCol([/(giá vay|vay nh|htls 18|htls 24|htls 30|htls|vay 70)/]);
  colMap.giaTttd    = findCol([/(tiến độ|tttđ|tttd|thanh toán chuẩn|tt chuẩn)/]);
  colMap.giaTts     = findCol([/(thanh toán sớm|tts|tt sớm|không vay)/]);
  colMap.donGiaM2   = findCol([/(đơn giá|don gia|giá\/m2|giá \/ m)/]);
  colMap.gift       = findCol([/(quà tặng|qua tang|ưu đãi|chiết khấu)/]);
  colMap.desc       = findCol([/(mô tả|mo ta|view|vị trí)/]);
  colMap.csbh       = findCol([/(csbh|chính sách)/]);
  colMap.bank       = findCol([/(ngân hàng|ngan hang|bank)/]);
  colMap.note       = findCol([/(ghi chú|ghi chu|note)/]);
  colMap.status     = findCol([/(trạng thái|trang thai|tình trạng)/]);
  colMap.fundGroup  = findCol([/(nhóm quỹ|nhom quy|loại quỹ|nguồn quỹ|độc quyền|^quỹ$)/]);
  colMap.chiCan     = findCol([/(ảnh chỉ căn|chỉ căn|mặt bằng|layout|hình ảnh|link ảnh)/]);
  colMap.ptg        = findCol([/(phiếu tính giá|ptg|bảng tính|file tính giá|link ptg|tài liệu)/]);
  colMap.issueDate  = findCol([/(ngày cấp|ngay cap|ngày vào hàng|ngày cập nhật)/]);

  return colMap;
}

/**
 * Tự động nhận diện dòng tiêu đề (Header Row) và ánh xạ chỉ số cột (0-based)
 */
function detectHeaderAndMapColumns_(values) {
  const maxScan = Math.min(values.length, 25);
  let bestRow = -1;
  let bestScore = 0;

  for (let r = 0; r < maxScan; r++) {
    const rowStr = values[r].map(v => String(v || '').toLowerCase().trim()).join(' | ');
    let score = 0;
    if (/(mã căn|ma can|mã sp|ký hiệu|căn số)/i.test(rowStr)) score += 4;
    if (/(diện tích|dien tich|dt đất|dtđ|dt thông thủy|dtxd)/i.test(rowStr)) score += 3;
    if (/(giá|gia ban|tổng giá|giá full|giá vay|tts)/i.test(rowStr)) score += 3;
    if (/(phân khu|phan khu|loại hình|hướng|tòa|tầng)/i.test(rowStr)) score += 2;
    if (score > bestScore) {
      bestScore = score;
      bestRow = r;
    }
  }

  if (bestRow === -1 || bestScore < 4) return null;
  const colMap = mapColumnsFromHeaderRow_(values[bestRow]);
  return { headerRowIndex: bestRow, colMap: colMap };
}

/**
 * (V4.1) Nhận diện dòng tiêu đề phụ xuất hiện ở giữa sheet (ví dụ bảng Five Star Tràng Cát ghép 2 bảng dọc)
 */
function isMidSheetHeaderRow_(rowCells) {
  const rowStr = (rowCells || []).map(v => String(v || '').toLowerCase().trim()).join(' | ');
  return /(mã căn|ma can)/i.test(rowStr) && /(dtđ|dtxd|diện tích|tổng giá|giá full|hướng)/i.test(rowStr);
}

/**
 * ============================================================================
 * 6. ĐỌC DANH SÁCH LINK ĐẠI LÝ TỪ FILE MASTER & ĐỒNG BỘ TỰ ĐỘNG 12 DỰ ÁN
 * ============================================================================
 */
function parseSpreadsheetUrlAndGid_(rawUrl) {
  if (!rawUrl) return null;
  const s = repairMalformedDriveUrl_(rawUrl);
  if (!s.includes('docs.google.com/spreadsheets')) return null;
  const idMatch = s.match(/\/spreadsheets\/(?:u\/\d+\/)?d\/([a-zA-Z0-9_-]{15,})/);
  if (!idMatch) return null;
  const gidMatch = s.match(/[?#&]gid=(\d+)/);
  return {
    spreadsheetId: idMatch[1],
    gid: gidMatch ? parseInt(gidMatch[1], 10) : null,
    url: s
  };
}

/**
 * (V4.1) Lấy danh sách các Sheet cần quét cho 1 link đại lý:
 * - Nếu link có gid cụ thể: lấy đúng tab theo gid; đồng thời nếu file có các tab Quỹ Độc Quyền tách theo phân khu
 *   (ví dụ "ĐQ BẠCH VÂN", "ĐQ ĐẢO NGỌC", "ĐQ GOLFLAND") thì quét bổ sung các tab hợp lệ đó và bỏ qua tab thông số/lưu trữ.
 */
function getSheetsToScanForLink_(spreadsheet, gid, isLowRise) {
  const allSheets = spreadsheet.getSheets();
  const result = [];
  const addedIds = new Set();

  const addSheetIfValid = (sh) => {
    if (!sh) return;
    const sid = sh.getSheetId();
    if (addedIds.has(sid)) return;
    if (shouldSkipAgencyTab_(sh, isLowRise)) return;
    addedIds.add(sid);
    result.push(sh);
  };

  if (gid !== null && gid !== undefined) {
    for (let i = 0; i < allSheets.length; i++) {
      if (allSheets[i].getSheetId() === gid) {
        addSheetIfValid(allSheets[i]);
        break;
      }
    }
  }

  if (result.length === 0 && allSheets.length > 0) {
    addSheetIfValid(allSheets[0]);
  }

  return result;
}

function readExistingTargetPool_(targetSheet, isLowRise) {
  const existingKeys = new Set();
  const existingRowsByKey = {};
  const lastRow = targetSheet.getLastRow();
  const lastCol = targetSheet.getLastColumn();
  if (lastRow < 2 || lastCol < 5) {
    return { existingKeys: existingKeys, existingRowsByKey: existingRowsByKey };
  }

  const data = targetSheet.getRange(2, 1, lastRow - 1, lastCol).getDisplayValues();
  for (let i = 0; i < data.length; i++) {
    const row = data[i];
    const unitCode = String(isLowRise ? row[2] : row[1] || '').trim().toUpperCase();
    const zone = String(isLowRise ? row[1] : row[2] || '').trim().toUpperCase();
    if (!unitCode) continue;
    const key = sanitizeUnitCodeV45_(unitCode);
    existingKeys.add(key);
    existingRowsByKey[key] = {
      rowArray: row,
      unitCode: unitCode,
      zone: zone,
      agency: String(isLowRise ? row[35] : row[29] || '').trim(),
      issueDate: String(isLowRise ? row[36] : row[30] || '').trim(),
      status: String(isLowRise ? row[31] : row[27] || '').trim(),
      fundGroup: String(isLowRise ? row[32] : row[28] || '').trim()
    };
  }
  return { existingKeys: existingKeys, existingRowsByKey: existingRowsByKey };
}

function writeNormalizedRowsToSheet(sheet, headers, rows, isLowRise) {
  sheet.clearContents();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  if (!rows || rows.length === 0) return;

  if (!isLowRise) {
    [2, 6, 7, 8, 11, 23, 31].forEach(colIdx => {
      sheet.getRange(2, colIdx, rows.length, 1).setNumberFormat('@');
    });
    sheet.getRange(2, 9, rows.length, 2).setNumberFormat('#,##0.##');
    sheet.getRange(2, 13, rows.length, 7).setNumberFormat('#,##0');
  } else {
    [3, 29, 37].forEach(colIdx => {
      sheet.getRange(2, colIdx, rows.length, 1).setNumberFormat('@');
    });
    sheet.getRange(2, 6, rows.length, 2).setNumberFormat('#,##0.##');
    sheet.getRange(2, 8, rows.length, 16).setNumberFormat('#,##0');
    sheet.getRange(2, 25, rows.length, 2).setNumberFormat('#,##0.##');
  }

  sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
}

/**
 * Quét 1 tab bảng hàng của đại lý và áp dụng toàn bộ quy tắc chuẩn hóa V4.1
 */
function scanAgencySheetWithV4Rules_(agencySheet, agencyName, projectKey, isLowRise, existingPoolKeys, todayStr) {
  if (shouldSkipAgencyTab_(agencySheet, isLowRise)) return [];

  const lastRow = Math.min(agencySheet.getLastRow(), 1200);
  const lastCol = Math.min(agencySheet.getLastColumn(), 45);
  if (lastRow < 2 || lastCol < 3) return [];

  const range = agencySheet.getRange(1, 1, lastRow, lastCol);
  const rawValues = range.getValues();
  const displayValues = range.getDisplayValues();
  const formulas = range.getFormulas();
  const backgrounds = range.getBackgrounds();
  let richTexts = null;
  try {
    richTexts = range.getRichTextValues();
  } catch (e) {}

  const detected = detectHeaderAndMapColumns_(displayValues);
  if (!detected || detected.colMap.unitCode === -1) return [];

  const hIdx = detected.headerRowIndex;
  let cm = detected.colMap;

  // (V4.1) Kiểm tra tương thích Thấp tầng vs Cao tầng (tránh trộn bảng NOXH Happy Home Tràng Cát vào Thấp tầng)
  if (isLowRise && cm.bedrooms !== -1 && cm.landArea === -1) {
    return [];
  }

  const scannedUnits = [];
  let inSoldSectionBanner = false;

  for (let r = hIdx + 1; r < lastRow; r++) {
    const row1Based = r + 1;
    const rowTextJoined = displayValues[r].map(v => String(v || '').trim()).join(' ');

    // (V4.1) Kiểm tra nếu gặp dòng tiêu đề phụ ở giữa sheet (như Five Star Tràng Cát) -> cập nhật lại colMap
    if (isMidSheetHeaderRow_(displayValues[r])) {
      const newMap = mapColumnsFromHeaderRow_(displayValues[r]);
      if (newMap.unitCode !== -1) {
        cm = newMap;
      }
      continue;
    }

    // (V4.1) Kiểm tra dòng phân nhóm "ĐÃ BÁN" / "ĐANG BÁN"
    if (/^\s*(đã bán|da ban|căn đã bán)\s*$/i.test(rowTextJoined)) {
      inSoldSectionBanner = true;
      continue;
    }
    if (/^\s*(đang bán|dang ban|còn hàng|bảng hàng)\s*$/i.test(rowTextJoined)) {
      inSoldSectionBanner = false;
      continue;
    }

    const rawUnitVal = displayValues[r][cm.unitCode];
    if (!rawUnitVal || String(rawUnitVal).trim().length < 2) continue;
    const rawUnitStr = String(rawUnitVal).trim();
    if (/^(stt|mã căn|tổng|ghi chú|chú thích|bảng hàng|đang bán|đã bán)/i.test(rawUnitStr)) continue;

    let rawZone = cm.zone !== -1 ? displayValues[r][cm.zone] : '';
    let unitCode = sanitizeUnitCodeV45_(rawUnitStr);
    if (!unitCode || unitCode.length < 2 || /^(PHÂNKHU|PHANKHU|ĐLMC|DLMC)$/i.test(unitCode)) continue;
    let tower = cm.tower !== -1 ? displayValues[r][cm.tower] : '';
    let floor = cm.floor !== -1 ? displayValues[r][cm.floor] : '';
    let axis  = cm.axis !== -1 ? displayValues[r][cm.axis] : '';

    if (!isLowRise) {
      const normHR = normalizeHighRiseUnitFloorAxis(unitCode, tower, floor, axis);
      unitCode = normHR.unitCode;
      tower = normHR.tower;
      floor = normHR.floor;
      axis = normHR.axis;
    }

    const zone = normalizeZoneName(rawZone, projectKey, unitCode, agencySheet.getName());
    const unitKey = unitCode;

    // Quy tắc 1 & 2 (V4.1): Kiểm tra dòng ẩn, nền đỏ, banner ĐÃ BÁN, trạng thái Đã có cọc / Thu hàng
    const rowState = isRowHiddenOrRed_(agencySheet, row1Based, backgrounds[r]);
    const rawStatus = cm.status !== -1 ? displayValues[r][cm.status] : '';
    const rawNoteForStatus = cm.note !== -1 ? displayValues[r][cm.note] : '';
    const combinedStatusSignal = String(rawStatus || '') + ' ' + String(rawNoteForStatus || '');
    const resolvedStatus = resolveUnitStatusWithPool_(
      unitKey,
      combinedStatusSignal,
      rowState.isHidden,
      rowState.isRed,
      inSoldSectionBanner,
      existingPoolKeys
    );
    if (resolvedStatus === null) {
      continue;
    }

    // Quy tắc 5 (V4.1): Bóc tách URL thực từ Smart Chip / Hyperlink & sửa lỗi URL thiếu dấu chấm
    const getUrlsAt = (colIdx) => {
      if (colIdx === -1) return [];
      return extractCellUrls(
        displayValues[r][colIdx],
        richTexts ? richTexts[r][colIdx] : null,
        formulas[r][colIdx]
      );
    };
    const unitUrls = getUrlsAt(cm.unitCode);
    const chiCanUrls = getUrlsAt(cm.chiCan);
    const ptgUrls = getUrlsAt(cm.ptg);
    const mediaLinks = resolveUnitMediaAndPtgLinks(unitCode, unitUrls, chiCanUrls, ptgUrls);

    // Quy tắc 6 (V4.1): Chuẩn hóa CSBH áp dụng về dd/mm/yyyy & điều hướng mã V15/V26/Tháng 4.2026
    const rawCsbh = cm.csbh !== -1 ? rawValues[r][cm.csbh] : '';
    const csbhRouted = normalizeAndRouteCsbhField_(rawCsbh, DEFAULT_POLICY_YEAR);

    let gift = cm.gift !== -1 ? String(displayValues[r][cm.gift] || '').trim() : '';
    let bank = cm.bank !== -1 ? String(displayValues[r][cm.bank] || '').trim() : '';
    let note = cm.note !== -1 ? String(displayValues[r][cm.note] || '').trim() : '';
    if (csbhRouted.extraGift && !gift.includes(csbhRouted.extraGift)) {
      gift = gift ? (gift + ' ; ' + csbhRouted.extraGift) : csbhRouted.extraGift;
    }
    if (csbhRouted.extraBank && !bank.includes(csbhRouted.extraBank)) {
      bank = bank ? (bank + ' ; ' + csbhRouted.extraBank) : csbhRouted.extraBank;
    }
    if (csbhRouted.extraNote && !note.includes(csbhRouted.extraNote)) {
      note = note ? (note + ' ; ' + csbhRouted.extraNote) : csbhRouted.extraNote;
    }

    // (V4.1) Nhận diện mã Quỹ riêng "QR" / "ĐQ" ở cả cột STT, cột Nhóm quỹ và tên Sheet
    const rawSttStr = cm.stt !== -1 ? String(displayValues[r][cm.stt] || '').trim() : '';
    const rawFund = cm.fundGroup !== -1 ? String(displayValues[r][cm.fundGroup] || '').trim() : '';
    const combinedFundSignal = rawSttStr + ' ' + rawFund + ' ' + agencySheet.getName();
    const isExclusive = /(độc quyền|doc quyen|\bđq\b|\bdq\b|\bqr\b|quỹ riêng|quy rieng)/i.test(combinedFundSignal);
    const fundGroup = isExclusive ? 'Độc quyền' : 'Quỹ chung';

    // Nếu cột Nhóm quỹ chứa thông tin HĐMB / VBCN / Ngân hàng (như VHM-BIO, VBCN-BIOCARE-TCB) -> chuyển sang Ngân hàng / Ghi chú
    if (rawFund && /(vbcn|hđmb|hdmb|tcb|vcb|bidv|mbv)/i.test(rawFund) && !note.includes(rawFund)) {
      note = note ? (note + ' ; ' + rawFund) : rawFund;
    }

    const rawIssueDate = cm.issueDate !== -1 ? rawValues[r][cm.issueDate] : '';
    const issueRouted = normalizeAndRouteCsbhField_(rawIssueDate, DEFAULT_POLICY_YEAR);
    const issueDate = issueRouted.csbhDate || '';

    if (isLowRise) {
      const rawTcbg = cm.tcbg !== -1 ? String(displayValues[r][cm.tcbg] || '').trim() : '';
      const rawType = cm.unitType !== -1 ? displayValues[r][cm.unitType] : '';
      const unitType = normalizeLowRiseType(rawType, rawTcbg);
      const areas = sanitizeAndCrossCheckAreas(
        cm.landArea !== -1 ? rawValues[r][cm.landArea] : '',
        cm.buildArea !== -1 ? rawValues[r][cm.buildArea] : '',
        true,
        unitType
      );
      const prices = crossValidateRowPrices({
        giaChuaVat: cm.giaChuaVat !== -1 ? normalizePriceToVND(rawValues[r][cm.giaChuaVat], 'TOTAL') : '',
        vatTong:    cm.vatTong !== -1 ? normalizePriceToVND(rawValues[r][cm.vatTong], 'VAT_KPBT') : '',
        kpbt:       cm.kpbt !== -1 ? normalizePriceToVND(rawValues[r][cm.kpbt], 'VAT_KPBT') : '',
        giaFull:    cm.giaFull !== -1 ? normalizePriceToVND(rawValues[r][cm.giaFull], 'TOTAL') : '',
        xayTrcVat:  '', vatXay: '', kpbtXay: '', tongXay: '',
        datTrcVat:  '', vatDat: '', kpbtDat: '', tongDat: '',
        donGiaM2:   cm.donGiaM2 !== -1 ? normalizePriceToVND(rawValues[r][cm.donGiaM2], 'M2') : '',
        giaVay:     cm.giaVay !== -1 ? normalizePriceToVND(rawValues[r][cm.giaVay], 'TOTAL') : '',
        giaTttd:    cm.giaTttd !== -1 ? normalizePriceToVND(rawValues[r][cm.giaTttd], 'TOTAL') : '',
        giaTts:     cm.giaTts !== -1 ? normalizePriceToVND(rawValues[r][cm.giaTts], 'TOTAL') : ''
      }, areas.area1, true);

      const ff = sanitizeFrontageAndFloors(
        cm.frontage !== -1 ? rawValues[r][cm.frontage] : '',
        cm.floors !== -1 ? rawValues[r][cm.floors] : '',
        areas.area1,
        unitType
      );

      scannedUnits.push({
        unitKey: unitKey,
        isExclusive: isExclusive,
        status: resolvedStatus,
        issueDate: issueDate,
        rowValues: [
          0, zone, unitCode, rawTcbg, unitType, areas.area1, areas.area2,
          prices.giaChuaVat, prices.vatTong, prices.kpbt, prices.giaFull,
          prices.xayTrcVat, prices.vatXay, prices.kpbtXay, prices.tongXay,
          prices.datTrcVat, prices.vatDat, prices.kpbtDat, prices.tongDat,
          prices.donGiaM2, prices.giaVay, prices.giaTttd, prices.giaTts,
          cm.direction !== -1 ? String(displayValues[r][cm.direction] || '').trim() : '',
          ff.frontage, ff.floors, gift,
          cm.desc !== -1 ? String(displayValues[r][cm.desc] || '').trim() : '',
          csbhRouted.csbhDate, bank, note,
          resolvedStatus, fundGroup,
          mediaLinks.anhChiCan, mediaLinks.anhPtg,
          agencyName, issueDate || todayStr
        ]
      });
    } else {
      const rawType = cm.unitType !== -1 ? displayValues[r][cm.unitType] : '';
      const unitType = normalizeHighRiseType(rawType);
      const areas = sanitizeAndCrossCheckAreas(
        cm.netArea !== -1 ? rawValues[r][cm.netArea] : '',
        cm.grossArea !== -1 ? rawValues[r][cm.grossArea] : '',
        false,
        unitType
      );
      const prices = crossValidateRowPrices({
        kpbt:       cm.kpbt !== -1 ? normalizePriceToVND(rawValues[r][cm.kpbt], 'VAT_KPBT') : '',
        giaChuaVat: cm.giaChuaVat !== -1 ? normalizePriceToVND(rawValues[r][cm.giaChuaVat], 'TOTAL') : '',
        giaFull:    cm.giaFull !== -1 ? normalizePriceToVND(rawValues[r][cm.giaFull], 'TOTAL') : '',
        giaVay:     cm.giaVay !== -1 ? normalizePriceToVND(rawValues[r][cm.giaVay], 'TOTAL') : '',
        giaTttd:    cm.giaTttd !== -1 ? normalizePriceToVND(rawValues[r][cm.giaTttd], 'TOTAL') : '',
        giaTts:     cm.giaTts !== -1 ? normalizePriceToVND(rawValues[r][cm.giaTts], 'TOTAL') : '',
        donGiaM2:   cm.donGiaM2 !== -1 ? normalizePriceToVND(rawValues[r][cm.donGiaM2], 'M2') : ''
      }, areas.area1, false);

      scannedUnits.push({
        unitKey: unitKey,
        isExclusive: isExclusive,
        status: resolvedStatus,
        issueDate: issueDate,
        rowValues: [
          0, unitCode, zone, unitType,
          cm.direction !== -1 ? String(displayValues[r][cm.direction] || '').trim() : '',
          tower, floor, axis, areas.area1, areas.area2,
          cm.bedrooms !== -1 ? String(displayValues[r][cm.bedrooms] || '').trim() : '',
          cm.wc !== -1 ? normalizeNumericOrNull_(rawValues[r][cm.wc], false) : '',
          prices.kpbt, prices.giaChuaVat, prices.giaFull,
          prices.giaVay, prices.giaTttd, prices.giaTts, prices.donGiaM2,
          cm.tcbg !== -1 ? String(displayValues[r][cm.tcbg] || '').trim() : '',
          gift,
          cm.desc !== -1 ? String(displayValues[r][cm.desc] || '').trim() : '',
          csbhRouted.csbhDate, bank,
          mediaLinks.anhChiCan, mediaLinks.anhPtg,
          note, resolvedStatus, fundGroup,
          agencyName, issueDate || todayStr
        ]
      });
    }
  }

  return scannedUnits;
}

function normalizeNumericOrNull_(val, isIntegerPrice) {
  if (val === null || val === undefined || val === '') return '';
  let num = (typeof val === 'number') ? val : parseFloat(String(val).replace(/\./g, '').replace(',', '.'));
  if (isNaN(num) || Math.abs(num) < 1e-9) return '';
  return isIntegerPrice ? Math.round(num) : Math.round(num * 100) / 100;
}

function deduplicateAndMergePool_(scannedList, existingRowsByKey, isLowRise, todayStr) {
  const bestByKey = {};
  const countFilledPrices = (row) => {
    const start = isLowRise ? 7 : 12;
    const end = isLowRise ? 22 : 18;
    let cnt = 0;
    for (let i = start; i <= end; i++) {
      if (row[i] !== '' && row[i] !== null && row[i] !== undefined) cnt++;
    }
    return cnt;
  };

  for (let i = 0; i < scannedList.length; i++) {
    const item = scannedList[i];
    const key = item.unitKey;
    if (!bestByKey[key]) {
      bestByKey[key] = item;
    } else {
      const cur = bestByKey[key];
      if (item.status === 'Đã bán') {
        cur.status = 'Đã bán';
        cur.rowValues[isLowRise ? 31 : 27] = 'Đã bán';
      }
      if (item.isExclusive && !cur.isExclusive) {
        if (cur.status === 'Đã bán') item.rowValues[isLowRise ? 31 : 27] = 'Đã bán';
        bestByKey[key] = item;
      } else if (item.isExclusive === cur.isExclusive) {
        if (countFilledPrices(item.rowValues) > countFilledPrices(cur.rowValues)) {
          if (cur.status === 'Đã bán') item.rowValues[isLowRise ? 31 : 27] = 'Đã bán';
          bestByKey[key] = item;
        }
      }
    }
  }

  const finalRows = [];
  const keys = Object.keys(bestByKey);
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    const row = bestByKey[k].rowValues.slice();
    const issueColIdx = isLowRise ? 36 : 30;
    if (!bestByKey[k].issueDate && existingRowsByKey[k] && existingRowsByKey[k].issueDate) {
      row[issueColIdx] = existingRowsByKey[k].issueDate;
    } else if (!row[issueColIdx]) {
      row[issueColIdx] = todayStr;
    }
    row[0] = i + 1;
    finalRows.push(row);
  }

  return finalRows;
}

function showToast_(msg, title, timeoutSec) {
  try {
    const activeSs = SpreadsheetApp.getActiveSpreadsheet();
    if (activeSs) {
      activeSs.toast(msg, title || '⚡ Đồng Bộ 12 Dự Án (v4.5)', timeoutSec || 5);
    }
  } catch (e) {}
}

/**
 * Lấy danh sách nguồn đại lý cho 1 dự án:
 * - Kết hợp danh sách nhúng sẵn EMBEDDED_MASTER_LINKS (419 link từ file .xlsx gốc)
 * - Tự động đọc bổ sung từ tab "Danh mục Link Đại lý" trong chính file Google Sheet dự án (nếu bạn thêm link mới vào tab này)
 * - Nếu file dự án chưa có tab "Danh mục Link Đại lý", tự động khởi tạo tab này để bạn dễ quản lý link ngay trên Google Sheet!
 */
function getProjectAgencyLinkList_(projectKey, targetSs, subTabFilter) {
  const combined = [];
  const seen = new Set();

  const addEntry = (agency, fileId, gid, url, sub) => {
    if (!agency || !fileId) return;
    if (subTabFilter && sub && String(sub).toUpperCase() !== String(subTabFilter).toUpperCase()) return;
    const key = String(agency).toUpperCase() + '__' + fileId + '__' + String(gid !== null && gid !== undefined ? gid : '') + '__' + String(sub || '');
    if (seen.has(key)) return;
    seen.add(key);
    combined.push({
      agency: String(agency).trim(),
      fileId: fileId,
      gid: (gid !== null && gid !== undefined && gid !== '') ? parseInt(gid, 10) : null,
      url: url,
      sub: sub || null
    });
  };

  // 1. Đọc trực tiếp từ file Google Sheet Master mới (1pYfZPbHwmhQzusYdupjoLo-EP280isvo2Pza-6Z22wo)
  try {
    const masterSs = SpreadsheetApp.openById(MASTER_LINK_SHEET_ID);
    const masterTab = masterSs.getSheetByName(projectKey);
    if (masterTab && masterTab.getLastRow() >= 2) {
      const mRange = masterTab.getDataRange();
      const mDisplay = mRange.getDisplayValues();
      const mFormulas = mRange.getFormulas();
      let mRich = null;
      try { mRich = mRange.getRichTextValues(); } catch (e) {}

      if (projectKey === 'MAS CAO TẦNG') {
        const subTabs = ['MGC', 'MEL', 'HSG', 'LEP'];
        for (let r = 1; r < mDisplay.length; r++) {
          const agencyName = String(mDisplay[r][1] || '').trim();
          if (!agencyName) continue;
          for (let sIdx = 0; sIdx < subTabs.length; sIdx++) {
            const sName = subTabs[sIdx];
            if (subTabFilter && sName !== subTabFilter) continue;
            const cIdx = 2 + sIdx;
            const cellUrls = extractCellUrls(mDisplay[r][cIdx], mRich ? mRich[r][cIdx] : null, mFormulas[r][cIdx]);
            const rawParts = String(mDisplay[r][cIdx] || '').split(';').concat(cellUrls);
            for (let p = 0; p < rawParts.length; p++) {
              const parsed = parseSpreadsheetUrlAndGid_(rawParts[p]);
              if (parsed) addEntry(agencyName, parsed.spreadsheetId, parsed.gid, parsed.url, sName);
            }
          }
        }
      } else {
        for (let r = 1; r < mDisplay.length; r++) {
          const agencyName = String(mDisplay[r][1] || '').trim();
          if (!agencyName) continue;
          const cellUrls = extractCellUrls(mDisplay[r][2], mRich ? mRich[r][2] : null, mFormulas[r][2]);
          const rawParts = String(mDisplay[r][2] || '').split(';').concat(cellUrls);
          for (let p = 0; p < rawParts.length; p++) {
            const parsed = parseSpreadsheetUrlAndGid_(rawParts[p]);
            if (parsed) addEntry(agencyName, parsed.spreadsheetId, parsed.gid, parsed.url, null);
          }
        }
      }
    }
  } catch (e) {
    Logger.log('Lỗi đọc Master Sheet: ' + e.message);
  }

  // 2. Đọc từ tab "Danh mục Link Đại lý" trong file dự án đích (nếu có)
  let linkSheet = targetSs.getSheetByName('Danh mục Link Đại lý');
  if (linkSheet && linkSheet.getLastRow() >= 2) {
    const linkData = linkSheet.getDataRange().getDisplayValues();
    for (let r = 1; r < linkData.length; r++) {
      const agencyName = String(linkData[r][1] || '').trim();
      const rawLinks = String(linkData[r][2] || '').trim();
      if (!agencyName || !rawLinks) continue;
      const parts = rawLinks.split(';');
      for (let p = 0; p < parts.length; p++) {
        const parsed = parseSpreadsheetUrlAndGid_(parts[p]);
        if (parsed) {
          addEntry(agencyName, parsed.spreadsheetId, parsed.gid, parsed.url, subTabFilter || null);
        }
      }
    }
  }

  // 2. Bổ sung từ EMBEDDED_MASTER_LINKS (toàn bộ 419 link chuẩn từ file Excel Master)
  const embeddedList = EMBEDDED_MASTER_LINKS[projectKey] || [];
  for (let i = 0; i < embeddedList.length; i++) {
    const item = embeddedList[i];
    addEntry(item.agency, item.file_id, item.gid, item.url, item.sub);
  }

  // 3. Nếu file đích chưa có tab "Danh mục Link Đại lý", tự động tạo tab này để bạn tiện theo dõi/thêm link
  if (!linkSheet && combined.length > 0 && !subTabFilter) {
    try {
      linkSheet = targetSs.insertSheet('Danh mục Link Đại lý');
      const rowsOut = [['STT', 'TÊN ĐẠI LÝ', 'LINK BẢNG HÀNG', 'TRẠNG THÁI']];
      for (let i = 0; i < combined.length; i++) {
        rowsOut.push([i + 1, combined[i].agency, combined[i].url, 'Đang hoạt động']);
      }
      linkSheet.getRange(1, 1, rowsOut.length, 4).setValues(rowsOut);
    } catch (e) {}
  }

  return combined;
}

function syncSingleProject(projectKey) {
  const config = TARGET_PROJECT_FILES[projectKey];
  if (!config) throw new Error('Không tìm thấy cấu hình dự án: ' + projectKey);

  const now = new Date();
  const todayStr = String(now.getDate()).padStart(2, '0') + '/' +
                   String(now.getMonth() + 1).padStart(2, '0') + '/' +
                   now.getFullYear();

  showToast_('Đang mở bảng hàng đích: ' + config.name + '...', '🚀 Bắt đầu đồng bộ', 5);
  const targetSs = SpreadsheetApp.openById(config.id);
  const isLowRise = config.type === 'LOW_RISE';
  const headers = isLowRise ? LOW_RISE_HEADERS : HIGH_RISE_HEADERS;

  if (projectKey === 'MAS CAO TẦNG' && config.tabs) {
    let totalMasUnits = 0;
    config.tabs.forEach((subTabName) => {
      let targetSheet = targetSs.getSheetByName(subTabName);
      if (!targetSheet) targetSheet = targetSs.insertSheet(subTabName);

      const existingPool = readExistingTargetPool_(targetSheet, false);
      const agencyLinks = getProjectAgencyLinkList_(projectKey, targetSs, subTabName);
      const allScanned = [];

      for (let i = 0; i < agencyLinks.length; i++) {
        const entry = agencyLinks[i];
        showToast_(
          '[' + subTabName + '] Đang quét (' + (i + 1) + '/' + agencyLinks.length + '): ' + entry.agency,
          '⚡ ' + config.name,
          4
        );
        try {
          const agencySs = SpreadsheetApp.openById(entry.fileId);
          const sheetsToScan = getSheetsToScanForLink_(agencySs, entry.gid, false);
          sheetsToScan.forEach(agencySheet => {
            const units = scanAgencySheetWithV4Rules_(
              agencySheet,
              entry.agency,
              projectKey,
              false,
              existingPool.existingKeys,
              todayStr
            );
            units.forEach(u => allScanned.push(u));
          });
        } catch (err) {
          Logger.log('Bỏ qua link không truy cập được (' + entry.agency + ' - ' + subTabName + '): ' + err.message);
        }
      }

      if (allScanned.length > 0) {
        const mergedRows = deduplicateAndMergePool_(allScanned, existingPool.existingRowsByKey, false, todayStr);
        writeNormalizedRowsToSheet(targetSheet, headers, mergedRows, false);
        totalMasUnits += mergedRows.length;
      }
    });
    showToast_('Đã cập nhật thành công ' + totalMasUnits + ' căn trên 4 tab (MGC, MEL, HSG, LEP)!', '✅ Hoàn tất ' + config.name, 8);
  } else {
    let targetSheet = targetSs.getSheetByName('Bảng hàng chuẩn hóa') || targetSs.getSheets()[0];
    const existingPool = readExistingTargetPool_(targetSheet, isLowRise);
    const agencyLinks = getProjectAgencyLinkList_(projectKey, targetSs, null);
    const allScanned = [];

    for (let i = 0; i < agencyLinks.length; i++) {
      const entry = agencyLinks[i];
      showToast_(
        'Đang quét nguồn [' + (i + 1) + '/' + agencyLinks.length + ']: ' + entry.agency,
        '⚡ ' + config.name,
        4
      );
      try {
        const agencySs = SpreadsheetApp.openById(entry.fileId);
        const sheetsToScan = getSheetsToScanForLink_(agencySs, entry.gid, isLowRise);
        sheetsToScan.forEach(agencySheet => {
          const units = scanAgencySheetWithV4Rules_(
            agencySheet,
            entry.agency,
            projectKey,
            isLowRise,
            existingPool.existingKeys,
            todayStr
          );
          units.forEach(u => allScanned.push(u));
        });
      } catch (err) {
        Logger.log('Bỏ qua link không truy cập được (' + entry.agency + ' - ' + projectKey + '): ' + err.message);
      }
    }

    if (allScanned.length > 0) {
      const mergedRows = deduplicateAndMergePool_(allScanned, existingPool.existingRowsByKey, isLowRise, todayStr);
      writeNormalizedRowsToSheet(targetSheet, headers, mergedRows, isLowRise);
      showToast_('Đã chuẩn hóa & cập nhật xong ' + mergedRows.length + ' căn!', '✅ Hoàn tất ' + config.name, 8);
    } else {
      showToast_('Không tìm thấy căn mới từ các nguồn truy cập được.', 'ℹ️ ' + config.name, 6);
    }
  }
}

/**
 * (V4.3) Cơ chế Smart Round-Robin & Auto-Continuation:
 * Vì Google Apps Script giới hạn tối đa 6 phút / lần chạy, nếu quét cả 12 dự án (419 link) trong 1 lượt
 * thì tập lệnh sẽ chỉ chạy xong Dự án số 1 (Làng Vân) rồi bị ngắt thời gian.
 * Hàm dưới đây tự động lưu vị trí dự án vừa chạy xong vào PropertiesService (NEXT_PROJECT_INDEX),
 * khi thời gian chạy đạt 3 phút 45 giây (225.000 ms) sẽ tự động lưu trạng thái và đặt Trigger chạy tiếp
 * sau 1 phút cho các dự án tiếp theo (VRI -> MIK OCP -> Dương Kinh -> ... -> OCP2-3) cho đến khi hết 12 dự án!
 */
function clearContinuationTriggers_() {
  const triggers = ScriptApp.getProjectTriggers();
  for (let i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'continueSyncRemainingProjects') {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

function continueSyncRemainingProjects() {
  clearContinuationTriggers_();
  syncAll12Projects();
}

function syncAll12Projects() {
  const startTime = Date.now();
  const MAX_EXECUTION_MS = 225000; // 3 phút 45 giây (an toàn tuyệt đối dưới ngưỡng 6 phút của Google)
  const props = PropertiesService.getScriptProperties();
  const keys = Object.keys(TARGET_PROJECT_FILES);
  let startIdx = parseInt(props.getProperty('NEXT_PROJECT_INDEX') || '0', 10);
  if (isNaN(startIdx) || startIdx < 0 || startIdx >= keys.length) {
    startIdx = 0;
  }

  for (let i = startIdx; i < keys.length; i++) {
    const projectKey = keys[i];
    try {
      Logger.log('Đang đồng bộ dự án [' + (i + 1) + '/' + keys.length + ']: ' + projectKey);
      syncSingleProject(projectKey);
    } catch (e) {
      Logger.log('Lỗi khi đồng bộ dự án ' + projectKey + ': ' + e.message);
    }

    // Lưu ngay chỉ số dự án tiếp theo sau khi hoàn thành mỗi dự án
    if (i + 1 < keys.length) {
      props.setProperty('NEXT_PROJECT_INDEX', String(i + 1));
      if (Date.now() - startTime >= MAX_EXECUTION_MS) {
        clearContinuationTriggers_();
        ScriptApp.newTrigger('continueSyncRemainingProjects')
          .timeBased()
          .after(60 * 1000)
          .create();
        const nextName = TARGET_PROJECT_FILES[keys[i + 1]].name;
        showToast_(
          'Đã chạy xong dự án [' + (i + 1) + '/12]. Hệ thống tự động chạy tiếp ' + nextName + ' sau 1 phút để tránh giới hạn 6 phút của Google!',
          '⏳ Tự động nối tiếp (v4.3)',
          10
        );
        Logger.log('Tạm dừng an toàn ở dự án số ' + (i + 1) + ', đã hẹn Trigger chạy tiếp dự án ' + keys[i + 1] + ' sau 1 phút.');
        return;
      }
    } else {
      props.setProperty('NEXT_PROJECT_INDEX', '0');
    }
  }

  clearContinuationTriggers_();
  props.setProperty('NEXT_PROJECT_INDEX', '0');
  showToast_('Đã hoàn tất đồng bộ trọn vẹn cả 12/12 dự án theo chuẩn v4.3!', '🎉 Hoàn tất 12 Dự Án', 10);
  Logger.log('HOÀN TẤT ĐỒNG BỘ TOÀN BỘ 12 DỰ ÁN THEO CHUẨN V4.3!');
}