"""
Module cấu hình toàn bộ hệ thống đồng bộ 12 dự án bất động sản.
"""

# ID của file Google Trang tính Master tổng hợp (chứa 12 tab dự án và tab "Bàng hàng")
MASTER_SPREADSHEET_ID = '1rd1aDyUO8Vu1mL8q8OSQtJ4AgJ3kBg2j'
LOW_RISE_TEMPLATE_GID = '904198174'

# Năm mặc định áp dụng cho chính sách bán hàng (CSBH) khi nguồn chỉ điền ngày/tháng
DEFAULT_POLICY_YEAR = 2026

# Cấu hình danh mục 12 dự án đích cần đồng bộ
TARGET_PROJECTS = {
    'làng vân': {
        'id': '1G7kWbKI1q8O_r2i5eeNCyAhPjr62EIYRIeXp1n4FZBI',
        'type': 'LOW_RISE',
        'name': 'Dự án Làng Vân'
    },
    'VRI': {
        'id': '1fLHY2nvP4pLXDFrY0GMfLLTpOHORhnZ5JePVxqh8kfU',
        'type': 'LOW_RISE',
        'name': 'Dự án VRI'
    },
    'MIK OCP': {
        'id': '1NhlYJU_eyv4AXYGY3YhJ2RESe32u7QhSevajFXX5b-c',
        'type': 'HIGH_RISE',
        'name': 'Dự án MIK OCP'
    },
    'DƯƠNG KINH': {
        'id': '1Xx2PSzX6LzYkiBeu9qM3cK5u2p_BjjVjSktR1_AIt7Q',
        'type': 'LOW_RISE',
        'name': 'Dự án Dương Kinh'
    },
    'HLX': {
        'id': '1TAkltHR0O6bvCdJ5s8LY1Ystq95eSuFXyLMscQ5xGJM',
        'type': 'LOW_RISE',
        'name': 'Dự án HLX'
    },
    'Đan phượng': {
        'id': '1VGF3Joh39qIT4hwpjNT_YETsCUoFmBdUsAQvhncbkC4',
        'type': 'LOW_RISE',
        'name': 'Dự án Đan Phượng'
    },
    'TRÀNG CÁT': {
        'id': '1lPCZGx2ngtFQkL7KBZkQDfVEQHUog91Fr8qfWsLVIlk',
        'type': 'LOW_RISE',
        'name': 'Dự án Tràng Cát'
    },
    'Cần giờ': {
        'id': '1yt1aiAt8ONkU1YKzHoO2zAjB-Oujne0tR3hbYOt2qQc',
        'type': 'LOW_RISE',
        'name': 'Dự án Cần Giờ'
    },
    'Hóc Môn': {
        'id': '1YzUhxCEqm47yxP7SOpuA8kktflQEAbvNkWIn5UxIM0U',
        'type': 'LOW_RISE',
        'name': 'Dự án Hóc Môn'
    },
    'Q9': {
        'id': '1HTcHXvk9gKZdE2fGGIkL4utSHZ-as5zZC0FxN2GVlYI',
        'type': 'HIGH_RISE',
        'name': 'Dự án Q9'
    },
    'MAS CAO TẦNG': {
        'id': '1fV1_ZKQXVzsrdMa8ElSpVu-32cj4vPTzgftN81sDynM',
        'type': 'HIGH_RISE',
        'name': 'Dự án MAS - Cao tầng',
        'sub_tabs': ['MGC', 'MEL', 'HSG', 'LEP']
    },
    'OCP2-3': {
        'id': '1LtzwcF6xP-ZdfuNoschNN3-LhbP1fuHqsiA_ad75jJQ',
        'type': 'LOW_RISE',
        'name': 'Dự án OCP2-3'
    }
}

# Tiêu chuẩn 39 cột chuẩn Thấp tầng (36 cột gốc + Cột 37 Đại lý, Cột 38 Ngày cấp hàng, Cột 39 Hạn cấp hàng)
LOW_RISE_HEADERS = [
    'STT', 'Phân khu', 'Mã căn', 'TCBG', 'Loại hình', 'Diện tích đất', 'Diện tích xây dựng',
    'Giá chưa gồm VAT', 'VAT', 'KPBT', 'Giá gồm VAT và KPBT',
    'Xây trc VAT', 'VAT', 'KPBT', 'Tổng Xây',
    'Đất trc VAT', 'VAT', 'KPBT', 'Tổng Đất',
    'Đơn giá / m²', 'Giá vay', 'Giá thanh toán theo tiến độ', 'Giá thanh toán sớm',
    'Hướng', 'Chiều rộng mặt tiền', 'Số tầng', 'Quà tặng', 'Mô tả', 'CSBH áp dụng',
    'Ngân hàng hỗ trợ giải ngân', 'Ghi chú', 'Trạng thái', 'Nhóm quỹ',
    'Ảnh chỉ căn', 'Ảnh phiếu tính giá', 'Ẩnh chỉ căn+ PTG',
    'Đại lý', 'Ngày cấp hàng', 'Hạn cấp hàng (Còn lại)'
]

# Tiêu chuẩn 32 cột chuẩn Cao tầng (30 cột gốc + Cột 31 Ngày cấp hàng, Cột 32 Hạn cấp hàng)
HIGH_RISE_HEADERS = [
    'STT', 'Mã căn', 'Phân khu', 'Loại hình', 'Hướng', 'Tên tòa', 'Tầng', 'Mã trục căn',
    'Diện tích thông thủy', 'Diện tích tim tường', 'Số phòng ngủ', 'Số WC',
    'KPBT (kinh phí bảo trì)', 'Giá chưa gồm VAT + KPBT', 'Giá niêm yết Gồm VAT + KPBT',
    'Giá vay', 'Giá thanh toán theo tiến độ', 'Giá thanh toán sớm', 'Đơn giá / m²',
    'Tiêu chuẩn bàn giao', 'Quà tặng', 'Mô tả', 'CSBH áp dụng',
    'Ngân hàng hỗ trợ giải ngân', 'Ảnh chỉ căn', 'Ảnh phiếu tính giá',
    'Ghi chú', 'Trạng thái', 'Nhóm quỹ', 'Đại lý', 'Ngày cấp hàng',
    'Hạn cấp hàng (Còn lại)'
]

# Danh sách mã màu đỏ thể hiện căn Đã bán / Thu hàng
RED_HEX_CODES = {
    '#ff0000', '#ea4335', '#e06666', '#f4cccc',
    '#cc0000', '#990000', '#ea9999', '#d9534f',
    '#ff3333', '#ff4d4d', '#ff6666', '#ff9999', '#fce8e6'
}

# Regex nhận diện tab rác / tab thông số không phải bảng hàng
NON_INVENTORY_TAB_REGEX = (
    r'(stk|tài khoản|tai khoan|giỏ bank|gio bank|đầu mối|dau moi|thông số|thong so|'
    r'giải chấp|giai chap|bàn giao|ban giao|csbh|đã bán|da ban|check ẩn|check an|'
    r'quỹ ẩn|quy an|quỹ cũ|quy cu|lưu|game|tạo tk|quy định|quy dinh|hướng dẫn|huong dan|'
    r'^\s*xd\b|dtxd|kỹ thuật|ky thuat)'
)
