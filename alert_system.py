"""
Module: alert_system.py
Phụ trách: Lộc (Thành viên 3 - Chuyên viên Cảnh báo & Xử lý Ngoại lệ)
Chủ đề 36: Mô phỏng cảm biến nhiệt độ/độ ẩm & cảnh báo ngưỡng (Kho nông sản)
"""

from datetime import datetime
from enum import Enum
import copy
import math
from typing import Dict, Any, Optional


# ==============================================================================
# 1. ĐỊNH NGHĨA MỨC ĐỘ CẢNH BÁO
# ==============================================================================
class AlertLevel(Enum):
    NORMAL = "Bình thường"
    WARNING = "Cảnh báo nhẹ"
    CRITICAL = "Cảnh báo nghiêm trọng"


# ==============================================================================
# 2. CÁC LỚP NGOẠI LỆ TÙY CHỈNH (CUSTOM EXCEPTIONS)
# ==============================================================================
class SensorError(Exception):
    """Lớp ngoại lệ cơ sở cho mọi lỗi liên quan đến cảm biến."""
    pass


class SensorDisconnectError(SensorError):
    """Ngoại lệ xảy ra khi cảm biến mất kết nối (trả về None hoặc mất tín hiệu)."""
    pass


class OutOfRangeDataError(SensorError):
    """Ngoại lệ xảy ra khi cảm biến trả về dữ liệu nhiễu phi vật lý (vd: -999°C)."""
    pass


# ==============================================================================
# 3. CẤU HÌNH BỘ NGƯỠNG AN TOÀN CHO 3 KHU VỰC KHO NÔNG SẢN
# ==============================================================================
DEFAULT_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "A": {
        "name": "Kho lạnh trái cây",
        "temp_min": 2.0,
        "temp_max": 8.0,
        "hum_min": 85.0,
        "hum_max": 95.0,
        # Độ lệch vượt ngưỡng để nâng từ Cảnh báo nhẹ -> Nghiêm trọng
        "temp_critical_delta": 3.0,   # < -1°C hoặc > 11°C -> Nghiêm trọng
        "hum_critical_delta": 10.0,   # < 75% hoặc > 100% -> Nghiêm trọng
    },
    "B": {
        "name": "Kho hạt khô",
        "temp_min": 18.0,
        "temp_max": 25.0,
        "hum_min": None,
        "hum_max": 60.0,
        "hum_max_inclusive": False,
        "temp_critical_delta": 3.0,
        "hum_critical_delta": 10.0,
    },
    "C": {
        "name": "Phòng tủ điện / Máy chủ",
        "temp_min": None,
        "temp_max": 30.0,
        "temp_max_inclusive": False,
        "hum_min": 40.0,
        "hum_max": 60.0,
        "temp_critical_delta": 3.0,
        "hum_critical_delta": 10.0,
    },
}


# ==============================================================================
# 4. LỚP HỆ THỐNG ĐÁNH GIÁ CẢNH BÁO & XỬ LÝ NGOẠI LỆ
# ==============================================================================
class AlertSystem:
    """
    Lớp chịu trách nhiệm kiểm tra tính hợp lệ của dữ liệu cảm biến,
    bắt các ngoại lệ lỗi phần cứng/nhiễu và phân loại mức độ cảnh báo.
    """

    # Giới hạn vật lý hợp lệ của cảm biến
    PHYSICAL_TEMP_MIN = -50.0
    PHYSICAL_TEMP_MAX = 100.0
    PHYSICAL_HUM_MIN = 0.0
    PHYSICAL_HUM_MAX = 100.0

    def __init__(self, thresholds: Optional[Dict[str, Dict[str, Any]]] = None):
        source = DEFAULT_THRESHOLDS if thresholds is None else thresholds
        self.thresholds = copy.deepcopy(source)

    def validate_reading(self, temperature: Any, humidity: Any) -> None:
        """
        Kiểm tra tính hợp lệ của dữ liệu đọc từ cảm biến.
        Ném ra ngoại lệ tùy chỉnh nếu phát hiện mất kết nối hoặc dữ liệu nhiễu.
        """
        # 1. Kiểm tra mất kết nối (giá trị None)
        if temperature is None or humidity is None:
            raise SensorDisconnectError(
                "Cảm biến mất kết nối (giá trị đọc được là None)."
            )

        # 2. Kiểm tra sai kiểu dữ liệu (không phải số)
        if (
            isinstance(temperature, bool)
            or isinstance(humidity, bool)
            or not isinstance(temperature, (int, float))
            or not isinstance(humidity, (int, float))
        ):
            raise OutOfRangeDataError(
                f"Dữ liệu sai định dạng: temp={temperature!r}, hum={humidity!r}."
            )

        # 3. Kiểm tra dữ liệu nhiễu phi vật lý (vd: -999°C, độ ẩm âm hoặc > 100%)
        if not math.isfinite(temperature) or not (
            self.PHYSICAL_TEMP_MIN <= temperature <= self.PHYSICAL_TEMP_MAX
        ):
            raise OutOfRangeDataError(
                f"Nhiệt độ nhiễu ngoài phạm vi vật lý ({temperature}°C)."
            )

        if not math.isfinite(humidity) or not (
            self.PHYSICAL_HUM_MIN <= humidity <= self.PHYSICAL_HUM_MAX
        ):
            raise OutOfRangeDataError(
                f"Độ ẩm nhiễu ngoài phạm vi vật lý ({humidity}%)."
            )

    def _classify_metric(
        self,
        value: float,
        min_val: Optional[float],
        max_val: Optional[float],
        critical_delta: float,
        unit: str,
        label: str,
        min_inclusive: bool = True,
        max_inclusive: bool = True,
    ):
        """Hàm nội bộ đánh giá 1 chỉ số (nhiệt độ hoặc độ ẩm)."""
        if min_val is not None and (
            value < min_val or (value == min_val and not min_inclusive)
        ):
            diff = min_val - value
            level = AlertLevel.CRITICAL if diff >= critical_delta else AlertLevel.WARNING
            msg = f"{label} thấp ({value}{unit} < {min_val}{unit}, lệch {diff:.1f}{unit})"
            return level, msg

        if max_val is not None and (
            value > max_val or (value == max_val and not max_inclusive)
        ):
            diff = value - max_val
            level = AlertLevel.CRITICAL if diff >= critical_delta else AlertLevel.WARNING
            msg = f"{label} cao ({value}{unit} > {max_val}{unit}, lệch {diff:.1f}{unit})"
            return level, msg

        return AlertLevel.NORMAL, None

    @staticmethod
    def _normalize_location(location: str) -> str:
        aliases = {"Khu A": "A", "Khu B": "B", "Khu C": "C"}
        return aliases.get(location, location)

    def evaluate_metrics(
        self, location: str, temperature: Any, humidity: Any
    ) -> tuple[AlertLevel, list[str]]:
        """Tra muc cao nhat va danh sach metric vi pham co cau truc."""
        location_id = self._normalize_location(location)
        if location_id not in self.thresholds:
            raise KeyError(f"Khu vực '{location}' chưa được cấu hình ngưỡng.")
        self.validate_reading(temperature, humidity)
        cfg = self.thresholds[location_id]
        temperature_level, _ = self._classify_metric(
            temperature,
            cfg.get("temp_min"),
            cfg.get("temp_max"),
            cfg["temp_critical_delta"],
            "°C",
            "Nhiệt độ",
            cfg.get("temp_min_inclusive", True),
            cfg.get("temp_max_inclusive", True),
        )
        humidity_level, _ = self._classify_metric(
            humidity,
            cfg.get("hum_min"),
            cfg.get("hum_max"),
            cfg["hum_critical_delta"],
            "%",
            "Độ ẩm",
            cfg.get("hum_min_inclusive", True),
            cfg.get("hum_max_inclusive", True),
        )
        metrics = []
        if temperature_level != AlertLevel.NORMAL:
            metrics.append("temperature")
        if humidity_level != AlertLevel.NORMAL:
            metrics.append("humidity")
        priority = {AlertLevel.NORMAL: 0, AlertLevel.WARNING: 1, AlertLevel.CRITICAL: 2}
        final_level = (
            temperature_level
            if priority[temperature_level] >= priority[humidity_level]
            else humidity_level
        )
        return final_level, metrics

    def evaluate(
        self,
        sensor_id: str,
        location: str,
        temperature: Any,
        humidity: Any,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Đánh giá một bản ghi cảm biến và trả về dictionary chuẩn hóa
        để truyền cho module Thống kê/Log (Lương) và Giao diện (Thục).
        """
        ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # Bước 1: Kiểm tra khu vực có trong cấu hình hay không
            location_id = self._normalize_location(location)
            if location_id not in self.thresholds:
                raise KeyError(f"Khu vực '{location}' chưa được cấu hình ngưỡng.")

            # Bước 2: Kiểm tra hợp lệ dữ liệu (có thể ném SensorDisconnectError / OutOfRangeDataError)
            self.validate_reading(temperature, humidity)

            cfg = self.thresholds[location_id]
            reasons = []
            final_level = AlertLevel.NORMAL

            # Bước 3: Đánh giá Nhiệt độ
            t_level, t_msg = self._classify_metric(
                temperature,
                cfg.get("temp_min"),
                cfg.get("temp_max"),
                cfg["temp_critical_delta"],
                "°C",
                "Nhiệt độ",
                cfg.get("temp_min_inclusive", True),
                cfg.get("temp_max_inclusive", True),
            )
            if t_msg:
                reasons.append(t_msg)

            # Bước 4: Đánh giá Độ ẩm
            h_level, h_msg = self._classify_metric(
                humidity,
                cfg.get("hum_min"),
                cfg.get("hum_max"),
                cfg["hum_critical_delta"],
                "%",
                "Độ ẩm",
                cfg.get("hum_min_inclusive", True),
                cfg.get("hum_max_inclusive", True),
            )
            if h_msg:
                reasons.append(h_msg)

            # Bước 5: Chọn mức cảnh báo cao nhất giữa Nhiệt độ và Độ ẩm
            priority = {AlertLevel.NORMAL: 0, AlertLevel.WARNING: 1, AlertLevel.CRITICAL: 2}
            final_level = t_level if priority[t_level] >= priority[h_level] else h_level

            return {
                "timestamp": ts,
                "sensor_id": sensor_id,
                "location": location_id,
                "location_name": cfg["name"],
                "temperature": temperature,
                "humidity": humidity,
                "status": "OK",
                "error_type": None,
                "alert_level": final_level.value,
                "message": "; ".join(reasons) if reasons else "Thông số trong ngưỡng an toàn",
            }

        except SensorDisconnectError as e:
            return {
                "timestamp": ts,
                "sensor_id": sensor_id,
                "location": location,
                "location_name": self.thresholds.get(self._normalize_location(location), {}).get("name", "Không xác định"),
                "temperature": temperature,
                "humidity": humidity,
                "status": "ERROR",
                "error_type": "SensorDisconnectError",
                "alert_level": AlertLevel.CRITICAL.value,
                "message": f"[LỖI MẤT KẾT NỐI] {e}",
            }

        except OutOfRangeDataError as e:
            return {
                "timestamp": ts,
                "sensor_id": sensor_id,
                "location": location,
                "location_name": self.thresholds.get(self._normalize_location(location), {}).get("name", "Không xác định"),
                "temperature": temperature,
                "humidity": humidity,
                "status": "ERROR",
                "error_type": "OutOfRangeDataError",
                "alert_level": AlertLevel.CRITICAL.value,
                "message": f"[LỖI DỮ LIỆU NHIỄU] {e}",
            }

        except Exception as e:
            return {
                "timestamp": ts,
                "sensor_id": sensor_id,
                "location": location,
                "location_name": self.thresholds.get(self._normalize_location(location), {}).get("name", "Không xác định"),
                "temperature": temperature,
                "humidity": humidity,
                "status": "ERROR",
                "error_type": type(e).__name__,
                "alert_level": AlertLevel.CRITICAL.value,
                "message": f"[LỖI HỆ THỐNG] {e}",
            }


# ==============================================================================
# 5. CHẠY KIỂM THỬ ĐỘC LẬP (UNIT TEST CÁC KỊCH BẢN)
# ==============================================================================
if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    alert_system = AlertSystem()

    test_cases = [
        # (Mô tả, sensor_id, location, temp, hum)
        ("1. Khu A - Bình thường", "S-A01", "Khu A", 5.0, 90.0),
        ("2. Khu A - Cảnh báo nhẹ (nhiệt hơi cao)", "S-A01", "Khu A", 9.5, 88.0),
        ("3. Khu A - Nghiêm trọng (hỏng điều hòa)", "S-A01", "Khu A", 14.0, 70.0),
        ("4. Khu B - Cảnh báo nhẹ (độ ẩm vượt nhẹ)", "S-B01", "Khu B", 22.0, 65.0),
        ("5. Khu C - Nghiêm trọng (quá nhiệt máy chủ)", "S-C01", "Khu C", 38.0, 50.0),
        ("6. Ngoại lệ - Mất kết nối (None)", "S-A02", "Khu A", None, 85.0),
        ("7. Ngoại lệ - Dữ liệu nhiễu (-999°C)", "S-B02", "Khu B", -999.0, 55.0),
        ("8. Ngoại lệ - Độ ẩm phi vật lý (150%)", "S-C02", "Khu C", 26.0, 150.0),
        ("9. Ngoại lệ - Khu vực không tồn tại", "S-X99", "Khu D", 25.0, 50.0),
    ]

    print("=" * 90)
    print("KẾT QUẢ KIỂM THỬ MODULE CẢNH BÁO & XỬ LÝ NGOẠI LỆ (LỘC - TV3)")
    print("=" * 90)
    for desc, sid, loc, t, h in test_cases:
        res = alert_system.evaluate(sid, loc, t, h)
        print(f"{desc}")
        print(f"  -> Trạng thái: {res['status']} | Mức độ: {res['alert_level']}")
        print(f"  -> Chi tiết  : {res['message']}")
        print("-" * 90)
