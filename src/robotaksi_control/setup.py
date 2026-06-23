from setuptools import setup
import os
from glob import glob

package_name = 'robotaksi_control'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='bumblebee',
    maintainer_email='takim@example.com',
    description='Robotaksi waypoint controller ve CAN bridge stub',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'waypoint_controller = robotaksi_control.waypoint_controller:main',
            'can_bridge_stub = robotaksi_control.can_bridge_stub:main',
        ],
    },
)