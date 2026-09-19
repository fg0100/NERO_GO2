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
exec rosrun web_video_server web_video_server _port:=8080 _address:=127.0.0.1
