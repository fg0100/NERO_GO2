#!/usr/bin/env bash
set -euo pipefail
source /opt/ros/noetic/setup.bash
: "${ROS_MASTER_URI:?Set ROS_MASTER_URI to the running robot master}"
: "${ROS_IP:?Set ROS_IP to the robot address}"
for attempt in {1..60}; do
  if rosparam get /run_id >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
rosparam get /run_id >/dev/null
exec rosrun usb_cam usb_cam_node \
  _video_device:=/dev/RgbCam \
  _image_width:=640 \
  _image_height:=480 \
  _pixel_format:=yuyv \
  _camera_frame_id:=c70_cam \
  _io_method:=mmap
