cmake_minimum_required(VERSION 3.5)
project(robotaksi_world)

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(gazebo_ros REQUIRED)

# launch/ ve worlds/ klasorlerini install dizinine kopyala
# (colcon build sonrasi bu dosyalar share/robotaksi_world/ altinda bulunur)
install(DIRECTORY
  launch
  worlds
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()