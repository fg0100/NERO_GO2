# M10P LiDAR Dockerben

Az image a roboton már meglévő, Noetichez fordított gyári LiDAR-binárist csomagolja be. Nem fordítja újra és nem módosítja a gyári forrást. A buildkontextus a roboton `/home/wheeltec/pickerbot-lidar-build-20260919/`; az itt lévő `Dockerfile` és `start-lidar.sh` mellett az alábbi állományok szükségesek a gyári `~/wheeltec_robot/devel/lib/` mappából:

| Buildkontextus | 2026-09-19-i SHA-256 |
|---|---|
| `bin/lslidar_driver_node` | `198dd585225f92285847e1c6ac94868787cdc69e82890d97d3ef58a59477380c` |
| `lib/liblslidar_driver.so` | `9b8ff6112eda6199530231edd7514ead4ad0cb9213200fc80e560af049487eb5` |
| `lib/liblslidar_input.so` | `9829d8873cb6d94b076ea910027597d410ae6bb6371919bbddb6d37f19bdf932` |
| `lib/liblslidar_serial.so` | `904994c923d1bee0fad23cd4be11a4b592be5295f34bfff6ff963cb7ed1dc2fb` |

Az indító ugyanazt az `M10_P`, `/dev/wheeltec_lidar`, `laser` és `/scan` beállítást használja, mint a gyári `lslidar_serial.launch`; a 110–250 fokos takarást is átveszi. Nem indít ROS mastert vagy alvázvezérlést. A soros eszköz a `0001` sorozatszámú `/dev/ttyCH343USB0`; az alváz a külön `0002` portot használja.

```bash
sudo docker build -t pickerbot/lidar:noetic-20260919 /home/wheeltec/pickerbot-lidar-build-20260919
sudo docker run -d --restart unless-stopped --name pickerbot-lidar --network host \
  --device /dev/wheeltec_lidar:/dev/wheeltec_lidar \
  -e ROS_MASTER_URI=http://192.168.123.50:11311 -e ROS_IP=192.168.123.50 \
  pickerbot/lidar:noetic-20260919
```

2026-09-19-én a konténer már létrejött; ne indíts másodikat. Ellenőrzés: `rostopic info /scan`, `rostopic hz /scan` és `rosrun tf tf_echo odom_combined laser`. A próbán a `/scan` kb. 12 Hz-cel futott, a TF-útvonal működött. Leállítás és visszavonás: `sudo docker stop pickerbot-lidar`, majd `sudo docker rm pickerbot-lidar`. A reboot utáni eszközhozzárendelést még igazolni kell.
