# Gmapping külön Docker-konténerben

Ez az image csak a `slam_gmapping` node-ot indítja. A [gmapping.launch](gmapping.launch) a gyári `algorithm_gmapping.launch` fő paramétereit használja: `base_footprint`, `odom_combined`, 5 cm-es rács, 8 részecske és `/scan` bemenet. A gyári `mapping.launch` az alvázat is újraindítaná, ezért azt a futó bringup mellett ne használd. A buildkontextus a roboton `/home/wheeltec/pickerbot-slam-build-20260919/`.

```bash
sudo docker build -t pickerbot/slam:noetic-20260919 /home/wheeltec/pickerbot-slam-build-20260919
sudo docker run -d --restart unless-stopped --name pickerbot-slam --network host \
  -e ROS_MASTER_URI=http://192.168.123.50:11311 -e ROS_IP=192.168.123.50 \
  pickerbot/slam:noetic-20260919
```

2026-09-19-én a konténer már létrejött; ne indíts másodikat. A sikeres próbán a `/map` témának volt publikálója, 384×384 cellás, 0,05 m felbontású térképet adott. Egy üzenet 4559 szabad és 412 foglalt cellát tartalmazott; nyolc másodperc alatt öt eltérő tartalmú üzenet érkezett álló robot mellett. Mozgás közbeni térképépítést és reboot utáni automatikus indulást még nem igazoltunk.

Ellenőrzés: `rostopic info /map`, `rostopic echo -n 1 /map/info`, `sudo docker logs --tail 50 pickerbot-slam`. Leállítás és visszavonás: `sudo docker stop pickerbot-slam`, majd `sudo docker rm pickerbot-slam`.
