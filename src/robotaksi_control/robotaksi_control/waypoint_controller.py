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
from std_msgs.msg import Bool


class WaypointController(Node):

    def __init__(self):
        super().__init__('waypoint_controller')

        self.estop_start_time = None
        self.ESTOP_TIMEOUT = 2.0  # seconds before we override and nudge forward

        # ===== Yeni Sabit Waypoint Listesi (pist.world topolojisiyle uyumlu) =====
        # (x, y) - metre, dunya/odom cercevesinde centerline takipli rota.
        self.waypoints = [
            (10.0,  0.0),   # ilk ara nokta
            (18.0,  0.0),   # engel oncesi yaklasma
            (20.0,  2.0),   # sola don — engelden once (SAFE: 2.0 < 2.97)
            (30.0,  2.0),   # engeli tamamen gec
            (35.0,  0.0),   # merkeze geri don
            (50.0,  0.0),   # hedef
        ]
        self.current_wp_idx = 0
        self.skip_initial_waypoints = True

        # ===== Fallback Güvenlik Bayrakları =====
        self.external_plan_locked = False
        self.plan_sub = self.create_subscription(
            Path, '/planlanan_rota', self.external_plan_callback, 10
        )

        # ===== Kontrol parametreleri =====
        self.hedef_tolerans = 0.5       # metre, waypoint'e "ulasildi" sayilma esigi
        self.max_linear_hiz = 1.0       # m/s
        self.max_angular_hiz = 1.0      # rad/s
        self.aci_kazanci = 1.0          # P-kontrolcu kazanci (heading error -> angular vel)
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

        self.pedestrian_detected = False
        self.lidar_emergency = False
        self.estop_start_time = None

        self.ped_sub = self.create_subscription(
            Bool, '/pedestrian_detected', self.ped_callback, 10
        )
        self.lidar_stop_sub = self.create_subscription(
            Bool, '/lidar_emergency_stop', self.lidar_stop_callback, 10
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
        
        if len(msg.poses) < 3:
            self.get_logger().warn("Tek noktalı plan reddedildi, hardcoded liste kullanılıyor.")
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

    def ped_callback(self, msg: Bool):
        prev = self.pedestrian_detected
        self.pedestrian_detected = msg.data
        if prev and not self.pedestrian_detected:
            self.estop_start_time = None

    def lidar_stop_callback(self, msg: Bool):
        prev = self.lidar_emergency
        self.lidar_emergency = msg.data
        # Engel kalktığında timer'ı sıfırla
        if prev and not self.lidar_emergency:
            self.estop_start_time = None

    def kontrol_dongusu(self):

        if self.skip_initial_waypoints and self.guncel_x != 0.0:
            while self.current_wp_idx < len(self.waypoints):
                hx, hy = self.waypoints[self.current_wp_idx]
                dx = hx - self.guncel_x
                dy = hy - self.guncel_y
                if math.sqrt(dx*dx + dy*dy) > self.hedef_tolerans:
                    break
                self.current_wp_idx += 1
            self.skip_initial_waypoints = False

        if self.pedestrian_detected or self.lidar_emergency:
            now = self.get_clock().now().nanoseconds / 1e9
            if self.estop_start_time is None:
                self.estop_start_time = now

            elapsed = now - self.estop_start_time

            if elapsed > self.ESTOP_TIMEOUT:
                # Nudge blindly yerine: bir sonraki waypoint'e dogru don ve ilerle
                if self.current_wp_idx < len(self.waypoints):
                    hedef_x, hedef_y = self.waypoints[self.current_wp_idx]
                    dx = hedef_x - self.guncel_x
                    dy = hedef_y - self.guncel_y
                    hedef_aci = math.atan2(dy, dx)
                    aci_hata = math.atan2(
                        math.sin(hedef_aci - self.guncel_yaw),
                        math.cos(hedef_aci - self.guncel_yaw)
                    )
                    cmd = Twist()
                    cmd.linear.x = 0.3
                    cmd.angular.z = self.clamp(
                        self.aci_kazanci * aci_hata,
                        -self.max_angular_hiz, self.max_angular_hiz
                    )
                    self.cmd_pub.publish(cmd)
                else:
                    self.yayinla_dur()
            else:
                self.yayinla_dur()
            return
        
        self.estop_start_time = None

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