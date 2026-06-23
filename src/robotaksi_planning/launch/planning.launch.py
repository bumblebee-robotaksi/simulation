"""
planning.launch.py
==================
BUMBLEBEE Takımı — robotaksi_planning paketi

Başlatılan node'lar:
    1. engel_algilama_node  — /scan → /engel_durumu, /engel_mesafe, /uyari_durumu
    2. waypoint_controller  — /odom + /engel_durumu → /cmd_vel

Kullanım:
    ros2 launch robotaksi_planning planning.launch.py

Parametreler (komut satırından override edilebilir):
    guvenli_mesafe:=2.5
    uyari_mesafe:=4.0
    fov_derece:=30.0
    max_hiz:=0.8

Örnek:
    ros2 launch robotaksi_planning planning.launch.py guvenli_mesafe:=1.5 max_hiz:=0.5
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    # ── Argüman tanımlamaları
    guvenli_mesafe_arg = DeclareLaunchArgument(
        'guvenli_mesafe', default_value='2.5',
        description='Durdurma eşiği (metre)'
    )
    uyari_mesafe_arg = DeclareLaunchArgument(
        'uyari_mesafe', default_value='4.0',
        description='Yavaşlama uyarısı eşiği (metre)'
    )
    fov_derece_arg = DeclareLaunchArgument(
        'fov_derece', default_value='30.0',
        description='Ön tarama açısı yarıçapı (derece)'
    )
    max_hiz_arg = DeclareLaunchArgument(
        'max_hiz', default_value='0.8',
        description='Maksimum seyir hızı (m/s)'
    )
    uyari_hiz_arg = DeclareLaunchArgument(
        'uyari_hiz', default_value='0.4',
        description='Uyarı bölgesi hızı (m/s)'
    )

    # ── Node tanımlamaları
    engel_algilama_node = Node(
        package='robotaksi_planning',
        executable='engel_algilama_node',
        name='engel_algilama_node',
        output='screen',
        parameters=[{
            'guvenli_mesafe':   LaunchConfiguration('guvenli_mesafe'),
            'uyari_mesafe':     LaunchConfiguration('uyari_mesafe'),
            'fov_derece':       LaunchConfiguration('fov_derece'),
            'filtre_penceresi': 5,
        }]
    )

    waypoint_controller_node = Node(
        package='robotaksi_planning',
        executable='waypoint_controller',
        name='waypoint_controller',
        output='screen',
        parameters=[{
            'max_hiz':          LaunchConfiguration('max_hiz'),
            'uyari_hiz':        LaunchConfiguration('uyari_hiz'),
            'yaklasma_mesafe':  0.5,
            'gorev_bekle_sn':   2.0,
        }]
    )

    return LaunchDescription([
        guvenli_mesafe_arg,
        uyari_mesafe_arg,
        fov_derece_arg,
        max_hiz_arg,
        uyari_hiz_arg,
        engel_algilama_node,
        waypoint_controller_node,
    ])
