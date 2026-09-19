FROM ros:noetic-ros-base-focal

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-noetic-usb-cam \
    ros-noetic-web-video-server \
    && rm -rf /var/lib/apt/lists/*

COPY start-c70.sh /usr/local/bin/start-c70
COPY start-web-video.sh /usr/local/bin/start-web-video
RUN chmod +x /usr/local/bin/start-c70 /usr/local/bin/start-web-video

ENTRYPOINT ["/usr/local/bin/start-c70"]
