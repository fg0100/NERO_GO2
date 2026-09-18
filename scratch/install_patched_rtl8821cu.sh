#!/bin/bash
set -e

echo "=== 1. Preparing patched driver directory ==="
cd /home/unitree/rtl8821cu_clean || exit 1

# Unload module if loaded
sudo modprobe -r 8821cu 2>/dev/null || true

# Clean previous build artifacts
make clean 2>/dev/null || true
rm -f 8821cu.ko

echo "=== 2. Building rtl8821cu driver (CONFIG_POWER_SAVING=n) ==="
make -j$(nproc)

echo "=== 3. Installing driver module & configuration ==="
sudo make install
if [ -f 8821cu.conf ]; then
    sudo cp -f 8821cu.conf /etc/modprobe.d/8821cu.conf
fi

echo "=== 4. Loading 8821cu module without power saving ==="
sudo modprobe 8821cu rtw_power_mgnt=0 rtw_led_ctrl=1

echo "=== 5. Verifying wlan0 interface ==="
sleep 2
sudo rfkill unblock wifi 2>/dev/null || true
ip link show wlan0

echo "=== 6. Connecting to NERO_GO2_WIFI Hotspot ==="
sudo nmcli dev wifi rescan 2>/dev/null || true
sleep 2
sudo nmcli dev wifi connect 'NERO_GO2_WIFI' password 'NeumannRobot2026'

echo "=== 7. Active Wi-Fi IP address ==="
ip -4 addr show wlan0
