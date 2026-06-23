#!/usr/bin/env python3
"""
engel_algilama_node.py
======================
BUMBLEBEE Takımı — robotaksi_planning paketi

Görev:
    /scan (LaserScan) topic'ini dinler.
    Aracın ön yayını (±FOV_DERECE) tarayarak en yakın engeli bulur.
    İki topic yayınlar:
        /engel_durumu   → std_msgs/Bool   (True = engel var, dur)
        /engel_mesafe   → std_msgs/Float32 (metre, engel yoksa inf)

waypoint_controller.py entegrasyonu:
    Controller /engel_durumu'nu subscribe eder.
    True gelince mevcut waypoint'te bekler, False gelince devam eder.

Bağımsız test:
    RViz'den veya aşağıdaki komutla sahte LaserScan atarak test edilebilir:
    ros2 topic pub /scan sensor_msgs/msg/LaserScan \
        "{header: {frame_id: 'base_link'}, \
          angle_min: -3.14, angle_max: 3.14, \
          angle_increment: 0.01, range_min: 0.1, range_max: 30.0, \
          ranges: [5.0, 5.0, ..., 1.0, ..., 5.0]}"
"""

import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, Float32


# ── Parametreler ──────────────────────────────────────────────────────────────
GUVENLI_MESAFE_M   = 2.5   # Bu mesafenin altındaki engel "tehlikeli" sayılır
UYARI_MESAFE_M     = 4.0   # Bu mesafede "yavaşla" sinyali gönderilir (ileride)
FOV_DERECE         = 30.0  # Ön yarıçap: 0° ± 30° (toplam 60° koni)
INF_ESIGI          = 29.9  # range_max'a yakın değerler "ölçüm yok" sayılır
FILTRE_PENCERESI   = 5     # Gürültü filtresi: son N ölçümün ortalaması
# ─────────────────────────────────────────────────────────────────────────────


class EngelAlgilamaNode(Node):
    """
    LaserScan verilerinden ön engel tespiti yapar.

    Yayınlanan topic'ler
    --------------------
    /engel_durumu  : Bool   — True  → engel var, dur/bekle
                             False → yol açık, devam et
    /engel_mesafe  : Float32 — En yakın ön engelin metre cinsinden mesafesi
    /uyari_durumu  : Bool   — True  → UYARI bölgesinde engel var, yavaşla
    """

    def __init__(self):
        super().__init__('engel_algilama_node')

        # ── Parametreleri ROS parametresi olarak da al (launch'tan override edilebilir)
        self.declare_parameter('guvenli_mesafe', GUVENLI_MESAFE_M)
        self.declare_parameter('uyari_mesafe',   UYARI_MESAFE_M)
        self.declare_parameter('fov_derece',     FOV_DERECE)
        self.declare_parameter('filtre_penceresi', FILTRE_PENCERESI)

        self.guvenli_mesafe  = self.get_parameter('guvenli_mesafe').value
        self.uyari_mesafe    = self.get_parameter('uyari_mesafe').value
        self.fov_rad         = math.radians(self.get_parameter('fov_derece').value)
        self.filtre_penceresi = int(self.get_parameter('filtre_penceresi').value)

        # Geçmiş ölçümler için buffer (medyan filtresi)
        self._mesafe_buffer: list[float] = []

        # ── QoS: Sensor verisi için Best-Effort yeterli
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=10
        )

        # ── Subscriber
        self._scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self._scan_callback,
            sensor_qos
        )

        # ── Publisher'lar
        self._engel_pub   = self.create_publisher(Bool,   '/engel_durumu', 10)
        self._mesafe_pub  = self.create_publisher(Float32, '/engel_mesafe', 10)
        self._uyari_pub   = self.create_publisher(Bool,   '/uyari_durumu', 10)

        self.get_logger().info(
            f'EngelAlgilamaNode başlatıldı | '
            f'Güvenli mesafe: {self.guvenli_mesafe}m | '
            f'Uyarı mesafesi: {self.uyari_mesafe}m | '
            f'FOV: ±{math.degrees(self.fov_rad):.0f}°'
        )

    # ── Yardımcı: indeks aralığını hesapla ──────────────────────────────────
    def _on_indeks_araligini_hesapla(
        self, scan: LaserScan
    ) -> tuple[int, int]:
        """
        LaserScan açı bilgisine göre ön FOV'a karşılık gelen
        dizin aralığını döndürür.

        LaserScan açıları genellikle -π'den +π'ye doğru artar.
        0 rad → düz ön.
        """
        toplam_ray = len(scan.ranges)
        if toplam_ray == 0:
            return 0, 0

        # 0 rad'ın dizin karşılığı
        sifir_indeks = int(
            (0.0 - scan.angle_min) / scan.angle_increment
        )

        # FOV yarıçapına karşılık gelen dizin adımı
        fov_adim = int(self.fov_rad / scan.angle_increment)

        bas = max(0, sifir_indeks - fov_adim)
        son = min(toplam_ray - 1, sifir_indeks + fov_adim)
        return bas, son

    # ── Ana callback ─────────────────────────────────────────────────────────
    def _scan_callback(self, scan: LaserScan) -> None:
        bas, son = self._on_indeks_araligini_hesapla(scan)

        if bas >= son:
            self.get_logger().warn('LaserScan boş veya geçersiz.', throttle_duration_sec=5)
            return

        # Ön koni içindeki geçerli mesafeleri filtrele
        on_mesafeler = [
            r for r in scan.ranges[bas:son + 1]
            if scan.range_min < r < INF_ESIGI
        ]

        # Geçerli ölçüm yoksa yolu açık say
        if not on_mesafeler:
            en_yakin = float('inf')
        else:
            en_yakin = min(on_mesafeler)

        # ── Medyan filtresi: ani spike'ları bastır ──────────────────────────
        self._mesafe_buffer.append(en_yakin)
        if len(self._mesafe_buffer) > self.filtre_penceresi:
            self._mesafe_buffer.pop(0)

        filtrelenmis = sorted(self._mesafe_buffer)[len(self._mesafe_buffer) // 2]

        # ── Karar ───────────────────────────────────────────────────────────
        engel_var  = filtrelenmis < self.guvenli_mesafe
        uyari_var  = filtrelenmis < self.uyari_mesafe

        # ── Yayın ────────────────────────────────────────────────────────────
        engel_msg          = Bool()
        engel_msg.data     = engel_var
        self._engel_pub.publish(engel_msg)

        mesafe_msg         = Float32()
        mesafe_msg.data    = float(filtrelenmis)
        self._mesafe_pub.publish(mesafe_msg)

        uyari_msg          = Bool()
        uyari_msg.data     = uyari_var
        self._uyari_pub.publish(uyari_msg)

        # ── Log ─────────────────────────────────────────────────────────────
        if engel_var:
            self.get_logger().warn(
                f'🚨 ENGEL: {filtrelenmis:.2f}m — DURDURMA sinyali gönderildi',
                throttle_duration_sec=1
            )
        elif uyari_var:
            self.get_logger().info(
                f'⚠️  UYARI: {filtrelenmis:.2f}m — yavaşlama önerilir',
                throttle_duration_sec=2
            )
        else:
            self.get_logger().debug(f'✅ Yol açık — en yakın: {filtrelenmis:.2f}m')


# ── Entry point ───────────────────────────────────────────────────────────────
def main(args=None):
    rclpy.init(args=args)
    node = EngelAlgilamaNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
