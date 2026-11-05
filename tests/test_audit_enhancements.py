from decimal import Decimal
import pytest

from src.normalizer import (
    sanitize_unit_code,
    normalize_direction,
    normalize_low_rise_type,
    normalize_high_rise_type,
    sanitize_and_cross_validate_prices
)
from src.db_writer import map_merged_row_to_db_record
from src.config import LOW_RISE_HEADERS, HIGH_RISE_HEADERS


class TestUnitCodeSanitization:
    def test_junk_announcements_rejected(self):
        junk_samples = [
            "QUỸ THÔ + GIÃN XÂY ( CỌC 200 TRIỆU/ 1 CĂN )",
            "• Số tiền cọc: 300.000.000 VNĐ/căn",
            "QUỸ HOÀN THIỆN ( CỌC 300 TRIỆU/ CĂN )",
            "THIÊNĐƯỜNGNHIỆTĐỚI1",
            "VỊNHBÌNHMINH1",
            "THÔKHÔNGTHANGXÂYSAU1,5NĂM",
            "BẢNG HÀNG ĐỘC QUYỀN",
            "THÔNG BÁO CHÍNH SÁCH MỚI",
        ]
        for s in junk_samples:
            assert sanitize_unit_code(s) == "", f"Expected '{s}' to be rejected"

    def test_extract_real_code_from_dirty_cells(self):
        assert sanitize_unit_code("TĐX20-12, Có cam kết tiền thuê 6%/năm") == "TĐX20-12"
        assert sanitize_unit_code("AS4-49 Căn góc 3 mặt tiền (Có cam kết tiền thuê 6%/năm, trong 5 năm)") == "AS4-49"
        assert sanitize_unit_code("Mã căn: LK-01") == "LK-01"

    def test_uppercase_normalization(self):
        assert sanitize_unit_code("p5.3x11") == "P5.3X11"
        assert sanitize_unit_code("vx2-0x") == "VX2-0X"
        assert sanitize_unit_code("tđ48-1x") == "TĐ48-1X"
        assert sanitize_unit_code("bx-206") == "BX-206"


class TestDirectionNormalization:
    def test_reject_numeric_strings_and_prices(self):
        dirty_numbers = [
            "6.388.998.545",
            "3,556,911,558",
            "24.773",
            "0",
            "46,3",
            "100.000.000",
            "4.187.063.388",
        ]
        for d in dirty_numbers:
            assert normalize_direction(d) == "", f"Expected '{d}' to be rejected as direction"

    def test_valid_directions_normalized(self):
        assert normalize_direction("ĐB") == "ĐB"
        assert normalize_direction("Đông Bắc") == "ĐB"
        assert normalize_direction("Đông Nam") == "ĐN"
        assert normalize_direction("Tây Bắc") == "TB"
        assert normalize_direction("Tây Nam") == "TN"
        assert normalize_direction("Đông Bắc - Đông Nam") == "ĐB-ĐN"
        assert normalize_direction("ĐB-ĐN") == "ĐB-ĐN"
        assert normalize_direction("Hướng Cửa Tây") == "Tây"
        assert normalize_direction("Ban công Nam") == "Nam"


class TestTypeNormalization:
    def test_low_rise_types_canonical(self):
        assert normalize_low_rise_type("LIÊN KẾ") == "LK"
        assert normalize_low_rise_type("Liền kề") == "LK"
        assert normalize_low_rise_type("Liền Kề") == "LK"
        assert normalize_low_rise_type("Biệt thự Song lập") == "BTSL"
        assert normalize_low_rise_type("Song lập") == "BTSL"
        assert normalize_low_rise_type("Biệt thự Đơn lập") == "BTĐL"
        assert normalize_low_rise_type("Đơn lập") == "BTĐL"
        assert normalize_low_rise_type("Shophouse") == "SH"
        assert normalize_low_rise_type("Nhà phố") == "SH"
        assert normalize_low_rise_type("TMDV") == "TMDV"
        assert normalize_low_rise_type("Tứ lập") == "BTTL"

    def test_high_rise_types_canonical(self):
        assert normalize_high_rise_type("1 Phòng ngủ+") == "1PN+"
        assert normalize_high_rise_type("1 Phòng ngủ") == "1PN"
        assert normalize_high_rise_type("2 Phòng ngủ+") == "2PN+"
        assert normalize_high_rise_type("2 Phòng ngủ") == "2PN"
        assert normalize_high_rise_type("3 Phòng ngủ") == "3PN"
        assert normalize_high_rise_type("Studio") == "STUDIO"
        assert normalize_high_rise_type("STUDIO") == "STUDIO"
        assert normalize_high_rise_type("1PN+1") == "1PN+"
        assert normalize_high_rise_type("2BR+1") == "2PN+"
        assert normalize_high_rise_type("Duplex") == "DUPLEX"
        assert normalize_high_rise_type("Penthouse") == "PENTHOUSE"


class TestPricingCrossValidation:
    def test_user_rule_no_vat_preserves_total_price(self):
        # User instruction: "Trường hợp không có VAT: giữ nguyên giá tổng"
        tot, prev, dg = sanitize_and_cross_validate_prices(
            total_price=25_000_000_000,
            price_before_vat=None,
            don_gia_m2=None
        )
        assert tot == 25_000_000_000
        assert prev is None

    def test_column_drift_detection(self):
        # Pre-VAT is 47.17 tỷ, but total is 238 triệu (don_gia_m2 misallocated into total)
        tot, prev, dg = sanitize_and_cross_validate_prices(
            total_price=238_259_733,
            price_before_vat=47_172_998_726,
            don_gia_m2=None
        )
        assert tot is None
        assert prev == 47_172_998_726
        assert dg == 238_259_733

    def test_outlier_price_rejected(self):
        tot, prev, dg = sanitize_and_cross_validate_prices(
            total_price=852_135,
            price_before_vat=None,
            don_gia_m2=None
        )
        assert tot is None


class TestSubdivisionResolutionInDbWriter:
    def test_canonical_subdivision_resolution(self):
        row = [""] * len(LOW_RISE_HEADERS)
        row[1] = "KĐAS"
        row[2] = "KĐ7-105"
        row[7] = 26_000_000_000
        row[10] = 29_360_000_000

        mock_catalog = {
            ("vinhomes-ocean-park-3", "kdas"): {
                "id": "6542d904-9f3f-4e0c-898a-8be52c041333",
                "code": "KINH-DO-ANH-SANG",
                "canonical_name": "Kinh Đô Ánh Sáng",
                "tour_id": "vinhomes-ocean-park-3"
            }
        }

        rec = map_merged_row_to_db_record(
            row=row,
            project_key="OCP2-3",
            is_low_rise=True,
            subdivision_catalog=mock_catalog
        )

        assert rec is not None
        assert rec["product_code"] == "KĐ7-105"
        assert rec["subdivision_id"] == "6542d904-9f3f-4e0c-898a-8be52c041333"
        assert rec["subdivision_code"] == "KINH-DO-ANH-SANG"
        assert rec["subdivision_name"] == "Kinh Đô Ánh Sáng"
        assert rec["subdivision_resolution_status"] == "resolved"

    def test_high_rise_area_swap(self):
        row = [""] * len(HIGH_RISE_HEADERS)
        row[1] = "P5.3111"
        row[2] = "The Wave"
        row[3] = "2 Phòng ngủ"
        row[4] = "Đông Bắc"
        row[8] = 75.0  # net_area (thông thủy) mistakenly > gross_area
        row[9] = 68.0  # gross_area (tim tường) mistakenly < net_area
        row[14] = 5_000_000_000

        rec = map_merged_row_to_db_record(
            row=row,
            project_key="MIK OCP",
            is_low_rise=False
        )

        assert rec is not None
        assert rec["carpet_area"] == Decimal("68.0")
        assert rec["built_up_area"] == Decimal("75.0")
        assert rec["apartment_type_name"] == "2PN"
        assert rec["base_direction_name"] == "ĐB"
