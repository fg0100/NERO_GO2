#!/usr/bin/env bash
set -euo pipefail
source /opt/ros/noetic/setup.bash
export LD_LIBRARY_PATH="/opt/pickerbot/lib:${LD_LIBRARY_PATH:-}"
: "${ROS_MASTER_URI:?Set ROS_MASTER_URI to the running robot master}"
: "${ROS_IP:?Set ROS_IP to the robot address}"
for attempt in {1..60}; do
  if rosparam get /run_id >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
rosparam get /run_id >/dev/null
exec /opt/pickerbot/bin/lslidar_driver_node \
  __name:=lslidar_driver_node \
  _lidar_name:=M10_P \
  _serial_port:=/dev/wheeltec_lidar \
  _interface_selection:=serial \
  _frame_id:=laser \
  _scan_topic:=scan \
  _truncated_mode:=1 \
  '_disable_min:=[110]' \
  '_disable_max:=[250]' \
  _min_range:=0.15 \
  _max_range:=100.0 \
  _pubScan:=true \
  _pubPointCloud2:=false
