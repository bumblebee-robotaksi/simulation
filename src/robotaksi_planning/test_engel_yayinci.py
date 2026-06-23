#!/usr/bin/env python3
"""
test_engel_yayinci.py
=====================
BUMBLEBEE Takımı — Bağımsız test aracı

Gerçek Gazebo veya RViz olmadan engel_algilama_node'u test etmek için
sahte (mock) LaserScan mesajları yayınlar.

Kullanım:
    Terminal 1: ros2 run robotaksi_planning engel_algilama_node
    Terminal 2: ros2 run robotaksi_planning test_engel_yayinci
    Terminal 3: ros2 topic echo /engel_durumu
                ros2 topic echo /engel_mesafe

Test senaryoları (3'er saniyelik aşamalar):
    Faz 1: Yol tamamen açık (tüm ray'lar 10m)
    Faz 2: UYARI bölgesi  (ön engel 3.5m)
    Faz 3: DURDURMA       (ön engel 1.5m — güvenli mesafe altı)
    Faz 4: Engel geçti    (yol tekrar açık)
    → Döngü başa döner
"""

import math
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Header
from builtin_interfaces.msg import Time as RosTime


class TestEngelYayinci(Node):

    # Test senaryosu: (açıklama, ön_mesafe, süre_sn)
    SENARYOLAR = [
        ('YOL AÇIK   — tüm raylar 10m',   10.0, 3.0),
        ('UYARI      — ön engel 3.5m',      3.5, 3.0),
        ('DURDURMA   — ön engel 1.5m',      1.5, 4.0),
        ('ENGEL GECİ — yol tekrar açık',   10.0, 3.0),
    ]

    RAY_SAYISI    = 360          # 360 ray, 1° aralıklı
    RANGE_MAX_M   = 30.0
    RANGE_MIN_M   = 0.1
    FOV_ON_DEG    = 30           # engelli ray'ların açı yarıçapı

    def __init__(self):
        super().__init__('test_engel_yayinci')

        self._scan_pub = self.create_publisher(LaserScan, '/scan', 10)
        self._senaryo_idx   = 0
        self._senaryo_baslangic = time.time()
        self._timer = self.create_timer(0.1, self._yayinla)  # 10 Hz

        self.get_logger().info('🧪 Test LaserScan yayıncısı başlatıldı')
        self._log_senaryo()

    def _log_senaryo(self) -> None:
        aciklama, mesafe, sure = self.SENARYOLAR[self._senaryo_idx]
        self.get_logger().info(
            f'[Senaryo {self._senaryo_idx + 1}/{len(self.SENARYOLAR)}] '
            f'{aciklama} ({sure:.0f}s)'
        )

    def _yayinla(self) -> None:
        # Senaryo geçişi
        _, _, sure = self.SENARYOLAR[self._senaryo_idx]
        if time.time() - self._senaryo_baslangic >= sure:
            self._senaryo_idx = (self._senaryo_idx + 1) % len(self.SENARYOLAR)
            self._senaryo_baslangic = time.time()
            self._log_senaryo()

        _, on_mesafe, _ = self.SENARYOLAR[self._senaryo_idx]

        # LaserScan oluştur
        msg                  = LaserScan()
        msg.header.frame_id  = 'base_link'
        msg.header.stamp     = self.get_clock().now().to_msg()
        msg.angle_min        = -math.pi
        msg.angle_max        =  math.pi
        msg.angle_increment  = 2 * math.pi / self.RAY_SAYISI
        msg.range_min        = self.RANGE_MIN_M
        msg.range_max        = self.RANGE_MAX_M
        msg.time_increment   = 0.0
        msg.scan_time        = 0.1

        # Varsayılan: tüm raylar açık
        ranges = [self.RANGE_MAX_M - 0.1] * self.RAY_SAYISI

        # Ön koni içine engel yerleştir
        #   0° = angle_min + N * angle_increment → index = N/2 ≈ 180
        merkez_idx = self.RAY_SAYISI // 2  # 0 rad karşılığı
        fov_adim   = int(
            math.radians(self.FOV_ON_DEG) / msg.angle_increment
        )
        for i in range(merkez_idx - fov_adim, merkez_idx + fov_adim + 1):
            if 0 <= i < self.RAY_SAYISI:
                ranges[i] = on_mesafe

        msg.ranges = ranges
        self._scan_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TestEngelYayinci()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
