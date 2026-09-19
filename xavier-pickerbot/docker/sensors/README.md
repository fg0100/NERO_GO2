# C70 kamera és helyi videófolyam

Ez a Docker-kép a robot meglévő ROS masteréhez csatlakozik. Nem indít új mastert, alvázdrivert vagy LiDAR-t. A `start-c70.sh` a `/dev/RgbCam` eszközről publikál a `/usb_cam/image_raw` témára. A `start-web-video.sh` a 8080-as porton szolgálja ki a képet, de csak a robot `127.0.0.1` címén. Mindkét indító legfeljebb 60 másodpercig vár a ROS master `/run_id` paraméterére.

Az image-et **a roboton** építsd, mert a Jetson ARM64-es. A mappa három futtatáshoz szükséges fájlját (`Dockerfile`, `start-c70.sh`, `start-web-video.sh`) másold a robot `/home/wheeltec/pickerbot-c70-build-20260919/` mappájába, majd:

```bash
sudo docker build -t pickerbot/c70:noetic-20260919 /home/wheeltec/pickerbot-c70-build-20260919
```

2026-09-19-én a két alábbi konténer már létrejött. Csak akkor futtasd újra a parancsokat, ha a konténerek nem léteznek; előbb ellenőrizd a `sudo docker ps -a` kimenetét. A `/dev/video0` megfelel a robot `/dev/RgbCam` szimbolikus linkjének.

```bash
sudo docker run -d --restart unless-stopped --name pickerbot-c70 --network host \
  --device /dev/video0:/dev/RgbCam \
  -e ROS_MASTER_URI=http://192.168.123.50:11311 -e ROS_IP=192.168.123.50 \
  pickerbot/c70:noetic-20260919

sudo docker run -d --restart unless-stopped --name pickerbot-web-video --network host \
  -e ROS_MASTER_URI=http://192.168.123.50:11311 -e ROS_IP=192.168.123.50 \
  --entrypoint /usr/local/bin/start-web-video pickerbot/c70:noetic-20260919
```

Ellenőrzés a roboton: `rostopic hz /usb_cam/image_raw`, `ss -ltn | grep :8080`. A portnak csak `127.0.0.1:8080` címen szabad figyelnie. A laptopon a `scripts/start-demo-view.ps1` indítja a helyi irányítópultot és az SSH-alagutat; a `scripts/stop-demo-view.ps1` csak ezeket a helyi segédfolyamatokat állítja le. A robot konténereinek leállításához:

```bash
sudo docker stop pickerbot-web-video pickerbot-c70
sudo docker rm pickerbot-web-video pickerbot-c70
```

A gyári ROS-fájlok és a három meglévő systemd-szolgáltatás nem változtak. A Docker-indítás reboot utáni működését még külön próbával kell igazolni.
