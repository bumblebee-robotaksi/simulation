"""
test_engel.launch.py
====================
Gazebo/RViz olmadan engel algılama sistemini bağımsız test eder.

Başlatılan node'lar:
    1. test_engel_yayinci   — Sahte LaserScan mesajları yayınlar
    2. engel_algilama_node  — Scan'i işleyip karar topic'leri üretir

Kullanım:
    ros2 launch robotaksi_planning test_engel.launch.py

Çıktıyı izlemek için:
    ros2 topic echo /engel_durumu
    ros2 topic echo /engel_mesafe
    ros2 topic echo /uyari_durumu
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    test_yayinci = Node(
        package='robotaksi_planning',
        executable='test_engel_yayinci',
        name='test_engel_yayinci',
        output='screen',
    )

    engel_algilama = Node(
        package='robotaksi_planning',
        executable='engel_algilama_node',
        name='engel_algilama_node',
        output='screen',
        parameters=[{
            'guvenli_mesafe':    2.5,
            'uyari_mesafe':      4.0,
            'fov_derece':       30.0,
            'filtre_penceresi':    5,
        }]
    )

    return LaunchDescription([
        test_yayinci,
        engel_algilama,
    ])
