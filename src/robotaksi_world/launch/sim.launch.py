import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node
from launch.substitutions import Command
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    world_pkg = get_package_share_directory('robotaksi_world')
    desc_pkg = get_package_share_directory('robotaksi_description')

    world_file = os.path.join(world_pkg, 'worlds', 'pist.world')
    xacro_file = os.path.join(desc_pkg, 'urdf', 'bee1.urdf.xacro')

    # ParameterValue(value_type=str) prevents yaml parsing the XML
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]),
        value_type=str
    )

    return LaunchDescription([

        ExecuteProcess(
            cmd=['gazebo', '--verbose', world_file,
                 '-s', 'libgazebo_ros_init.so',
                 '-s', 'libgazebo_ros_factory.so'],
            output='screen'
        ),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}]
        ),

        TimerAction(
            period=5.0,
            actions=[
                Node(
                    package='gazebo_ros',
                    executable='spawn_entity.py',
                    arguments=[
                        '-topic', 'robot_description',
                        '-entity', 'bee1',
                        '-x', '2.0', '-y', '0.0', '-z', '0.5', '-Y', '0.0'
                    ],
                    output='screen'
                ),
            ]
        ),
    ])