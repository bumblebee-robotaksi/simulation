cmake_minimum_required(VERSION 3.5)
project(robotaksi_description)

find_package(ament_cmake REQUIRED)
find_package(urdf REQUIRED)
find_package(xacro REQUIRED)

# urdf/ klasorunu install dizinine kopyala
install(DIRECTORY
  urdf
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()