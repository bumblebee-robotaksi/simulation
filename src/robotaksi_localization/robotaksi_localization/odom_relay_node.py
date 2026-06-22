
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import NavSatFix, Imu


class OdomRelayNode(Node):
    def __init__(self):
        super().__init__('odom_relay_node')

        self.pub = self.create_publisher(Odometry, '/robotaksi/odom', 10)

        # Oncelik 1: KISS-ICP LiDAR odometrisi
        self.create_subscription(
            Odometry,
            '/kiss_icp/odometry',
            lambda msg: self.odom_callback(msg, 'kiss_icp'),
            10
        )

        # Oncelik 2: ZED2 gorsel-inersiyal odometri
        self.create_subscription(
            Odometry,
            '/zed/odom',
            lambda msg: self.odom_callback(msg, 'zed_vio'),
            10
        )

        # GPS ve IMU sadece loglanir (gercek EKF gelince kullanilacak)
        self.create_subscription(NavSatFix, '/gps/fix',  self.gps_callback,  10)
        self.create_subscription(Imu,       '/imu/data', self.imu_callback,  10)

        self.last_source = None
        self.msg_count   = 0

        self.get_logger().info('OdomRelayNode baslatildi.')
        self.get_logger().info('  /kiss_icp/odometry → /robotaksi/odom  (oncelik 1)')
        self.get_logger().info('  /zed/odom          → /robotaksi/odom  (oncelik 2)')
        self.get_logger().info('  /gps/fix ve /imu/data izleniyor (log icin)')
        self.get_logger().info('  NOT: Gercek EKF yok — gelecek asama:')
        self.get_logger().info('       robot_localization + iki katmanli EKF fuzyonu')

    def odom_callback(self, msg: Odometry, source: str):
        msg.header.frame_id    = 'odom'
        msg.child_frame_id     = 'base_link'
        self.pub.publish(msg)

        # Her 50 mesajda bir log
        self.msg_count += 1
        if self.msg_count % 50 == 0 or self.last_source != source:
            x = msg.pose.pose.position.x
            y = msg.pose.pose.position.y
            self.get_logger().info(
                f'[{source}] → /robotaksi/odom  x={x:.2f} y={y:.2f}'
            )
            self.last_source = source

    def gps_callback(self, msg: NavSatFix):
        # Simdilik sadece log — EKF gelince navsat_transform'a baglanacak
        pass

    def imu_callback(self, msg: Imu):
        # Simdilik sadece log — EKF gelince lokal EKF'e baglanacak
        pass


def main(args=None):
    rclpy.init(args=args)
    node = OdomRelayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()