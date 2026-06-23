import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
from launch.substitutions import Command
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    world_pkg = get_package_share_directory('robotaksi_world')
    desc_pkg = get_package_share_directory('robotaksi_description')

    world_file = os.path.join(world_pkg, 'worlds', 'pist.world')
    xacro_file = os.path.join(desc_pkg, 'urdf', 'bee1.urdf.xacro')

    robot_description = Command(['xacro ', xacro_file])

    return LaunchDescription([

        # Gazebo'yu pist.world ile baslat
        ExecuteProcess(
            cmd=['gazebo', '--verbose', world_file,
                 '-s', 'libgazebo_ros_init.so',
                 '-s', 'libgazebo_ros_factory.so'],
            output='screen'
        ),

        # URDF'i robot_description parametresi olarak yayinla (TF agaci icin gerekli)
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}]
        ),

        # Araci Gazebo'ya spawn et
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=['-topic', 'robot_description',
           '-entity', 'bee1',
           '-x', '2.0', '-y', '0.0', '-z', '0.3',
           '-Y', '0.0'],  # facing +X
            # arguments=['-topic', 'robot_description',
            #            '-entity', 'bee1',
            #            '-x', '5.0', '-y', '23.975', '-z', '0.1'],
            output='screen'
        ),
    ])