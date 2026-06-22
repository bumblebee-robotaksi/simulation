#!/usr/bin/env python3
"""
waypoint_controller.py

Basit bir P-kontrolcu ile sabit (hardcoded) waypoint listesine dogru araci
suren node. /odom'dan anlik konum ve yonelimi okur, hedefe gore /cmd_vel
yayinlar. Son waypoint'e ulasinca aracı durdurur (park yerine gec).

Bu, KTR'deki "planning_node + control_node" mimarisinin basitlestirilmis bir
stand-in'idir. Gercek A*/TEB rota planlama ve Stanley/PID kontrolculeri
yerine; tek dosyada P-kontrolcu kullanilmistir. Gelecek calisma olarak KTR'de
tanimlanan tam mimariye gecis planlanmaktadir.
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry, Path


class WaypointController(Node):

    def __init__(self):
        super().__init__('waypoint_controller')

        # ===== Yeni Sabit Waypoint Listesi (pist.world topolojisiyle uyumlu) =====
        # (x, y) - metre, dunya/odom cercevesinde centerline takipli rota.
        self.waypoints = [
            (5.00, 23.975),    # 1. Gorev Noktasi (Yolcu Alma / Yesil Kutu)
            (12.04, 23.975),   # Kolon 1 & Satir 12 Kesisimi (Gecis Noktasi)
            (20.72, 23.975),   # Kolon 2 & Satir 12 Kesisimi (Gorev 2 oncesi kesisim)
            (20.72, 25.50),    # 2. Gorev Noktasi (Gorev Kutusu - hafif kuzeyde)
            (20.72, 23.975),   # Kolon 2 kesisimine geri donus
            (30.065, 23.975),  # Kolon 3 & Satir 12 Kesisimi (B4_TALL engelinden kacis baslangici)
            (30.065, 12.425),  # Kolon 3 uzerinden alt yola inis (Gecis Waypoint'i)
            (39.50, 12.425),   # Alt yol uzerinden sag tarafa ilerleme (Park hiza noktasi)
            (39.50, 24.745),   # park_giris_noktasi (Park Alani Giris Noktasi)
            (40.60, 24.70)     # park_slot_3 (Girisle tam hizalanmis nihai park cebi)
        ]
        self.current_wp_idx = 0

        # ===== Fallback Güvenlik Bayrakları =====
        self.external_plan_locked = False
        self.plan_sub = self.create_subscription(
            Path, '/planlanan_rota', self.external_plan_callback, 10
        )

        # ===== Kontrol parametreleri =====
        self.hedef_tolerans = 0.5       # metre, waypoint'e "ulasildi" sayilma esigi
        self.max_linear_hiz = 1.0       # m/s
        self.max_angular_hiz = 1.0      # rad/s
        self.aci_kazanci = 1.5          # P-kontrolcu kazanci (heading error -> angular vel)
        self.durma_aci_esigi = 1.2      # rad, bu acidan fazla hatada once sadece don, ilerleme

        # ===== Durum =====
        self.gorev_tamamlandi = False
        self.guncel_x = 0.0
        self.guncel_y = 0.0
        self.guncel_yaw = 0.0

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10
        )

        # Kontrol dongusu: 10 Hz
        self.timer = self.create_timer(0.1, self.kontrol_dongusu)

        self.get_logger().info(
            f'Waypoint controller baslatildi. {len(self.waypoints)} waypoint yuklendi.'
        )

    def external_plan_callback(self, msg: Path):
        # Eğer A* planı daha önce başarıyla alındıysa, yeni gelenleri reddet (Sonsuz döngü koruması)
        if self.external_plan_locked or len(msg.poses) == 0:
            return

        yeni_liste = []
        for p in msg.poses:
            yeni_liste.append((p.pose.position.x, p.pose.position.y))

        self.waypoints = yeni_liste
        self.current_wp_idx = 0
        self.gorev_tamamlandi = False
        self.external_plan_locked = True
        
        self.get_logger().info(
            f"*** DIŞ ROTA ALGILANDI! Hardcoded liste devre dışı. "
            f"A* algoritmasının ürettiği {len(self.waypoints)} hedefe kilitlenildi. ***"
        )

    def odom_callback(self, msg: Odometry):
        self.guncel_x = msg.pose.pose.position.x
        self.guncel_y = msg.pose.pose.position.y

        # Quaternion -> yaw (basit donusum, sadece Z ekseni donusu onemli)
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.guncel_yaw = math.atan2(siny_cosp, cosy_cosp)

    def kontrol_dongusu(self):
        if self.gorev_tamamlandi:
            self.yayinla_dur()
            return

        if self.current_wp_idx >= len(self.waypoints):
            self.gorev_tamamlandi = True
            self.get_logger().info('Tum waypointlere ulasildi. Park modu (durduruluyor).')
            self.yayinla_dur()
            return

        hedef_x, hedef_y = self.waypoints[self.current_wp_idx]

        dx = hedef_x - self.guncel_x
        dy = hedef_y - self.guncel_y
        mesafe = math.sqrt(dx * dx + dy * dy)

        # Waypoint'e ulasildi mi kontrolu
        if mesafe < self.hedef_tolerans:
            self.get_logger().info(
                f'Waypoint {self.current_wp_idx} ulasildi '
                f'({hedef_x:.1f}, {hedef_y:.1f}). Sirada bir sonraki.'
            )
            self.current_wp_idx += 1
            return

        # Hedefe olan aci ile guncel yonelim arasindaki fark (heading error)
        hedef_aci = math.atan2(dy, dx)
        aci_hata = hedef_aci - self.guncel_yaw

        # Aciyi [-pi, pi] araligina normallestir
        aci_hata = math.atan2(math.sin(aci_hata), math.cos(aci_hata))

        cmd = Twist()

        if abs(aci_hata) > self.durma_aci_esigi:
            # Cok buyuk aci hatasi varsa: once sadece don, ileri gitme
            cmd.linear.x = 0.0
            cmd.angular.z = self.clamp(
                self.aci_kazanci * aci_hata, -self.max_angular_hiz, self.max_angular_hiz
            )
        else:
            # Aci kabul edilebilir seviyedeyse: ilerle + aci duzelt
            # Mesafeye gore hiz olcekle (yaklasinca yavasla)
            hiz_olcek = min(mesafe / 2.0, 1.0)
            cmd.linear.x = self.max_linear_hiz * hiz_olcek
            cmd.angular.z = self.clamp(
                self.aci_kazanci * aci_hata, -self.max_angular_hiz, self.max_angular_hiz
            )

        self.cmd_pub.publish(cmd)

    def yayinla_dur(self):
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.cmd_pub.publish(cmd)

    @staticmethod
    def clamp(deger, min_deger, max_deger):
        return max(min_deger, min(deger, max_deger))


def main(args=None):
    rclpy.init(args=args)
    node = WaypointController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        node.get_logger().info('Waypoint controller kapatildi.')
        rclpy.shutdown()


if __name__ == '__main__':
    main()