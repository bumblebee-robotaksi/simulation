import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Int32

class CanBridgeStub(Node):
    def __init__(self):
        super().__init__('can_bridge_stub')

        #--Parametreler
        self.declare_parameter('max_linear_vel', 3.0)
        self.declare_parameter('max_angular_vel', 1.5)

        self.max_linear_vel=self.get_parameter('max_linear_vel').get_parameter_value().double_value
        self.max_angular_vel=self.get_parameter('max_angular_vel').get_parameter_value().double_value

        #--Subscription
        self.subscription=self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)

        #--Publishers
        self.steering_pub=self.create_publisher(Int32, '/beemobs/AUTONOMOUS_SteeringMot_Control', 10)
        self.throttle_pub=self.create_publisher(Int32, '/beemobs/RC_THRT_DATA',10)
        self.brake_pub=self.create_publisher(Int32,'/beemobs/AUTONOMOUS_Brake_Control',10)

    def cmd_vel_callback(self,msg):
        linear_x=msg.linear.x
        angular_z=msg.angular.z

        if linear_x<0:
            throttle_pwm=50
        else:
            throttle_pwm=int(50 + (linear_x / self.max_linear_vel) * (250 - 50))
            throttle_pwm=max(50, min(throttle_pwm, 250))

        steering_center=127
        steering_range=127
        steering_pwm=int(steering_center + (angular_z / self.max_angular_vel) * steering_range)
        steering_pwm=max(0,min(steering_pwm,255))

        if linear_x==0.0:
            brake_value=100
        else:
            brake_value=0
        
        #--Verileri yayınlama

        throttle_msg=Int32()
        throttle_msg.data=throttle_pwm
        self.throttle_pub.publish(throttle_msg)

        steering_msg=Int32()
        steering_msg.data=steering_pwm
        self.steering_pub.publish(steering_msg)

        brake_msg=Int32()
        brake_msg.data=brake_value
        self.brake_pub.publish(brake_msg)

def main(args=None):
    rclpy.init(args=args)
    node=CanBridgeStub()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
