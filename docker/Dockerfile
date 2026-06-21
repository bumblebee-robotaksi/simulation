FROM osrf/ros:foxy-desktop

# Gazebo classic 11 + ROS2 Foxy integration packages
RUN apt-get update && apt-get install -y \
    ros-foxy-gazebo-ros-pkgs \
    ros-foxy-gazebo-ros2-control \
    ros-foxy-xacro \
    ros-foxy-robot-state-publisher \
    ros-foxy-teleop-twist-keyboard \
    ros-foxy-robot-localization \
    python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /robotaksi_ws
SHELL ["/bin/bash", "-c"]
RUN echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc && \
    echo "if [ -f /robotaksi_ws/install/setup.bash ]; then source /robotaksi_ws/install/setup.bash; fi" >> ~/.bashrc && \
    echo "export PS1='\[\033[1;32m\](robotaksi)\[\033[0m\] \w \$ '" >> ~/.bashrc

CMD ["bash"]