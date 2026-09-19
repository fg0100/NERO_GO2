FROM ros:noetic-ros-base-focal

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-noetic-slam-gmapping \
    && rm -rf /var/lib/apt/lists/*

COPY gmapping.launch /opt/pickerbot/gmapping.launch
COPY start-slam.sh /usr/local/bin/start-slam
RUN chmod +x /usr/local/bin/start-slam

ENTRYPOINT ["/usr/local/bin/start-slam"]
