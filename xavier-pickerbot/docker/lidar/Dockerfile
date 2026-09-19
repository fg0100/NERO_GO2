FROM ros:noetic-ros-base-focal

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap0.8 \
    ros-noetic-diagnostic-updater \
    && rm -rf /var/lib/apt/lists/*

COPY bin/lslidar_driver_node /opt/pickerbot/bin/lslidar_driver_node
COPY lib/ /opt/pickerbot/lib/
COPY start-lidar.sh /usr/local/bin/start-lidar
RUN chmod +x /opt/pickerbot/bin/lslidar_driver_node /usr/local/bin/start-lidar

ENV LD_LIBRARY_PATH=/opt/pickerbot/lib:/opt/ros/noetic/lib
ENTRYPOINT ["/usr/local/bin/start-lidar"]
