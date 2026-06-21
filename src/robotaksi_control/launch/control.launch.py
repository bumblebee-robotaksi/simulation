from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robotaksi_control',
            executable='waypoint_controller',
            name='waypoint_controller',
            output='screen',
        ),
    ])