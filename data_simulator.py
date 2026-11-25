"""
Module: data_simulator.py
Phụ trách: Lợi (Thành viên 2 - Chuyên viên Mô phỏng Dữ liệu)
Nâng cấp thuật toán:
1. Dynamic Mean-Reverting Random Walk (Ornstein-Uhlenbeck rời rạc): Tự thích nghi với mọi khu vực & ngưỡng bất kỳ.
2. Quán tính nhiệt (Momentum) & Tương quan vật lý Nhiệt độ - Độ ẩm.
3. Bộ lọc phản xạ EWMA & Phát hiện gai nhiễu (Z-Score) cho dữ liệu đầu vào động.
"""

import math
import random
from collections import deque
from typing import Dict, Tuple, Optional


class DataSimulator:
    """Bộ mô phỏng và xử lý phản xạ dữ liệu môi trường kho bảo quản nông sản."""

    # Cấu hình mặc định (có thể mở rộng động bằng hàm register_zone)
    DEFAULT_ZONES = {
        "Khu A": {"name": "Kho lạnh trái cây", "temp_range": (2.0, 8.0), "hum_range": (85.0, 95.0)},
        "Khu B": {"name": "Kho hạt khô", "temp_range": (18.0, 25.0), "hum_range": (40.0, 60.0)},
        "Khu C": {"name": "Phòng tủ điện/máy chủ", "temp_range": (20.0, 30.0), "hum_range": (40.0, 60.0)},
    }

    def __init__(self, mssv: str, inertia: float = 0.35, alpha_ewma: float = 0.7):
        """
        :param mssv: Mã số sinh viên làm hạt giống ngẫu nhiên tái lập.
        :param inertia: Hệ số quán tính vật lý [0.0 - 0.8] giúp đường nhiệt độ cong mượt tự nhiên.
        :param alpha_ewma: Hệ số phản xạ của bộ lọc làm mượt mũ (0 < alpha <= 1).
        """
        self.mssv = str(mssv).strip()
        self._rng = random.Random(self.mssv)
        self.inertia = max(0.0, min(0.8, inertia))
        self.alpha = max(0.1, min(1.0, alpha_ewma))

        self._zones: Dict[str, dict] = {}
        self._state: Dict[str, dict] = {}
        self._fault_active: Dict[str, bool] = {}
        self._history: Dict[str, deque] = {}

        # Đăng ký sẵn 3 khu vực mặc định của đề tài
        for zone_id, cfg in self.DEFAULT_ZONES.items():
            self.register_zone(zone_id, cfg["temp_range"], cfg["hum_range"], cfg["name"])

    def register_zone(
        self,
        zone_id: str,
        temp_range: Tuple[float, float],
        hum_range: Tuple[float, float],
        name: str = "",
    ) -> None:
        """
        Đăng ký động bất kỳ khu vực mới nào với dải ngưỡng (min, max) tùy ý.
        Thuật toán tự tính điểm cân bằng và biên độ dao động chuẩn theo quy tắc 3-Sigma.
        """
        t_min, t_max = temp_range
        h_min, h_max = hum_range
        t_mean = (t_min + t_max) / 2.0
        h_mean = (h_min + h_max) / 2.0

        self._zones[zone_id] = {
            "name": name or zone_id,
            "t_min": t_min,
            "t_max": t_max,
            "t_mean": t_mean,
            "t_sigma": max(0.15, (t_max - t_min) / 6.0),
            "h_min": h_min,
            "h_max": h_max,
            "h_mean": h_mean,
            "h_sigma": max(0.5, (h_max - h_min) / 6.0),
        }
        self._state[zone_id] = {
            "temp": t_mean,
            "humidity": h_mean,
            "vel_t": 0.0,  # Vận tốc biến thiên nhiệt độ (quán tính)
            "vel_h": 0.0,  # Vận tốc biến thiên độ ẩm
        }
        self._fault_active[zone_id] = False
        self._history[zone_id] = deque(maxlen=15)

    def trigger_ac_failure(self, zone_id: str, status: bool = True) -> None:
        """Bật/tắt sự cố hỏng điều hòa (tạo ngoại lực đẩy nhiệt độ vượt ngưỡng)."""
        if zone_id in self._fault_active:
            self._fault_active[zone_id] = status

    def reset_zone(self, zone_id: str) -> None:
        """Đưa khu vực về trạng thái cân bằng ban đầu."""
        if zone_id in self._zones:
            cfg = self._zones[zone_id]
            self._state[zone_id] = {
                "temp": cfg["t_mean"],
                "humidity": cfg["h_mean"],
                "vel_t": 0.0,
                "vel_h": 0.0,
            }
            self._fault_active[zone_id] = False
            self._history[zone_id].clear()

    def reflect_external_input(
        self, zone_id: str, raw_temp: Optional[float], raw_hum: Optional[float]
    ) -> Tuple[Optional[float], Optional[float], str]:
        """
        THUẬT TOÁN PHẢN XẠ DỮ LIỆU ĐẦU VÀO:
        Nhận bất kỳ cặp số liệu (nhiệt độ, độ ẩm) nào từ bên ngoài/cảm biến thực:
        - Tự phát hiện mất kết nối (None) hoặc nhiễu phần cứng cực đoan.
        - Tự phát hiện gai nhiễu đột biến (Z-score > 3.0) so với lịch sử gần nhất.
        - Cập nhật trạng thái nội tại để chuỗi mô phỏng tiếp nối mượt mà từ chính số liệu mới này.
        """
        if raw_temp is None or raw_hum is None:
            return None, None, "DISCONNECTED"

        if raw_temp <= -100.0 or raw_temp >= 150.0 or not (0.0 <= raw_hum <= 100.0):
            return raw_temp, raw_hum, "HARDWARE_NOISE"

        if zone_id not in self._zones:
            # Tự động tạo khu vực mới lấy chính giá trị đầu vào làm điểm cân bằng
            self.register_zone(zone_id, (raw_temp - 3.0, raw_temp + 3.0), (max(0, raw_hum - 10), min(100, raw_hum + 10)))

        hist = self._history[zone_id]
        status = "NORMAL_SYNCED"

        # Kiểm tra gai nhiễu thống kê (Z-score) nếu đã có ít nhất 5 mẫu lịch sử
        if len(hist) >= 5:
            temps = [x[0] for x in hist]
            mean_t = sum(temps) / len(temps)
            std_t = math.sqrt(sum((x - mean_t) ** 2 for x in temps) / len(temps)) + 1e-6
            if abs(raw_temp - mean_t) / std_t > 3.5:
                status = "SPIKE_DETECTED"

        # Đồng bộ hóa trạng thái nội tại theo dữ liệu vừa nhận (làm mượt EWMA)
        st = self._state[zone_id]
        smoothed_t = round(self.alpha * raw_temp + (1 - self.alpha) * st["temp"], 2)
        smoothed_h = round(self.alpha * raw_hum + (1 - self.alpha) * st["humidity"], 2)

        st["vel_t"] = smoothed_t - st["temp"]
        st["vel_h"] = smoothed_h - st["humidity"]
        st["temp"] = smoothed_t
        st["humidity"] = smoothed_h
        hist.append((smoothed_t, smoothed_h))

        return smoothed_t, smoothed_h, status

    def next_reading(
        self,
        zone_id: str,
        inject_noise_prob: float = 0.03,
        inject_disconnect_prob: float = 0.02,
        dynamic_bounds: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Sinh cặp dữ liệu tiếp theo bằng mô hình Ornstein-Uhlenbeck có quán tính & tương quan vật lý.
        Nếu zone_id chưa tồn tại, tự động khởi tạo theo dynamic_bounds (hoặc mặc định).
        """
        if zone_id not in self._zones:
            t_b, h_b = dynamic_bounds if dynamic_bounds else ((20.0, 26.0), (50.0, 70.0))
            self.register_zone(zone_id, t_b, h_b)

        # 1. Mô phỏng lỗi phần cứng để module của Lộc bắt ngoại lệ
        if self._rng.random() < inject_disconnect_prob:
            return None, None
        if self._rng.random() < inject_noise_prob:
            return -999.0, -999.0

        cfg = self._zones[zone_id]
        st = self._state[zone_id]

        # 2. Tính ngoại lực (lực kéo về cân bằng hoặc lực đẩy sự cố)
        if self._fault_active[zone_id]:
            # Hỏng điều hòa: lực đẩy nhiệt độ tăng theo tỷ lệ ngưỡng của chính khu vực đó
            drift_t = max(0.6, cfg["t_sigma"] * 1.4)
            noise_t = self._rng.gauss(0, cfg["t_sigma"] * 0.4)
            force_t = drift_t + noise_t
        else:
            # Hồi quy Ornstein-Uhlenbeck: càng xa điểm cân bằng, lực kéo về càng mạnh
            reversion_speed = 0.18
            force_t = reversion_speed * (cfg["t_mean"] - st["temp"]) + self._rng.gauss(0, cfg["t_sigma"] * 0.45)

        # 3. Áp dụng quán tính nhiệt (Momentum) giúp đồ thị cong mượt thay vì răng cưa
        delta_t = self.inertia * st["vel_t"] + (1 - self.inertia) * force_t

        # 4. Tương quan vật lý: nhiệt độ tăng làm độ ẩm tương đối có xu hướng giảm nhẹ (-0.45 * delta_t)
        thermal_coupling = -0.45 * delta_t
        force_h = 0.18 * (cfg["h_mean"] - st["humidity"]) + self._rng.gauss(0, cfg["h_sigma"] * 0.45) + thermal_coupling
        delta_h = self.inertia * st["vel_h"] + (1 - self.inertia) * force_h

        new_temp = round(st["temp"] + delta_t, 2)
        new_hum = round(max(0.0, min(100.0, st["humidity"] + delta_h)), 2)

        st["vel_t"] = delta_t
        st["vel_h"] = delta_h
        st["temp"] = new_temp
        st["humidity"] = new_hum
        self._history[zone_id].append((new_temp, new_hum))

        return new_temp, new_hum


if __name__ == "__main__":
    sim = DataSimulator(mssv="079207050455")  

    print("--- 1. TỰ THÍCH NGHI VỚI KHU VỰC MỚI CHƯA TỪNG KHAI BÁO ---")
    for i in range(1, 5):
        t, h = sim.next_reading("Kho D - Đông lạnh sâu", 0, 0, dynamic_bounds=((-22.0, -18.0), (75.0, 85.0)))
        print(f"Bước {i} | Kho D (-22°C..-18°C): Nhiệt độ = {t}°C, Độ ẩm = {h}%")

    print("\n--- 2. PHẢN XẠ KHI CÓ DỮ LIỆU ĐẦU VÀO BẤT NGỜ TỪ BÊN NGOÀI ---")
    # Giả sử cảm biến thật bên ngoài truyền vào mức nhiệt 14.5°C ở Khu A
    t_sync, h_sync, st = sim.reflect_external_input("Khu A", 14.5, 82.0)
    print(f"Nhận dữ liệu ngoài (14.5°C, 82%) -> Trạng thái: {st} | Đồng bộ: {t_sync}°C, {h_sync}%")
    # Các bước tiếp theo tự động hồi quy mượt từ 14.5°C về vùng an toàn 5°C của Khu A
    for i in range(1, 5):
        t, h = sim.next_reading("Khu A", 0, 0)
        print(f"Hồi quy bước {i} | Khu A: Nhiệt độ = {t}°C, Độ ẩm = {h}%")